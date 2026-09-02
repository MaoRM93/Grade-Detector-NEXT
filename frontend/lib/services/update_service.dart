import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:package_info_plus/package_info_plus.dart';

import '../core/logger/app_logger.dart';

/// 检查更新结果
class UpdateCheckResult {
  /// 请求与解析是否成功
  final bool ok;

  /// 是否存在新版本
  final bool hasUpdate;

  /// 最新版本号（去除 tag 前缀 v）
  final String latestVersion;

  /// 更新说明（release body）
  final String releaseNotes;

  /// 失败原因
  final String? error;

  const UpdateCheckResult({
    required this.ok,
    this.hasUpdate = false,
    this.latestVersion = '',
    this.releaseNotes = '',
    this.error,
  });
}

/// 更新与全局禁用服务
///
/// - 检查更新：GitHub Releases API（收纯文本后手动 jsonDecode）
/// - 远程停用开关：最新正式 release tag 等于 [killSwitchVersion] 时禁用程序
/// - 防滥用检测：短时间高频查询触发禁用
class UpdateService {
  UpdateService._() {
    _checkDio = Dio(
      BaseOptions(
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 15),
        // 收纯文本后手动 jsonDecode，非 JSON 内容不会直接抛异常
        responseType: ResponseType.plain,
        validateStatus: (_) => true,
        // GitHub API 强制要求 User-Agent，缺失会被 403 拒绝
        headers: {
          'User-Agent': 'GradeMonitor-UpdateCheck',
          'Accept': 'application/vnd.github+json',
        },
      ),
    );
  }

  static final UpdateService _instance = UpdateService._();
  factory UpdateService() => _instance;

  // ---- 常量 ----

  /// GitHub 仓库地址
  static const String repoUrl =
      'https://github.com/MaoRM93/Grade-Detector-NEXT';

  /// 检查更新 API 地址（最新正式 release，不含 draft / pre-release）
  ///
  /// 注意：必须是 api.github.com 的 API 地址。
  /// 不能用 repoUrl/releases/latest 网页地址——那返回的是 HTML 页面，
  /// 会一直报"GitHub 返回了非 JSON 内容"。
  static const String _latestReleaseApi =
      'https://api.github.com/repos/MaoRM93/Grade-Detector-NEXT/releases/latest';

  /// 简洁展示版本号（手动维护）
  static const String shortVersion = '7.0.2';

  /// 远程停用开关：最新 release tag 等于此值时禁用程序
  static const String killSwitchVersion = '114.514';

  /// 全局禁用开关：为 true 时 main.dart 切换显示 DisabledScreen
  static final ValueNotifier<bool> disabled = ValueNotifier<bool>(false);

  /// 运行时完整版本号（如 107.0.0.115），未加载完成时为空字符串
  String currentVersion = '';

  final AppLogger _log = AppLogger('update_service');
  late final Dio _checkDio;

  // ---- 防滥用：60 秒滑动窗口内查询计数 ----
  static const int _abuseWindowMs = 60000;
  static const int _abuseThreshold = 40;
  final List<int> _queryTimestamps = [];
  bool _abuseTriggered = false;

  /// 初始化：读取完整版本号 + 静默检查远程停用开关（不弹任何 UI）
  Future<void> init() async {
    try {
      final info = await PackageInfo.fromPlatform();
      currentVersion = info.buildNumber.isEmpty
          ? info.version
          : '${info.version}.${info.buildNumber}';
      _log.info('当前完整版本: $currentVersion');
    } catch (e) {
      _log.warning('读取版本信息失败: $e');
    }

    // 静默检查：仅处理远程停用开关
    unawaited(checkForUpdate(silent: true));
  }

  /// 检查更新（GitHub Releases latest，不含 draft / pre-release）
  Future<UpdateCheckResult> checkForUpdate({bool silent = false}) async {
    try {
      final resp = await _checkDio.get(_latestReleaseApi);

      if (resp.statusCode == 404) {
        return const UpdateCheckResult(ok: false, error: '仓库暂未发布任何版本');
      }
      if (resp.statusCode != 200) {
        return UpdateCheckResult(ok: false, error: 'HTTP ${resp.statusCode}');
      }

      dynamic data;
      try {
        data = jsonDecode(resp.data.toString());
      } catch (_) {
        final body = resp.data?.toString() ?? '';
        final head = body.length > 120 ? body.substring(0, 120) : body;
        _log.error('GitHub 返回了非 JSON 内容: $head');
        return const UpdateCheckResult(ok: false, error: 'GitHub 返回了非 JSON 内容');
      }

      final tag = ((data['tag_name'] as String?) ?? '').trim();
      if (tag.isEmpty) {
        return const UpdateCheckResult(ok: false, error: '未获取到版本号');
      }

      // 远程停用开关命中
      if (tag == killSwitchVersion) {
        _log.warning('命中远程停用开关 (tag=$tag)，禁用程序');
        disabled.value = true;
        return UpdateCheckResult(ok: false, error: '当前版本已被停用');
      }

      final latest = tag.startsWith('v') ? tag.substring(1) : tag;
      final hasUpdate = _isNewer(latest, currentVersion);
      if (hasUpdate && !silent) {
        _log.info('发现新版本: $latest');
      }
      return UpdateCheckResult(
        ok: true,
        hasUpdate: hasUpdate,
        latestVersion: latest,
        releaseNotes: ((data['body'] as String?) ?? '').trim(),
      );
    } on DioException catch (e) {
      if (!silent) _log.warning('检查更新失败: ${e.message}');
      final networkError =
          e.type == DioExceptionType.connectionError ||
          e.type == DioExceptionType.connectionTimeout;
      return UpdateCheckResult(
        ok: false,
        error: networkError ? '网络连接失败' : (e.message ?? '网络错误'),
      );
    } catch (e) {
      if (!silent) _log.warning('检查更新异常: $e');
      return UpdateCheckResult(ok: false, error: e.toString());
    }
  }

  /// 上报一次成绩查询（供防滥用检测统计）
  void reportQuery() {
    if (disabled.value || _abuseTriggered) return;
    final now = DateTime.now().millisecondsSinceEpoch;
    _queryTimestamps.add(now);
    while (_queryTimestamps.isNotEmpty &&
        now - _queryTimestamps.first > _abuseWindowMs) {
      _queryTimestamps.removeAt(0);
    }
    if (_queryTimestamps.length > _abuseThreshold) {
      _abuseTriggered = true;
      _log.warning('防滥用检测命中：60 秒内 $_queryTimestamps 次查询，禁用程序');
      disabled.value = true;
    }
  }

  /// 用系统默认浏览器打开链接
  Future<void> openInBrowser([String? url]) async {
    final target = url ?? repoUrl;
    try {
      if (Platform.isWindows) {
        await Process.run('cmd', ['/c', 'start', '', target]);
      } else if (Platform.isMacOS) {
        await Process.run('open', [target]);
      } else {
        await Process.run('xdg-open', [target]);
      }
    } catch (e) {
      _log.warning('打开链接失败: $e');
    }
  }

  /// 逐段数值比较：latest 是否新于 current
  bool _isNewer(String latest, String current) {
    if (current.isEmpty || latest.isEmpty) return false;
    List<int> parse(String v) =>
        v.split(RegExp(r'[.\-+]')).map((p) => int.tryParse(p) ?? 0).toList();
    final a = parse(latest);
    final b = parse(current);
    final n = a.length > b.length ? a.length : b.length;
    for (int i = 0; i < n; i++) {
      final x = i < a.length ? a[i] : 0;
      final y = i < b.length ? b[i] : 0;
      if (x != y) return x > y;
    }
    return false;
  }
}

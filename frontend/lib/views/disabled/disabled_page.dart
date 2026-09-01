import 'dart:async';

import 'dart:io' show Process, exit;

import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:window_manager/window_manager.dart';

import '../../core/service/update_service.dart';

/// 全屏禁用页 — 检测到停用条件（开发者标记的停用版本 / 高频查询滥用）时接管整个应用页面
class DisabledScreen extends StatefulWidget {
  const DisabledScreen({super.key});

  @override
  State<DisabledScreen> createState() => _DisabledScreenState();
}

class _DisabledScreenState extends State<DisabledScreen> {
  /// 禁用页主色（R:174 G:11 B:42）
  static const Color _bgColor = Color(0xFFAE0B2A);

  static const List<String> _reasons = [
    '1. 违反有关主管单位的规定，由开发者主动停用。',
    '2. 您设置的请求次数过于频繁，对服务器造成负担过重。',
    '3. 当前版本已过期，需要检查并安装更新。',
    '4. 误触了仅开发者可使用的功能。',
    '5. 程序文件损坏或意外丢失。',
  ];

  /// 页面出现时刻（事件时间）
  final DateTime _errorTime = DateTime.now();

  String _appVersion = '';

  // 伪装后门：900ms 内连续点击三次“版本号”三个字回到主页（不退出程序）
  int _secretTaps = 0;
  Timer? _secretTapReset;
  late final TapGestureRecognizer _secretRecognizer = TapGestureRecognizer()
    ..onTap = _onSecretTap;
  late final TapGestureRecognizer _repoRecognizer = TapGestureRecognizer()
    ..onTap = () => Process.run('open', [UpdateService.repoUrl]);

  @override
  void initState() {
    super.initState();
    if (UpdateService().currentVersion.isEmpty) {
      UpdateService().loadCurrentVersion().then((_) {
        if (mounted) {
          setState(() => _appVersion = UpdateService().currentVersion);
        }
      });
    } else {
      _appVersion = UpdateService().currentVersion;
    }
  }

  @override
  void dispose() {
    _secretTapReset?.cancel();
    _secretRecognizer.dispose();
    _repoRecognizer.dispose();
    super.dispose();
  }

  void _onSecretTap() {
    _secretTaps++;
    _secretTapReset?.cancel();
    _secretTapReset = Timer(
      const Duration(milliseconds: 900),
      () => _secretTaps = 0,
    );
    if (_secretTaps < 3) return;
    _secretTaps = 0;
    _secretTapReset?.cancel();
    // 解除禁用状态（触发 main.dart 监听切回主页），程序本身继续运行
    if (UpdateService().disabled.value) {
      UpdateService().disabled.value = false;
    }
    if (mounted && Navigator.of(context).canPop()) {
      Navigator.of(context).pop();
    }
  }

  /// GMT+8 形式的时区标签
  String get _gmtLabel {
    final o = _errorTime.timeZoneOffset;
    final sign = o.isNegative ? '-' : '+';
    final m = o.inMinutes.abs() % 60;
    return 'GMT$sign${o.inHours.abs()}'
        '${m > 0 ? ':${m.toString().padLeft(2, '0')}' : ''}';
  }

  /// YYYY:MM:DD_HH:MM:SS
  String get _formattedTime {
    final t = _errorTime;
    String p(int v) => v.toString().padLeft(2, '0');
    return '${t.year.toString().padLeft(4, '0')}:'
        '${p(t.month)}:${p(t.day)}_${p(t.hour)}:${p(t.minute)}:${p(t.second)}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _bgColor,
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              // 内容块整体居中，文字左对齐（左侧留安全边界）
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 640),
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 48,
                      vertical: 40,
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Material 设计警告图标（圆角三角形 + 感叹号）
                        const Icon(
                          Icons.warning_amber_rounded,
                          size: 113,
                          color: Colors.white,
                        ),
                        const SizedBox(height: 32),
                        const Text(
                          '程序已禁用',
                          style: TextStyle(
                            fontSize: 40,
                            fontWeight: FontWeight.w900,
                            color: Colors.white,
                          ),
                        ),
                        const SizedBox(height: 18),
                        const Text(
                          '当前程序副本因为下述中的一个或几个原因已被停用。'
                          '您可以通过 Github 的 issue 功能提交反馈。',
                          style: TextStyle(
                            fontSize: 15,
                            height: 1.6,
                            color: Colors.white,
                          ),
                        ),
                        const SizedBox(height: 20),
                        ..._reasons.map(
                          (r) => Padding(
                            padding: const EdgeInsets.symmetric(vertical: 3),
                            child: Text(
                              r,
                              style: TextStyle(
                                fontSize: 14,
                                height: 1.6,
                                color: Colors.white.withValues(alpha: .92),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 44),
                        FilledButton(
                          style: FilledButton.styleFrom(
                            backgroundColor: Colors.white,
                            foregroundColor: _bgColor,
                            padding: const EdgeInsets.symmetric(
                              horizontal: 52,
                              vertical: 18,
                            ),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                          ),
                          onPressed: _forceExit,
                          child: const Text(
                            '好',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            // 页面最底部：版本号 / 事件时间 / 仓库地址（左对齐）
            Padding(
              padding: const EdgeInsets.fromLTRB(48, 0, 48, 18),
              child: Text.rich(
                TextSpan(
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.white.withValues(alpha: .75),
                  ),
                  children: [
                    // 伪装后门触发区：900ms 内连点三次“版本号”三个字回主页
                    TextSpan(text: '版本号', recognizer: _secretRecognizer),
                    TextSpan(
                      text: '：${_appVersion.isEmpty ? '…' : _appVersion}',
                    ),
                    TextSpan(text: '    事件时间：$_gmtLabel $_formattedTime'),
                    const TextSpan(text: '    '),
                    TextSpan(
                      text: 'Github',
                      style: const TextStyle(
                        color: Colors.white,
                        decoration: TextDecoration.underline,
                        decorationColor: Colors.white,
                      ),
                      recognizer: _repoRecognizer,
                    ),
                  ],
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// 强制退出应用
  Future<void> _forceExit() async {
    try {
      await windowManager.destroy();
    } catch (_) {}
    exit(0);
  }
}

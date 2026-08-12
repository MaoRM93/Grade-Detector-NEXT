/// 前端统一日志模块
///
/// - 输出到 /Applications/Projects/GradeDetector_4/logs/frontend.log
/// - 同时输出到 debugPrint (Flutter 控制台)
/// - 支持日志级别过滤
library;

import 'dart:io';
import 'package:flutter/foundation.dart';

/// 日志级别
enum LogLevel { debug, info, warning, error }

/// 获取日志目录（绝对路径）
String _getLogDir() {
  // 优先使用项目固定路径
  const projectPath = '/Applications/Projects/GradeDetector_4';
  final projectLogs = Directory('$projectPath/logs');
  if (projectLogs.existsSync()) {
    return projectLogs.path;
  }

  // 回退：尝试从可执行文件路径推导
  try {
    final exeDir = Directory(Platform.resolvedExecutable).parent;
    // 从 .app/Contents/MacOS/ 向上找
    var dir = exeDir;
    for (int i = 0; i < 6; i++) {
      final logsDir = Directory('${dir.path}/logs');
      if (logsDir.existsSync()) {
        return logsDir.path;
      }
      dir = dir.parent;
    }
  } catch (_) {}

  // 最终回退：~/Library/Application Support/GradeMonitor/logs
  final home = Platform.environment['HOME'] ?? '/tmp';
  return '$home/Library/Application Support/GradeMonitor/logs';
}

/// 前端日志记录器
class AppLogger {
  static AppLogger? _instance;

  final String _name;
  final IOSink? _sink;
  LogLevel _minLevel;

  AppLogger._(this._name, this._sink, this._minLevel);

  /// 初始化日志系统（应在 main() 中调用）
  static Future<void> init({LogLevel minLevel = LogLevel.info}) async {
    if (_instance != null) return;

    try {
      final logDirPath = _getLogDir();
      final logDir = Directory(logDirPath);
      if (!await logDir.exists()) {
        await logDir.create(recursive: true);
      }

      final logFile = File('$logDirPath/frontend.log');
      final sink = logFile.openWrite(mode: FileMode.append);

      _instance = AppLogger._('grademonitor', sink, minLevel);
      _instance!.info('=== GradeMonitor Frontend v3.0.0 启动 ===');
      _instance!.info('日志文件: ${logFile.absolute.path}');
    } catch (e) {
      debugPrint('[AppLogger] Failed to initialize file logging: $e');
      _instance = AppLogger._('grademonitor', null, minLevel);
      _instance!.info('=== GradeMonitor Frontend v3.0.0 启动 (仅控制台) ===');
    }
  }

  /// 获取指定模块的 logger
  factory AppLogger(String name) {
    if (_instance == null) {
      // 未初始化时创建仅控制台的 logger
      debugPrint('[AppLogger] Not initialized, using console-only logger');
      _instance = AppLogger._('grademonitor', null, LogLevel.debug);
    }
    return AppLogger._(name, _instance!._sink, _instance!._minLevel);
  }

  /// 释放资源
  static void dispose() {
    _instance?._sink?.close();
    _instance = null;
  }

  // ---------- 日志方法 ----------

  void debug(String message) {
    _log(LogLevel.debug, message);
  }

  void info(String message) {
    _log(LogLevel.info, message);
  }

  void warning(String message) {
    _log(LogLevel.warning, message);
  }

  void error(String message, [Object? error, StackTrace? stackTrace]) {
    final buffer = StringBuffer(message);
    if (error != null) {
      buffer.write(' | Error: $error');
    }
    if (stackTrace != null) {
      buffer.write('\n$stackTrace');
    }
    _log(LogLevel.error, buffer.toString());
  }

  void _log(LogLevel level, String message) {
    if (level.index < _minLevel.index) return;

    final timestamp = _now();
    final levelStr = level.name.toUpperCase().padRight(7);
    final line = '$timestamp | $levelStr | $_name | $message';

    // 控制台输出
    if (level == LogLevel.error) {
      debugPrint('\x1B[31m$line\x1B[0m'); // 红色
    } else if (level == LogLevel.warning) {
      debugPrint('\x1B[33m$line\x1B[0m'); // 黄色
    } else {
      debugPrint(line);
    }

    // 文件输出
    try {
      _sink?.writeln(line);
      _sink?.flush();
    } catch (_) {
      // 文件写入失败静默忽略
    }
  }

  String _now() {
    final now = DateTime.now();
    final ms = now.millisecond.toString().padLeft(3, '0');
    return '${_fmt(now.year)}-${_fmt(now.month)}-${_fmt(now.day)} '
        '${_fmt(now.hour)}:${_fmt(now.minute)}:${_fmt(now.second)}.$ms';
  }

  static String _fmt(int n) => n.toString().padLeft(2, '0');
}

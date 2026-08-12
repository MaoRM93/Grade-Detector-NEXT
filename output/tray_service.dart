import 'dart:io';
import 'package:flutter/services.dart';
import 'package:tray_manager/tray_manager.dart';
import 'package:window_manager/window_manager.dart';
import '../logger/app_logger.dart';
import 'backend_service.dart';

/// 系统托盘（菜单栏图标）服务
///
/// 提供托盘初始化、销毁、事件处理，供 main.dart 和设置页共用。
class TrayService {
  static final TrayService _instance = TrayService._();
  factory TrayService() => _instance;
  TrayService._();

  final _log = AppLogger('tray_svc');
  bool _initialized = false;

  /// 初始化系统托盘
  Future<void> init() async {
    if (_initialized) return;
    _initialized = true;

    try {
      await trayManager.setIcon('assets/tray_icon.png');
      await trayManager.setToolTip('GradeMonitor');

      final menu = Menu(
        items: [
          MenuItem(key: 'show', label: '开启主界面'),
          MenuItem(key: 'quit', label: '退出程序'),
        ],
      );
      await trayManager.setContextMenu(menu);

      try {
        trayManager.addListener(_TrayHandler(_log));
        _log.info('系统托盘事件监听已注册');
      } catch (e) {
        _log.warning('托盘事件监听注册失败（尝试备用方案）: $e');
        try {
          const channel = MethodChannel('tray_manager');
          channel.setMethodCallHandler((call) async {
            if (call.method == 'onTrayIconMouseDown') {
              await windowManager.show();
              await windowManager.focus();
            } else if (call.method == 'onTrayMenuItemClick') {
              final args = call.arguments as Map?;
              final key = args?['key'] as String?;
              if (key == 'show') {
                await windowManager.show();
                await windowManager.focus();
              } else if (key == 'quit') {
                await _quitApp();
              }
            }
          });
          _log.info('托盘事件通过 MethodChannel 注册成功');
        } catch (e2) {
          _log.warning('托盘事件备用方案也失败: $e2');
        }
      }

      _log.info('系统托盘已初始化（图标 + 右键菜单）');
    } catch (e) {
      _initialized = false;
      _log.warning('系统托盘初始化失败: $e');
    }
  }

  /// 销毁系统托盘
  Future<void> destroy() async {
    if (!_initialized) return;
    try {
      await trayManager.destroy();
    } catch (_) {}
    _initialized = false;
    _log.info('系统托盘已销毁');
  }

  bool get initialized => _initialized;

  Future<void> _quitApp() async {
    _log.info('退出程序');
    await BackendService().stop();
    await trayManager.destroy();
    exit(0);
  }
}

class _TrayHandler implements TrayListener {
  final AppLogger _log;
  _TrayHandler(this._log);

  @override
  void onTrayIconMouseDown() {
    windowManager.show();
    windowManager.focus();
    _log.info('托盘图标左键点击 -> 显示窗口');
  }

  @override
  void onTrayIconMouseUp() {}

  @override
  void onTrayIconRightMouseDown() {}

  @override
  void onTrayIconRightMouseUp() {}

  @override
  void onTrayMenuItemClick(MenuItem menuItem) {
    if (menuItem.key == 'show') {
      windowManager.show();
      windowManager.focus();
      _log.info('托盘菜单: 显示主窗口');
    } else if (menuItem.key == 'quit') {
      _log.info('退出程序');
      BackendService().stop();
      trayManager.destroy();
      exit(0);
    }
  }
}

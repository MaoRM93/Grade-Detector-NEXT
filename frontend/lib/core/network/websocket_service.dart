import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../constants/api_path.dart';
import '../logger/app_logger.dart';

/// WebSocket 事件类型
enum WsEventType {
  connected,
  gradesChanged,
  rankChanged,
  showNotification,
  unknown,
}

/// WebSocket 事件
class WsEvent {
  final WsEventType type;
  final Map<String, dynamic> data;

  const WsEvent({required this.type, required this.data});

  factory WsEvent.fromJson(Map<String, dynamic> json) {
    final typeStr = json['type'] as String? ?? '';
    WsEventType type;
    switch (typeStr) {
      case 'connected':
        type = WsEventType.connected;
      case 'grades_changed':
        type = WsEventType.gradesChanged;
      case 'rank_changed':
        type = WsEventType.rankChanged;
      case 'show_notification':
        type = WsEventType.showNotification;
      default:
        type = WsEventType.unknown;
    }
    return WsEvent(type: type, data: json);
  }
}

/// WebSocket 服务 - 实时事件推送
class WebSocketService {
  WebSocketChannel? _channel;
  final StreamController<WsEvent> _eventController =
      StreamController<WsEvent>.broadcast();

  Stream<WsEvent> get eventStream => _eventController.stream;

  bool _isConnected = false;
  bool get isConnected => _isConnected;

  Timer? _reconnectTimer;
  int _reconnectAttempts = 0;
  static const int _maxReconnectDelay = 30;

  final _log = AppLogger('websocket');

  /// 连接 WebSocket
  void connect() {
    if (_isConnected) return;
    _doConnect();
  }

  void _doConnect() {
    try {
      _channel = WebSocketChannel.connect(Uri.parse(ApiPath.wsUrl));
      _isConnected = true;
      _reconnectAttempts = 0;
      _log.info('WebSocket 已连接');

      _channel!.stream.listen(
        (data) {
          try {
            final json = jsonDecode(data as String) as Map<String, dynamic>;
            final event = WsEvent.fromJson(json);
            _log.debug('收到事件: ${event.type.name}');
            _eventController.add(event);
          } catch (e) {
            _log.error('解析 WebSocket 消息失败: $data', e);
          }
        },
        onError: (error) {
          _log.warning('WebSocket 错误: $error');
          _isConnected = false;
          _scheduleReconnect();
        },
        onDone: () {
          _log.warning('WebSocket 连接关闭');
          _isConnected = false;
          _scheduleReconnect();
        },
      );
    } catch (e) {
      _log.error('WebSocket 连接失败', e);
      _isConnected = false;
      _scheduleReconnect();
    }
  }

  void _scheduleReconnect() {
    _reconnectTimer?.cancel();
    final delay = (_reconnectAttempts < 5)
        ? _reconnectAttempts + 1
        : _maxReconnectDelay;
    _reconnectAttempts++;
    _log.info('WebSocket 将在 ${delay}s 后重连 (尝试 #$_reconnectAttempts)');
    _reconnectTimer = Timer(Duration(seconds: delay), _doConnect);
  }

  /// 断开 WebSocket
  void disconnect() {
    _log.info('WebSocket 主动断开');
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
    _channel?.sink.close();
    _channel = null;
    _isConnected = false;
  }

  /// 释放资源
  void dispose() {
    disconnect();
    _eventController.close();
  }
}

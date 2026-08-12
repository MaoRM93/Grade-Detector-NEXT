import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/network/api_client.dart';
import '../core/logger/app_logger.dart';
import '../core/network/websocket_service.dart';

/// API 客户端 Provider
final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());

/// WebSocket 服务 Provider
final webSocketProvider = Provider<WebSocketService>((ref) {
  final ws = WebSocketService();
  ref.onDispose(() => ws.dispose());
  return ws;
});

/// 监控状态数据模型
class MonitorStatus {
  final bool isRunning;
  final int totalQueries;
  final String? lastQueryAt;
  final bool autoMonitorEnabled;
  final bool rankMonitorEnabled;
  final int intervalSeconds;
  final String startTime;
  final String endTime;

  const MonitorStatus({
    this.isRunning = false,
    this.totalQueries = 0,
    this.lastQueryAt,
    this.autoMonitorEnabled = false,
    this.rankMonitorEnabled = false,
    this.intervalSeconds = 300,
    this.startTime = '08:00',
    this.endTime = '23:00',
  });

  factory MonitorStatus.fromJson(Map<String, dynamic> json) {
    return MonitorStatus(
      isRunning: json['is_running'] ?? false,
      totalQueries: json['total_queries'] ?? 0,
      lastQueryAt: json['last_query_at'],
      autoMonitorEnabled: json['auto_monitor_enabled'] ?? false,
      rankMonitorEnabled: json['rank_monitor_enabled'] ?? false,
      intervalSeconds: json['interval_seconds'] ?? 300,
      startTime: json['start_time'] ?? '08:00',
      endTime: json['end_time'] ?? '23:00',
    );
  }

  MonitorStatus copyWith({
    bool? isRunning,
    int? totalQueries,
    String? lastQueryAt,
    bool? autoMonitorEnabled,
    bool? rankMonitorEnabled,
    int? intervalSeconds,
    String? startTime,
    String? endTime,
  }) {
    return MonitorStatus(
      isRunning: isRunning ?? this.isRunning,
      totalQueries: totalQueries ?? this.totalQueries,
      lastQueryAt: lastQueryAt ?? this.lastQueryAt,
      autoMonitorEnabled: autoMonitorEnabled ?? this.autoMonitorEnabled,
      rankMonitorEnabled: rankMonitorEnabled ?? this.rankMonitorEnabled,
      intervalSeconds: intervalSeconds ?? this.intervalSeconds,
      startTime: startTime ?? this.startTime,
      endTime: endTime ?? this.endTime,
    );
  }
}

/// 监控状态 Provider
class MonitorNotifier extends StateNotifier<MonitorStatus> {
  final ApiClient _api;
  final _log = AppLogger('monitor');

  MonitorNotifier(this._api) : super(const MonitorStatus());

  Future<void> fetchStatus() async {
    try {
      final resp = await _api.getMonitorStatus();
      state = MonitorStatus.fromJson(resp.data as Map<String, dynamic>);
      _log.debug(
        '监控状态: running=${state.isRunning}, queries=${state.totalQueries}',
      );
    } catch (e) {
      _log.error('获取监控状态失败', e);
    }
  }

  Future<bool> startMonitor() async {
    try {
      await _api.startMonitor();
      state = state.copyWith(isRunning: true);
      _log.info('监控已启动');
      return true;
    } catch (e) {
      _log.error('启动监控失败', e);
      return false;
    }
  }

  Future<bool> stopMonitor() async {
    try {
      await _api.stopMonitor();
      state = state.copyWith(isRunning: false);
      _log.info('监控已停止');
      return true;
    } catch (e) {
      _log.error('停止监控失败', e);
      return false;
    }
  }

  Future<bool> restartMonitor() async {
    try {
      await _api.restartMonitor();
      await fetchStatus();
      _log.info('监控已重启');
      return true;
    } catch (e) {
      _log.error('重启监控失败', e);
      return false;
    }
  }
}

final monitorProvider = StateNotifierProvider<MonitorNotifier, MonitorStatus>((
  ref,
) {
  final api = ref.watch(apiClientProvider);
  return MonitorNotifier(api);
});

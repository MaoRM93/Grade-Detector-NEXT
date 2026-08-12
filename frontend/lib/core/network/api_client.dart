import 'package:dio/dio.dart';
import 'dart:io';

import '../constants/api_path.dart';
import '../logger/app_logger.dart';

/// Dio HTTP 请求封装（macOS 优化版）
class ApiClient {
  static final ApiClient _instance = ApiClient._();
  factory ApiClient() => _instance;

  late final Dio dio;
  final _log = AppLogger('api_client');

  ApiClient._() {
    dio = Dio(
      BaseOptions(
        baseUrl: ApiPath.baseUrl,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 30),
        sendTimeout: const Duration(seconds: 15),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        validateStatus: (status) => status != null && status < 500,
      ),
    );

    // 日志拦截器：打印请求和响应
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          _log.debug('${options.method} ${options.uri}');
          if (options.data != null) {
            _log.debug('Body: ${options.data}');
          }
          handler.next(options);
        },
        onResponse: (response, handler) {
          _log.debug(
            'Response ${response.statusCode}: ${_truncate(response.data)}',
          );
          handler.next(response);
        },
        onError: (error, handler) {
          _log.error('HTTP Error: ${error.message}', error);
          if (error.response != null) {
            _log.error(
              'Status: ${error.response?.statusCode}, Body: ${_truncate(error.response?.data)}',
            );
          }
          if (error.error is SocketException) {
            _log.warning('Socket Error - backend may not be running');
          }
          handler.next(error);
        },
      ),
    );
  }

  String _truncate(dynamic data, [int maxLen = 500]) {
    final s = data?.toString() ?? '';
    return s.length > maxLen ? '${s.substring(0, maxLen)}...' : s;
  }

  // ---- Auth ----

  Future<Response> login(String username, String password) async {
    return dio.post(
      ApiPath.login,
      data: {'username': username, 'password': password},
    );
  }

  // ---- Data ----

  Future<Response> getGrades() async {
    return dio.get(ApiPath.grades);
  }

  Future<Response> getRank() async {
    return dio.get(ApiPath.rank);
  }

  // ---- Settings ----

  Future<Response> getSettings() async {
    return dio.get(ApiPath.settings);
  }

  Future<Response> updateSettings(Map<String, dynamic> data) async {
    return dio.post(ApiPath.settings, data: data);
  }

  // ---- Monitor ----

  Future<Response> getMonitorStatus() async {
    return dio.get(ApiPath.monitorStatus);
  }

  Future<Response> startMonitor() async {
    return dio.post(ApiPath.monitorStart);
  }

  Future<Response> stopMonitor() async {
    return dio.post(ApiPath.monitorStop);
  }

  Future<Response> restartMonitor() async {
    return dio.post(ApiPath.monitorRestart);
  }

  // ---- Notification ----

  Future<Response> sendTestNotification() async {
    return dio.post(ApiPath.notificationTest);
  }

  Future<Response> getNotificationPreview(String mode) async {
    return dio.get(
      ApiPath.notificationPreview,
      queryParameters: {'mode': mode},
    );
  }

  // ---- Dev Tools ----

  Future<Response> queryOnce() async {
    return dio.post(ApiPath.devQueryOnce);
  }

  Future<Response> clearCache() async {
    return dio.post(ApiPath.devClearCache);
  }

  Future<Response> clearAllData() async {
    return dio.post(ApiPath.devClearAllData);
  }

  Future<Response> openLogDir() async {
    return dio.get(ApiPath.devOpenLogDir);
  }

  // ---- Welcome ----

  Future<Response> getWelcomeStatus() async {
    return dio.get(ApiPath.welcomeStatus);
  }

  Future<Response> completeWelcome() async {
    return dio.post(ApiPath.welcomeComplete);
  }
}

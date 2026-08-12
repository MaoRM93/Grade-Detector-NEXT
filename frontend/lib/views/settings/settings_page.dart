import 'dart:io' show Process;
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../core/service/tray_service.dart';
import '../../providers/settings_provider.dart';
import '../../providers/monitor_provider.dart';
import '../../widgets/glass_card.dart';

/// 系统设置页面（所有开关即时生效）
class SettingsPage extends ConsumerStatefulWidget {
  const SettingsPage({super.key});

  @override
  ConsumerState<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends ConsumerState<SettingsPage> {
  // 表单控制器
  final _usernameCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  bool _hidePassword = true;
  bool _rememberMe = false;
  bool _isLoggingIn = false;
  String? _loginMsg;

  // 监控设置
  bool _autoMonitor = false;
  bool _rankMonitor = false;
  double _intervalValue = 300;
  TimeOfDay _startTime = const TimeOfDay(hour: 8, minute: 0);
  TimeOfDay _endTime = const TimeOfDay(hour: 23, minute: 0);

  // 通知设置
  String _notifyMode = '详细';
  bool _autoStart = false;
  bool _showMenubarIcon = true;
  bool _hideUnknownCourses = true;
  bool _prevShowMenubarIcon = true;
  bool _loaded = false;

  @override
  void initState() {
    super.initState();
    Future.microtask(_loadSettings);
  }

  Future<void> _loadSettings() async {
    await ref.read(settingsProvider.notifier).fetchSettings();
    final s = ref.read(settingsProvider);
    _usernameCtrl.text = s.username;
    _passwordCtrl.text = s.password;
    _rememberMe = s.rememberMe;
    _hidePassword = true;
    _autoMonitor = s.autoMonitorEnabled;
    _rankMonitor = s.rankMonitorEnabled;
    _intervalValue = s.intervalSeconds.toDouble();
    final start = _parseTime(s.startTime);
    final end = _parseTime(s.endTime);
    _startTime = start;
    _endTime = end;
    _notifyMode = s.notifyMode;
    _autoStart = s.autoStart;
    _showMenubarIcon = s.showMenubarIcon;
    _hideUnknownCourses = s.hideUnknownCourses;
    _prevShowMenubarIcon = s.showMenubarIcon;
    _loaded = true;
    setState(() {});

    if (!s.showMenubarIcon) {
      await TrayService().destroy();
    }
  }

  TimeOfDay _parseTime(String t) {
    final parts = t.split(':');
    final h = int.tryParse(parts[0]) ?? 8;
    final m = parts.length > 1 ? (int.tryParse(parts[1]) ?? 0) : 0;
    return TimeOfDay(hour: h, minute: m);
  }

  String _formatTime(TimeOfDay t) {
    final h = t.hour.toString().padLeft(2, '0');
    final m = t.minute.toString().padLeft(2, '0');
    return '$h:$m';
  }

  /// 即时保存单个/多个设置字段
  Future<void> _saveSettings(Map<String, dynamic> changes) async {
    if (!_loaded) return;
    try {
      await ref.read(apiClientProvider).updateSettings(changes);
      // 同步本地 provider 状态
      final notifier = ref.read(settingsProvider.notifier);
      final current = ref.read(settingsProvider);
      final merged = AppSettings(
        username: current.username,
        password: current.password,
        rememberMe: current.rememberMe,
        notifyMode: (changes['notify_mode'] as String?) ?? current.notifyMode,
        startTime: (changes['start_time'] as String?) ?? current.startTime,
        endTime: (changes['end_time'] as String?) ?? current.endTime,
        intervalSeconds:
            (changes['interval_seconds'] as int?) ?? current.intervalSeconds,
        autoStart: (changes['auto_start'] as bool?) ?? current.autoStart,
        autoMonitorEnabled:
            (changes['auto_monitor_enabled'] as bool?) ??
            current.autoMonitorEnabled,
        rankMonitorEnabled:
            (changes['rank_monitor_enabled'] as bool?) ??
            current.rankMonitorEnabled,
        showMenubarIcon:
            (changes['show_menubar_icon'] as bool?) ?? current.showMenubarIcon,
        hideUnknownCourses:
            (changes['hide_unknown_courses'] as bool?) ??
            current.hideUnknownCourses,
        welcomeCompleted: current.welcomeCompleted,
        showWelcomeAlways: current.showWelcomeAlways,
      );
      await notifier.saveSettings(merged);
    } catch (_) {}
  }

  /// 切换监控启停，同步后台服务
  Future<void> _syncMonitor() async {
    try {
      if (_autoMonitor || _rankMonitor) {
        await ref.read(monitorProvider.notifier).startMonitor();
      } else {
        await ref.read(monitorProvider.notifier).stopMonitor();
      }
    } catch (_) {}
  }

  // ── 各个控件的即时保存回调 ──

  void _onAutoMonitorChanged(bool v) {
    _autoMonitor = v;
    setState(() {});
    _saveSettings({'auto_monitor_enabled': v});
    _syncMonitor();
  }

  void _onRankMonitorChanged(bool v) {
    _rankMonitor = v;
    setState(() {});
    _saveSettings({'rank_monitor_enabled': v});
    _syncMonitor();
  }

  void _onIntervalChanged(double v) {
    _intervalValue = v;
    setState(() {});
  }

  void _onIntervalChangeEnd(double v) {
    _saveSettings({'interval_seconds': v.toInt()});
  }

  Future<void> _onStartTimeChanged(TimeOfDay t) async {
    _startTime = t;
    setState(() {});
    _saveSettings({'start_time': _formatTime(t)});
  }

  Future<void> _onEndTimeChanged(TimeOfDay t) async {
    _endTime = t;
    setState(() {});
    _saveSettings({'end_time': _formatTime(t)});
  }

  void _onNotifyModeChanged(String mode) {
    _notifyMode = mode;
    setState(() {});
    _saveSettings({'notify_mode': mode});
  }

  void _onAutoStartChanged(bool v) {
    _autoStart = v;
    setState(() {});
    _saveSettings({'auto_start': v});
  }

  void _onMenubarIconChanged(bool v) {
    _showMenubarIcon = v;
    setState(() {});
    _saveSettings({'show_menubar_icon': v});
    if (v) {
      TrayService().init();
    } else {
      TrayService().destroy();
    }
  }

  void _onHideUnknownChanged(bool v) {
    _hideUnknownCourses = v;
    setState(() {});
    _saveSettings({'hide_unknown_courses': v});
  }

  Future<void> _testLogin() async {
    setState(() {
      _isLoggingIn = true;
      _loginMsg = null;
    });
    final result = await ref
        .read(settingsProvider.notifier)
        .login(_usernameCtrl.text.trim(), _passwordCtrl.text);
    if (result.success) {
      final notifier = ref.read(settingsProvider.notifier);
      final current = ref.read(settingsProvider);
      final updated = current.copyWith(
        username: _usernameCtrl.text.trim(),
        password: _passwordCtrl.text,
        rememberMe: _rememberMe,
        autoMonitorEnabled: _autoMonitor,
        rankMonitorEnabled: _rankMonitor,
        intervalSeconds: _intervalValue.toInt(),
        startTime: _formatTime(_startTime),
        endTime: _formatTime(_endTime),
        notifyMode: _notifyMode,
        autoStart: _autoStart,
        showMenubarIcon: _showMenubarIcon,
        hideUnknownCourses: _hideUnknownCourses,
      );
      await notifier.saveSettings(updated);
    }

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(result.message),
          behavior: SnackBarBehavior.floating,
          margin: const EdgeInsets.all(16),
          duration: Duration(seconds: result.success ? 2 : 4),
          backgroundColor: result.success ? AppTheme.success : AppTheme.error,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
        ),
      );
    }

    setState(() {
      _isLoggingIn = false;
      _loginMsg = result.message;
    });
  }

  @override
  void dispose() {
    _usernameCtrl.dispose();
    _passwordCtrl.dispose();
    super.dispose();
  }

  // ── 时间选择器 ──

  Future<void> _pickStartTime() async {
    final picked = await showTimePicker(
      context: context,
      initialTime: _startTime,
      helpText: '选择开始时间',
    );
    if (picked != null) await _onStartTimeChanged(picked);
  }

  Future<void> _pickEndTime() async {
    final picked = await showTimePicker(
      context: context,
      initialTime: _endTime,
      helpText: '选择结束时间',
    );
    if (picked != null) await _onEndTimeChanged(picked);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(28, 28, 28, 40),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '系统设置',
                style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.w700,
                  color: colorScheme.onSurface,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                '所有设置即时生效，无需手动保存',
                style: TextStyle(
                  fontSize: 14,
                  color: colorScheme.onSurface.withValues(alpha: .5),
                ),
              ),
              const SizedBox(height: 28),

              // ---- ① 账号与登录 ----
              _SectionTitle(title: '账号与登录', icon: Icons.lock_rounded),
              const SizedBox(height: 12),
              GlassCard(
                padding: const EdgeInsets.all(20),
                child: Column(
                  children: [
                    TextField(
                      controller: _usernameCtrl,
                      decoration: const InputDecoration(
                        labelText: '学号',
                        hintText: '输入教务系统学号',
                        prefixIcon: Icon(Icons.badge_rounded, size: 20),
                      ),
                    ),
                    const SizedBox(height: 14),
                    TextField(
                      controller: _passwordCtrl,
                      obscureText: _hidePassword,
                      keyboardType: TextInputType.visiblePassword,
                      enableSuggestions: false,
                      autocorrect: false,
                      enableIMEPersonalizedLearning: false,
                      inputFormatters: [
                        FilteringTextInputFormatter.allow(
                          RegExp(r'[\x00-\x7F]'),
                        ),
                      ],
                      decoration: InputDecoration(
                        labelText: '密码',
                        hintText: '输入教务系统密码（仅英文/数字/符号）',
                        prefixIcon: const Icon(Icons.key_rounded, size: 20),
                        suffixIcon: IconButton(
                          icon: Icon(
                            _hidePassword
                                ? Icons.visibility_off_rounded
                                : Icons.visibility_rounded,
                            size: 20,
                          ),
                          onPressed: () =>
                              setState(() => _hidePassword = !_hidePassword),
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Checkbox(
                          value: _rememberMe,
                          onChanged: (v) =>
                              setState(() => _rememberMe = v ?? false),
                        ),
                        GestureDetector(
                          onTap: () =>
                              setState(() => _rememberMe = !_rememberMe),
                          child: Text(
                            '记住密码',
                            style: TextStyle(
                              fontSize: 13,
                              color: colorScheme.onSurface.withValues(
                                alpha: .6,
                              ),
                            ),
                          ),
                        ),
                        const Spacer(),
                        FilledButton.icon(
                          onPressed: _isLoggingIn ? null : _testLogin,
                          icon: _isLoggingIn
                              ? const SizedBox(
                                  width: 14,
                                  height: 14,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: Colors.white,
                                  ),
                                )
                              : const Icon(Icons.login_rounded, size: 18),
                          label: Text(_isLoggingIn ? '验证中...' : '登录并保存'),
                        ),
                      ],
                    ),
                    if (_loginMsg != null)
                      Padding(
                        padding: const EdgeInsets.only(top: 8),
                        child: Text(
                          _loginMsg!,
                          style: TextStyle(
                            fontSize: 12,
                            color: _loginMsg == '登录成功'
                                ? AppTheme.success
                                : AppTheme.error,
                          ),
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              // ---- ② 自动监控设置 ----
              _SectionTitle(title: '自动监控设置', icon: Icons.timer_rounded),
              const SizedBox(height: 12),
              GlassCard(
                padding: const EdgeInsets.all(20),
                child: Column(
                  children: [
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text(
                        '成绩自动监控',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      value: _autoMonitor,
                      onChanged: _onAutoMonitorChanged,
                    ),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text(
                        '排名自动监控',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      value: _rankMonitor,
                      onChanged: _onRankMonitorChanged,
                    ),
                    const SizedBox(height: 8),
                    Padding(
                      padding: const EdgeInsets.only(
                        left: 16,
                        right: 16,
                        top: 4,
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '轮询间隔: ${_intervalValue.toInt()} 秒',
                            style: TextStyle(
                              fontSize: 13,
                              color: colorScheme.onSurface.withValues(
                                alpha: .5,
                              ),
                            ),
                          ),
                          Slider(
                            value: _intervalValue,
                            min: 300,
                            max: 3600,
                            divisions: 33,
                            label: '${_intervalValue.toInt()}秒',
                            onChanged: _onIntervalChanged,
                            onChangeEnd: _onIntervalChangeEnd,
                          ),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                '300s',
                                style: TextStyle(
                                  fontSize: 11,
                                  color: colorScheme.onSurface.withValues(
                                    alpha: .3,
                                  ),
                                ),
                              ),
                              Text(
                                '3600s',
                                style: TextStyle(
                                  fontSize: 11,
                                  color: colorScheme.onSurface.withValues(
                                    alpha: .3,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              // ---- ③ 监控时间 ----
              _SectionTitle(title: '监控时间', icon: Icons.schedule_rounded),
              const SizedBox(height: 12),
              GlassCard(
                padding: const EdgeInsets.all(20),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: ListTile(
                            contentPadding: EdgeInsets.zero,
                            title: const Text(
                              '开始时间',
                              style: TextStyle(fontSize: 13),
                            ),
                            trailing: Text(
                              _startTime.format(context),
                              style: const TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            onTap: _pickStartTime,
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: ListTile(
                            contentPadding: EdgeInsets.zero,
                            title: const Text(
                              '结束时间',
                              style: TextStyle(fontSize: 13),
                            ),
                            trailing: Text(
                              _endTime.format(context),
                              style: const TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            onTap: _pickEndTime,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      '非窗口期内监控自动休眠',
                      style: TextStyle(
                        fontSize: 11,
                        color: colorScheme.onSurface.withValues(alpha: .35),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              // ---- ④ 系统通知偏好 ----
              _SectionTitle(title: '系统通知偏好', icon: Icons.notifications_rounded),
              const SizedBox(height: 12),
              GlassCard(
                padding: const EdgeInsets.all(20),
                child: Column(
                  children: ['详细', '简洁'].map((mode) {
                    return InkWell(
                      onTap: () => _onNotifyModeChanged(mode),
                      borderRadius: BorderRadius.circular(12),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(
                          vertical: 8,
                          horizontal: 4,
                        ),
                        child: Row(
                          children: [
                            Radio<String>(
                              value: mode,
                              groupValue: _notifyMode,
                              onChanged: (v) => _onNotifyModeChanged(v ?? '详细'),
                            ),
                            const SizedBox(width: 8),
                            Text(
                              mode == '详细'
                                  ? '完整模式：显示课程名称、成绩与位次'
                                  : '简洁模式：仅显示有成绩或位次更新',
                              style: const TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ),
              const SizedBox(height: 24),

              // ---- ⑤ 高级设置 ----
              _SectionTitle(title: '高级设置', icon: Icons.tune_rounded),
              const SizedBox(height: 12),
              GlassCard(
                padding: const EdgeInsets.all(20),
                child: Column(
                  children: [
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text(
                        '开机自启动',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      value: _autoStart,
                      onChanged: _onAutoStartChanged,
                    ),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text(
                        '菜单栏图标',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      value: _showMenubarIcon,
                      onChanged: _onMenubarIconChanged,
                    ),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text(
                        '隐藏未知课程',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      value: _hideUnknownCourses,
                      onChanged: _onHideUnknownChanged,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              // ── 版本与版权 ──
              Center(
                child: Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text.rich(
                    TextSpan(
                      style: TextStyle(
                        fontSize: 11,
                        color: colorScheme.onSurface.withValues(alpha: .25),
                      ),
                      children: [
                        const TextSpan(text: 'Version: 27G36 · '),
                        const TextSpan(
                          text:
                              'Copyright © 2024-2030 GradeDetector. All rights reserved. · ',
                        ),
                        TextSpan(
                          text: 'Github',
                          style: TextStyle(
                            color: colorScheme.primary.withValues(alpha: .5),
                            decoration: TextDecoration.underline,
                          ),
                          recognizer: TapGestureRecognizer()
                            ..onTap = () {
                              Process.run('open', [
                                'https://github.com/MaoRM93/Grade-Detector-NEXT',
                              ]);
                            },
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }
}

/// 分区标题
class _SectionTitle extends StatelessWidget {
  final String title;
  final IconData icon;

  const _SectionTitle({required this.title, required this.icon});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Row(
      children: [
        Icon(icon, size: 20, color: colorScheme.primary),
        const SizedBox(width: 10),
        Text(
          title,
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w700,
            color: colorScheme.onSurface,
          ),
        ),
      ],
    );
  }
}

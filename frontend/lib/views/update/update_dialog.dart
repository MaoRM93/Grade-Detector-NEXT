import 'package:flutter/material.dart';

import '../../core/service/update_service.dart';

/// 发现新版本弹窗（L1 方案：展示版本与说明，跳转浏览器下载）
Future<void> showUpdateDialog(BuildContext context, UpdateCheckResult result) {
  return showDialog<void>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: const Row(
        children: [
          Icon(Icons.system_update_rounded, size: 22),
          SizedBox(width: 8),
          Text('发现新版本'),
        ],
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '最新版本: ${result.latestVersion}    当前版本: ${result.currentVersion}',
            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
          ),
          if (result.releaseNotes.isNotEmpty) ...[
            const SizedBox(height: 12),
            SizedBox(
              height: 180,
              width: 380,
              child: SingleChildScrollView(
                child: Text(
                  result.releaseNotes,
                  style: const TextStyle(fontSize: 13, height: 1.5),
                ),
              ),
            ),
          ],
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(ctx).pop(),
          child: const Text('下次再说'),
        ),
        FilledButton.icon(
          onPressed: () {
            Navigator.of(ctx).pop();
            UpdateService().openDownloadUrl(result.downloadUrl);
          },
          icon: const Icon(Icons.download_rounded, size: 18),
          label: const Text('前往下载'),
        ),
      ],
    ),
  );
}

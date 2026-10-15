import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';

import '../../providers/notification_provider.dart';
import '../../providers/providers.dart';
import '../services/web_notification_helper.dart';

class NotificationBell extends ConsumerWidget {
  const NotificationBell({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final unreadCount = ref.watch(unreadNotificationsCountProvider);

    return Stack(
      clipBehavior: Clip.none,
      children: [
        IconButton(
          icon: const Icon(Icons.notifications_none),
          onPressed: () {
            _showNotificationsDialog(context, ref);
          },
        ),
        if (unreadCount > 0)
          Positioned(
            right: 8,
            top: 8,
            child: Container(
              padding: const EdgeInsets.all(2),
              decoration: BoxDecoration(
                color: Colors.red,
                borderRadius: BorderRadius.circular(10),
              ),
              constraints: const BoxConstraints(minWidth: 16, minHeight: 16),
              child: Text(
                '$unreadCount',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 10,
                  fontWeight: FontWeight.bold,
                ),
                textAlign: TextAlign.center,
              ),
            ),
          ),
      ],
    );
  }

  void _showNotificationsDialog(BuildContext context, WidgetRef ref) {
    showDialog(
      context: context,
      builder: (context) {
        return const _NotificationDialog();
      },
    );
  }
}

class _NotificationDialog extends ConsumerStatefulWidget {
  const _NotificationDialog();

  @override
  ConsumerState<_NotificationDialog> createState() => _NotificationDialogState();
}

class _NotificationDialogState extends ConsumerState<_NotificationDialog> {
  String _webPermission = 'default';
  bool _isRequesting = false;

  @override
  void initState() {
    super.initState();
    _checkPermission();
  }

  void _checkPermission() {
    if (kIsWeb) {
      setState(() {
        _webPermission = WebNotificationHelper.instance.permissionStatus;
      });
    }
  }

  Future<void> _handleRequestPermission() async {
    setState(() {
      _isRequesting = true;
    });

    final granted =
        await ref.read(pushServiceProvider).requestPermissionAndRegister();

    if (mounted) {
      setState(() {
        _isRequesting = false;
        _webPermission = WebNotificationHelper.instance.permissionStatus;
      });

      if (granted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Powiadomienia przeglądarkowe zostały włączone!'),
            backgroundColor: Color(0xFF006A6A),
          ),
        );
      } else if (_webPermission == 'denied') {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Powiadomienia są zablokowane w ustawieniach przeglądarki.',
            ),
            backgroundColor: Colors.orange,
          ),
        );
      }
    }
  }

  Widget _buildWebPermissionBanner() {
    if (!kIsWeb) return const SizedBox.shrink();

    if (_webPermission == 'granted') {
      return Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: Colors.green.shade50,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.green.shade200),
        ),
        child: Row(
          children: [
            Icon(Icons.check_circle, size: 16, color: Colors.green.shade700),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                'Powiadomienia w przeglądarce są aktywne',
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.green.shade900,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ],
        ),
      );
    }

    if (_webPermission == 'denied') {
      return Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: Colors.orange.shade50,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.orange.shade200),
        ),
        child: Row(
          children: [
            Icon(
              Icons.notifications_off,
              size: 16,
              color: Colors.orange.shade800,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                'Powiadomienia są zablokowane w przeglądarce. Zezwól na nie w ustawieniach strony.',
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.orange.shade900,
                ),
              ),
            ),
          ],
        ),
      );
    }

    // Default or not yet prompted (crucial for iOS Safari PWA & Chrome)
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFE0F2F1), // Light Teal
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF80CBC4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Row(
            children: [
              Icon(
                Icons.notifications_active,
                size: 18,
                color: Color(0xFF006A6A),
              ),
              SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Włącz powiadomienia w przeglądarce',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 13,
                    color: Color(0xFF004D40),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          const Text(
            'Otrzymuj natychmiastowe alerty o grafikach i wnioskach na tym urządzeniu.',
            style: TextStyle(fontSize: 12, color: Color(0xFF1E3535)),
          ),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerRight,
            child: FilledButton.icon(
              style: FilledButton.styleFrom(
                visualDensity: VisualDensity.compact,
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 6,
                ),
                backgroundColor: const Color(0xFF006A6A),
              ),
              onPressed: _isRequesting ? null : _handleRequestPermission,
              icon:
                  _isRequesting
                      ? const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                      : const Icon(Icons.touch_app, size: 16),
              label: Text(
                _isRequesting ? 'Włączanie...' : 'Włącz powiadomienia',
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final notificationsAsync = ref.watch(notificationsProvider);

    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Container(
        padding: const EdgeInsets.all(16),
        width: 400,
        height: 520,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Powiadomienia',
                  style: GoogleFonts.outfit(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    IconButton(
                      icon: const Icon(Icons.refresh),
                      tooltip: 'Odśwież',
                      onPressed: () {
                        _checkPermission();
                        ref
                            .read(notificationsProvider.notifier)
                            .fetchNotifications();
                      },
                    ),
                    IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  ],
                ),
              ],
            ),
            const Divider(),
            if (kIsWeb) _buildWebPermissionBanner(),
            Expanded(
              child: notificationsAsync.when(
                data: (notifications) {
                  if (notifications.isEmpty) {
                    return const Center(child: Text('Brak powiadomień.'));
                  }
                  return ListView.builder(
                    itemCount: notifications.length,
                    itemBuilder: (context, index) {
                      final n = notifications[index];
                      return Card(
                        color: n.isRead ? null : Colors.blue.shade50,
                        margin: const EdgeInsets.symmetric(vertical: 4),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8),
                          side: BorderSide(
                            color:
                                n.isRead
                                    ? Colors.grey.shade300
                                    : Colors.blue.shade200,
                          ),
                        ),
                        child: ListTile(
                          title: Text(
                            n.title,
                            style: TextStyle(
                              fontWeight:
                                  n.isRead
                                      ? FontWeight.normal
                                      : FontWeight.bold,
                            ),
                          ),
                          subtitle: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const SizedBox(height: 4),
                              Text(n.body),
                              const SizedBox(height: 4),
                              Text(
                                DateFormat(
                                  'dd.MM.yyyy HH:mm',
                                ).format(n.createdAt.toLocal()),
                                style: TextStyle(
                                  fontSize: 12,
                                  color: Colors.grey.shade600,
                                ),
                              ),
                            ],
                          ),
                          isThreeLine: true,
                          trailing:
                              n.isRead
                                  ? null
                                  : IconButton(
                                    icon: const Icon(
                                      Icons.check,
                                      color: Colors.blue,
                                    ),
                                    onPressed: () {
                                      ref
                                          .read(notificationsProvider.notifier)
                                          .markAsRead(n.id);
                                    },
                                    tooltip: 'Oznacz jako przeczytane',
                                  ),
                        ),
                      );
                    },
                  );
                },
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (err, _) => Center(child: Text('Błąd: $err')),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

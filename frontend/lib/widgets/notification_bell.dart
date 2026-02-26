import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';

import '../../providers/notification_provider.dart';

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
        return _NotificationDialog();
      },
    );
  }
}

class _NotificationDialog extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notificationsAsync = ref.watch(notificationsProvider);

    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Container(
        padding: const EdgeInsets.all(16),
        width: 400,
        height: 500,
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
                IconButton(
                  icon: const Icon(Icons.refresh),
                  onPressed: () {
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
            const Divider(),
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

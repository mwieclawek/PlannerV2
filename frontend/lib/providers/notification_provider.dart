import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import 'providers.dart';

final notificationsProvider = StateNotifierProvider<
  NotificationsNotifier,
  AsyncValue<List<AppNotification>>
>((ref) {
  final apiService = ref.watch(apiServiceProvider);
  final authState = ref.watch(authProvider);

  return NotificationsNotifier(apiService, authState);
});

final unreadNotificationsCountProvider = Provider<int>((ref) {
  final notifsAsync = ref.watch(notificationsProvider);
  return notifsAsync.maybeWhen(
    data: (notifs) => notifs.where((n) => !n.isRead).length,
    orElse: () => 0,
  );
});

class NotificationsNotifier
    extends StateNotifier<AsyncValue<List<AppNotification>>> {
  final ApiService _apiService;
  final AsyncValue<User?> _authState;
  Timer? _pollingTimer;

  NotificationsNotifier(this._apiService, this._authState)
    : super(const AsyncValue.loading()) {
    if (_authState.value != null) {
      fetchNotifications();
      _startPolling();
    } else {
      _stopPolling();
      state = const AsyncValue.data([]);
    }
  }

  void _startPolling() {
    _stopPolling();
    _pollingTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      fetchNotifications();
    });
  }

  void _stopPolling() {
    _pollingTimer?.cancel();
    _pollingTimer = null;
  }

  @override
  void dispose() {
    _stopPolling();
    super.dispose();
  }

  Future<void> fetchNotifications() async {
    try {
      if (state is! AsyncLoading && state.value == null) {
        state = const AsyncValue.loading();
      }
      final notifs = await _apiService.getNotifications();
      state = AsyncValue.data(notifs);
    } catch (e, st) {
      if (state.value == null) {
        state = AsyncValue.error(e, st);
      }
      // If we already have data, we might not want to overwrite it with an error on background poll
    }
  }

  Future<void> markAsRead(String id) async {
    try {
      await _apiService.markNotificationRead(id);
      // Optimistically update
      if (state.value != null) {
        final current = state.value!;
        final updated =
            current.map((n) {
              if (n.id == id) {
                return AppNotification(
                  id: n.id,
                  title: n.title,
                  body: n.body,
                  isRead: true,
                  createdAt: n.createdAt,
                );
              }
              return n;
            }).toList();
        state = AsyncValue.data(updated);
      }
    } catch (e) {
      // Revert or show error
      fetchNotifications();
    }
  }
}

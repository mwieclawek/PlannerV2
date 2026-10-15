import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/notification_provider.dart';
import '../utils/scaffold_messenger.dart';
import 'api_service.dart';
import 'web_notification_helper.dart';

class PushService {
  final ApiService _apiService;
  final Ref? _ref;
  final FirebaseMessaging? _customMessaging;

  FirebaseMessaging get _messaging =>
      _customMessaging ?? FirebaseMessaging.instance;

  static const String vapidKey = String.fromEnvironment(
    'FCM_VAPID_KEY',
    defaultValue: '',
  );

  PushService(this._apiService, [this._ref, this._customMessaging]);

  String? get _resolvedVapidKey {
    final trimmed = vapidKey.trim();
    return trimmed.isNotEmpty ? trimmed : null;
  }

  Future<NotificationSettings> requestPermission() async {
    if (kIsWeb) {
      // Direct Web Notification API request (required for iOS Safari PWA / modern browsers)
      await WebNotificationHelper.instance.requestPermission();
    }

    return await _messaging.requestPermission(
      alert: true,
      announcement: false,
      badge: true,
      carPlay: false,
      criticalAlert: false,
      provisional: false,
      sound: true,
    );
  }

  Future<bool> requestPermissionAndRegister() async {
    try {
      final settings = await requestPermission();
      if (settings.authorizationStatus == AuthorizationStatus.authorized ||
          settings.authorizationStatus == AuthorizationStatus.provisional) {
        await fetchAndRegisterToken();
        return true;
      }
    } catch (e) {
      debugPrint('Błąd żądania uprawnień: $e');
    }
    return false;
  }

  Future<String?> fetchAndRegisterToken() async {
    try {
      final token = await _messaging.getToken(
        vapidKey: kIsWeb ? _resolvedVapidKey : null,
      );

      if (token != null) {
        debugPrint('FCM Token: $token');
        await _apiService.registerDeviceToken(token);
        return token;
      }
    } catch (e) {
      debugPrint('Błąd podczas pobierania tokena FCM: $e');
    }
    return null;
  }

  Future<void> initialize() async {
    // 1. Request permissions (required on iOS and Web)
    try {
      NotificationSettings settings;
      if (kIsWeb) {
        final status = WebNotificationHelper.instance.permissionStatus;
        if (status == 'granted') {
          settings = await requestPermission();
        } else {
          // On web, if not granted yet, try to request; catch if browser requires user gesture
          settings = await requestPermission();
        }
      } else {
        settings = await requestPermission();
      }

      if (settings.authorizationStatus == AuthorizationStatus.authorized ||
          settings.authorizationStatus == AuthorizationStatus.provisional) {
        debugPrint('User granted permission');
        await fetchAndRegisterToken();
      } else {
        debugPrint('User declined or has not accepted permission');
      }
    } catch (e) {
      debugPrint('Info: permission request during initialize deferred: $e');
    }

    // 2. Listen to token refreshes
    _messaging.onTokenRefresh.listen((newToken) {
      debugPrint('FCM Token refreshed: $newToken');
      _apiService.registerDeviceToken(newToken);
    });

    // 3. Setup foreground message handler
    _setupForegroundListener();
  }

  void _setupForegroundListener() {
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      debugPrint('Got a message whilst in the foreground!');
      debugPrint('Message data: ${message.data}');

      // Refresh notifications under the bell
      try {
        _ref?.read(notificationsProvider.notifier).fetchNotifications();
      } catch (e) {
        debugPrint('Błąd odświeżania powiadomień: $e');
      }

      final title =
          message.notification?.title ??
          message.data['title']?.toString() ??
          'Nowe powiadomienie';
      final body =
          message.notification?.body ??
          message.data['body']?.toString() ??
          '';

      // 1. Native browser notification on Web (if tab is in background or alongside banner)
      if (kIsWeb) {
        WebNotificationHelper.instance.showNotification(
          title: title,
          body: body,
          icon: '/icons/Icon-192.png',
        );
      }

      // 2. Show prominent banner at the top of the screen via ScaffoldMessenger
      showForegroundBanner(title, body);
    });
  }

  void showForegroundBanner(String title, String body) {
    final messenger = rootScaffoldMessengerKey.currentState;
    if (messenger == null) return;

    final banner = MaterialBanner(
      backgroundColor: const Color(0xFFE0F2F1), // Teal 50
      leading: const Icon(
        Icons.notifications_active,
        color: Color(0xFF006A6A),
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              fontWeight: FontWeight.bold,
              color: Color(0xFF003737),
            ),
          ),
          if (body.isNotEmpty) ...[
            const SizedBox(height: 2),
            Text(
              body,
              style: const TextStyle(color: Color(0xFF1E3535)),
            ),
          ],
        ],
      ),
      actions: [
        TextButton(
          onPressed: () {
            messenger.hideCurrentMaterialBanner();
          },
          child: const Text(
            'Zamknij',
            style: TextStyle(
              color: Color(0xFF006A6A),
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
      ],
    );

    messenger.hideCurrentMaterialBanner();
    messenger.showMaterialBanner(banner);

    Future.delayed(const Duration(seconds: 6), () {
      try {
        messenger.hideCurrentMaterialBanner();
      } catch (_) {}
    });
  }

  Future<void> unregisterOnLogout() async {
    try {
      final token = await _messaging.getToken(
        vapidKey: kIsWeb ? _resolvedVapidKey : null,
      );
      if (token != null) {
        await _apiService.unregisterDeviceToken(token);
      }
    } catch (e) {
      debugPrint('Błąd podczas usuwania tokena FCM: $e');
    }
  }
}

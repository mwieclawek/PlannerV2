import 'dart:io';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'api_service.dart';

class PushService {
  final ApiService _apiService;
  final FirebaseMessaging _messaging = FirebaseMessaging.instance;

  PushService(this._apiService);

  Future<void> initialize() async {
    // 1. Request permissions (required on iOS and Web)
    NotificationSettings settings = await _messaging.requestPermission(
      alert: true,
      announcement: false,
      badge: true,
      carPlay: false,
      criticalAlert: false,
      provisional: false,
      sound: true,
    );

    if (settings.authorizationStatus == AuthorizationStatus.authorized) {
      print('User granted permission');
    } else if (settings.authorizationStatus ==
        AuthorizationStatus.provisional) {
      print('User granted provisional permission');
    } else {
      print('User declined or has not accepted permission');
      // If no permission, do not try to get token
      return;
    }

    // 2. Fetch the FCM token for this device
    try {
      String? token;

      if (kIsWeb) {
        // Web requires pushing VAPID key which we might not have configured.
        // It's optional if already configured in firebase-messaging-sw.js.
        token = await _messaging.getToken();
      } else {
        token = await _messaging.getToken();
      }

      if (token != null) {
        print('FCM Token: $token');
        await _apiService.registerDeviceToken(token);
      }
    } catch (e) {
      print('Błąd podczas pobierania tokena FCM: $e');
    }

    // 3. Listen to token refreshes
    _messaging.onTokenRefresh.listen((newToken) {
      print('FCM Token refreshed: $newToken');
      _apiService.registerDeviceToken(newToken);
    });

    // 4. Setup foreground message handler
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      print('Got a message whilst in the foreground!');
      print('Message data: ${message.data}');

      if (message.notification != null) {
        print('Message also contained a notification: ${message.notification}');
        // Here we could use a SnackBar, showDialog, or a local notification plugin
        // Since Riverpod state manages notifications, we can optionally trigger a refresh
        // of getNotifications() if we pass the ref down or dispatch an event.
      }
    });
  }

  Future<void> unregisterOnLogout() async {
    try {
      String? token = await _messaging.getToken();
      if (token != null) {
        await _apiService.unregisterDeviceToken(token);
        // Do not delete token locally since same device might login later, delete from server is enough.
      }
    } catch (e) {
      print('Błąd podczas usuwania tokena FCM: $e');
    }
  }
}

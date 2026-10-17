import 'dart:js_interop';
import 'package:web/web.dart' as web;
import 'web_notification_helper.dart';

WebNotificationHelper getWebNotificationHelper() => WebNotificationHelperWeb();

class WebNotificationHelperWeb implements WebNotificationHelper {
  @override
  bool get isSupported {
    try {
      return web.Notification.permission.isNotEmpty;
    } catch (_) {
      return false;
    }
  }

  @override
  String get permissionStatus {
    try {
      return web.Notification.permission;
    } catch (_) {
      return 'unsupported';
    }
  }

  @override
  Future<String> requestPermission() async {
    try {
      final jsResult = await web.Notification.requestPermission().toDart;
      return jsResult.toDart;
    } catch (e) {
      web.console.error(
        'WebNotificationHelper: requestPermission error: $e'.toJS,
      );
      return 'denied';
    }
  }

  @override
  void showNotification({
    required String title,
    required String body,
    String? icon,
  }) {
    try {
      if (web.Notification.permission != 'granted') {
        return;
      }
      final options = web.NotificationOptions(
        body: body,
        icon: icon ?? '/icons/Icon-192.png',
      );
      try {
        final notif = web.Notification(title, options);
        notif.onclick = ((web.Event _) {
          try {
            web.window.focus();
          } catch (_) {}
        }).toJS;
      } catch (ctorErr) {
        // Mobile browsers and PWAs with active Service Worker throw Illegal constructor
        // and require ServiceWorkerRegistration.showNotification().
        web.console.warn(
          'WebNotificationHelper: Notification constructor failed ($ctorErr), falling back to serviceWorker.ready'.toJS,
        );
        web.window.navigator.serviceWorker.ready.toDart.then((registration) {
          return registration.showNotification(title, options).toDart;
        }).catchError((Object swErr) {
          web.console.error(
            'WebNotificationHelper: ServiceWorker showNotification failed: $swErr'.toJS,
          );
          return null;
        });
      }
    } catch (e) {
      web.console.error(
        'WebNotificationHelper: showNotification unexpected error: $e'.toJS,
      );
    }
  }
}

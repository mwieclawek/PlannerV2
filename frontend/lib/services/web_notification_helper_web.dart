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
    } catch (_) {
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
      if (web.Notification.permission == 'granted') {
        final notif = web.Notification(
          title,
          web.NotificationOptions(
            body: body,
            icon: icon ?? '/icons/Icon-192.png',
          ),
        );
        notif.onclick = ((web.Event _) {
          try {
            web.window.focus();
          } catch (_) {}
        }).toJS;
      }
    } catch (_) {}
  }
}

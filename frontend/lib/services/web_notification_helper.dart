import 'web_notification_helper_stub.dart'
    if (dart.library.js_interop) 'web_notification_helper_web.dart';

abstract class WebNotificationHelper {
  static WebNotificationHelper get instance => getWebNotificationHelper();

  bool get isSupported;
  String get permissionStatus;
  Future<String> requestPermission();
  void showNotification({
    required String title,
    required String body,
    String? icon,
  });
}

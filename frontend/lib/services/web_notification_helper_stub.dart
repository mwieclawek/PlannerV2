import 'web_notification_helper.dart';

WebNotificationHelper getWebNotificationHelper() => WebNotificationHelperStub();

class WebNotificationHelperStub implements WebNotificationHelper {
  @override
  bool get isSupported => false;

  @override
  String get permissionStatus => 'unsupported';

  @override
  Future<String> requestPermission() async => 'unsupported';

  @override
  void showNotification({
    required String title,
    required String body,
    String? icon,
  }) {}
}

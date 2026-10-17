import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/services/api_service.dart';
import 'package:frontend/services/push_service.dart';
import 'package:frontend/services/web_notification_helper.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Web Push & Notification Tests', () {
    test('WebNotificationHelper instance is accessible', () {
      final helper = WebNotificationHelper.instance;
      expect(helper, isNotNull);
      // In Dart VM unit tests, isSupported is either false or stubbed
      expect(helper.permissionStatus, isA<String>());
    });

    test('PushService exposes vapidKey constant', () {
      expect(PushService.vapidKey, isA<String>());
    });

    test('PushService foreground banner handles null messenger gracefully', () {
      final service = PushService(ApiService('http://test-server'));
      // Should not throw even when no ScaffoldMessenger is attached in headless test
      expect(() => service.showForegroundBanner('Test Title', 'Test Body'), returnsNormally);
    });
  });
}

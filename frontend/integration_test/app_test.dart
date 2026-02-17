import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:frontend/main.dart' as app;
import 'package:flutter/material.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('App starts and shows login screen', (WidgetTester tester) async {
    app.main();
    await tester.pumpAndSettle();

    // Verify that the login screen is displayed
    // Assuming there are text fields for username/password or a Login button
    expect(find.text('Zaloguj'), findsOneWidget); 
    // Or check for specific Key if present
    // expect(find.byKey(const Key('login_button')), findsOneWidget);
  });
}

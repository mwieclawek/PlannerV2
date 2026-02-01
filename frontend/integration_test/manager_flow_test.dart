import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:frontend/main.dart' as app;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('Manager end-to-end flow test: Register -> Setup -> Requirements',
      (WidgetTester tester) async {
    // 1. Start App
    app.main();
    await tester.pumpAndSettle();

    // 2. Register new Manager
    // Find and tap 'Zarejestruj się'
    final registerLink = find.text('Zarejestruj się');
    if (findsOneWidget.matches(registerLink, {})) {
       await tester.tap(registerLink);
       await tester.pumpAndSettle();
    }

    // Generate unique email
    final timestamp = DateTime.now().millisecondsSinceEpoch;
    final email = 'manager_test_$timestamp@example.com';

    // Fill Registration Form
    await tester.enterText(find.ancestor(of: find.text('Email'), matching: find.byType(TextFormField)), email);
    await tester.enterText(find.ancestor(of: find.text('Hasło'), matching: find.byType(TextFormField)), 'password123');
    await tester.enterText(find.ancestor(of: find.text('Pełne Imię i Nazwisko'), matching: find.byType(TextFormField)), 'Test Manager');
    
    // Select Role "Manager" (Dropdown)
    await tester.tap(find.byType(DropdownButtonFormField<String>));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Manager').last);
    await tester.pumpAndSettle();

    // Submit Register
    await tester.tap(find.text('Zarejestruj się').last); // Button
    await tester.pumpAndSettle(const Duration(seconds: 2));

    // Verify Dashboard
    expect(find.text('Panel Managera'), findsOneWidget);

    // 3. Setup (Konfiguracja)
    // Current tab is Setup by default
    
    // Create Role
    await tester.enterText(find.widgetWithText(TextFormField, 'Nazwa roli'), 'Barista');
    await tester.tap(find.text('Dodaj'));
    await tester.pumpAndSettle(const Duration(seconds: 1));

    // Create Shift
    await tester.enterText(find.widgetWithText(TextFormField, 'Nazwa zmiany'), 'Rano');
    await tester.enterText(find.widgetWithText(TextFormField, 'Start (HH:MM)'), '08:00');
    await tester.enterText(find.widgetWithText(TextFormField, 'Koniec (HH:MM)'), '16:00');
    await tester.tap(find.text('Dodaj').last); // Second 'Dodaj' button for Shift
    await tester.pumpAndSettle(const Duration(seconds: 1));

    // 4. Go to Requirements (Wymagania) - CRITICAL CHECK
    await tester.tap(find.text('Wymagania'));
    await tester.pumpAndSettle(const Duration(seconds: 2));

    // Check for error (if red screen of death showing error text)
    expect(find.textContaining('Type \'String\' is not a subtype'), findsNothing);
    
    // Verify Grid is visible
    expect(find.text('Wymagania Obsadowe'), findsOneWidget);
    expect(find.text('Barista'), findsOneWidget); // Role should be visible
    expect(find.text('Rano'), findsOneWidget); // Shift should be visible

    // 5. Interact with counters
    // Find the '+' icon/button. There might be many, let's tap the first one.
    await tester.tap(find.byIcon(Icons.add).first);
    await tester.pumpAndSettle();
    
    // Verify count increased to 1
    expect(find.text('1'), findsOneWidget);

    // 6. Save Requirements
    await tester.tap(find.text('Zapisz Wymagania'));
    await tester.pumpAndSettle(const Duration(seconds: 2));

    // Verify Success validation
    expect(find.text('✓ Wymagania zapisane'), findsOneWidget);
    
    // 7. Generate Schedule
    await tester.tap(find.text('Grafik'));
    await tester.pumpAndSettle();
    
    await tester.tap(find.text('Generuj Grafik (AI)'));
    await tester.pumpAndSettle(const Duration(seconds: 5)); // Wait for generation
    
    // It will likely fail (infeasible) because no employees, but we check if UI crashes
    // If we see "Wyniki" or message, it works.
    expect(find.textContaining('Wygenerowano'), findsOneWidget); // Or 'Niewykonalne'
  });
}

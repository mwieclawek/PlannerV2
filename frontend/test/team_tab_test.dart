import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/screens/manager/team_tab.dart';
import 'package:frontend/services/api_service.dart';
import 'package:frontend/models/models.dart';
import 'package:frontend/providers/providers.dart';

// Fake ApiService
class FakeApiService implements ApiService {
  final List<TeamMember> _users = [];
  final List<JobRole> _roles = [];

  @override
  Future<List<TeamMember>> getUsers({bool includeInactive = false}) async => _users;

  @override
  Future<List<JobRole>> getRoles() async => _roles;

  @override
  Future<void> createUser({
    required String username,
    required String password,
    required String fullName,
    required String roleSystem,
    String? email,
    int? targetHoursPerMonth,
    int? targetShiftsPerMonth,
  }) async {
    // Simulate network delay
    await Future.delayed(const Duration(milliseconds: 10));
    _users.add(TeamMember(
      id: 'new_id',
      username: username,
      email: email,
      fullName: fullName,
      roleSystem: roleSystem,
      jobRoleIds: [],
      targetHoursPerMonth: targetHoursPerMonth,
      targetShiftsPerMonth: targetShiftsPerMonth,
    ));
  }

  // Stubs for other methods to satisfy interface
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  late FakeApiService fakeApi;

  setUp(() {
    fakeApi = FakeApiService();
  });

  testWidgets('TeamTab shows Add User button', (WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          apiServiceProvider.overrideWithValue(fakeApi),
        ],
        child: const MaterialApp(home: Scaffold(body: TeamTab())),
      ),
    );
    await tester.pumpAndSettle();

    // Verify FAB
    expect(find.byType(FloatingActionButton), findsOneWidget);
    expect(find.byIcon(Icons.person_add), findsOneWidget);
  });

  testWidgets('Clicking Add User button opens dialog and adds user', (WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          apiServiceProvider.overrideWithValue(fakeApi),
        ],
        child: const MaterialApp(home: Scaffold(body: TeamTab())),
      ),
    );
    await tester.pumpAndSettle();

    // Open Dialog
    await tester.tap(find.byType(FloatingActionButton));
    await tester.pumpAndSettle();

    expect(find.text('Dodaj pracownika'), findsOneWidget);

    // Fill form
    await tester.enterText(find.widgetWithText(TextFormField, 'Login *'), 'newuser');
    await tester.enterText(find.widgetWithText(TextFormField, 'Hasło *'), 'password123');
    await tester.enterText(find.widgetWithText(TextFormField, 'Pełna nazwa *'), 'Test User');

    // Submit
    await tester.tap(find.text('Dodaj'));
    await tester.pumpAndSettle(); // Wait for async create and dialog close

    // Verify dialog closed
    expect(find.text('Dodaj pracownika'), findsNothing);

    // Verify user was added to fake api
    final users = await fakeApi.getUsers();
    expect(users.length, 1);
    expect(users.first.username, 'newuser');
  });
}

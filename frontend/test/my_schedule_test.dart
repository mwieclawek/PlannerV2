import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mockito/mockito.dart';
import 'package:mockito/annotations.dart';
import 'package:frontend/models/models.dart';
import 'package:frontend/providers/providers.dart';
import 'package:frontend/services/api_service.dart';
import 'package:frontend/screens/employee/my_schedule_screen.dart';

import 'package:intl/date_symbol_data_local.dart';

import 'my_schedule_test.mocks.dart';

class FakeAuthNotifier extends StateNotifier<AsyncValue<User?>> implements AuthNotifier {
  FakeAuthNotifier() : super(AsyncValue.data(
    User(
      id: 'user1',
      username: 'Test User',
      fullName: 'Test User',
      roleSystem: 'EMPLOYEE',
      createdAt: DateTime.now(),
    )
  ));
  
  @override
  Future<void> login(String username, String password) async {}
  @override
  Future<void> register(String username, String password, String fullName, String roleSystem, {String? managerPin}) async {}
  @override
  Future<void> logout() async {}
}

@GenerateMocks([ApiService])
void main() {
  late MockApiService mockApiService;

  setUp(() async {
    await initializeDateFormatting('pl_PL', null);
    mockApiService = MockApiService();
  });

  testWidgets('Toggling "Cała załoga" loads team schedule', (WidgetTester tester) async {
    // Stub API responses
    when(mockApiService.getEmployeeSchedule(any, any))
        .thenAnswer((_) async => [
              EmployeeScheduleEntry(
                id: '2',
                date: DateTime.now(),
                roleName: 'Obsługa',
                shiftName: 'Popołudnie',
                startTime: '16:00',
                endTime: '24:00',
                isOnGiveaway: false,
              )
            ]);
    when(mockApiService.getScheduleSummary(
            year: anyNamed('year'), month: anyNamed('month'), weekStart: anyNamed('weekStart'), weekEnd: anyNamed('weekEnd')))
        .thenAnswer((_) async => {'week_hours': 0, 'month_hours': 0});
    
    // Stub getTeamSchedule
    when(mockApiService.getTeamSchedule(any, any))
        .thenAnswer((_) async => [
              ScheduleEntry(
                id: '1',
                date: DateTime.now(),
                shiftDefId: 1,
                userId: 'user1',
                userName: 'Test User',
                roleId: 1,
                roleName: 'Kuchnia',
                shiftName: 'Rano',
                startTime: '08:00',
                endTime: '16:00',
                isPublished: true,
              )
            ]);

    // Build the widget
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          apiServiceProvider.overrideWithValue(mockApiService),
          authProvider.overrideWith((ref) => FakeAuthNotifier()),
        ],
        child: const MaterialApp(
          home: Scaffold(
            body: MyScheduleScreen(),
          ),
        ),
      ),
    );

    // Initial load
    await tester.pumpAndSettle();

    // Verify employee schedule was called
    verify(mockApiService.getEmployeeSchedule(any, any)).called(1);

    // Find the "Cała załoga" button
    final teamButton = find.text('Cała załoga').first;
    expect(teamButton, findsOneWidget);

    // Tap the button
    await tester.tap(teamButton);
    await tester.pumpAndSettle();

    // Verify getTeamSchedule was called
    verify(mockApiService.getTeamSchedule(any, any)).called(1);
    
    // Expect the coworker's shift to be visible
    expect(find.text('Test User'), findsOneWidget);
  });
}

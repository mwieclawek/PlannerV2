
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/models/models.dart';
import 'package:frontend/providers/providers.dart';
import 'package:frontend/screens/manager/home_tab.dart';
import 'package:frontend/services/api_service.dart';
import 'package:calendar_view/calendar_view.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';

import 'home_tab_test.mocks.dart';

import 'package:google_fonts/google_fonts.dart';
import 'package:intl/date_symbol_data_local.dart';

@GenerateMocks([ApiService])
void main() {
  late MockApiService mockApiService;

  setUp(() async {
    await initializeDateFormatting('pl_PL', null);
    GoogleFonts.config.allowRuntimeFetching = false;
    mockApiService = MockApiService();
    final TestWidgetsFlutterBinding binding = TestWidgetsFlutterBinding.ensureInitialized();
    binding.window.physicalSizeTestValue = const Size(1080, 1920);
    binding.window.devicePixelRatioTestValue = 1.0;
  });

  tearDown(() {
    final TestWidgetsFlutterBinding binding = TestWidgetsFlutterBinding.ensureInitialized();
    binding.window.clearPhysicalSizeTestValue();
    binding.window.clearDevicePixelRatioTestValue();
  });

  Widget createWidgetUnderTest() {
    return CalendarControllerProvider(
      controller: EventController(),
      child: ProviderScope(
        overrides: [
          apiServiceProvider.overrideWithValue(mockApiService),
        ],
        child: const MaterialApp(
          home: Scaffold(body: HomeTab()),
        ),
      ),
    );
  }

  testWidgets('HomeTab displays loading indicator initially', (WidgetTester tester) async {
    // Arrange
    when(mockApiService.getDashboardHome(date: anyNamed('date'))).thenAnswer(
      (_) async => Future.delayed(const Duration(seconds: 1), () => DashboardHome(workingToday: [], missingConfirmations: [], openGiveaways: [])),
    );

    // Act
    await tester.pumpWidget(createWidgetUnderTest());

    // Assert
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    
    // Drain the timer
    await tester.pump(const Duration(seconds: 1));
    await tester.pump();
  });

  testWidgets('HomeTab displays data when loaded', (WidgetTester tester) async {
    // Arrange
    final today = DateTime.now();
    final dashboardData = DashboardHome(
      workingToday: [
        ScheduleEntry(
          id: '1', date: today, shiftDefId: 1, userId: 'u1', roleId: 1, isPublished: true,
          userName: 'Janusz', roleName: 'Kucharz', shiftName: 'Rano', startTime: '08:00', endTime: '16:00',
        )
      ],
      missingConfirmations: [],
      openGiveaways: [],
    );

    when(mockApiService.getDashboardHome(date: anyNamed('date'))).thenAnswer((_) async => dashboardData);

    // Act
    await tester.pumpWidget(createWidgetUnderTest());
    await tester.pumpAndSettle(); // Wait for all animations and futures

    // Assert
    expect(find.text('Dzień dobry!'), findsOneWidget);
    expect(find.text('Dzisiaj w pracy'), findsOneWidget);
    // DayView constructs complex widgets, but we can verify our text appears
    // Note: DayView might render asynchronously or need size to layout.
    // In test environment, screen size is small.
  });
}

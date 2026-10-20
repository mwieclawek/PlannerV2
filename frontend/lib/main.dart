import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:google_fonts/google_fonts.dart';
import 'utils/router.dart';
import 'utils/scaffold_messenger.dart';

import 'services/config_service.dart';

import 'package:calendar_view/calendar_view.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_crashlytics/firebase_crashlytics.dart';
import 'package:flutter/foundation.dart';
import 'firebase_options_dev.dart' as dev_options;
import 'firebase_options_prod.dart' as prod_options;

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ConfigService().init();
  await initializeDateFormatting('pl_PL', null);

  const environment = String.fromEnvironment('ENV', defaultValue: 'dev');
  final firebaseOptions =
      environment == 'prod'
          ? prod_options.DefaultFirebaseOptions.currentPlatform
          : dev_options.DefaultFirebaseOptions.currentPlatform;

  try {
    await Firebase.initializeApp(options: firebaseOptions);
  } catch (e) {
    if (e is FirebaseException && e.code == 'duplicate-app') {
      debugPrint('Firebase already initialized natively.');
    } else if (e.toString().contains('duplicate-app')) {
      debugPrint('Firebase already initialized natively.');
    } else {
      rethrow;
    }
  }

  if (!kIsWeb) {
    // Pass all uncaught "fatal" errors from the framework to Crashlytics
    FlutterError.onError = (errorDetails) {
      FirebaseCrashlytics.instance.recordFlutterFatalError(errorDetails);
    };

    // Pass all uncaught asynchronous errors that aren't handled by the Flutter framework to Crashlytics
    PlatformDispatcher.instance.onError = (error, stack) {
      FirebaseCrashlytics.instance.recordError(error, stack, fatal: true);
      return true;
    };
  }

  runApp(
    CalendarControllerProvider(
      controller: EventController(),
      child: const ProviderScope(child: MyApp()),
    ),
  );
}

class MyApp extends ConsumerWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);

    final colorScheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFF0F5247), // Deep Teal / Forest Green
      primary: const Color(0xFF0F5247),
      surface: Colors.white,
      brightness: Brightness.light,
    );

    return MaterialApp.router(
      scaffoldMessengerKey: rootScaffoldMessengerKey,
      title: 'Planista',
      debugShowCheckedModeBanner: false,
      locale: const Locale('pl', 'PL'),
      supportedLocales: const [
        Locale('pl', 'PL'),
        Locale('en', 'US'),
      ],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      theme: ThemeData(
        colorScheme: colorScheme,
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFFF6F8F8), // Soft sage light background
        textTheme: GoogleFonts.interTextTheme(ThemeData.light().textTheme),
        cardTheme: CardTheme(
          color: Colors.white,
          surfaceTintColor: Colors.transparent,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: const BorderSide(color: Color(0xFFE2E8F0), width: 1),
          ),
        ),
        expansionTileTheme: const ExpansionTileThemeData(
          shape: Border(),
          collapsedShape: Border(),
        ),
        appBarTheme: AppBarTheme(
          centerTitle: false,
          elevation: 0,
          scrolledUnderElevation: 0,
          backgroundColor: const Color(0xFFF6F8F8),
          foregroundColor: const Color(0xFF0F172A),
          titleTextStyle: GoogleFonts.inter(
            fontSize: 20,
            fontWeight: FontWeight.w600,
            color: const Color(0xFF0F172A),
          ),
        ),
        filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(
            minimumSize: const Size(110, 42),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(10),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
          ),
        ),
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            minimumSize: const Size(110, 42),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(10),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: colorScheme.surfaceContainerLow,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: BorderSide.none,
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: BorderSide(color: colorScheme.outline.withValues(alpha: 0.3)),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: BorderSide(color: colorScheme.primary, width: 2),
          ),
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 14,
          ),
        ),
        chipTheme: ChipThemeData(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
        ),
        snackBarTheme: SnackBarThemeData(
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
        navigationBarTheme: NavigationBarThemeData(
          labelTextStyle: WidgetStateProperty.all(
            GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w500),
          ),
        ),
      ),
      routerConfig: router,
    );
  }
}

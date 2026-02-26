import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_analytics/firebase_analytics.dart';
import '../providers/providers.dart';
import '../screens/login_screen.dart';
import '../screens/employee/employee_dashboard.dart';
import '../screens/manager/manager_dashboard.dart';
import '../screens/server_setup_screen.dart';
import '../providers/config_provider.dart';

/// Listenable that notifies when auth state changes
class AuthNotifierListenable extends ChangeNotifier {
  AuthNotifierListenable(this._ref) {
    _ref.listen(authProvider, (_, __) {
      notifyListeners();
    });
  }

  final Ref _ref;
}

final authListenableProvider = Provider<AuthNotifierListenable>((ref) {
  return AuthNotifierListenable(ref);
});

final routerProvider = Provider<GoRouter>((ref) {
  final authListenable = ref.watch(authListenableProvider);

  return GoRouter(
    initialLocation: '/login',
    refreshListenable: authListenable,
    observers: [
      FirebaseAnalyticsObserver(analytics: FirebaseAnalytics.instance),
    ],
    redirect: (context, state) {
      final configUrl = ref.read(configProvider);
      final isSetupRoute = state.matchedLocation == '/setup';

      if (configUrl == null) {
        return isSetupRoute ? null : '/setup';
      }

      if (isSetupRoute) {
        return '/login';
      }

      final authState = ref.read(authProvider);
      final isLoading = authState.isLoading;
      final user = authState.value;
      final isLoggedIn = user != null;

      final isLoginRoute = state.matchedLocation == '/login';

      if (isLoading) {
        return null; // Wait for auth check
      }

      if (!isLoggedIn && !isLoginRoute) {
        return '/login';
      }

      if (isLoggedIn) {
        // Prevent employees from accessing manager routes
        if (!user.isManager && state.matchedLocation.startsWith('/manager')) {
          return '/employee';
        }

        if (isLoginRoute) {
          // Redirect based on role
          return user.isManager ? '/manager' : '/employee';
        }
      }

      return null;
    },
    routes: [
      GoRoute(
        path: '/setup',
        builder: (context, state) => const ServerSetupScreen(),
      ),
      GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
      GoRoute(
        path: '/employee',
        builder: (context, state) => const EmployeeDashboard(),
      ),
      GoRoute(
        path: '/manager',
        builder: (context, state) => const ManagerDashboard(),
      ),
    ],
  );
});

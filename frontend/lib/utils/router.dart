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

import '../providers/module_provider.dart';
import '../screens/pos/manager_setup_screen.dart';
import '../screens/pos/waiter_tables_screen.dart';
import '../screens/pos/kds_screen.dart';

/// Listenable that notifies when auth state or module state changes
class RouterNotifierListenable extends ChangeNotifier {
  RouterNotifierListenable(this._ref) {
    _ref.listen(authProvider, (_, __) {
      notifyListeners();
    });
    _ref.listen(moduleProvider, (_, __) {
      notifyListeners();
    });
  }

  final Ref _ref;
}

final routerListenableProvider = Provider<RouterNotifierListenable>((ref) {
  return RouterNotifierListenable(ref);
});

final routerProvider = Provider<GoRouter>((ref) {
  final routerListenable = ref.watch(routerListenableProvider);

  return GoRouter(
    initialLocation: '/login',
    refreshListenable: routerListenable,
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
        final activeModule = ref.read(moduleProvider);

        if (isLoginRoute) {
          if (activeModule == AppModule.planning) {
            return user.isManager ? '/manager' : '/employee';
          } else {
            return user.isManager ? '/pos/manager' : '/pos/waiter';
          }
        }

        // Module isolation redirects
        final isPosRoute = state.matchedLocation.startsWith('/pos');

        if (activeModule == AppModule.planning && isPosRoute) {
          return user.isManager ? '/manager' : '/employee';
        }

        if (activeModule == AppModule.posKds && !isPosRoute) {
          return user.isManager ? '/pos/manager' : '/pos/waiter';
        }

        // Role isolation redirects within modules
        if (activeModule == AppModule.planning) {
          if (!user.isManager && state.matchedLocation.startsWith('/manager')) {
            return '/employee';
          }
        } else {
          if (!user.isManager &&
              state.matchedLocation.startsWith('/pos/manager')) {
            return '/pos/waiter';
          }
        }
      }

      return null;
    },
    routes: [
      // Common Auth/Setup
      GoRoute(
        path: '/setup',
        builder: (context, state) => const ServerSetupScreen(),
      ),
      GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),

      // Module: Planning
      GoRoute(
        path: '/employee',
        builder: (context, state) => const EmployeeDashboard(),
      ),
      GoRoute(
        path: '/manager',
        builder: (context, state) => const ManagerDashboard(),
      ),

      // Module: POS & KDS
      GoRoute(
        path: '/pos/manager',
        builder: (context, state) => const ManagerSetupScreen(),
      ),
      GoRoute(
        path: '/pos/waiter',
        builder: (context, state) => const WaiterTablesScreen(),
      ),
      GoRoute(path: '/pos/kds', builder: (context, state) => const KdsScreen()),
    ],
  );
});

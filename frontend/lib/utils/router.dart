import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/providers.dart';
import '../screens/login_screen.dart';
import '../screens/employee/employee_dashboard.dart';
import '../screens/manager/manager_dashboard.dart';

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
    redirect: (context, state) {
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

      if (isLoggedIn && isLoginRoute) {
        // Redirect based on role
        if (user.isManager) {
          return '/manager';
        } else {
          return '/employee';
        }
      }

      return null;
    },
    routes: [
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginScreen(),
      ),
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


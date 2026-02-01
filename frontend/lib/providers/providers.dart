import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/api_service.dart';
import '../models/models.dart';

// API Service Provider
final apiServiceProvider = Provider<ApiService>((ref) => ApiService());

// Current User Provider
final currentUserProvider = FutureProvider<User?>((ref) async {
  final api = ref.watch(apiServiceProvider);
  try {
    final isLoggedIn = await api.isLoggedIn();
    if (!isLoggedIn) return null;
    return await api.getCurrentUser();
  } catch (e) {
    return null;
  }
});

// Roles Provider
final rolesProvider = FutureProvider<List<JobRole>>((ref) async {
  final api = ref.watch(apiServiceProvider);
  return await api.getRoles();
});

// Shifts Provider
final shiftsProvider = FutureProvider<List<ShiftDefinition>>((ref) async {
  final api = ref.watch(apiServiceProvider);
  return await api.getShifts();
});

// Availability Provider (for a specific week)
final availabilityProvider = FutureProvider.family<List<Availability>, DateRange>((ref, dateRange) async {
  final api = ref.watch(apiServiceProvider);
  return await api.getAvailability(dateRange.start, dateRange.end);
});

class DateRange {
  final DateTime start;
  final DateTime end;

  DateRange(this.start, this.end);

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is DateRange && runtimeType == other.runtimeType && start == other.start && end == other.end;

  @override
  int get hashCode => start.hashCode ^ end.hashCode;
}

// Auth State Notifier
class AuthNotifier extends StateNotifier<AsyncValue<User?>> {
  final ApiService _api;

  AuthNotifier(this._api) : super(const AsyncValue.loading()) {
    _checkAuth();
  }

  Future<void> _checkAuth() async {
    state = const AsyncValue.loading();
    try {
      final isLoggedIn = await _api.isLoggedIn();
      if (isLoggedIn) {
        try {
          final user = await _api.getCurrentUser();
          state = AsyncValue.data(user);
        } catch (e) {
          // If token is invalid (401) or other error, treat as logged out
          await _api.logout();
          state = const AsyncValue.data(null);
        }
      } else {
        state = const AsyncValue.data(null);
      }
    } catch (e, stack) {
      // Fallback for unexpected errors
      state = const AsyncValue.data(null);
    }
  }

  Future<void> login(String email, String password) async {
    state = const AsyncValue.loading();
    try {
      await _api.login(email, password);
      final user = await _api.getCurrentUser();
      state = AsyncValue.data(user);
    } catch (e, stack) {
      state = const AsyncValue.data(null);
      rethrow; // Rethrow so UI can show SnackBar
    }
  }

  Future<void> register(String email, String password, String fullName, String roleSystem, {String? managerPin}) async {
    state = const AsyncValue.loading();
    try {
      await _api.register(email, password, fullName, roleSystem, managerPin: managerPin);
      final user = await _api.getCurrentUser();
      state = AsyncValue.data(user);
    } catch (e, stack) {
      state = const AsyncValue.data(null);
      rethrow; // Rethrow so UI can show SnackBar
    }
  }

  Future<void> logout() async {
    await _api.logout();
    state = const AsyncValue.data(null);
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AsyncValue<User?>>((ref) {
  final api = ref.watch(apiServiceProvider);
  return AuthNotifier(api);
});

// Track unsaved changes in scheduler (for warning on tab switch/exit)
final hasUnsavedScheduleChangesProvider = StateProvider<bool>((ref) => false);

import 'package:flutter/foundation.dart';
import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/models.dart';
import '../utils/api_error_handler.dart';

class ApiService {
  final String baseUrl;
  final Dio _dio;
  String? _memoryAccessToken;
  String? _memoryRefreshToken;
  bool _isRefreshing = false;

  ApiService(this.baseUrl) : _dio = Dio(BaseOptions(baseUrl: baseUrl)) {
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          // Skip auth for login/register/refresh
          if (options.path.contains('/auth/token') ||
              options.path.contains('/auth/register') ||
              options.path.contains('/auth/refresh')) {
            return handler.next(options);
          }

          try {
            final prefs = await SharedPreferences.getInstance();
            final token = prefs.getString('access_token') ?? _memoryAccessToken;
            if (token != null) {
              options.headers['Authorization'] = 'Bearer $token';
            }
          } catch (e) {
            if (_memoryAccessToken != null) {
              options.headers['Authorization'] = 'Bearer $_memoryAccessToken';
            }
            debugPrint('Error getting token: $e');
          }
          return handler.next(options);
        },
        onError: (error, handler) async {
          final isAuthEndpoint = error.requestOptions.path.contains('/auth/token') ||
              error.requestOptions.path.contains('/auth/refresh') ||
              error.requestOptions.path.contains('/auth/register');

          if (error.response?.statusCode == 401 &&
              !isAuthEndpoint &&
              error.requestOptions.extra['_retried'] != true &&
              !_isRefreshing) {
            _isRefreshing = true;
            try {
              final prefs = await SharedPreferences.getInstance();
              final refreshToken =
                  prefs.getString('refresh_token') ?? _memoryRefreshToken;
              final rememberMe = prefs.getBool('remember_me') ?? true;

              if (refreshToken != null && refreshToken.isNotEmpty) {
                final refreshDio = Dio(BaseOptions(baseUrl: baseUrl));
                final refreshRes = await refreshDio.post(
                  '/auth/refresh',
                  options: Options(
                    headers: {'Authorization': 'Bearer $refreshToken'},
                  ),
                );
                final newAccess = refreshRes.data['access_token'] as String?;
                final newRefresh = refreshRes.data['refresh_token'] as String?;
                if (newAccess != null && newAccess.isNotEmpty) {
                  _memoryAccessToken = newAccess;
                  if (newRefresh != null && newRefresh.isNotEmpty) {
                    _memoryRefreshToken = newRefresh;
                  }
                  if (rememberMe) {
                    await prefs.setString('access_token', newAccess);
                    if (newRefresh != null && newRefresh.isNotEmpty) {
                      await prefs.setString('refresh_token', newRefresh);
                    }
                  }
                  _isRefreshing = false;
                  final retryOpts = error.requestOptions;
                  retryOpts.headers['Authorization'] = 'Bearer $newAccess';
                  retryOpts.extra['_retried'] = true;
                  final retryResponse = await _dio.fetch(retryOpts);
                  return handler.resolve(retryResponse);
                }
              }
            } catch (refreshErr) {
              debugPrint('Token refresh failed: $refreshErr');
            } finally {
              _isRefreshing = false;
            }

            try {
              _memoryAccessToken = null;
              _memoryRefreshToken = null;
              final prefs = await SharedPreferences.getInstance();
              await prefs.remove('access_token');
              await prefs.remove('refresh_token');
            } catch (e) {
              debugPrint('Error removing token: $e');
            }
          }
          final friendly = FriendlyDioException.fromDioException(error);
          return handler.next(friendly);
        },
      ),
    );
  }

  /// Authenticated HTTP client (token injection + 401 handling) shared with
  /// feature-specific services such as SysAdminService.
  Dio get client => _dio;

  // Auth
  Future<String> login(
    String email,
    String password, {
    String? tenantSlug,
    bool rememberMe = true,
  }) async {
    final response = await _dio.post(
      '/auth/token',
      data: {'username': email, 'password': password},
      options: Options(
        contentType: Headers.formUrlEncodedContentType,
        headers: {
          if (tenantSlug != null && tenantSlug.isNotEmpty)
            'X-Tenant-Slug': tenantSlug,
        },
      ),
    );
    final token = response.data['access_token'] as String;
    final refreshToken = response.data['refresh_token'] as String?;
    _memoryAccessToken = token;
    _memoryRefreshToken = refreshToken;

    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('remember_me', rememberMe);
    if (rememberMe) {
      await prefs.setString('access_token', token);
      if (refreshToken != null) {
        await prefs.setString('refresh_token', refreshToken);
      }
    } else {
      await prefs.remove('access_token');
      await prefs.remove('refresh_token');
    }
    return token;
  }

  Future<String> register(
    String username,
    String password,
    String fullName,
    String roleSystem, {
    String? managerPin,
  }) async {
    final data = {
      'username': username,
      'password': password,
      'full_name': fullName,
      'role_system': roleSystem,
    };
    if (managerPin != null && managerPin.isNotEmpty) {
      data['manager_pin'] = managerPin;
    }
    final response = await _dio.post('/auth/register', data: data);
    final token = response.data['access_token'];
    _memoryAccessToken = token;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('access_token', token);
    return token;
  }

  Future<User> getCurrentUser() async {
    final response = await _dio.get('/auth/me');
    return User.fromJson(response.data);
  }

  Future<User> updateMyProfile({String? email, String? fullName}) async {
    final data = <String, dynamic>{};
    if (email != null) data['email'] = email;
    if (fullName != null) data['full_name'] = fullName;
    final response = await _dio.put('/auth/me', data: data);
    return User.fromJson(response.data);
  }

  Future<void> logout() async {
    _memoryAccessToken = null;
    _memoryRefreshToken = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('access_token');
    await prefs.remove('refresh_token');
  }

  Future<void> changePassword(String oldPassword, String newPassword) async {
    await _dio.put(
      '/auth/change-password',
      data: {'old_password': oldPassword, 'new_password': newPassword},
    );
  }

  // Roles
  Future<List<JobRole>> getRoles() async {
    final response = await _dio.get('/manager/roles');
    return (response.data as List).map((e) => JobRole.fromJson(e)).toList();
  }

  Future<JobRole> createRole(
    String name,
    String colorHex, {
    double? hourlyRate,
  }) async {
    final response = await _dio.post(
      '/manager/roles',
      data: {
        'name': name,
        'color_hex': colorHex,
        if (hourlyRate != null) 'hourly_rate': hourlyRate,
      },
    );
    return JobRole.fromJson(response.data);
  }

  // Shifts
  Future<List<ShiftDefinition>> getShifts({bool allShifts = false}) async {
    final response = await _dio.get(
      '/manager/shifts',
      queryParameters: allShifts ? {'all_shifts': 'true'} : null,
    );
    return (response.data as List)
        .map((e) => ShiftDefinition.fromJson(e))
        .toList();
  }

  Future<ShiftDefinition> createShift(
    String name,
    String startTime,
    String endTime, {
    List<int>? applicableDays,
    List<int>? allowedRoleIds,
  }) async {
    final response = await _dio.post(
      '/manager/shifts',
      data: {
        'name': name,
        'start_time': startTime,
        'end_time': endTime,
        'applicable_days': applicableDays ?? [0, 1, 2, 3, 4, 5, 6],
        'allowed_role_ids': allowedRoleIds ?? [],
      },
    );
    return ShiftDefinition.fromJson(response.data);
  }

  // Availability (Employee)
  Future<List<Availability>> getAvailability(
    DateTime startDate,
    DateTime endDate,
  ) async {
    final response = await _dio.get(
      '/employee/availability',
      queryParameters: {
        'start_date': startDate.toIso8601String().split('T')[0],
        'end_date': endDate.toIso8601String().split('T')[0],
      },
    );
    return (response.data as List)
        .map((e) => Availability.fromJson(e))
        .toList();
  }

  Future<void> updateAvailability(List<AvailabilityUpdate> updates) async {
    await _dio.post(
      '/employee/availability',
      data: updates.map((e) => e.toJson()).toList(),
    );
  }

  // Scheduler (Manager)
  Future<Map<String, dynamic>> generateSchedule(
    DateTime startDate,
    DateTime endDate,
  ) async {
    final response = await _dio.post(
      '/scheduler/generate',
      data: {
        'start_date': startDate.toIso8601String().split('T')[0],
        'end_date': endDate.toIso8601String().split('T')[0],
      },
    );
    return response.data;
  }

  // Requirements (Manager)
  Future<List<Requirement>> getRequirements(
    DateTime startDate,
    DateTime endDate,
  ) async {
    final response = await _dio.get(
      '/manager/requirements',
      queryParameters: {
        'start_date': startDate.toIso8601String().split('T')[0],
        'end_date': endDate.toIso8601String().split('T')[0],
      },
    );
    return (response.data as List).map((e) => Requirement.fromJson(e)).toList();
  }

  Future<void> setRequirements(List<RequirementUpdate> requirements) async {
    await _dio.post(
      '/manager/requirements',
      data: requirements.map((e) => e.toJson()).toList(),
    );
  }

  // Schedule viewing (Manager)
  Future<List<ScheduleEntry>> getManagerSchedule(
    DateTime startDate,
    DateTime endDate,
  ) async {
    final response = await _dio.get(
      '/scheduler/list',
      queryParameters: {
        'start_date': startDate.toIso8601String().split('T')[0],
        'end_date': endDate.toIso8601String().split('T')[0],
      },
    );
    return (response.data as List)
        .map((e) => ScheduleEntry.fromJson(e))
        .toList();
  }

  // Schedule viewing (Employee)
  Future<List<EmployeeScheduleEntry>> getEmployeeSchedule(
    DateTime startDate,
    DateTime endDate,
  ) async {
    final response = await _dio.get(
      '/employee/my-schedule',
      queryParameters: {
        'start_date': startDate.toIso8601String().split('T')[0],
        'end_date': endDate.toIso8601String().split('T')[0],
      },
    );
    return (response.data as List)
        .map((e) => EmployeeScheduleEntry.fromJson(e))
        .toList();
  }

  Future<List<ScheduleEntry>> getTeamSchedule(
    DateTime startDate,
    DateTime endDate,
  ) async {
    final response = await _dio.get(
      '/employee/schedules/all',
      queryParameters: {
        'start_date': startDate.toIso8601String().split('T')[0],
        'end_date': endDate.toIso8601String().split('T')[0],
      },
    );
    return (response.data as List)
        .map((e) => ScheduleEntry.fromJson(e))
        .toList();
  }

  // Check if user is logged in
  Future<bool> isLoggedIn() async {
    if (_memoryAccessToken != null && _memoryAccessToken!.isNotEmpty) {
      return true;
    }
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('access_token');
    return token != null && token.isNotEmpty;
  }

  // Team Management (Manager)
  Future<List<TeamMember>> getUsers({bool includeInactive = false}) async {
    final response = await _dio.get(
      '/manager/users',
      queryParameters: {if (includeInactive) 'include_inactive': true},
    );
    return (response.data as List).map((e) => TeamMember.fromJson(e)).toList();
  }

  Future<void> setUserRoles(String userId, List<int> roleIds) async {
    // Using PUT endpoint which clears existing roles and sets new ones
    await _dio.put('/manager/users/$userId/roles', data: {'role_ids': roleIds});
  }

  Future<void> resetUserPassword(String userId, String newPassword) async {
    await _dio.put(
      '/manager/users/$userId/password',
      data: {'new_password': newPassword},
    );
  }

  Future<void> updateUser(
    String userId, {
    String? fullName,
    String? email,
    String? roleSystem,
    int? targetHoursPerMonth,
    int? targetShiftsPerMonth,
    double? hourlyRate,
    bool? isActive,
    bool clearTargets = false,
    bool clearHourlyRate = false,
  }) async {
    final Map<String, dynamic> data = {};
    if (fullName != null) data['full_name'] = fullName;
    if (email != null) data['email'] = email;
    if (roleSystem != null) data['role_system'] = roleSystem;
    if (isActive != null) data['is_active'] = isActive;
    if (clearHourlyRate) {
      data['hourly_rate'] = null;
    } else if (hourlyRate != null) {
      data['hourly_rate'] = hourlyRate;
    }

    if (clearTargets) {
      data['target_hours_per_month'] = null;
      data['target_shifts_per_month'] = null;
    } else {
      if (targetHoursPerMonth != null) {
        data['target_hours_per_month'] = targetHoursPerMonth;
      }
      if (targetShiftsPerMonth != null) {
        data['target_shifts_per_month'] = targetShiftsPerMonth;
      }
    }

    await _dio.put('/manager/users/$userId', data: data);
  }

  Future<void> createUser({
    required String username,
    required String password,
    required String fullName,
    required String roleSystem,
    String? email,
    int? targetHoursPerMonth,
    int? targetShiftsPerMonth,
    double? hourlyRate,
  }) async {
    await _dio.post(
      '/manager/users',
      data: {
        'username': username,
        'password': password,
        'full_name': fullName,
        'role_system': roleSystem,
        if (email != null && email.isNotEmpty) 'email': email,
        if (targetHoursPerMonth != null)
          'target_hours_per_month': targetHoursPerMonth,
        if (targetShiftsPerMonth != null)
          'target_shifts_per_month': targetShiftsPerMonth,
        if (hourlyRate != null) 'hourly_rate': hourlyRate,
      },
    );
  }

  // Manual Schedule Editing
  Future<void> createAssignment({
    required DateTime date,
    required int shiftDefId,
    required String userId,
    required int roleId,
  }) async {
    await _dio.post(
      '/scheduler/assignment',
      data: {
        'date': date.toIso8601String().split('T').first,
        'shift_def_id': shiftDefId,
        'user_id': userId,
        'role_id': roleId,
      },
    );
  }

  Future<void> deleteAssignment(String scheduleId) async {
    await _dio.delete('/scheduler/assignment/$scheduleId');
  }

  // Role Management
  Future<void> deleteRole(int roleId) async {
    await _dio.delete('/manager/roles/$roleId');
  }

  // Shift Management
  Future<void> deleteShift(int shiftId) async {
    await _dio.delete('/manager/shifts/$shiftId');
  }

  // Batch Schedule Save
  Future<void> saveBatchSchedule(
    DateTime startDate,
    DateTime endDate,
    List<ScheduleEntry> entries,
  ) async {
    final data =
        entries
            .map(
              (e) => {
                'date': e.date.toIso8601String().split('T').first,
                'shift_def_id': e.shiftDefId,
                'user_id': e.userId,
                'role_id': e.roleId,
              },
            )
            .toList();

    await _dio.post(
      '/scheduler/save_batch',
      data: {
        'start_date': startDate.toIso8601String().split('T').first,
        'end_date': endDate.toIso8601String().split('T').first,
        'items': data,
      },
    );
  }

  // Publish Schedule (Manager)
  Future<Map<String, dynamic>> publishSchedule(
    DateTime startDate,
    DateTime endDate,
  ) async {
    final sStr = startDate.toIso8601String().split('T').first;
    final eStr = endDate.toIso8601String().split('T').first;
    final response = await _dio.post(
      '/manager/schedules/publish',
      queryParameters: {'start_date': sStr, 'end_date': eStr},
      data: {'start_date': sStr, 'end_date': eStr},
    );
    return response.data as Map<String, dynamic>;
  }

  // Update Role
  Future<void> updateRole(
    int roleId,
    String name,
    String colorHex, {
    double? hourlyRate,
  }) async {
    await _dio.put(
      '/manager/roles/$roleId',
      data: {
        'name': name,
        'color_hex': colorHex,
        if (hourlyRate != null) 'hourly_rate': hourlyRate,
      },
    );
  }

  // Update Shift
  Future<void> updateShift(
    int shiftId,
    String name,
    String startTime,
    String endTime,
    List<int> applicableDays,
    List<int> allowedRoleIds,
  ) async {
    await _dio.put(
      '/manager/shifts/$shiftId',
      data: {
        'name': name,
        'start_time': startTime,
        'end_time': endTime,
        'applicable_days': applicableDays,
        'allowed_role_ids': allowedRoleIds,
      },
    );
  }

  // Admin System Settings (Kill Switch / Maintenance Mode)
  Future<Map<String, dynamic>> getAdminSettings() async {
    final response = await _dio.get('/api/admin/settings');
    return response.data;
  }

  Future<Map<String, dynamic>> updateAdminSettings({
    bool? isLoginEnabled,
    String? blockedLoginMessage,
  }) async {
    final data = <String, dynamic>{};
    if (isLoginEnabled != null) data['is_login_enabled'] = isLoginEnabled;
    if (blockedLoginMessage != null) {
      data['blocked_login_message'] = blockedLoginMessage;
    }
    final response = await _dio.put('/api/admin/settings', data: data);
    return response.data;
  }

  // App Settings
  Future<Map<String, dynamic>> updateAppSettings(
    Map<String, dynamic> settings,
  ) async {
    final response = await _dio.put('/manager/settings', data: settings);
    return response.data;
  }


  // --- Notifications ---
  // (FCM Token Registration)
  Future<void> registerDeviceToken(String token) async {
    try {
      await _dio.post('/api/notifications/devices', data: {'token': token});
    } catch (e) {
      print('Wystąpił błąd podczas rejestrowania tokena urządzenia: $e');
      // Non-fatal, dont throw
    }
  }

  Future<void> unregisterDeviceToken(String token) async {
    try {
      await _dio.delete('/api/notifications/devices/$token');
    } catch (e) {
      print('Wystąpił błąd podczas usuwania tokena urządzenia: $e');
      // Non-fatal
    }
  }

  Future<List<AppNotification>> getNotifications() async {
    final response = await _dio.get('/api/notifications');
    return (response.data as List)
        .map((e) => AppNotification.fromJson(e))
        .toList();
  }

  Future<void> markNotificationRead(String id) async {
    await _dio.patch('/api/notifications/$id/read');
  }

  // Restaurant Config
  Future<Map<String, dynamic>> getConfig() async {
    final response = await _dio.get('/manager/config');
    return response.data;
  }

  Future<Map<String, dynamic>> getEmployeeRestaurantConfig() async {
    final response = await _dio.get('/employee/config');
    return response.data as Map<String, dynamic>;
  }

  Future<void> saveConfig(
    String name,
    String openingHours,
    String? address, {
    bool? posEnabled,
    bool? requireAttendanceRegistration,
    String? attendanceRequiredFrom,
    bool clearAttendanceRequiredFrom = false,
    bool? enableTipPool,
    bool? requireChecklists,
  }) async {
    final data = <String, dynamic>{
      'name': name,
      'opening_hours': openingHours,
      'address': address,
    };
    if (posEnabled != null) data['pos_enabled'] = posEnabled;
    if (requireAttendanceRegistration != null) {
      data['require_attendance_registration'] = requireAttendanceRegistration;
    }
    if (clearAttendanceRequiredFrom) {
      data['attendance_required_from'] = null;
    } else if (attendanceRequiredFrom != null) {
      data['attendance_required_from'] = attendanceRequiredFrom;
    }
    if (enableTipPool != null) {
      data['enable_tip_pool'] = enableTipPool;
    }
    if (requireChecklists != null) {
      data['require_checklists'] = requireChecklists;
    }
    await _dio.post('/manager/config', data: data);
  }

  // Team Availability (Manager)
  Future<List<TeamAvailability>> getTeamAvailability(
    DateTime weekStart,
    DateTime weekEnd,
  ) async {
    final response = await _dio.get(
      '/manager/availability',
      queryParameters: {
        'week_start': weekStart.toIso8601String().split('T')[0],
        'week_end': weekEnd.toIso8601String().split('T')[0],
      },
    );
    return (response.data as List)
        .map((e) => TeamAvailability.fromJson(e))
        .toList();
  }

  // Attendance (Employee)
  Future<Map<String, dynamic>> getMissingAttendance() async {
    final response = await _dio.get('/employee/attendance/missing');
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getAttendanceDefaults(DateTime date) async {
    final response = await _dio.get(
      '/employee/attendance/defaults/${date.toIso8601String().split('T')[0]}',
    );
    return response.data;
  }

  Future<Map<String, dynamic>> registerAttendance(
    DateTime date,
    String checkIn,
    String checkOut, {
    String? checklistSkipReason,
    bool isAbsent = false,
    String? absenceReason,
  }) async {
    final response = await _dio.post(
      '/employee/attendance',
      queryParameters: {
        'target_date': date.toIso8601String().split('T')[0],
        'check_in': checkIn,
        'check_out': checkOut,
        if (checklistSkipReason != null && checklistSkipReason.isNotEmpty)
          'checklist_skip_reason': checklistSkipReason,
        'is_absent': isAbsent,
        if (absenceReason != null && absenceReason.isNotEmpty)
          'absence_reason': absenceReason,
      },
    );
    return response.data;
  }

  Future<void> registerManualAttendance({
    required String userId,
    required DateTime date,
    required String checkIn,
    required String checkOut,
    bool wasScheduled = true,
    String status = 'CONFIRMED',
  }) async {
    await _dio.post(
      '/manager/attendance',
      data: {
        'user_id': userId,
        'date': date.toIso8601String().split('T')[0],
        'check_in': checkIn,
        'check_out': checkOut,
        'was_scheduled': wasScheduled,
        'status': status,
      },
    );
  }

  Future<List<Map<String, dynamic>>> getMyAttendance(
    DateTime startDate,
    DateTime endDate,
  ) async {
    final response = await _dio.get(
      '/employee/attendance/my',
      queryParameters: {
        'start_date': startDate.toIso8601String().split('T')[0],
        'end_date': endDate.toIso8601String().split('T')[0],
      },
    );
    return (response.data as List).cast<Map<String, dynamic>>();
  }

  // Attendance (Manager)
  Future<List<Map<String, dynamic>>> getPendingAttendance() async {
    final response = await _dio.get('/manager/attendance/pending');
    return (response.data as List).cast<Map<String, dynamic>>();
  }

  Future<void> confirmAttendance(String attendanceId) async {
    await _dio.put('/manager/attendance/$attendanceId/confirm');
  }

  Future<void> rejectAttendance(String attendanceId) async {
    await _dio.put('/manager/attendance/$attendanceId/reject');
  }

  Future<List<Map<String, dynamic>>> getAllAttendance(
    DateTime startDate,
    DateTime endDate, {
    String? status,
  }) async {
    final params = {
      'start_date': startDate.toIso8601String().split('T')[0],
      'end_date': endDate.toIso8601String().split('T')[0],
      if (status != null) 'status': status,
    };
    final response = await _dio.get(
      '/manager/attendance',
      queryParameters: params,
    );
    return (response.data as List).cast<Map<String, dynamic>>();
  }

  Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('access_token');
  }

  String getAttendanceExportUrl(
    DateTime startDate,
    DateTime endDate, {
    String? status,
    String? token,
  }) {
    final start = startDate.toIso8601String().split('T')[0];
    final end = endDate.toIso8601String().split('T')[0];
    String url =
        '$baseUrl/manager/attendance/export?start_date=$start&end_date=$end';
    if (status != null) {
      url += '&status=$status';
    }
    if (token != null) {
      url += '&token=$token';
    }
    return url;
  }

  Future<List<Map<String, dynamic>>> getEmployeeHours(
    int month,
    int year,
  ) async {
    final response = await _dio.get(
      '/manager/employee-hours',
      queryParameters: {'month': month, 'year': year},
    );
    return (response.data as List).cast<Map<String, dynamic>>();
  }

  // New features
  Future<UserStats> getUserStats(String userId) async {
    final response = await _dio.get('/manager/users/$userId/stats');
    return UserStats.fromJson(response.data);
  }

  Future<DashboardHome> getDashboardHome({DateTime? date}) async {
    final Map<String, dynamic> queryParameters = {};
    if (date != null) {
      queryParameters['date'] = date.toIso8601String().split('T')[0];
    }
    final response = await _dio.get(
      '/manager/dashboard/home',
      queryParameters: queryParameters,
    );
    return DashboardHome.fromJson(response.data);
  }

  // --- Shift Giveaway ---
  Future<List<ShiftGiveaway>> getGiveaways() async {
    final response = await _dio.get('/manager/giveaways');
    return (response.data as List)
        .map((e) => ShiftGiveaway.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<void> reassignGiveaway(String giveawayId, String newUserId) async {
    await _dio.post(
      '/manager/giveaways/$giveawayId/reassign',
      data: {'new_user_id': newUserId},
    );
  }

  Future<void> cancelGiveaway(String giveawayId) async {
    await _dio.delete('/manager/giveaways/$giveawayId');
  }

  // --- Bug Reporting ---
  Future<Map<String, dynamic>> submitBugReport({
    required String title,
    required String description,
    String steps = '',
  }) async {
    final response = await _dio.post(
      '/api/bug-report',
      data: {
        'title': title,
        'description': description,
        'steps_to_reproduce': steps,
      },
    );
    return response.data as Map<String, dynamic>;
  }

  Future<void> giveAwayShift(String scheduleId, {String? targetShiftId}) async {
    await _dio.post(
      '/employee/giveaway/$scheduleId',
      data: targetShiftId != null ? {'target_shift_id': targetShiftId} : null,
    );
  }

  Future<Map<String, dynamic>> validateSwap(
    String offeredScheduleId,
    String targetScheduleId,
  ) async {
    final response = await _dio.get(
      '/employee/giveaways/validate-swap',
      queryParameters: {
        'offered_schedule_id': offeredScheduleId,
        'target_schedule_id': targetScheduleId,
      },
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<List<Map<String, dynamic>>> getShiftAuditLog(String shiftId) async {
    final response = await _dio.get('/manager/shifts/$shiftId/audit-log');
    return (response.data as List).map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  // --- Google Calendar Integration ---
  Future<Map<String, dynamic>> getGoogleCalendarStatus() async {
    final response = await _dio.get('/employee/google-calendar/status');
    return response.data;
  }

  Future<Map<String, dynamic>> connectGoogleCalendar(String authCode) async {
    final response = await _dio.post(
      '/employee/google-calendar/auth',
      data: {'auth_code': authCode},
    );
    return response.data is Map<String, dynamic> ? response.data : {};
  }

  Future<void> disconnectGoogleCalendar() async {
    await _dio.delete('/employee/google-calendar/auth');
  }

  Future<Map<String, dynamic>> syncGoogleCalendar() async {
    final response = await _dio.post('/employee/google-calendar/sync');
    return response.data;
  }


  // --- Leave Requests (Employee) ---
  Future<List<LeaveRequest>> getMyLeaveRequests({String? status}) async {
    final params = <String, dynamic>{};
    if (status != null) params['status'] = status;
    final response = await _dio.get(
      '/employee/leave-requests',
      queryParameters: params,
    );
    return (response.data as List)
        .map((e) => LeaveRequest.fromJson(e))
        .toList();
  }

  Future<void> createLeaveRequest(
    DateTime startDate,
    DateTime endDate,
    String? reason,
  ) async {
    await _dio.post(
      '/employee/leave-requests',
      data: {
        'start_date': startDate.toIso8601String().split('T')[0],
        'end_date': endDate.toIso8601String().split('T')[0],
        'reason': reason,
      },
    );
  }

  Future<void> cancelLeaveRequest(String requestId) async {
    await _dio.delete('/employee/leave-requests/$requestId');
  }

  // --- Leave Requests (Manager) ---
  Future<List<LeaveRequest>> getAllLeaveRequests({String? status}) async {
    final params = <String, dynamic>{};
    if (status != null) params['status'] = status;
    final response = await _dio.get(
      '/manager/leave-requests',
      queryParameters: params,
    );
    return (response.data as List)
        .map((e) => LeaveRequest.fromJson(e))
        .toList();
  }

  Future<void> approveLeaveRequest(String requestId) async {
    await _dio.post('/manager/leave-requests/$requestId/approve');
  }

  Future<void> rejectLeaveRequest(String requestId) async {
    await _dio.post('/manager/leave-requests/$requestId/reject');
  }

  Future<List<LeaveCalendarEntry>> getLeaveCalendar(int year, int month) async {
    final response = await _dio.get(
      '/manager/leave-requests/calendar',
      queryParameters: {'year': year, 'month': month},
    );
    return (response.data['entries'] as List)
        .map((e) => LeaveCalendarEntry.fromJson(e))
        .toList();
  }

  Future<List<AvailableEmployee>> getAvailableEmployeesForShift(
    DateTime date,
    int shiftDefId,
  ) async {
    final response = await _dio.get(
      '/manager/schedules/available-employees',
      queryParameters: {
        'date': date.toIso8601String().split('T')[0],
        'shift_def_id': shiftDefId,
      },
    );
    return (response.data as List)
        .map((e) => AvailableEmployee.fromJson(e))
        .toList();
  }

  // --- Schedule Summary (Employee) ---
  Future<Map<String, dynamic>> getScheduleSummary({
    required int year,
    required int month,
    required DateTime weekStart,
    required DateTime weekEnd,
  }) async {
    final response = await _dio.get(
      '/employee/schedule-summary',
      queryParameters: {
        'year': year,
        'month': month,
        'week_start': weekStart.toIso8601String().split('T')[0],
        'week_end': weekEnd.toIso8601String().split('T')[0],
      },
    );
    return response.data as Map<String, dynamic>;
  }

  // --- Employee Giveaways ---
  Future<List<Map<String, dynamic>>> getEmployeeGiveaways() async {
    final response = await _dio.get('/employee/giveaways');
    return (response.data as List).cast<Map<String, dynamic>>();
  }

  Future<void> claimGiveaway(String giveawayId) async {
    await _dio.post('/employee/giveaways/$giveawayId/claim');
  }

  Future<void> cancelEmployeeGiveaway(String giveawayId) async {
    await _dio.delete('/employee/giveaway/$giveawayId');
  }

  // ── POS & Kitchen ────────────────────────────────────────────────────────

  // Tables
  Future<List<RestaurantTable>> getTables({
    bool includeInactive = false,
  }) async {
    final response = await _dio.get(
      '/kitchen/tables',
      queryParameters: {if (includeInactive) 'include_inactive': true},
    );
    return (response.data as List)
        .map((e) => RestaurantTable.fromJson(e))
        .toList();
  }

  Future<RestaurantTable> createTable(String name) async {
    final response = await _dio.post('/kitchen/tables', data: {'name': name});
    return RestaurantTable.fromJson(response.data);
  }

  Future<void> deleteTable(String tableId) async {
    await _dio.delete('/kitchen/tables/$tableId');
  }

  // Menu
  Future<List<MenuItem>> getMenu({
    String? category,
    bool includeInactive = false,
  }) async {
    final Map<String, dynamic> params = {};
    if (category != null) params['category'] = category;
    if (includeInactive) params['include_inactive'] = true;
    final response = await _dio.get('/kitchen/menu', queryParameters: params);
    return (response.data as List).map((e) => MenuItem.fromJson(e)).toList();
  }

  Future<MenuItem> createMenuItem(
    String name,
    double price,
    String category,
  ) async {
    final response = await _dio.post(
      '/kitchen/menu',
      data: {'name': name, 'price': price, 'category': category},
    );
    return MenuItem.fromJson(response.data);
  }

  Future<MenuItem> updateMenuItem(
    String itemId,
    Map<String, dynamic> data,
  ) async {
    final response = await _dio.put('/kitchen/menu/$itemId', data: data);
    return MenuItem.fromJson(response.data);
  }

  Future<void> deleteMenuItem(String itemId) async {
    await _dio.delete('/kitchen/menu/$itemId');
  }

  // Orders
  Future<KitchenOrder> createOrder(
    String tableId,
    List<Map<String, dynamic>> items,
  ) async {
    final response = await _dio.post(
      '/kitchen/orders',
      data: {'table_id': tableId, 'items': items},
    );
    return KitchenOrder.fromJson(response.data);
  }

  Future<List<KitchenOrder>> getOrders({
    String? tableId,
    String? status,
  }) async {
    final Map<String, dynamic> params = {};
    if (tableId != null) params['table_id'] = tableId;
    if (status != null) params['status'] = status;
    final response = await _dio.get('/kitchen/orders', queryParameters: params);
    return (response.data as List)
        .map((e) => KitchenOrder.fromJson(e))
        .toList();
  }

  Future<KitchenOrder> updateOrderStatus(String orderId, String status) async {
    final response = await _dio.patch(
      '/kitchen/orders/$orderId/status',
      data: {'status': status},
    );
    return KitchenOrder.fromJson(response.data);
  }

  Future<KitchenOrder> cancelOrder(String orderId) async {
    final response = await _dio.delete('/kitchen/orders/$orderId');
    return KitchenOrder.fromJson(response.data);
  }

  // ── POS v2 API ──────────────────────────────────────────────────────────────

  // Zones
  Future<List<TableZone>> getZones() async {
    final response = await _dio.get('/pos/v2/zones');
    return (response.data as List).map((e) => TableZone.fromJson(e)).toList();
  }

  Future<TableZone> createZone(String name, {int sortOrder = 0}) async {
    final response = await _dio.post('/pos/v2/zones',
        data: {'name': name, 'sort_order': sortOrder});
    return TableZone.fromJson(response.data);
  }

  // Tables v2
  Future<List<PosTable>> getTablesV2({String? zoneId, String? status}) async {
    final params = <String, dynamic>{};
    if (zoneId != null) params['zone_id'] = zoneId;
    if (status != null) params['status'] = status;
    final response = await _dio.get('/pos/v2/tables', queryParameters: params);
    return (response.data as List).map((e) => PosTable.fromJson(e)).toList();
  }

  Future<PosTable> createTableV2(String name,
      {String? zoneId, int seats = 4, int sortOrder = 0}) async {
    final response = await _dio.post('/pos/v2/tables', data: {
      'name': name, 'zone_id': zoneId, 'seats': seats, 'sort_order': sortOrder,
    });
    return PosTable.fromJson(response.data);
  }

  Future<PosTable> updateTableV2(String tableId, Map<String, dynamic> data) async {
    final response = await _dio.patch('/pos/v2/tables/$tableId', data: data);
    return PosTable.fromJson(response.data);
  }

  // Categories
  Future<List<PosCategory>> getCategories() async {
    final response = await _dio.get('/pos/v2/categories');
    return (response.data as List).map((e) => PosCategory.fromJson(e)).toList();
  }

  Future<PosCategory> createCategory(String name,
      {String colorHex = '#607D8B', String? iconName}) async {
    final response = await _dio.post('/pos/v2/categories', data: {
      'name': name, 'color_hex': colorHex,
      if (iconName != null) 'icon_name': iconName,
    });
    return PosCategory.fromJson(response.data);
  }

  Future<PosCategory> updateCategory(int categoryId, Map<String, dynamic> data) async {
    final response = await _dio.patch('/pos/v2/categories/$categoryId', data: data);
    return PosCategory.fromJson(response.data);
  }

  // Menu v2
  Future<List<PosMenuItem>> getMenuV2({int? categoryId}) async {
    final params = <String, dynamic>{};
    if (categoryId != null) params['category_id'] = categoryId;
    final response = await _dio.get('/pos/v2/menu', queryParameters: params);
    return (response.data as List).map((e) => PosMenuItem.fromJson(e)).toList();
  }

  Future<PosMenuItem> createMenuItemV2(String name, double price, int categoryId,
      {String? description, double taxRate = 0.23}) async {
    final response = await _dio.post('/pos/v2/menu', data: {
      'name': name, 'price': price, 'category_id': categoryId,
      if (description != null) 'description': description, 'tax_rate': taxRate,
    });
    return PosMenuItem.fromJson(response.data);
  }

  Future<PosMenuItem> updateMenuItemV2(String itemId, Map<String, dynamic> data) async {
    final response = await _dio.patch('/pos/v2/menu/$itemId', data: data);
    return PosMenuItem.fromJson(response.data);
  }

  // Modifier Groups
  Future<List<ModifierGroup>> getModifierGroups() async {
    final response = await _dio.get('/pos/v2/modifier-groups');
    return (response.data as List).map((e) => ModifierGroup.fromJson(e)).toList();
  }

  Future<ModifierGroup> createModifierGroup(String name,
      {int minSelect = 0, int maxSelect = 1,
       List<Map<String, dynamic>>? modifiers}) async {
    final response = await _dio.post('/pos/v2/modifier-groups', data: {
      'name': name, 'min_select': minSelect, 'max_select': maxSelect,
      if (modifiers != null) 'modifiers': modifiers,
    });
    return ModifierGroup.fromJson(response.data);
  }

  Future<void> linkModifierGroup(String itemId, int groupId) async {
    await _dio.post('/pos/v2/menu/$itemId/modifier-groups/$groupId');
  }

  // Orders v2
  Future<PosOrder> createOrderV2(String tableId, List<Map<String, dynamic>> items,
      {int guestCount = 1, String? notes}) async {
    final response = await _dio.post('/pos/v2/orders', data: {
      'table_id': tableId, 'items': items,
      'guest_count': guestCount, if (notes != null) 'notes': notes,
    });
    return PosOrder.fromJson(response.data);
  }

  Future<List<PosOrder>> getOrdersV2({String? tableId, String? status, String? waiterId}) async {
    final params = <String, dynamic>{};
    if (tableId != null) params['table_id'] = tableId;
    if (status != null) params['status'] = status;
    if (waiterId != null) params['waiter_id'] = waiterId;
    final response = await _dio.get('/pos/v2/orders', queryParameters: params);
    return (response.data as List).map((e) => PosOrder.fromJson(e)).toList();
  }

  Future<PosOrder> getOrderV2(String orderId) async {
    final response = await _dio.get('/pos/v2/orders/$orderId');
    return PosOrder.fromJson(response.data);
  }

  Future<PosOrder> addItemsToOrder(String orderId, List<Map<String, dynamic>> items) async {
    final response = await _dio.post('/pos/v2/orders/$orderId/items', data: items);
    return PosOrder.fromJson(response.data);
  }

  Future<PosOrder> updateOrderStatusV2(String orderId, String status) async {
    final response = await _dio.patch('/pos/v2/orders/$orderId/status',
        data: {'status': status});
    return PosOrder.fromJson(response.data);
  }

  Future<PosOrder> applyDiscount(String orderId, double discountPct, String managerPin) async {
    final response = await _dio.patch('/pos/v2/orders/$orderId/discount',
        data: {'discount_pct': discountPct, 'manager_pin': managerPin});
    return PosOrder.fromJson(response.data);
  }

  // KDS v2
  Future<PosOrderItem> updateKdsItemStatus(String itemId, String kdsStatus) async {
    final response = await _dio.patch('/pos/v2/order-items/$itemId/kds-status',
        data: {'kds_status': kdsStatus});
    return PosOrderItem.fromJson(response.data);
  }

  Future<List<dynamic>> getKdsItems({String? status}) async {
    final params = <String, dynamic>{};
    if (status != null) params['status'] = status;
    final response = await _dio.get('/pos/v2/kds/items', queryParameters: params);
    return response.data as List;
  }

  // Payments
  Future<PosPayment> createPayment(String orderId, String method,
      double amount, {double tipAmount = 0.0}) async {
    final response = await _dio.post('/pos/v2/payments', data: {
      'order_id': orderId, 'method': method,
      'amount': amount, 'tip_amount': tipAmount,
    });
    return PosPayment.fromJson(response.data);
  }

  // Tips
  Future<TipSummary> getMyTips({String? date}) async {
    final params = <String, dynamic>{};
    if (date != null) params['target_date'] = date;
    final response = await _dio.get('/pos/v2/tips/my', queryParameters: params);
    return TipSummary.fromJson(response.data);
  }

  // ── Module A: Payroll, Daily Closeout & Tip Pooling ────────────────────────

  Future<DailyCloseoutSummary> upsertDailyCloseout({
    required DateTime date,
    required double dailyRevenue,
    required double tipPool,
    String? notes,
  }) async {
    final response = await _dio.post(
      '/manager/closeouts',
      data: {
        'date': date.toIso8601String().split('T')[0],
        'daily_revenue': dailyRevenue,
        'tip_pool': tipPool,
        if (notes != null && notes.isNotEmpty) 'notes': notes,
      },
    );
    return DailyCloseoutSummary.fromJson(
      response.data as Map<String, dynamic>,
    );
  }

  Future<DailyCloseoutSummary> getDailyCloseoutSummary(DateTime date) async {
    final d = date.toIso8601String().split('T')[0];
    final response = await _dio.get('/manager/closeouts/$d');
    return DailyCloseoutSummary.fromJson(
      response.data as Map<String, dynamic>,
    );
  }

  Future<MonthlyPayrollSummary> getMonthlyPayroll(int year, int month) async {
    final response = await _dio.get(
      '/manager/payroll',
      queryParameters: {'year': year, 'month': month},
    );
    return MonthlyPayrollSummary.fromJson(
      response.data as Map<String, dynamic>,
    );
  }

  String getPayrollExportCsvUrl(int year, int month, {String? token}) {
    String url = '$baseUrl/manager/payroll/export/csv?year=$year&month=$month';
    if (token != null) url += '&token=$token';
    return url;
  }

  String getPayrollExportPdfUrl(int year, int month, {String? token}) {
    String url = '$baseUrl/manager/payroll/export/pdf?year=$year&month=$month';
    if (token != null) url += '&token=$token';
    return url;
  }

  Future<EmployeeMonthlyEarnings> getMyMonthlyEarnings(
    int year,
    int month,
  ) async {
    final response = await _dio.get(
      '/employee/payroll/my',
      queryParameters: {'year': year, 'month': month},
    );
    return EmployeeMonthlyEarnings.fromJson(
      response.data as Map<String, dynamic>,
    );
  }

  // ── Module B: Operational Checklists & Digital HACCP Registry ──────────────

  Future<List<ChecklistTemplateModel>> getChecklistTemplates({
    bool includeInactive = false,
  }) async {
    final response = await _dio.get(
      '/manager/checklists',
      queryParameters: {'include_inactive': includeInactive},
    );
    return (response.data as List)
        .map((e) => ChecklistTemplateModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<ChecklistTemplateModel> createChecklistTemplate({
    required String title,
    String? description,
    int? roleId,
    required String shiftPeriod,
    required bool isMandatory,
    required List<Map<String, dynamic>> items,
  }) async {
    final response = await _dio.post(
      '/manager/checklists',
      data: {
        'title': title,
        if (description != null && description.isNotEmpty)
          'description': description,
        'role_id': roleId,
        'shift_period': shiftPeriod,
        'is_mandatory': isMandatory,
        'is_active': true,
        'items': items,
      },
    );
    return ChecklistTemplateModel.fromJson(
      response.data as Map<String, dynamic>,
    );
  }

  Future<void> deleteChecklistTemplate(String templateId) async {
    await _dio.delete('/manager/checklists/$templateId');
  }

  Future<List<ChecklistTemplateModel>> getManagerDailyChecklists(
    DateTime date,
  ) async {
    final d = date.toIso8601String().split('T')[0];
    final response = await _dio.get('/manager/checklists/daily/$d');
    return (response.data as List)
        .map((e) => ChecklistTemplateModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<List<ChecklistTemplateModel>> getEmployeeChecklists({
    DateTime? date,
  }) async {
    final response = await _dio.get(
      '/employee/checklists',
      queryParameters: {
        if (date != null) 'target_date': date.toIso8601String().split('T')[0],
      },
    );
    return (response.data as List)
        .map((e) => ChecklistTemplateModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<ChecklistItemModel> toggleChecklistItem(
    String itemId, {
    DateTime? date,
    bool? isCompleted,
  }) async {
    final response = await _dio.post(
      '/employee/checklists/items/$itemId/toggle',
      data: {
        if (date != null) 'date': date.toIso8601String().split('T')[0],
        if (isCompleted != null) 'is_completed': isCompleted,
      },
    );
    return ChecklistItemModel.fromJson(response.data as Map<String, dynamic>);
  }

  Future<ClockoutValidationResult> validateClockoutChecklists({
    DateTime? date,
  }) async {
    final response = await _dio.get(
      '/employee/checklists/validate-clockout',
      queryParameters: {
        if (date != null) 'target_date': date.toIso8601String().split('T')[0],
      },
    );
    return ClockoutValidationResult.fromJson(
      response.data as Map<String, dynamic>,
    );
  }

  Future<List<HaccpDeviceModel>> getHaccpDevices({
    bool isManager = false,
  }) async {
    final path = isManager ? '/manager/haccp/devices' : '/employee/haccp/devices';
    final response = await _dio.get(path);
    return (response.data as List)
        .map((e) => HaccpDeviceModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<HaccpDeviceModel> createHaccpDevice({
    required String name,
    required double minTemp,
    required double maxTemp,
  }) async {
    final response = await _dio.post(
      '/manager/haccp/devices',
      data: {
        'name': name,
        'min_temp': minTemp,
        'max_temp': maxTemp,
        'is_active': true,
      },
    );
    return HaccpDeviceModel.fromJson(response.data as Map<String, dynamic>);
  }

  Future<void> deleteHaccpDevice(String deviceId) async {
    await _dio.delete('/manager/haccp/devices/$deviceId');
  }

  Future<List<HaccpLogModel>> getHaccpLogs({
    required bool isManager,
    DateTime? startDate,
    DateTime? endDate,
    bool violationsOnly = false,
  }) async {
    final path = isManager ? '/manager/haccp/logs' : '/employee/haccp/logs';
    final response = await _dio.get(
      path,
      queryParameters: {
        if (startDate != null)
          'start_date': startDate.toIso8601String().split('T')[0],
        if (endDate != null)
          'end_date': endDate.toIso8601String().split('T')[0],
        if (violationsOnly) 'violations_only': true,
      },
    );
    return (response.data as List)
        .map((e) => HaccpLogModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<HaccpLogModel> createHaccpLog({
    required bool isManager,
    required String logType,
    String? deviceId,
    String? deviceName,
    double? measuredTemp,
    String? correctiveAction,
  }) async {
    final path = isManager ? '/manager/haccp/logs' : '/employee/haccp/logs';
    final response = await _dio.post(
      path,
      data: {
        'log_type': logType,
        if (deviceId != null) 'device_id': deviceId,
        if (deviceName != null && deviceName.isNotEmpty)
          'device_name': deviceName,
        if (measuredTemp != null) 'measured_temp': measuredTemp,
        if (correctiveAction != null && correctiveAction.isNotEmpty)
          'corrective_action': correctiveAction,
      },
    );
    return HaccpLogModel.fromJson(response.data as Map<String, dynamic>);
  }

  String getHaccpExportPdfUrl(
    DateTime startDate,
    DateTime endDate, {
    String? token,
  }) {
    final start = startDate.toIso8601String().split('T')[0];
    final end = endDate.toIso8601String().split('T')[0];
    String url =
        '$baseUrl/manager/haccp/export/pdf?start_date=$start&end_date=$end';
    if (token != null) url += '&token=$token';
    return url;
  }

  // ── Module C: Announcement Board with Read Receipts ────────────────────────

  Future<List<AnnouncementModel>> getManagerAnnouncements() async {
    final response = await _dio.get('/manager/announcements');
    return (response.data as List)
        .map((e) => AnnouncementModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<AnnouncementModel> createAnnouncement({
    required String title,
    required String content,
    bool isPinned = false,
  }) async {
    final response = await _dio.post(
      '/manager/announcements',
      data: {'title': title, 'content': content, 'is_pinned': isPinned},
    );
    return AnnouncementModel.fromJson(response.data as Map<String, dynamic>);
  }

  Future<AnnouncementModel> getAnnouncementReceipts(
    String announcementId,
  ) async {
    final response = await _dio.get(
      '/manager/announcements/$announcementId/receipts',
    );
    return AnnouncementModel.fromJson(response.data as Map<String, dynamic>);
  }

  Future<void> deleteAnnouncement(String announcementId) async {
    await _dio.delete('/manager/announcements/$announcementId');
  }

  Future<List<AnnouncementModel>> getEmployeeAnnouncements() async {
    final response = await _dio.get('/employee/announcements');
    return (response.data as List)
        .map((e) => AnnouncementModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<void> markAnnouncementRead(String announcementId) async {
    await _dio.post('/employee/announcements/$announcementId/read');
  }
}



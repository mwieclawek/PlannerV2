import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/models.dart';

class ApiService {
  final String baseUrl;
  final Dio _dio;

  ApiService(this.baseUrl) : _dio = Dio(BaseOptions(baseUrl: baseUrl)) {
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        // Skip auth for login/register
        if (options.path.contains('/auth/token') || options.path.contains('/auth/register')) {
          return handler.next(options);
        }

        try {
          final prefs = await SharedPreferences.getInstance();
          final token = prefs.getString('access_token');
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
        } catch (e) {
          // If SharedPreferences fails, just proceed without token
          debugPrint('Error getting token: $e');
        }
        return handler.next(options);
      },
      onError: (error, handler) async {
        if (error.response?.statusCode == 401) {
          try {
            final prefs = await SharedPreferences.getInstance();
            await prefs.remove('access_token');
          } catch (e) {
             debugPrint('Error removing token: $e');
          }
        }
        return handler.next(error);
      },
    ));
  }

  // Auth
  Future<String> login(String email, String password) async {
    final response = await _dio.post(
      '/auth/token',
      data: {
        'username': email,
        'password': password,
      },
      options: Options(
        contentType: Headers.formUrlEncodedContentType,
        // prevent throwing for 400 so we can inspect it, or just let it throw but ensure Interceptor handles it?
        // Actually, let's keep it throwing but standard
      ),
    );
    final token = response.data['access_token'];
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('access_token', token);
    return token;
  }

  Future<String> register(String username, String password, String fullName, String roleSystem, {String? managerPin}) async {
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
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('access_token', token);
    return token;
  }

  Future<User> getCurrentUser() async {
    final response = await _dio.get('/auth/me');
    return User.fromJson(response.data);
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('access_token');
  }

  Future<void> changePassword(String oldPassword, String newPassword) async {
    await _dio.put('/auth/change-password', data: {
      'old_password': oldPassword,
      'new_password': newPassword,
    });
  }

  // Roles
  Future<List<JobRole>> getRoles() async {
    final response = await _dio.get('/manager/roles');
    return (response.data as List).map((e) => JobRole.fromJson(e)).toList();
  }

  Future<JobRole> createRole(String name, String colorHex) async {
    final response = await _dio.post('/manager/roles', data: {
      'name': name,
      'color_hex': colorHex,
    });
    return JobRole.fromJson(response.data);
  }

  // Shifts
  Future<List<ShiftDefinition>> getShifts() async {
    final response = await _dio.get('/manager/shifts');
    return (response.data as List).map((e) => ShiftDefinition.fromJson(e)).toList();
  }

  Future<ShiftDefinition> createShift(String name, String startTime, String endTime, {List<int>? applicableDays}) async {
    final response = await _dio.post('/manager/shifts', data: {
      'name': name,
      'start_time': startTime,
      'end_time': endTime,
      'applicable_days': applicableDays ?? [0, 1, 2, 3, 4, 5, 6],
    });
    return ShiftDefinition.fromJson(response.data);
  }

  // Availability (Employee)
  Future<List<Availability>> getAvailability(DateTime startDate, DateTime endDate) async {
    final response = await _dio.get('/employee/availability', queryParameters: {
      'start_date': startDate.toIso8601String().split('T')[0],
      'end_date': endDate.toIso8601String().split('T')[0],
    });
    return (response.data as List).map((e) => Availability.fromJson(e)).toList();
  }

  Future<void> updateAvailability(List<AvailabilityUpdate> updates) async {
    await _dio.post('/employee/availability', data: updates.map((e) => e.toJson()).toList());
  }

  // Scheduler (Manager)
  Future<Map<String, dynamic>> generateSchedule(DateTime startDate, DateTime endDate) async {
    final response = await _dio.post('/scheduler/generate', data: {
      'start_date': startDate.toIso8601String().split('T')[0],
      'end_date': endDate.toIso8601String().split('T')[0],
    });
    return response.data;
  }

  // Requirements (Manager)
  Future<List<Requirement>> getRequirements(DateTime startDate, DateTime endDate) async {
    final response = await _dio.get('/manager/requirements', queryParameters: {
      'start_date': startDate.toIso8601String().split('T')[0],
      'end_date': endDate.toIso8601String().split('T')[0],
    });
    return (response.data as List).map((e) => Requirement.fromJson(e)).toList();
  }

  Future<void> setRequirements(List<RequirementUpdate> requirements) async {
    await _dio.post('/manager/requirements', 
      data: requirements.map((e) => e.toJson()).toList()
    );
  }

  // Schedule viewing (Manager)
  Future<List<ScheduleEntry>> getManagerSchedule(DateTime startDate, DateTime endDate) async {
    final response = await _dio.get('/scheduler/list', queryParameters: {
      'start_date': startDate.toIso8601String().split('T')[0],
      'end_date': endDate.toIso8601String().split('T')[0],
    });
    return (response.data as List).map((e) => ScheduleEntry.fromJson(e)).toList();
  }

  // Schedule viewing (Employee)
  Future<List<EmployeeScheduleEntry>> getEmployeeSchedule(DateTime startDate, DateTime endDate) async {
    final response = await _dio.get('/employee/my-schedule', queryParameters: {
      'start_date': startDate.toIso8601String().split('T')[0],
      'end_date': endDate.toIso8601String().split('T')[0],
    });
    return (response.data as List).map((e) => EmployeeScheduleEntry.fromJson(e)).toList();
  }

  // Check if user is logged in
  Future<bool> isLoggedIn() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('access_token');
    return token != null;
  }

  // Team Management (Manager)
  Future<List<TeamMember>> getUsers({bool includeInactive = false}) async {
    final response = await _dio.get('/manager/users', queryParameters: {
      if (includeInactive) 'include_inactive': true,
    });
    return (response.data as List).map((e) => TeamMember.fromJson(e)).toList();
  }

  Future<void> setUserRoles(String userId, List<int> roleIds) async {
    // Using PUT endpoint which clears existing roles and sets new ones
    await _dio.put('/manager/users/$userId/roles', data: {
      'role_ids': roleIds,
    });
  }

  Future<void> resetUserPassword(String userId, String newPassword) async {
    await _dio.put('/manager/users/$userId/password', data: {
      'new_password': newPassword,
    });
  }

  Future<void> updateUser(String userId, {
    String? fullName,
    String? email,
    String? roleSystem,
    int? targetHoursPerMonth,
    int? targetShiftsPerMonth,
    bool? isActive,
  }) async {
    await _dio.put('/manager/users/$userId', data: {
      if (fullName != null) 'full_name': fullName,
      if (email != null) 'email': email,
      if (roleSystem != null) 'role_system': roleSystem,
      if (targetHoursPerMonth != null) 'target_hours_per_month': targetHoursPerMonth,
      if (targetShiftsPerMonth != null) 'target_shifts_per_month': targetShiftsPerMonth,
      if (isActive != null) 'is_active': isActive,
    });
  }

  Future<void> createUser({
    required String username,
    required String password,
    required String fullName,
    required String roleSystem,
    String? email,
    int? targetHoursPerMonth,
    int? targetShiftsPerMonth,
  }) async {
    await _dio.post('/manager/users', data: {
      'username': username,
      'password': password,
      'full_name': fullName,
      'role_system': roleSystem,
      if (email != null && email.isNotEmpty) 'email': email,
      if (targetHoursPerMonth != null) 'target_hours_per_month': targetHoursPerMonth,
      if (targetShiftsPerMonth != null) 'target_shifts_per_month': targetShiftsPerMonth,
    });
  }

  // Manual Schedule Editing
  Future<void> createAssignment({
    required DateTime date,
    required int shiftDefId,
    required String userId,
    required int roleId,
  }) async {
    await _dio.post('/scheduler/assignment', data: {
      'date': date.toIso8601String().split('T').first,
      'shift_def_id': shiftDefId,
      'user_id': userId,
      'role_id': roleId,
    });
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
  Future<void> saveBatchSchedule(DateTime startDate, DateTime endDate, List<ScheduleEntry> entries) async {
    final data = entries.map((e) => {
      'date': e.date.toIso8601String().split('T').first,
      'shift_def_id': e.shiftDefId,
      'user_id': e.userId,
      'role_id': e.roleId,
    }).toList();
    
    await _dio.post('/scheduler/save_batch', data: {
      'start_date': startDate.toIso8601String().split('T').first,
      'end_date': endDate.toIso8601String().split('T').first,
      'items': data,
    });
  }

  // Update Role
  Future<void> updateRole(int roleId, String name, String colorHex) async {
    await _dio.put('/manager/roles/$roleId', data: {
      'name': name,
      'color_hex': colorHex,
    });
  }

  // Update Shift
  Future<void> updateShift(int shiftId, String name, String startTime, String endTime, List<int> applicableDays) async {
    await _dio.put('/manager/shifts/$shiftId', data: {
      'name': name,
      'start_time': startTime,
      'end_time': endTime,
      'applicable_days': applicableDays,
    });
  }

  // Restaurant Config
  Future<Map<String, dynamic>> getConfig() async {
    final response = await _dio.get('/manager/config');
    return response.data;
  }

  Future<void> saveConfig(String name, String openingHours, String? address) async {
    await _dio.post('/manager/config', data: {
      'name': name,
      'opening_hours': openingHours,
      'address': address,
    });
  }

  // Team Availability (Manager)
  Future<List<TeamAvailability>> getTeamAvailability(DateTime weekStart, DateTime weekEnd) async {
    final response = await _dio.get('/manager/availability', queryParameters: {
      'week_start': weekStart.toIso8601String().split('T')[0],
      'week_end': weekEnd.toIso8601String().split('T')[0],
    });
    return (response.data as List).map((e) => TeamAvailability.fromJson(e)).toList();
  }

  // Attendance (Employee)
  Future<Map<String, dynamic>> getAttendanceDefaults(DateTime date) async {
    final response = await _dio.get('/employee/attendance/defaults/${date.toIso8601String().split('T')[0]}');
    return response.data;
  }

  Future<Map<String, dynamic>> registerAttendance(DateTime date, String checkIn, String checkOut) async {
    final response = await _dio.post('/employee/attendance', queryParameters: {
      'target_date': date.toIso8601String().split('T')[0],
      'check_in': checkIn,
      'check_out': checkOut,
    });
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
    await _dio.post('/manager/attendance', data: {
      'user_id': userId,
      'date': date.toIso8601String().split('T')[0],
      'check_in': checkIn,
      'check_out': checkOut,
      'was_scheduled': wasScheduled,
      'status': status,
    });
  }

  Future<List<Map<String, dynamic>>> getMyAttendance(DateTime startDate, DateTime endDate) async {
    final response = await _dio.get('/employee/attendance/my', queryParameters: {
      'start_date': startDate.toIso8601String().split('T')[0],
      'end_date': endDate.toIso8601String().split('T')[0],
    });
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
    final response = await _dio.get('/manager/attendance', queryParameters: params);
    return (response.data as List).cast<Map<String, dynamic>>();
  }

  Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('access_token');
  }

  String getAttendanceExportUrl(DateTime startDate, DateTime endDate, {String? status, String? token}) {
    // baseUrl is now an instance field
    final start = startDate.toIso8601String().split('T')[0];
    final end = endDate.toIso8601String().split('T')[0];
    String url = '$baseUrl/manager/attendance/export?start_date=$start&end_date=$end';
    if (status != null) {
      url += '&status=$status';
    }
    if (token != null) {
      url += '&token=$token';
    }
    return url;
  }

  Future<List<Map<String, dynamic>>> getEmployeeHours(int month, int year) async {
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
    final response = await _dio.get('/manager/dashboard/home', queryParameters: queryParameters);
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
    await _dio.post('/manager/giveaways/$giveawayId/reassign', data: {
      'new_user_id': newUserId,
    });
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
    final response = await _dio.post('/bug-report', data: {
      'title': title,
      'description': description,
      'steps_to_reproduce': steps,
    });
    return response.data as Map<String, dynamic>;
  }

}

import 'package:flutter/foundation.dart';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../models/models.dart';

class ApiService {
  static String get baseUrl {
    if (kReleaseMode) {
      return '';
    }
    return 'http://127.0.0.1:8000';
  }
  final Dio _dio;
  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  ApiService() : _dio = Dio(BaseOptions(baseUrl: baseUrl)) {
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await _storage.read(key: 'access_token');
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        return handler.next(options);
      },
      onError: (error, handler) {
        if (error.response?.statusCode == 401) {
          // Token expired or invalid
          _storage.delete(key: 'access_token');
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
    await _storage.write(key: 'access_token', value: token);
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
    await _storage.write(key: 'access_token', value: token);
    return token;
  }

  Future<User> getCurrentUser() async {
    final response = await _dio.get('/auth/me');
    return User.fromJson(response.data);
  }

  Future<void> logout() async {
    await _storage.delete(key: 'access_token');
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
    final token = await _storage.read(key: 'access_token');
    return token != null;
  }

  // Team Management (Manager)
  Future<List<TeamMember>> getUsers() async {
    final response = await _dio.get('/manager/users');
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
  Future<void> updateShift(int shiftId, String name, String startTime, String endTime, {List<int>? applicableDays}) async {
    await _dio.put('/manager/shifts/$shiftId', data: {
      'name': name,
      'start_time': startTime,
      'end_time': endTime,
      'applicable_days': applicableDays ?? [0, 1, 2, 3, 4, 5, 6],
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

  Future<List<Map<String, dynamic>>> getEmployeeHours(int month, int year) async {
    final response = await _dio.get(
      '/manager/employee-hours',
      queryParameters: {'month': month, 'year': year},
    );
    return (response.data as List).cast<Map<String, dynamic>>();
  }

}

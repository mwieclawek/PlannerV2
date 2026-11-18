import 'package:dio/dio.dart';

class SysAdminService {
  final Dio _dio;

  SysAdminService(this._dio);

  Future<List<Map<String, dynamic>>> getRestaurants() async {
    final response = await _dio.get('/sysadmin/restaurants');
    return List<Map<String, dynamic>>.from(response.data);
  }

  Future<Map<String, dynamic>> createRestaurant(String name, String loginId) async {
    final response = await _dio.post(
      '/sysadmin/restaurants',
      data: {
        'name': name,
        'login_id': loginId,
      },
    );
    return response.data;
  }

  Future<Map<String, dynamic>> updateRestaurant(int id, {String? name, String? loginId}) async {
    final response = await _dio.put(
      '/sysadmin/restaurants/$id',
      data: {
        if (name != null) 'name': name,
        if (loginId != null) 'login_id': loginId,
      },
    );
    return response.data;
  }

  Future<Map<String, dynamic>> updateRestaurantStatus(int id, bool isActive) async {
    final response = await _dio.put(
      '/sysadmin/restaurants/$id/status',
      data: {'is_active': isActive},
    );
    return response.data;
  }

  Future<Map<String, dynamic>> createManager(
    int restaurantId,
    String email,
    String firstName,
    String lastName,
    String password,
  ) async {
    final response = await _dio.post(
      '/sysadmin/restaurants/$restaurantId/managers',
      data: {
        'email': email,
        'first_name': firstName,
        'last_name': lastName,
        'password': password,
      },
    );
    return response.data;
  }

  Future<List<Map<String, dynamic>>> getRestaurantUsers(int id) async {
    final response = await _dio.get('/sysadmin/restaurants/$id/users');
    return List<Map<String, dynamic>>.from(response.data);
  }

  Future<void> resetUserPassword(String userId, String newPassword) async {
    await _dio.put(
      '/sysadmin/users/$userId/reset-password',
      data: {'new_password': newPassword},
    );
  }

  Future<Map<String, dynamic>> getLogs({
    int? restaurantId,
    String? level,
    String? category,
    String? search,
    int limit = 200,
    int offset = 0,
  }) async {
    final queryParams = <String, dynamic>{
      'limit': limit,
      'offset': offset,
    };
    if (restaurantId != null) queryParams['restaurant_id'] = restaurantId;
    if (level != null && level.toUpperCase() != 'ALL') {
      queryParams['level'] = level.toUpperCase();
    }
    if (category != null && category.trim().isNotEmpty && category.toUpperCase() != 'ALL') {
      queryParams['category'] = category.trim().toUpperCase();
    }
    if (search != null && search.trim().isNotEmpty) {
      queryParams['search'] = search.trim();
    }

    final response = await _dio.get(
      '/sysadmin/logs',
      queryParameters: queryParams,
    );
    return Map<String, dynamic>.from(response.data);
  }

  Future<void> clearLogs() async {
    await _dio.delete('/sysadmin/logs');
  }

  Future<List<Map<String, dynamic>>> getDatabaseTables() async {
    final response = await _dio.get('/sysadmin/db/tables');
    final data = response.data;
    if (data is Map && data['tables'] is List) {
      return List<Map<String, dynamic>>.from(
        (data['tables'] as List).map((item) => Map<String, dynamic>.from(item as Map)),
      );
    }
    if (data is List) {
      return List<Map<String, dynamic>>.from(
        data.map((item) => Map<String, dynamic>.from(item as Map)),
      );
    }
    return [];
  }

  Future<Map<String, dynamic>> getDatabaseTableRows(
    String tableName, {
    int limit = 50,
    int offset = 0,
    String? search,
    int? tenantId,
    String? sortBy,
    bool sortDesc = true,
    bool resolveFks = true,
  }) async {
    final queryParams = <String, dynamic>{
      'limit': limit,
      'offset': offset,
      'sort_desc': sortDesc,
      'resolve_fks': resolveFks,
    };
    if (search != null && search.trim().isNotEmpty) {
      queryParams['search'] = search.trim();
    }
    if (tenantId != null) {
      queryParams['tenant_id'] = tenantId;
    }
    if (sortBy != null && sortBy.trim().isNotEmpty) {
      queryParams['sort_by'] = sortBy.trim();
    }

    final response = await _dio.get(
      '/sysadmin/db/tables/${Uri.encodeComponent(tableName)}/rows',
      queryParameters: queryParams,
    );
    return Map<String, dynamic>.from(response.data);
  }
}

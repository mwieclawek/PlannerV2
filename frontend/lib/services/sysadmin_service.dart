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
}

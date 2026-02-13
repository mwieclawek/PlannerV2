import 'package:shared_preferences/shared_preferences.dart';

class ConfigService {
  static const String keyBaseUrl = 'base_url';
  
  // Singleton pattern
  static final ConfigService _instance = ConfigService._internal();
  factory ConfigService() => _instance;
  ConfigService._internal();

  late SharedPreferences _prefs;

  Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
  }

  String? get baseUrl => _prefs.getString(keyBaseUrl);

  Future<void> setBaseUrl(String url) async {
    await _prefs.setString(keyBaseUrl, url);
  }

  Future<void> clear() async {
    await _prefs.remove(keyBaseUrl);
  }
}

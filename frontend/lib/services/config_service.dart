import 'package:flutter/foundation.dart';
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

  String? get baseUrl {
    final stored = _prefs.getString(keyBaseUrl);
    if (stored != null) return stored;
    
    // On Web, default to current origin in release/deployed mode
    if (kIsWeb) {
      final origin = Uri.base.origin;
      // If we are on localhost, we might want to keep it or handle it specifically.
      // But origin is safe for both local and prod.
      return origin; 
    }
    return null;
  }

  Future<void> setBaseUrl(String url) async {
    await _prefs.setString(keyBaseUrl, url);
  }

  Future<void> clear() async {
    await _prefs.remove(keyBaseUrl);
  }
}

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/config_service.dart';

final configServiceProvider = Provider<ConfigService>((ref) => ConfigService());

class ConfigNotifier extends StateNotifier<String?> {
  final ConfigService _configService;

  ConfigNotifier(this._configService)
    : super(
        (kIsWeb &&
                (Uri.base.host == 'localhost' || Uri.base.host == '127.0.0.1'))
            ? '${Uri.base.scheme}://127.0.0.1:8000'
            : _configService.baseUrl,
      );
  Future<void> setBaseUrl(String url) async {
    await _configService.setBaseUrl(url);
    state = url;
  }

  Future<void> clear() async {
    await _configService.clear();
    state = null;
  }
}

final configProvider = StateNotifierProvider<ConfigNotifier, String?>((ref) {
  final configService = ref.watch(configServiceProvider);
  return ConfigNotifier(configService);
});

import 'package:flutter_riverpod/flutter_riverpod.dart';

enum AppModule { planning, posKds }

class ModuleNotifier extends StateNotifier<AppModule> {
  ModuleNotifier() : super(AppModule.planning);

  void switchModule(AppModule module) {
    state = module;
  }
}

final moduleProvider = StateNotifierProvider<ModuleNotifier, AppModule>((ref) {
  return ModuleNotifier();
});

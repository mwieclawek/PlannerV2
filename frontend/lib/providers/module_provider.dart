import 'package:flutter_riverpod/flutter_riverpod.dart';

enum AppModule { planning, posKds }

/// Moduł POS/KDS jest domyślnie wygaszony na frontendzie.
const bool kPosModuleDefaultEnabled = false;

class ModuleNotifier extends StateNotifier<AppModule> {
  final bool posEnabled;

  ModuleNotifier({this.posEnabled = kPosModuleDefaultEnabled})
    : super(AppModule.planning);

  void switchModule(AppModule module) {
    if (module == AppModule.posKds && !posEnabled) {
      state = AppModule.planning;
      return;
    }
    state = module;
  }
}

final moduleProvider = StateNotifierProvider<ModuleNotifier, AppModule>((ref) {
  return ModuleNotifier(posEnabled: kPosModuleDefaultEnabled);
});

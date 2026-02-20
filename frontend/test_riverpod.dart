import 'package:flutter_riverpod/flutter_riverpod.dart';

final a = Provider<int>((ref) { throw Exception('A'); });
final b = Provider<int>((ref) => ref.watch(a));

void main() {
  final container = ProviderContainer();
  try {
    container.listen(b, (_, __) {});
    print('Listen succeeded');
  } catch (e) {
    print('Listen threw: $e');
  }
}

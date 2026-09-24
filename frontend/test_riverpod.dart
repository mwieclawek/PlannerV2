import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final a = Provider<int>((ref) { throw Exception('A'); });
final b = Provider<int>((ref) => ref.watch(a));

void main() {
  test('riverpod exception handling test', () {
    final container = ProviderContainer();
    expect(() => container.read(b), throwsA(isA<Exception>()));
  });
}



import 'dart:convert';
import 'package:flutter_test/flutter_test.dart'; // Using the proper test package now
import 'package:frontend/models/models.dart';

void main() {
  test('Requirement model should handle UUID string IDs', () {
    // Symulacja JSON-a z backendu dla Requirement
    final jsonString = '''
    {
      "id": "cbe56eb2-b97b-4287-853e-a436bb4d1f7c",
      "date": "2026-02-01",
      "shift_def_id": 1,
      "role_id": 1,
      "min_count": 2
    }
    ''';

    final Map<String, dynamic> json = jsonDecode(jsonString);
    final req = Requirement.fromJson(json);
    
    expect(req.id, isA<String>());
    expect(req.id, equals("cbe56eb2-b97b-4287-853e-a436bb4d1f7c"));
    expect(req.minCount, equals(2));
  });
}

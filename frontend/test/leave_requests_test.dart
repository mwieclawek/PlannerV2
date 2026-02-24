import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/models/models.dart';

void main() {
  group('LeaveRequest Models', () {
    test('LeaveRequest parses from JSON correctly', () {
      final json = {
        'id': 'req-123',
        'user_id': 'user-1',
        'user_name': 'Test User',
        'start_date': '2026-03-15',
        'end_date': '2026-03-22',
        'reason': 'Vacation',
        'status': 'PENDING',
        'created_at': '2026-03-01T10:00:00Z',
        'reviewed_at': null,
      };

      final req = LeaveRequest.fromJson(json);

      expect(req.id, 'req-123');
      expect(req.userId, 'user-1');
      expect(req.userName, 'Test User');
      expect(req.startDate, '2026-03-15');
      expect(req.endDate, '2026-03-22');
      expect(req.reason, 'Vacation');
      expect(req.status, 'PENDING');
      expect(req.createdAt, '2026-03-01T10:00:00Z');
      expect(req.reviewedAt, isNull);
    });

    test('LeaveCalendarEntry parses from JSON correctly', () {
      final json = {
        'user_id': 'user-2',
        'user_name': 'Another User',
        'start_date': '2026-04-01',
        'end_date': '2026-04-05',
        'status': 'APPROVED',
      };

      final entry = LeaveCalendarEntry.fromJson(json);

      expect(entry.userId, 'user-2');
      expect(entry.userName, 'Another User');
      expect(entry.startDate, '2026-04-01');
      expect(entry.endDate, '2026-04-05');
      expect(entry.status, 'APPROVED');
    });
  });
}

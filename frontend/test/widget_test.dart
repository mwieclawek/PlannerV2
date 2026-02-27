// Widget Tests for PlannerV2 Frontend
// Run with: flutter test

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/models/models.dart';

void main() {
  group('Model Tests', () {
    test('User model parses correctly', () {
      final json = {
        'id': '123e4567-e89b-12d3-a456-426614174000',
        'email': 'test@test.com',
        'full_name': 'Test User',
        'role_system': 'MANAGER',
        'created_at': '2026-01-01T00:00:00Z',
        'job_roles': [1, 2],
      };

      final user = User.fromJson(json);
      expect(user.email, 'test@test.com');
      expect(user.isManager, true);
    });

    test('User isEmployee works correctly', () {
      final json = {
        'id': '123e4567-e89b-12d3-a456-426614174000',
        'email': 'emp@test.com',
        'full_name': 'Test Employee',
        'role_system': 'EMPLOYEE',
        'created_at': '2026-01-01T00:00:00Z',
        'job_roles': [],
      };

      final user = User.fromJson(json);
      expect(user.isEmployee, true);
      expect(user.isManager, false);
    });

    test('JobRole parses correctly', () {
      final json = {'id': 1, 'name': 'Barista', 'color_hex': '#FF5733'};

      final role = JobRole.fromJson(json);
      expect(role.name, 'Barista');
      expect(role.colorHex, '#FF5733');
    });

    test('ShiftDefinition parses correctly', () {
      final json = {
        'id': 1,
        'name': 'Morning',
        'start_time': '08:00',
        'end_time': '16:00',
      };

      final shift = ShiftDefinition.fromJson(json);
      expect(shift.name, 'Morning');
      expect(shift.startTime, '08:00');
      expect(shift.endTime, '16:00');
    });

    test('ScheduleEntry parses correctly', () {
      final json = {
        'id': '123',
        'date': '2026-02-01',
        'shift_def_id': 1,
        'user_id': 'user-uuid',
        'role_id': 2,
        'is_published': false,
        'user_name': 'John Doe',
        'role_name': 'Barista',
        'shift_name': 'Morning',
      };

      final entry = ScheduleEntry.fromJson(json);
      expect(entry.userName, 'John Doe');
      expect(entry.roleName, 'Barista');
      expect(entry.shiftName, 'Morning');
      expect(entry.isPublished, false);
    });

    test('TeamMember parses correctly', () {
      final json = {
        'id': 'uuid-123',
        'email': 'member@test.com',
        'full_name': 'Team Member',
        'role_system': 'EMPLOYEE',
        'job_roles': [1, 2],
      };

      final member = TeamMember.fromJson(json);
      expect(member.fullName, 'Team Member');
      expect(member.isEmployee, true);
      expect(member.jobRoleIds, [1, 2]);
    });

    test('EmployeeScheduleEntry parses coworkers correctly', () {
      final json = {
        'id': 'shift-001',
        'date': '2026-03-01',
        'shift_name': 'Morning',
        'role_name': 'Barista',
        'start_time': '08:00',
        'end_time': '16:00',
        'is_on_giveaway': false,
        'coworkers': [
          {'name': 'Anna Kowalska', 'role_name': 'Barista'},
          {'name': 'Jan Nowak', 'role_name': 'Shift Leader'},
        ],
      };

      final entry = EmployeeScheduleEntry.fromJson(json);
      expect(entry.shiftName, 'Morning');
      expect(entry.coworkers.map((c) => c.name).toList(), [
        'Anna Kowalska',
        'Jan Nowak',
      ]);
      expect(entry.coworkers.length, 2);
    });

    test('EmployeeScheduleEntry defaults coworkers to empty list', () {
      final json = {
        'id': 'shift-002',
        'date': '2026-03-02',
        'shift_name': 'Evening',
        'role_name': 'Cashier',
        'start_time': '16:00',
        'end_time': '23:00',
      };

      final entry = EmployeeScheduleEntry.fromJson(json);
      expect(entry.coworkers, isEmpty);
      expect(entry.isOnGiveaway, false);
    });
  });
}

class User {
  final String id;
  final String username;
  final String? email;
  final String fullName;
  final String roleSystem;
  final DateTime createdAt;
  final int? targetHoursPerMonth;
  final int? targetShiftsPerMonth;
  final bool isActive;

  User({
    required this.id,
    required this.username,
    this.email,
    required this.fullName,
    required this.roleSystem,
    required this.createdAt,
    this.targetHoursPerMonth,
    this.targetShiftsPerMonth,
    this.isActive = true,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'],
      username: json['username'] ?? '',
      email: json['email'],
      fullName: json['full_name'],
      roleSystem: json['role_system'],
      createdAt: DateTime.parse(json['created_at']),
      targetHoursPerMonth: json['target_hours_per_month'],
      targetShiftsPerMonth: json['target_shifts_per_month'],
      isActive: json['is_active'] ?? true,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'username': username,
      'email': email,
      'full_name': fullName,
      'role_system': roleSystem,
      'created_at': createdAt.toIso8601String(),
      'target_hours_per_month': targetHoursPerMonth,
      'target_shifts_per_month': targetShiftsPerMonth,
      'is_active': isActive,
    };
  }

  bool get isManager => roleSystem == 'MANAGER';
  bool get isEmployee => roleSystem == 'EMPLOYEE';
}

class JobRole {
  final int id;
  final String name;
  final String colorHex;

  JobRole({
    required this.id,
    required this.name,
    required this.colorHex,
  });

  factory JobRole.fromJson(Map<String, dynamic> json) {
    return JobRole(
      id: json['id'],
      name: json['name'],
      colorHex: json['color_hex'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'color_hex': colorHex,
    };
  }
}

class ShiftDefinition {
  final int id;
  final String name;
  final String startTime;
  final String endTime;
  final List<int> applicableDays; // 0=Mon, 1=Tue ... 6=Sun

  ShiftDefinition({
    required this.id,
    required this.name,
    required this.startTime,
    required this.endTime,
    this.applicableDays = const [0, 1, 2, 3, 4, 5, 6], // Default: all days
  });

  factory ShiftDefinition.fromJson(Map<String, dynamic> json) {
    // Parse applicable_days from backend (List<int>)
    List<int> days = const [0, 1, 2, 3, 4, 5, 6];
    if (json['applicable_days'] != null) {
      days = List<int>.from(json['applicable_days']);
    }
    return ShiftDefinition(
      id: json['id'],
      name: json['name'],
      startTime: json['start_time'],
      endTime: json['end_time'],
      applicableDays: days,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'start_time': startTime,
      'end_time': endTime,
      'applicable_days': applicableDays,
    };
  }
}

enum AvailabilityStatus {
  unavailable,
  available;

  String toJson() {
    switch (this) {
      case AvailabilityStatus.unavailable:
        return 'UNAVAILABLE';
      case AvailabilityStatus.available:
        return 'AVAILABLE';
    }
  }

  static AvailabilityStatus fromJson(String value) {
    switch (value) {
      case 'UNAVAILABLE':
        return AvailabilityStatus.unavailable;
      case 'AVAILABLE':
      case 'PREFERRED':
      case 'NEUTRAL':
        return AvailabilityStatus.available;
      default:
        return AvailabilityStatus.available;
    }
  }
}

class Availability {
  final String id;
  final String userId;
  final DateTime date;
  final int shiftDefId;
  final AvailabilityStatus status;

  Availability({
    required this.id,
    required this.userId,
    required this.date,
    required this.shiftDefId,
    required this.status,
  });

  factory Availability.fromJson(Map<String, dynamic> json) {
    return Availability(
      id: json['id'],
      userId: json['user_id'],
      date: DateTime.parse(json['date']),
      shiftDefId: json['shift_def_id'],
      status: AvailabilityStatus.fromJson(json['status']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'user_id': userId,
      'date': date.toIso8601String().split('T')[0],
      'shift_def_id': shiftDefId,
      'status': status.toJson(),
    };
  }
}

class AvailabilityUpdate {
  final DateTime date;
  final int shiftDefId;
  final AvailabilityStatus status;

  AvailabilityUpdate({
    required this.date,
    required this.shiftDefId,
    required this.status,
  });

  Map<String, dynamic> toJson() {
    return {
      'date': date.toIso8601String().split('T')[0],
      'shift_def_id': shiftDefId,
      'status': status.toJson(),
    };
  }
}

class Schedule {
  final String id;
  final DateTime date;
  final int shiftDefId;
  final String userId;
  final int roleId;
  final bool isPublished;

  Schedule({
    required this.id,
    required this.date,
    required this.shiftDefId,
    required this.userId,
    required this.roleId,
    required this.isPublished,
  });

  factory Schedule.fromJson(Map<String, dynamic> json) {
    return Schedule(
      id: json['id'],
      date: DateTime.parse(json['date']),
      shiftDefId: json['shift_def_id'],
      userId: json['user_id'],
      roleId: json['role_id'],
      isPublished: json['is_published'],
    );
  }
}

class Requirement {
  final String id;
  final DateTime? date;
  final int? dayOfWeek;
  final int shiftDefId;
  final int roleId;
  final int minCount;

  Requirement({
    required this.id,
    this.date,
    this.dayOfWeek,
    required this.shiftDefId,
    required this.roleId,
    required this.minCount,
  });

  factory Requirement.fromJson(Map<String, dynamic> json) {
    return Requirement(
      id: json['id'],
      date: json['date'] != null ? DateTime.parse(json['date']) : null,
      dayOfWeek: json['day_of_week'],
      shiftDefId: json['shift_def_id'],
      roleId: json['role_id'],
      minCount: json['min_count'],
    );
  }
}

class RequirementUpdate {
  final DateTime? date;
  final int? dayOfWeek;
  final int shiftDefId;
  final int roleId;
  final int minCount;

  RequirementUpdate({
    this.date,
    this.dayOfWeek,
    required this.shiftDefId,
    required this.roleId,
    required this.minCount,
  });

  Map<String, dynamic> toJson() {
    return {
      'date': date?.toIso8601String().split('T')[0],
      'day_of_week': dayOfWeek,
      'shift_def_id': shiftDefId,
      'role_id': roleId,
      'min_count': minCount,
    };
  }
}

class ScheduleEntry {
  final String id;
  final DateTime date;
  final int shiftDefId;
  final String userId;
  final int roleId;
  final bool isPublished;
  final String userName;
  final String roleName;
  final String shiftName;
  final String startTime;
  final String endTime;
  final bool isOnGiveaway;

  ScheduleEntry({
    required this.id,
    required this.date,
    required this.shiftDefId,
    required this.userId,
    required this.roleId,
    required this.isPublished,
    required this.userName,
    required this.roleName,
    required this.shiftName,
    required this.startTime,
    required this.endTime,
    this.isOnGiveaway = false,
  });

  factory ScheduleEntry.fromJson(Map<String, dynamic> json) {
    return ScheduleEntry(
      id: json['id'],
      date: DateTime.parse(json['date']),
      shiftDefId: json['shift_def_id'],
      userId: json['user_id'],
      roleId: json['role_id'],
      isPublished: json['is_published'],
      userName: json['user_name'],
      roleName: json['role_name'],
      shiftName: json['shift_name'],
      startTime: json['start_time'] ?? '09:00', // Fallback if missing
      endTime: json['end_time'] ?? '17:00',
      isOnGiveaway: json['is_on_giveaway'] ?? false,
    );
  }
}

class EmployeeScheduleEntry {
  final String id;
  final DateTime date;
  final String shiftName;
  final String roleName;
  final String startTime;
  final String endTime;
  final bool isOnGiveaway;

  EmployeeScheduleEntry({
    required this.id,
    required this.date,
    required this.shiftName,
    required this.roleName,
    required this.startTime,
    required this.endTime,
    this.isOnGiveaway = false,
  });

  factory EmployeeScheduleEntry.fromJson(Map<String, dynamic> json) {
    return EmployeeScheduleEntry(
      id: json['id'],
      date: DateTime.parse(json['date']),
      shiftName: json['shift_name'],
      roleName: json['role_name'],
      startTime: json['start_time'],
      endTime: json['end_time'],
      isOnGiveaway: json['is_on_giveaway'] ?? false,
    );
  }
}

class TeamMember {
  final String id;
  final String username;
  final String? email;  // Now optional
  final String fullName;
  final String roleSystem;
  final List<int> jobRoleIds;
  final int? targetHoursPerMonth;
  final int? targetShiftsPerMonth;
  final bool isActive;
  final NextShiftInfo? nextShift;

  TeamMember({
    required this.id,
    required this.username,
    this.email,
    required this.fullName,
    required this.roleSystem,
    required this.jobRoleIds,
    this.targetHoursPerMonth,
    this.targetShiftsPerMonth,
    this.isActive = true,
    this.nextShift,
  });

  factory TeamMember.fromJson(Map<String, dynamic> json) {
    return TeamMember(
      id: json['id'],
      username: json['username'] ?? '',
      email: json['email'],
      fullName: json['full_name'],
      roleSystem: json['role_system'],
      jobRoleIds: (json['job_roles'] as List).map((e) => e as int).toList(),
      targetHoursPerMonth: json['target_hours_per_month'],
      targetShiftsPerMonth: json['target_shifts_per_month'],
      isActive: json['is_active'] ?? true,
      nextShift: json['next_shift'] != null ? NextShiftInfo.fromJson(json['next_shift']) : null,
    );
  }

  bool get isManager => roleSystem == 'MANAGER';
  bool get isEmployee => roleSystem == 'EMPLOYEE';
}

class StaffingWarning {
  final DateTime date;
  final int shiftDefId;
  final int roleId;
  final String roleName;
  final String shiftName;
  final int required;
  final int assigned;
  final int missing;

  StaffingWarning({
    required this.date,
    required this.shiftDefId,
    required this.roleId,
    required this.roleName,
    required this.shiftName,
    required this.required,
    required this.assigned,
    required this.missing,
  });

  factory StaffingWarning.fromJson(Map<String, dynamic> json) {
    return StaffingWarning(
      date: DateTime.parse(json['date']),
      shiftDefId: json['shift_def_id'] as int,
      roleId: json['role_id'] as int,
      roleName: json['role_name'] as String,
      shiftName: json['shift_name'] as String,
      required: json['required'] as int,
      assigned: json['assigned'] as int,
      missing: json['missing'] as int,
    );
  }
}

// Manager Availability View Models
class AvailabilityEntry {
  final String date;
  final int shiftDefId;
  final String status;

  AvailabilityEntry({
    required this.date,
    required this.shiftDefId,
    required this.status,
  });

  factory AvailabilityEntry.fromJson(Map<String, dynamic> json) {
    return AvailabilityEntry(
      date: json['date'] as String,
      shiftDefId: json['shift_def_id'] as int,
      status: json['status'] as String,
    );
  }
}

class TeamAvailability {
  final String userId;
  final String userName;
  final List<AvailabilityEntry> entries;

  TeamAvailability({
    required this.userId,
    required this.userName,
    required this.entries,
  });

  factory TeamAvailability.fromJson(Map<String, dynamic> json) {
    return TeamAvailability(
      userId: json['user_id'] as String,
      userName: json['user_name'] as String,
      entries: (json['entries'] as List)
          .map((e) => AvailabilityEntry.fromJson(e))
          .toList(),
    );
  }
}


class NextShiftInfo {
  final DateTime date;
  final String startTime;
  final String endTime;
  final String shiftName;
  final String roleName;

  NextShiftInfo({
    required this.date,
    required this.startTime,
    required this.endTime,
    required this.shiftName,
    required this.roleName,
  });

  factory NextShiftInfo.fromJson(Map<String, dynamic> json) {
    return NextShiftInfo(
      date: DateTime.parse(json['date']),
      startTime: json['start_time'],
      endTime: json['end_time'],
      shiftName: json['shift_name'],
      roleName: json['role_name'],
    );
  }
}

class UserStats {
  final int totalShiftsCompleted;
  final double totalHoursWorked;
  final List<Map<String, dynamic>> monthlyShifts;

  UserStats({
    required this.totalShiftsCompleted,
    required this.totalHoursWorked,
    required this.monthlyShifts,
  });

  factory UserStats.fromJson(Map<String, dynamic> json) {
    return UserStats(
      totalShiftsCompleted: json['total_shifts_completed'],
      totalHoursWorked: (json['total_hours_worked'] as num).toDouble(),
      monthlyShifts: (json['monthly_shifts'] as List).cast<Map<String, dynamic>>(),
    );
  }
}

class DashboardHome {
  final List<ScheduleEntry> workingToday;
  final List<Map<String, dynamic>> missingConfirmations;
  final List<ShiftGiveaway> openGiveaways;

  DashboardHome({
    required this.workingToday,
    required this.missingConfirmations,
    required this.openGiveaways,
  });

  factory DashboardHome.fromJson(Map<String, dynamic> json) {
    return DashboardHome(
      workingToday: (json['working_today'] as List)
          .map((e) => ScheduleEntry.fromJson(e))
          .toList(),
      missingConfirmations: (json['missing_confirmations'] as List).cast<Map<String, dynamic>>(),
      openGiveaways: (json['open_giveaways'] as List?)
          ?.map((e) => ShiftGiveaway.fromJson(e))
          .toList() ?? [],
    );
  }
}

// --- Shift Giveaway ---

class GiveawaySuggestion {
  final String userId;
  final String fullName;
  final String? availabilityStatus;

  GiveawaySuggestion({
    required this.userId,
    required this.fullName,
    this.availabilityStatus,
  });

  factory GiveawaySuggestion.fromJson(Map<String, dynamic> json) {
    return GiveawaySuggestion(
      userId: json['user_id'] as String,
      fullName: json['full_name'] as String,
      availabilityStatus: json['availability_status'] as String?,
    );
  }
}

class ShiftGiveaway {
  final String id;
  final String scheduleId;
  final String offeredBy;
  final String offeredByName;
  final String status;
  final DateTime createdAt;
  final String? takenBy;
  final String? takenByName;
  final String? date;
  final String? shiftName;
  final String? roleName;
  final String? startTime;
  final String? endTime;
  final List<GiveawaySuggestion> suggestions;

  ShiftGiveaway({
    required this.id,
    required this.scheduleId,
    required this.offeredBy,
    required this.offeredByName,
    required this.status,
    required this.createdAt,
    this.takenBy,
    this.takenByName,
    this.date,
    this.shiftName,
    this.roleName,
    this.startTime,
    this.endTime,
    this.suggestions = const [],
  });

  factory ShiftGiveaway.fromJson(Map<String, dynamic> json) {
    return ShiftGiveaway(
      id: json['id'] as String,
      scheduleId: json['schedule_id'] as String,
      offeredBy: json['offered_by'] as String,
      offeredByName: json['offered_by_name'] as String? ?? '',
      status: json['status'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      takenBy: json['taken_by'] as String?,
      takenByName: json['taken_by_name'] as String?,
      date: json['date'] as String?,
      shiftName: json['shift_name'] as String?,
      roleName: json['role_name'] as String?,
      startTime: json['start_time'] as String?,
      endTime: json['end_time'] as String?,
      suggestions: (json['suggestions'] as List? ?? [])
          .map((e) => GiveawaySuggestion.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

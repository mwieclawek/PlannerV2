class User {
  final String id;
  final String email;
  final String fullName;
  final String roleSystem;
  final DateTime createdAt;

  User({
    required this.id,
    required this.email,
    required this.fullName,
    required this.roleSystem,
    required this.createdAt,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'],
      email: json['email'],
      fullName: json['full_name'],
      roleSystem: json['role_system'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'full_name': fullName,
      'role_system': roleSystem,
      'created_at': createdAt.toIso8601String(),
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

  ShiftDefinition({
    required this.id,
    required this.name,
    required this.startTime,
    required this.endTime,
  });

  factory ShiftDefinition.fromJson(Map<String, dynamic> json) {
    return ShiftDefinition(
      id: json['id'],
      name: json['name'],
      startTime: json['start_time'],
      endTime: json['end_time'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'start_time': startTime,
      'end_time': endTime,
    };
  }
}

enum AvailabilityStatus {
  preferred,
  neutral,
  unavailable,
  available;

  String toJson() {
    switch (this) {
      case AvailabilityStatus.preferred:
        return 'PREFERRED';
      case AvailabilityStatus.neutral:
        return 'NEUTRAL';
      case AvailabilityStatus.unavailable:
        return 'UNAVAILABLE';
      case AvailabilityStatus.available:
        return 'AVAILABLE';
    }
  }

  static AvailabilityStatus fromJson(String value) {
    switch (value) {
      case 'PREFERRED':
        return AvailabilityStatus.preferred;
      case 'NEUTRAL':
        return AvailabilityStatus.neutral;
      case 'UNAVAILABLE':
        return AvailabilityStatus.unavailable;
      case 'AVAILABLE':
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
  final DateTime date;
  final int shiftDefId;
  final int roleId;
  final int minCount;

  Requirement({
    required this.id,
    required this.date,
    required this.shiftDefId,
    required this.roleId,
    required this.minCount,
  });

  factory Requirement.fromJson(Map<String, dynamic> json) {
    return Requirement(
      id: json['id'],
      date: DateTime.parse(json['date']),
      shiftDefId: json['shift_def_id'],
      roleId: json['role_id'],
      minCount: json['min_count'],
    );
  }
}

class RequirementUpdate {
  final DateTime date;
  final int shiftDefId;
  final int roleId;
  final int minCount;

  RequirementUpdate({
    required this.date,
    required this.shiftDefId,
    required this.roleId,
    required this.minCount,
  });

  Map<String, dynamic> toJson() {
    return {
      'date': date.toIso8601String().split('T')[0],
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

  EmployeeScheduleEntry({
    required this.id,
    required this.date,
    required this.shiftName,
    required this.roleName,
    required this.startTime,
    required this.endTime,
  });

  factory EmployeeScheduleEntry.fromJson(Map<String, dynamic> json) {
    return EmployeeScheduleEntry(
      id: json['id'],
      date: DateTime.parse(json['date']),
      shiftName: json['shift_name'],
      roleName: json['role_name'],
      startTime: json['start_time'],
      endTime: json['end_time'],
    );
  }
}

class TeamMember {
  final String id;
  final String email;
  final String fullName;
  final String roleSystem;
  final List<int> jobRoleIds;

  TeamMember({
    required this.id,
    required this.email,
    required this.fullName,
    required this.roleSystem,
    required this.jobRoleIds,
  });

  factory TeamMember.fromJson(Map<String, dynamic> json) {
    return TeamMember(
      id: json['id'],
      email: json['email'],
      fullName: json['full_name'],
      roleSystem: json['role_system'],
      jobRoleIds: (json['job_roles'] as List).map((e) => e as int).toList(),
    );
  }

  bool get isManager => roleSystem == 'MANAGER';
  bool get isEmployee => roleSystem == 'EMPLOYEE';
}

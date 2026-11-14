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
  final String? tenantId;
  final String? tenantSlug;
  final String? tenantName;
  final bool isSuperadmin;
  final List<int> jobRoleIds;
  final List<String> jobRoleNames;
  final double? hourlyRate;
  final bool isGoogleCalendarConnected;

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
    this.tenantId,
    this.tenantSlug,
    this.tenantName,
    this.isSuperadmin = false,
    this.jobRoleIds = const [],
    this.jobRoleNames = const [],
    this.hourlyRate,
    this.isGoogleCalendarConnected = false,
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
      // Backend returns tenant_id as int - must not be assigned directly to String?
      tenantId: json['tenant_id']?.toString(),
      tenantSlug: json['tenant_slug'],
      tenantName: json['tenant_name'],
      isSuperadmin: json['is_superadmin'] == true,
      jobRoleIds: (json['job_roles'] as List<dynamic>?)
              ?.map((e) => (e as num).toInt())
              .toList() ??
          [],
      jobRoleNames: (json['job_role_names'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      hourlyRate: (json['hourly_rate'] as num?)?.toDouble(),
      isGoogleCalendarConnected: json['is_google_calendar_connected'] == true,
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
      'tenant_id': tenantId,
      'tenant_slug': tenantSlug,
      'tenant_name': tenantName,
      'is_superadmin': isSuperadmin,
      'job_roles': jobRoleIds,
      'job_role_names': jobRoleNames,
      'hourly_rate': hourlyRate,
      'is_google_calendar_connected': isGoogleCalendarConnected,
    };
  }

  bool get isManager => roleSystem == 'MANAGER';
  bool get isEmployee => roleSystem == 'EMPLOYEE';
}

class JobRole {
  final int id;
  final String name;
  final String colorHex;
  final double? hourlyRate;

  JobRole({
    required this.id,
    required this.name,
    required this.colorHex,
    this.hourlyRate,
  });

  factory JobRole.fromJson(Map<String, dynamic> json) {
    return JobRole(
      id: json['id'],
      name: json['name'],
      colorHex: json['color_hex'],
      hourlyRate: (json['hourly_rate'] as num?)?.toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'color_hex': colorHex,
      'hourly_rate': hourlyRate,
    };
  }
}

class ShiftDefinition {
  final int id;
  final String name;
  final String startTime;
  final String endTime;
  final List<int> applicableDays; // 0=Mon, 1=Tue ... 6=Sun
  final List<int> allowedRoleIds;

  ShiftDefinition({
    required this.id,
    required this.name,
    required this.startTime,
    required this.endTime,
    this.applicableDays = const [0, 1, 2, 3, 4, 5, 6], // Default: all days
    this.allowedRoleIds = const [],
  });

  factory ShiftDefinition.fromJson(Map<String, dynamic> json) {
    // Parse applicable_days from backend (List<int>)
    List<int> days = const [0, 1, 2, 3, 4, 5, 6];
    if (json['applicable_days'] != null) {
      days = List<int>.from(json['applicable_days']);
    }
    List<int> roles = [];
    if (json['allowed_role_ids'] != null) {
      roles = List<int>.from(json['allowed_role_ids']);
    }
    
    return ShiftDefinition(
      id: json['id'],
      name: json['name'],
      startTime: json['start_time'],
      endTime: json['end_time'],
      applicableDays: days,
      allowedRoleIds: roles,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'start_time': startTime,
        'end_time': endTime,
        'applicable_days': applicableDays,
        'allowed_role_ids': allowedRoleIds,
      };
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

class CoworkerEntry {
  final String name;
  final String roleName;

  CoworkerEntry({required this.name, required this.roleName});

  factory CoworkerEntry.fromJson(Map<String, dynamic> json) {
    return CoworkerEntry(
      name: json['name'] ?? 'Unknown',
      roleName: json['role_name'] ?? 'Unknown',
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
  final List<CoworkerEntry> coworkers;
  final int? roleId;
  final int? shiftDefId;

  EmployeeScheduleEntry({
    required this.id,
    required this.date,
    required this.shiftName,
    required this.roleName,
    required this.startTime,
    required this.endTime,
    this.isOnGiveaway = false,
    this.coworkers = const [],
    this.roleId,
    this.shiftDefId,
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
      coworkers:
          (json['coworkers'] as List?)
              ?.map((e) => CoworkerEntry.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      roleId: json['role_id'] as int?,
      shiftDefId: json['shift_def_id'] as int?,
    );
  }
}

class TeamMember {
  final String id;
  final String username;
  final String? email; // Now optional
  final String fullName;
  final String roleSystem;
  final List<int> jobRoleIds;
  final int? targetHoursPerMonth;
  final int? targetShiftsPerMonth;
  final double? hourlyRate;
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
    this.hourlyRate,
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
      hourlyRate: (json['hourly_rate'] as num?)?.toDouble(),
      isActive: json['is_active'] ?? true,
      nextShift:
          json['next_shift'] != null
              ? NextShiftInfo.fromJson(json['next_shift'])
              : null,
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
      entries:
          (json['entries'] as List)
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
  final String? selectedMonth;
  final double selectedMonthWorkedHours;
  final double selectedMonthPlannedHours;
  final int selectedMonthShifts;
  final int? targetHoursPerMonth;

  UserStats({
    required this.totalShiftsCompleted,
    required this.totalHoursWorked,
    required this.monthlyShifts,
    this.selectedMonth,
    this.selectedMonthWorkedHours = 0.0,
    this.selectedMonthPlannedHours = 0.0,
    this.selectedMonthShifts = 0,
    this.targetHoursPerMonth,
  });

  factory UserStats.fromJson(Map<String, dynamic> json) {
    return UserStats(
      totalShiftsCompleted: json['total_shifts_completed'] ?? 0,
      totalHoursWorked: (json['total_hours_worked'] as num?)?.toDouble() ?? 0.0,
      monthlyShifts:
          (json['monthly_shifts'] as List? ?? const [])
              .cast<Map<String, dynamic>>(),
      selectedMonth: json['selected_month'] as String?,
      selectedMonthWorkedHours:
          (json['selected_month_worked_hours'] as num?)?.toDouble() ?? 0.0,
      selectedMonthPlannedHours:
          (json['selected_month_planned_hours'] as num?)?.toDouble() ?? 0.0,
      selectedMonthShifts: json['selected_month_shifts'] as int? ?? 0,
      targetHoursPerMonth: json['target_hours_per_month'] as int?,
    );
  }
}

class DashboardHome {
  final List<ScheduleEntry> workingToday;
  final List<Map<String, dynamic>> missingConfirmations;
  final List<ShiftGiveaway> openGiveaways;
  final DailyCloseoutSummary? dailyCloseout;

  DashboardHome({
    required this.workingToday,
    required this.missingConfirmations,
    required this.openGiveaways,
    this.dailyCloseout,
  });

  factory DashboardHome.fromJson(Map<String, dynamic> json) {
    return DashboardHome(
      workingToday:
          (json['working_today'] as List)
              .map((e) => ScheduleEntry.fromJson(e))
              .toList(),
      missingConfirmations:
          (json['missing_confirmations'] as List).cast<Map<String, dynamic>>(),
      openGiveaways:
          (json['open_giveaways'] as List?)
              ?.map((e) => ShiftGiveaway.fromJson(e))
              .toList() ??
          [],
      dailyCloseout:
          json['daily_closeout'] != null
              ? DailyCloseoutSummary.fromJson(
                json['daily_closeout'] as Map<String, dynamic>,
              )
              : null,
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
  final String? targetShiftId;
  final bool isDirectSwap;
  final String? targetUserName;
  final String? targetDate;
  final String? targetShiftName;
  final String? targetStartTime;
  final String? targetEndTime;
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
    this.targetShiftId,
    this.isDirectSwap = false,
    this.targetUserName,
    this.targetDate,
    this.targetShiftName,
    this.targetStartTime,
    this.targetEndTime,
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
      targetShiftId: json['target_shift_id'] as String?,
      isDirectSwap: json['is_direct_swap'] == true || json['target_shift_id'] != null,
      targetUserName: json['target_user_name'] as String?,
      targetDate: json['target_date'] as String?,
      targetShiftName: json['target_shift_name'] as String?,
      targetStartTime: json['target_start_time'] as String?,
      targetEndTime: json['target_end_time'] as String?,
      suggestions:
          (json['suggestions'] as List? ?? [])
              .map(
                (e) => GiveawaySuggestion.fromJson(e as Map<String, dynamic>),
              )
              .toList(),
    );
  }
}

// --- Leave Requests ---

class LeaveRequest {
  final String id;
  final String userId;
  final String userName;
  final String startDate; // "YYYY-MM-DD"
  final String endDate;
  final String? reason;
  final String status; // PENDING, APPROVED, REJECTED, CANCELLED
  final String createdAt;
  final String? reviewedAt;

  LeaveRequest({
    required this.id,
    required this.userId,
    required this.userName,
    required this.startDate,
    required this.endDate,
    this.reason,
    required this.status,
    required this.createdAt,
    this.reviewedAt,
  });

  factory LeaveRequest.fromJson(Map<String, dynamic> json) {
    return LeaveRequest(
      id: json['id'],
      userId: json['user_id'],
      userName: json['user_name'] ?? '',
      startDate: json['start_date'],
      endDate: json['end_date'],
      reason: json['reason'],
      status: json['status'],
      createdAt: json['created_at'],
      reviewedAt: json['reviewed_at'],
    );
  }
}

class LeaveCalendarEntry {
  final String userId;
  final String userName;
  final String startDate;
  final String endDate;
  final String status;

  LeaveCalendarEntry({
    required this.userId,
    required this.userName,
    required this.startDate,
    required this.endDate,
    required this.status,
  });

  factory LeaveCalendarEntry.fromJson(Map<String, dynamic> json) {
    return LeaveCalendarEntry(
      userId: json['user_id'],
      userName: json['user_name'],
      startDate: json['start_date'],
      endDate: json['end_date'],
      status: json['status'],
    );
  }
}

class AvailableEmployee {
  final String userId;
  final String fullName;
  final String availabilityStatus;
  final List<JobRole> jobRoles;
  final double? targetHours;
  final double hoursThisMonth;

  AvailableEmployee({
    required this.userId,
    required this.fullName,
    required this.availabilityStatus,
    required this.jobRoles,
    this.targetHours,
    required this.hoursThisMonth,
  });

  factory AvailableEmployee.fromJson(Map<String, dynamic> json) {
    return AvailableEmployee(
      userId: json['user_id'],
      fullName: json['full_name'],
      availabilityStatus: json['availability_status'],
      jobRoles:
          (json['job_roles'] as List? ?? [])
              .map((e) => JobRole.fromJson(e as Map<String, dynamic>))
              .toList(),
      targetHours: json['target_hours']?.toDouble(),
      hoursThisMonth: json['hours_this_month']?.toDouble() ?? 0.0,
    );
  }
}

class AppNotification {
  final String id;
  final String title;
  final String body;
  final bool isRead;
  final DateTime createdAt;

  AppNotification({
    required this.id,
    required this.title,
    required this.body,
    required this.isRead,
    required this.createdAt,
  });

  factory AppNotification.fromJson(Map<String, dynamic> json) {
    return AppNotification(
      id: json['id'],
      title: json['title'],
      body: json['body'],
      isRead: json['is_read'] ?? false,
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}

// ── POS & Kitchen Models ──────────────────────────────────────────────────────

class RestaurantTable {
  final String id;
  final String name;
  final bool isActive;

  RestaurantTable({required this.id, required this.name, this.isActive = true});

  factory RestaurantTable.fromJson(Map<String, dynamic> json) {
    return RestaurantTable(
      id: json['id'],
      name: json['name'],
      isActive: json['is_active'] ?? true,
    );
  }
}

enum MenuCategory {
  SOUPS,
  MAINS,
  DESSERTS,
  DRINKS;

  String get label {
    switch (this) {
      case MenuCategory.SOUPS:
        return 'Zupy';
      case MenuCategory.MAINS:
        return 'Drugie Dania';
      case MenuCategory.DESSERTS:
        return 'Desery';
      case MenuCategory.DRINKS:
        return 'Napoje';
    }
  }

  static MenuCategory fromString(String value) {
    return MenuCategory.values.firstWhere(
      (e) => e.name == value,
      orElse: () => MenuCategory.MAINS,
    );
  }
}

class MenuItem {
  final String id;
  final String name;
  final double price;
  final MenuCategory category;
  final bool isActive;

  MenuItem({
    required this.id,
    required this.name,
    required this.price,
    required this.category,
    this.isActive = true,
  });

  factory MenuItem.fromJson(Map<String, dynamic> json) {
    return MenuItem(
      id: json['id'],
      name: json['name'],
      price: (json['price'] as num).toDouble(),
      category: MenuCategory.fromString(json['category']),
      isActive: json['is_active'] ?? true,
    );
  }
}

class KitchenOrderItem {
  final String id;
  final String orderId;
  final String menuItemId;
  final int quantity;
  final String? notes;
  final double unitPrice;
  final String? menuItemName;

  KitchenOrderItem({
    required this.id,
    required this.orderId,
    required this.menuItemId,
    required this.quantity,
    this.notes,
    required this.unitPrice,
    this.menuItemName,
  });

  factory KitchenOrderItem.fromJson(Map<String, dynamic> json) {
    return KitchenOrderItem(
      id: json['id'],
      orderId: json['order_id'],
      menuItemId: json['menu_item_id'],
      quantity: json['quantity'] ?? 1,
      notes: json['notes'],
      unitPrice: (json['unit_price'] as num).toDouble(),
      menuItemName: json['menu_item_name'],
    );
  }
}

enum KitchenOrderStatus {
  PENDING,
  IN_PROGRESS,
  READY,
  DELIVERED,
  CANCELLED;

  String get label {
    switch (this) {
      case KitchenOrderStatus.PENDING:
        return 'Oczekujące';
      case KitchenOrderStatus.IN_PROGRESS:
        return 'W trakcie';
      case KitchenOrderStatus.READY:
        return 'Gotowe';
      case KitchenOrderStatus.DELIVERED:
        return 'Wydane';
      case KitchenOrderStatus.CANCELLED:
        return 'Anulowane';
    }
  }

  static KitchenOrderStatus fromString(String value) {
    return KitchenOrderStatus.values.firstWhere(
      (e) => e.name == value,
      orElse: () => KitchenOrderStatus.PENDING,
    );
  }
}

class KitchenOrder {
  final String id;
  final String tableId;
  final KitchenOrderStatus status;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String waiterId;
  final List<KitchenOrderItem> items;
  final String? tableName;
  final String? waiterName;
  final double totalAmount;

  KitchenOrder({
    required this.id,
    required this.tableId,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    required this.waiterId,
    this.items = const [],
    this.tableName,
    this.waiterName,
    this.totalAmount = 0.0,
  });

  factory KitchenOrder.fromJson(Map<String, dynamic> json) {
    return KitchenOrder(
      id: json['id'],
      tableId: json['table_id'],
      status: KitchenOrderStatus.fromString(json['status']),
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
      waiterId: json['waiter_id'],
      items:
          (json['items'] as List?)
              ?.map((e) => KitchenOrderItem.fromJson(e))
              .toList() ??
          [],
      tableName: json['table_name'],
      waiterName: json['waiter_name'],
      totalAmount: (json['total_amount'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

// ── POS v2 Models ────────────────────────────────────────────────────────────

enum TableStatus {
  FREE, OCCUPIED, BILL_PRINTED, DIRTY;

  String get label {
    switch (this) {
      case TableStatus.FREE: return 'Wolny';
      case TableStatus.OCCUPIED: return 'Zajęty';
      case TableStatus.BILL_PRINTED: return 'Rachunek';
      case TableStatus.DIRTY: return 'Do sprzątnięcia';
    }
  }

  static TableStatus fromString(String v) =>
      TableStatus.values.firstWhere((e) => e.name == v, orElse: () => TableStatus.FREE);
}

class TableZone {
  final String id;
  final String name;
  final int sortOrder;
  final bool isActive;

  TableZone({required this.id, required this.name, this.sortOrder = 0, this.isActive = true});

  factory TableZone.fromJson(Map<String, dynamic> json) => TableZone(
    id: json['id'], name: json['name'],
    sortOrder: json['sort_order'] ?? 0, isActive: json['is_active'] ?? true,
  );
}

class PosTable {
  final String id;
  final String name;
  final String? zoneId;
  final int seats;
  final TableStatus status;
  final int sortOrder;
  final bool isActive;
  final String? zoneName;

  PosTable({
    required this.id, required this.name, this.zoneId, this.seats = 4,
    this.status = TableStatus.FREE, this.sortOrder = 0, this.isActive = true,
    this.zoneName,
  });

  factory PosTable.fromJson(Map<String, dynamic> json) => PosTable(
    id: json['id'], name: json['name'], zoneId: json['zone_id'],
    seats: json['seats'] ?? 4,
    status: TableStatus.fromString(json['status'] ?? 'FREE'),
    sortOrder: json['sort_order'] ?? 0, isActive: json['is_active'] ?? true,
    zoneName: json['zone_name'],
  );
}

class PosCategory {
  final int id;
  final String name;
  final String colorHex;
  final String? iconName;
  final int sortOrder;
  final bool isActive;

  PosCategory({
    required this.id, required this.name, this.colorHex = '#607D8B',
    this.iconName, this.sortOrder = 0, this.isActive = true,
  });

  factory PosCategory.fromJson(Map<String, dynamic> json) => PosCategory(
    id: json['id'], name: json['name'],
    colorHex: json['color_hex'] ?? '#607D8B', iconName: json['icon_name'],
    sortOrder: json['sort_order'] ?? 0, isActive: json['is_active'] ?? true,
  );
}

class PosMenuItem {
  final String id;
  final String name;
  final String? description;
  final double price;
  final int categoryId;
  final String? categoryName;
  final double taxRate;
  final bool kitchenPrint;
  final bool barPrint;
  final int sortOrder;
  final bool isActive;

  PosMenuItem({
    required this.id, required this.name, this.description, required this.price,
    required this.categoryId, this.categoryName, this.taxRate = 0.23,
    this.kitchenPrint = true, this.barPrint = false, this.sortOrder = 0,
    this.isActive = true,
  });

  factory PosMenuItem.fromJson(Map<String, dynamic> json) => PosMenuItem(
    id: json['id'], name: json['name'], description: json['description'],
    price: (json['price'] as num).toDouble(),
    categoryId: json['category_id'], categoryName: json['category_name'],
    taxRate: (json['tax_rate'] as num?)?.toDouble() ?? 0.23,
    kitchenPrint: json['kitchen_print'] ?? true,
    barPrint: json['bar_print'] ?? false,
    sortOrder: json['sort_order'] ?? 0, isActive: json['is_active'] ?? true,
  );
}

class PosModifier {
  final int id;
  final int groupId;
  final String name;
  final double priceOverride;
  final int sortOrder;
  final bool isActive;

  PosModifier({
    required this.id, required this.groupId, required this.name,
    this.priceOverride = 0.0, this.sortOrder = 0, this.isActive = true,
  });

  factory PosModifier.fromJson(Map<String, dynamic> json) => PosModifier(
    id: json['id'], groupId: json['group_id'], name: json['name'],
    priceOverride: (json['price_override'] as num?)?.toDouble() ?? 0.0,
    sortOrder: json['sort_order'] ?? 0, isActive: json['is_active'] ?? true,
  );
}

class ModifierGroup {
  final int id;
  final String name;
  final int minSelect;
  final int maxSelect;
  final bool isActive;
  final List<PosModifier> modifiers;

  ModifierGroup({
    required this.id, required this.name, this.minSelect = 0,
    this.maxSelect = 1, this.isActive = true, this.modifiers = const [],
  });

  factory ModifierGroup.fromJson(Map<String, dynamic> json) => ModifierGroup(
    id: json['id'], name: json['name'],
    minSelect: json['min_select'] ?? 0, maxSelect: json['max_select'] ?? 1,
    isActive: json['is_active'] ?? true,
    modifiers: (json['modifiers'] as List? ?? [])
        .map((e) => PosModifier.fromJson(e)).toList(),
  );
}

enum OrderStatus {
  OPEN, SENT, PARTIALLY_PAID, PAID, CANCELLED;

  String get label {
    switch (this) {
      case OrderStatus.OPEN: return 'Otwarte';
      case OrderStatus.SENT: return 'Wysłane';
      case OrderStatus.PARTIALLY_PAID: return 'Częściowo opłacone';
      case OrderStatus.PAID: return 'Opłacone';
      case OrderStatus.CANCELLED: return 'Anulowane';
    }
  }

  static OrderStatus fromString(String v) =>
      OrderStatus.values.firstWhere((e) => e.name == v, orElse: () => OrderStatus.OPEN);
}

enum KdsStatus {
  NEW, ACKNOWLEDGED, PREPARING, READY, DELIVERED, VOIDED_PENDING_ACK, VOIDED;

  String get label {
    switch (this) {
      case KdsStatus.NEW: return 'Nowe';
      case KdsStatus.ACKNOWLEDGED: return 'Przyjęte';
      case KdsStatus.PREPARING: return 'W przygotowaniu';
      case KdsStatus.READY: return 'Gotowe';
      case KdsStatus.DELIVERED: return 'Wydane';
      case KdsStatus.VOIDED_PENDING_ACK: return 'Anulowane (Oczekuje)';
      case KdsStatus.VOIDED: return 'Anulowane';
    }
  }

  static KdsStatus fromString(String v) =>
      KdsStatus.values.firstWhere((e) => e.name == v, orElse: () => KdsStatus.NEW);
}

class OrderItemModifier {
  final String id;
  final int modifierId;
  final String modifierNameSnapshot;
  final double priceSnapshot;

  OrderItemModifier({
    required this.id, required this.modifierId,
    required this.modifierNameSnapshot, this.priceSnapshot = 0.0,
  });

  factory OrderItemModifier.fromJson(Map<String, dynamic> json) => OrderItemModifier(
    id: json['id'], modifierId: json['modifier_id'],
    modifierNameSnapshot: json['modifier_name_snapshot'],
    priceSnapshot: (json['price_snapshot'] as num?)?.toDouble() ?? 0.0,
  );
}

class PosOrderItem {
  final String id;
  final String orderId;
  final String menuItemId;
  final int quantity;
  final double unitPriceSnapshot;
  final String itemNameSnapshot;
  final int course;
  final String? notes;
  final KdsStatus kdsStatus;
  final DateTime? sentToKitchenAt;
  final DateTime? readyAt;
  final String? splitTag;
  final List<OrderItemModifier> modifiers;

  PosOrderItem({
    required this.id, required this.orderId, required this.menuItemId,
    this.quantity = 1, required this.unitPriceSnapshot,
    required this.itemNameSnapshot, this.course = 1, this.notes,
    this.kdsStatus = KdsStatus.NEW, this.sentToKitchenAt, this.readyAt,
    this.splitTag, this.modifiers = const [],
  });

  double get lineTotal => unitPriceSnapshot * quantity +
      modifiers.fold(0.0, (sum, m) => sum + m.priceSnapshot);

  factory PosOrderItem.fromJson(Map<String, dynamic> json) => PosOrderItem(
    id: json['id'], orderId: json['order_id'], menuItemId: json['menu_item_id'],
    quantity: json['quantity'] ?? 1,
    unitPriceSnapshot: (json['unit_price_snapshot'] as num).toDouble(),
    itemNameSnapshot: json['item_name_snapshot'],
    course: json['course'] ?? 1, notes: json['notes'],
    kdsStatus: KdsStatus.fromString(json['kds_status'] ?? 'NEW'),
    sentToKitchenAt: json['sent_to_kitchen_at'] != null
        ? DateTime.parse(json['sent_to_kitchen_at']) : null,
    readyAt: json['ready_at'] != null ? DateTime.parse(json['ready_at']) : null,
    splitTag: json['split_tag'],
    modifiers: (json['modifiers'] as List? ?? [])
        .map((e) => OrderItemModifier.fromJson(e)).toList(),
  );
}

class PosOrder {
  final String id;
  final String tableId;
  final String waiterId;
  final OrderStatus status;
  final int guestCount;
  final String? notes;
  final double discountPct;
  final DateTime createdAt;
  final DateTime? closedAt;
  final List<PosOrderItem> items;
  final String? tableName;
  final String? waiterName;
  final double totalAmount;
  final double amountPaid;
  final double amountDue;

  PosOrder({
    required this.id, required this.tableId, required this.waiterId,
    this.status = OrderStatus.OPEN, this.guestCount = 1, this.notes,
    this.discountPct = 0.0, required this.createdAt, this.closedAt,
    this.items = const [], this.tableName, this.waiterName,
    this.totalAmount = 0.0, this.amountPaid = 0.0, this.amountDue = 0.0,
  });

  factory PosOrder.fromJson(Map<String, dynamic> json) => PosOrder(
    id: json['id'], tableId: json['table_id'], waiterId: json['waiter_id'],
    status: OrderStatus.fromString(json['status'] ?? 'OPEN'),
    guestCount: json['guest_count'] ?? 1, notes: json['notes'],
    discountPct: (json['discount_pct'] as num?)?.toDouble() ?? 0.0,
    createdAt: DateTime.parse(json['created_at']),
    closedAt: json['closed_at'] != null ? DateTime.parse(json['closed_at']) : null,
    items: (json['items'] as List? ?? [])
        .map((e) => PosOrderItem.fromJson(e)).toList(),
    tableName: json['table_name'], waiterName: json['waiter_name'],
    totalAmount: (json['total_amount'] as num?)?.toDouble() ?? 0.0,
    amountPaid: (json['amount_paid'] as num?)?.toDouble() ?? 0.0,
    amountDue: (json['amount_due'] as num?)?.toDouble() ?? 0.0,
  );
}

enum PaymentMethod {
  CASH, CARD, VOUCHER, MOBILE;

  String get label {
    switch (this) {
      case PaymentMethod.CASH: return 'Gotówka';
      case PaymentMethod.CARD: return 'Karta';
      case PaymentMethod.VOUCHER: return 'Voucher';
      case PaymentMethod.MOBILE: return 'Mobilna';
    }
  }

  static PaymentMethod fromString(String v) =>
      PaymentMethod.values.firstWhere((e) => e.name == v, orElse: () => PaymentMethod.CASH);
}

class PosPayment {
  final String id;
  final String orderId;
  final PaymentMethod method;
  final double amount;
  final double tipAmount;
  final String receivedBy;
  final DateTime createdAt;

  PosPayment({
    required this.id, required this.orderId, required this.method,
    required this.amount, this.tipAmount = 0.0, required this.receivedBy,
    required this.createdAt,
  });

  factory PosPayment.fromJson(Map<String, dynamic> json) => PosPayment(
    id: json['id'], orderId: json['order_id'],
    method: PaymentMethod.fromString(json['method'] ?? 'CASH'),
    amount: (json['amount'] as num).toDouble(),
    tipAmount: (json['tip_amount'] as num?)?.toDouble() ?? 0.0,
    receivedBy: json['received_by'],
    createdAt: DateTime.parse(json['created_at']),
  );
}

class TipSummary {
  final double totalTips;
  final int tipCount;
  final Map<String, double> tipsByMethod;

  TipSummary({required this.totalTips, required this.tipCount, this.tipsByMethod = const {}});

  factory TipSummary.fromJson(Map<String, dynamic> json) => TipSummary(
    totalTips: (json['total_tips'] as num).toDouble(),
    tipCount: json['tip_count'] ?? 0,
    tipsByMethod: (json['tips_by_method'] as Map<String, dynamic>? ?? {})
        .map((k, v) => MapEntry(k, (v as num).toDouble())),
  );
}

// ── Module A: Payroll, Daily Closeout & Tip Pooling ──────────────────────────

class EmployeeTipAllocation {
  final String userId;
  final String userName;
  final double confirmedHours;
  final double allocatedTip;

  EmployeeTipAllocation({
    required this.userId,
    required this.userName,
    required this.confirmedHours,
    required this.allocatedTip,
  });

  factory EmployeeTipAllocation.fromJson(Map<String, dynamic> json) =>
      EmployeeTipAllocation(
        userId: json['user_id'].toString(),
        userName: json['user_name'] ?? '',
        confirmedHours: (json['confirmed_hours'] as num?)?.toDouble() ?? 0.0,
        allocatedTip: (json['allocated_tip'] as num?)?.toDouble() ?? 0.0,
      );
}

class DailyCloseoutSummary {
  final String? id;
  final String date;
  final double dailyRevenue;
  final double tipPool;
  final String? notes;
  final double confirmedHours;
  final double scheduledHours;
  final double laborCost;
  final double laborCostPct;
  final bool isClosedOut;
  final List<EmployeeTipAllocation> tipAllocations;

  DailyCloseoutSummary({
    this.id,
    required this.date,
    required this.dailyRevenue,
    required this.tipPool,
    this.notes,
    required this.confirmedHours,
    required this.scheduledHours,
    required this.laborCost,
    required this.laborCostPct,
    required this.isClosedOut,
    this.tipAllocations = const [],
  });

  factory DailyCloseoutSummary.fromJson(Map<String, dynamic> json) =>
      DailyCloseoutSummary(
        id: json['id']?.toString(),
        date: json['date']?.toString() ?? '',
        dailyRevenue: (json['daily_revenue'] as num?)?.toDouble() ?? 0.0,
        tipPool: (json['tip_pool'] as num?)?.toDouble() ?? 0.0,
        notes: json['notes'] as String?,
        confirmedHours: (json['confirmed_hours'] as num?)?.toDouble() ?? 0.0,
        scheduledHours: (json['scheduled_hours'] as num?)?.toDouble() ?? 0.0,
        laborCost: (json['labor_cost'] as num?)?.toDouble() ?? 0.0,
        laborCostPct: (json['labor_cost_pct'] as num?)?.toDouble() ?? 0.0,
        isClosedOut: json['is_closed_out'] == true,
        tipAllocations:
            (json['tip_allocations'] as List? ?? [])
                .map(
                  (e) => EmployeeTipAllocation.fromJson(
                    e as Map<String, dynamic>,
                  ),
                )
                .toList(),
      );
}

class PayrollEmployeeItem {
  final String userId;
  final String userName;
  final double hourlyRate;
  final double confirmedHours;
  final double pendingHours;
  final int shiftsCount;
  final double basePay;
  final double allocatedTips;
  final double totalPay;

  PayrollEmployeeItem({
    required this.userId,
    required this.userName,
    required this.hourlyRate,
    required this.confirmedHours,
    required this.pendingHours,
    required this.shiftsCount,
    required this.basePay,
    required this.allocatedTips,
    required this.totalPay,
  });

  factory PayrollEmployeeItem.fromJson(Map<String, dynamic> json) =>
      PayrollEmployeeItem(
        userId: json['user_id'].toString(),
        userName: json['user_name'] ?? '',
        hourlyRate: (json['hourly_rate'] as num?)?.toDouble() ?? 0.0,
        confirmedHours: (json['confirmed_hours'] as num?)?.toDouble() ?? 0.0,
        pendingHours: (json['pending_hours'] as num?)?.toDouble() ?? 0.0,
        shiftsCount: (json['shifts_count'] as num?)?.toInt() ?? 0,
        basePay: (json['base_pay'] as num?)?.toDouble() ?? 0.0,
        allocatedTips: (json['allocated_tips'] as num?)?.toDouble() ?? 0.0,
        totalPay: (json['total_pay'] as num?)?.toDouble() ?? 0.0,
      );
}

class MonthlyPayrollSummary {
  final int year;
  final int month;
  final List<PayrollEmployeeItem> items;
  final double totalConfirmedHours;
  final double totalPendingHours;
  final double totalBasePay;
  final double totalTips;
  final double totalPayroll;
  final double totalMonthlyRevenue;
  final double monthlyLaborCostPct;

  MonthlyPayrollSummary({
    required this.year,
    required this.month,
    required this.items,
    required this.totalConfirmedHours,
    required this.totalPendingHours,
    required this.totalBasePay,
    required this.totalTips,
    required this.totalPayroll,
    required this.totalMonthlyRevenue,
    required this.monthlyLaborCostPct,
  });

  factory MonthlyPayrollSummary.fromJson(Map<String, dynamic> json) =>
      MonthlyPayrollSummary(
        year: (json['year'] as num).toInt(),
        month: (json['month'] as num).toInt(),
        items:
            (json['items'] as List? ?? [])
                .map(
                  (e) =>
                      PayrollEmployeeItem.fromJson(e as Map<String, dynamic>),
                )
                .toList(),
        totalConfirmedHours:
            (json['total_confirmed_hours'] as num?)?.toDouble() ?? 0.0,
        totalPendingHours:
            (json['total_pending_hours'] as num?)?.toDouble() ?? 0.0,
        totalBasePay: (json['total_base_pay'] as num?)?.toDouble() ?? 0.0,
        totalTips: (json['total_tips'] as num?)?.toDouble() ?? 0.0,
        totalPayroll: (json['total_payroll'] as num?)?.toDouble() ?? 0.0,
        totalMonthlyRevenue:
            (json['total_monthly_revenue'] as num?)?.toDouble() ?? 0.0,
        monthlyLaborCostPct:
            (json['monthly_labor_cost_pct'] as num?)?.toDouble() ?? 0.0,
      );
}

class EmployeeDailyEarningItem {
  final String date;
  final String status;
  final double hours;
  final double hourlyRate;
  final double basePay;
  final double allocatedTip;
  final double totalPay;

  EmployeeDailyEarningItem({
    required this.date,
    required this.status,
    required this.hours,
    required this.hourlyRate,
    required this.basePay,
    required this.allocatedTip,
    required this.totalPay,
  });

  factory EmployeeDailyEarningItem.fromJson(Map<String, dynamic> json) =>
      EmployeeDailyEarningItem(
        date: json['date']?.toString() ?? '',
        status: json['status']?.toString() ?? '',
        hours: (json['hours'] as num?)?.toDouble() ?? 0.0,
        hourlyRate: (json['hourly_rate'] as num?)?.toDouble() ?? 0.0,
        basePay: (json['base_pay'] as num?)?.toDouble() ?? 0.0,
        allocatedTip: (json['allocated_tip'] as num?)?.toDouble() ?? 0.0,
        totalPay: (json['total_pay'] as num?)?.toDouble() ?? 0.0,
      );
}

class EmployeeMonthlyEarnings {
  final int year;
  final int month;
  final String userId;
  final String userName;
  final double hourlyRate;
  final double confirmedHours;
  final double pendingHours;
  final double basePay;
  final double allocatedTips;
  final double totalPay;
  final List<EmployeeDailyEarningItem> dailyBreakdown;

  EmployeeMonthlyEarnings({
    required this.year,
    required this.month,
    required this.userId,
    required this.userName,
    required this.hourlyRate,
    required this.confirmedHours,
    required this.pendingHours,
    required this.basePay,
    required this.allocatedTips,
    required this.totalPay,
    this.dailyBreakdown = const [],
  });

  factory EmployeeMonthlyEarnings.fromJson(Map<String, dynamic> json) =>
      EmployeeMonthlyEarnings(
        year: (json['year'] as num).toInt(),
        month: (json['month'] as num).toInt(),
        userId: json['user_id'].toString(),
        userName: json['user_name'] ?? '',
        hourlyRate: (json['hourly_rate'] as num?)?.toDouble() ?? 0.0,
        confirmedHours: (json['confirmed_hours'] as num?)?.toDouble() ?? 0.0,
        pendingHours: (json['pending_hours'] as num?)?.toDouble() ?? 0.0,
        basePay: (json['base_pay'] as num?)?.toDouble() ?? 0.0,
        allocatedTips: (json['allocated_tips'] as num?)?.toDouble() ?? 0.0,
        totalPay: (json['total_pay'] as num?)?.toDouble() ?? 0.0,
        dailyBreakdown:
            (json['daily_breakdown'] as List? ?? [])
                .map(
                  (e) => EmployeeDailyEarningItem.fromJson(
                    e as Map<String, dynamic>,
                  ),
                )
                .toList(),
      );
}

// ── Module B: Operational Checklists & Digital HACCP Registry ────────────────

class ChecklistItemModel {
  final String id;
  final String templateId;
  final String title;
  final bool isMandatory;
  final int sortOrder;
  final bool isCompleted;
  final DateTime? completedAt;
  final String? completedByUserName;

  ChecklistItemModel({
    required this.id,
    required this.templateId,
    required this.title,
    required this.isMandatory,
    required this.sortOrder,
    this.isCompleted = false,
    this.completedAt,
    this.completedByUserName,
  });

  factory ChecklistItemModel.fromJson(Map<String, dynamic> json) =>
      ChecklistItemModel(
        id: json['id'].toString(),
        templateId: json['template_id'].toString(),
        title: json['title'] ?? '',
        isMandatory: json['is_mandatory'] ?? true,
        sortOrder: (json['sort_order'] as num?)?.toInt() ?? 0,
        isCompleted: json['is_completed'] == true,
        completedAt:
            json['completed_at'] != null
                ? DateTime.tryParse(json['completed_at'].toString())
                : null,
        completedByUserName: json['completed_by_user_name'] as String?,
      );
}

class ChecklistTemplateModel {
  final String id;
  final String title;
  final String? description;
  final int? roleId;
  final String? roleName;
  final String shiftPeriod; // OPENING, CLOSING, ALL
  final bool isMandatory;
  final bool isActive;
  final List<ChecklistItemModel> items;
  final int completedCount;
  final int totalCount;

  ChecklistTemplateModel({
    required this.id,
    required this.title,
    this.description,
    this.roleId,
    this.roleName,
    required this.shiftPeriod,
    required this.isMandatory,
    this.isActive = true,
    this.items = const [],
    this.completedCount = 0,
    this.totalCount = 0,
  });

  factory ChecklistTemplateModel.fromJson(Map<String, dynamic> json) {
    final parsedItems =
        (json['items'] as List? ?? [])
            .map((e) => ChecklistItemModel.fromJson(e as Map<String, dynamic>))
            .toList();
    return ChecklistTemplateModel(
      id: json['id'].toString(),
      title: json['title'] ?? '',
      description: json['description'] as String?,
      roleId: (json['role_id'] as num?)?.toInt(),
      roleName: json['role_name'] as String?,
      shiftPeriod: json['shift_period']?.toString() ?? 'OPENING',
      isMandatory: json['is_mandatory'] ?? true,
      isActive: json['is_active'] ?? true,
      items: parsedItems,
      completedCount:
          (json['completed_count'] as num?)?.toInt() ??
          parsedItems.where((i) => i.isCompleted).length,
      totalCount:
          (json['total_count'] as num?)?.toInt() ?? parsedItems.length,
    );
  }
}

class ClockoutValidationResult {
  final String date;
  final bool allMandatoryCompleted;
  final int missingMandatoryCount;
  final List<Map<String, dynamic>> missingItems;

  ClockoutValidationResult({
    required this.date,
    required this.allMandatoryCompleted,
    required this.missingMandatoryCount,
    this.missingItems = const [],
  });

  factory ClockoutValidationResult.fromJson(Map<String, dynamic> json) =>
      ClockoutValidationResult(
        date: json['date']?.toString() ?? '',
        allMandatoryCompleted: json['all_mandatory_completed'] == true,
        missingMandatoryCount:
            (json['missing_mandatory_count'] as num?)?.toInt() ?? 0,
        missingItems:
            (json['missing_items'] as List? ?? [])
                .map((e) => Map<String, dynamic>.from(e as Map))
                .toList(),
      );
}

class HaccpDeviceModel {
  final String id;
  final String name;
  final double minTemp;
  final double maxTemp;
  final bool isActive;

  HaccpDeviceModel({
    required this.id,
    required this.name,
    required this.minTemp,
    required this.maxTemp,
    this.isActive = true,
  });

  factory HaccpDeviceModel.fromJson(Map<String, dynamic> json) =>
      HaccpDeviceModel(
        id: json['id'].toString(),
        name: json['name'] ?? '',
        minTemp: (json['min_temp'] as num?)?.toDouble() ?? 0.0,
        maxTemp: (json['max_temp'] as num?)?.toDouble() ?? 4.0,
        isActive: json['is_active'] ?? true,
      );
}

class HaccpLogModel {
  final String id;
  final String logType; // TEMPERATURE, SANITATION
  final String? deviceId;
  final String deviceName;
  final double? minTemp;
  final double? maxTemp;
  final double? measuredTemp;
  final bool isWithinNorm;
  final String? correctiveAction;
  final String userId;
  final String userName;
  final DateTime createdAt;

  HaccpLogModel({
    required this.id,
    required this.logType,
    this.deviceId,
    required this.deviceName,
    this.minTemp,
    this.maxTemp,
    this.measuredTemp,
    required this.isWithinNorm,
    this.correctiveAction,
    required this.userId,
    required this.userName,
    required this.createdAt,
  });

  factory HaccpLogModel.fromJson(Map<String, dynamic> json) => HaccpLogModel(
    id: json['id'].toString(),
    logType: json['log_type']?.toString() ?? 'TEMPERATURE',
    deviceId: json['device_id']?.toString(),
    deviceName: json['device_name'] ?? '',
    minTemp: (json['min_temp'] as num?)?.toDouble(),
    maxTemp: (json['max_temp'] as num?)?.toDouble(),
    measuredTemp: (json['measured_temp'] as num?)?.toDouble(),
    isWithinNorm: json['is_within_norm'] ?? true,
    correctiveAction: json['corrective_action'] as String?,
    userId: json['user_id'].toString(),
    userName: json['user_name'] ?? '',
    createdAt: DateTime.parse(json['created_at'].toString()),
  );
}

// ── Module C: Announcement Board with Read Receipts ──────────────────────────

class AnnouncementReaderModel {
  final String userId;
  final String userName;
  final DateTime? readAt;

  AnnouncementReaderModel({
    required this.userId,
    required this.userName,
    this.readAt,
  });

  factory AnnouncementReaderModel.fromJson(Map<String, dynamic> json) =>
      AnnouncementReaderModel(
        userId: json['user_id'].toString(),
        userName: json['user_name'] ?? '',
        readAt:
            json['read_at'] != null
                ? DateTime.tryParse(json['read_at'].toString())
                : null,
      );
}

class AnnouncementModel {
  final String id;
  final String title;
  final String content;
  final bool isPinned;
  final String authorId;
  final String authorName;
  final DateTime createdAt;
  // Employee fields
  final bool isRead;
  final DateTime? readAt;
  // Manager fields
  final int readCount;
  final int totalTargetCount;
  final List<AnnouncementReaderModel> readBy;
  final List<AnnouncementReaderModel> unreadBy;

  AnnouncementModel({
    required this.id,
    required this.title,
    required this.content,
    required this.isPinned,
    required this.authorId,
    required this.authorName,
    required this.createdAt,
    this.isRead = false,
    this.readAt,
    this.readCount = 0,
    this.totalTargetCount = 0,
    this.readBy = const [],
    this.unreadBy = const [],
  });

  factory AnnouncementModel.fromJson(Map<String, dynamic> json) =>
      AnnouncementModel(
        id: json['id'].toString(),
        title: json['title'] ?? '',
        content: json['content'] ?? '',
        isPinned: json['is_pinned'] == true,
        authorId: json['author_id'].toString(),
        authorName: json['author_name'] ?? 'Manager',
        createdAt: DateTime.parse(json['created_at'].toString()),
        isRead: json['is_read'] == true,
        readAt:
            json['read_at'] != null
                ? DateTime.tryParse(json['read_at'].toString())
                : null,
        readCount: (json['read_count'] as num?)?.toInt() ?? 0,
        totalTargetCount: (json['total_target_count'] as num?)?.toInt() ?? 0,
        readBy:
            (json['read_by'] as List? ?? [])
                .map(
                  (e) => AnnouncementReaderModel.fromJson(
                    e as Map<String, dynamic>,
                  ),
                )
                .toList(),
        unreadBy:
            (json['unread_by'] as List? ?? [])
                .map(
                  (e) => AnnouncementReaderModel.fromJson(
                    e as Map<String, dynamic>,
                  ),
                )
                .toList(),
      );
}

// ═══════════════════════════════════════════════════════════════════════════
//  Solver Explanation, Shift Audit Log & WFM Prediction Models
// ═══════════════════════════════════════════════════════════════════════════

class SolverDeficitExplanation {
  final String date;
  final int shiftDefId;
  final String shiftName;
  final int roleId;
  final String roleName;
  final int requiredCount;
  final int assignedCount;
  final int missingCount;
  final List<String> rootCauses;

  SolverDeficitExplanation({
    required this.date,
    required this.shiftDefId,
    required this.shiftName,
    required this.roleId,
    required this.roleName,
    required this.requiredCount,
    required this.assignedCount,
    required this.missingCount,
    this.rootCauses = const [],
  });

  factory SolverDeficitExplanation.fromJson(Map<String, dynamic> json) =>
      SolverDeficitExplanation(
        date: json['date']?.toString() ?? '',
        shiftDefId: (json['shift_def_id'] as num?)?.toInt() ?? 0,
        shiftName: json['shift_name']?.toString() ?? '',
        roleId: (json['role_id'] as num?)?.toInt() ?? 0,
        roleName: json['role_name']?.toString() ?? '',
        requiredCount: (json['required'] as num?)?.toInt() ?? 0,
        assignedCount: (json['assigned'] as num?)?.toInt() ?? 0,
        missingCount: (json['missing'] as num?)?.toInt() ?? 0,
        rootCauses:
            (json['root_causes'] as List? ?? [])
                .map((e) => e.toString())
                .toList(),
      );
}

class SolverEmployeeSummary {
  final String userId;
  final String userName;
  final int assignedShifts;
  final double assignedHours;
  final double mtdHours;
  final double totalMonthHours;
  final double? targetHours;
  final int? targetShifts;
  final double effectiveWeeklyTargetHours;
  final double scarcityRatio;

  SolverEmployeeSummary({
    required this.userId,
    required this.userName,
    required this.assignedShifts,
    required this.assignedHours,
    required this.mtdHours,
    required this.totalMonthHours,
    this.targetHours,
    this.targetShifts,
    this.effectiveWeeklyTargetHours = 0.0,
    this.scarcityRatio = 0.0,
  });

  factory SolverEmployeeSummary.fromJson(Map<String, dynamic> json) =>
      SolverEmployeeSummary(
        userId: json['user_id']?.toString() ?? '',
        userName: json['user_name']?.toString() ?? '',
        assignedShifts: (json['assigned_shifts'] as num?)?.toInt() ?? 0,
        assignedHours: (json['assigned_hours'] as num?)?.toDouble() ?? 0.0,
        mtdHours: (json['mtd_hours'] as num?)?.toDouble() ?? 0.0,
        totalMonthHours: (json['total_month_hours'] as num?)?.toDouble() ?? 0.0,
        targetHours: (json['target_hours'] as num?)?.toDouble(),
        targetShifts: (json['target_shifts'] as num?)?.toInt(),
        effectiveWeeklyTargetHours:
            (json['effective_weekly_target_hours'] as num?)?.toDouble() ?? 0.0,
        scarcityRatio: (json['scarcity_ratio'] as num?)?.toDouble() ?? 0.0,
      );
}

class SolverRestViolation {
  final String userId;
  final String userName;
  final String dateFrom;
  final String dateTo;
  final String shiftFrom;
  final String shiftTo;

  SolverRestViolation({
    required this.userId,
    required this.userName,
    required this.dateFrom,
    required this.dateTo,
    required this.shiftFrom,
    required this.shiftTo,
  });

  factory SolverRestViolation.fromJson(Map<String, dynamic> json) =>
      SolverRestViolation(
        userId: json['user_id']?.toString() ?? '',
        userName: json['user_name']?.toString() ?? '',
        dateFrom: json['date_from']?.toString() ?? '',
        dateTo: json['date_to']?.toString() ?? '',
        shiftFrom: json['shift_from']?.toString() ?? '',
        shiftTo: json['shift_to']?.toString() ?? '',
      );
}

class SolverExplanation {
  final String solverStatus;
  final double solveDurationSec;
  final int variablesCount;
  final int objectiveTermsCount;
  final double objectiveValue;
  final int totalRequiredSlots;
  final int totalAssignedSlots;
  final double coveragePct;
  final String? executedVia;
  final List<SolverDeficitExplanation> deficitExplanations;
  final List<SolverEmployeeSummary> employeeSummaries;
  final List<SolverRestViolation> restViolations;
  final List<String> domainLogs;

  SolverExplanation({
    required this.solverStatus,
    this.solveDurationSec = 0.0,
    this.variablesCount = 0,
    this.objectiveTermsCount = 0,
    this.objectiveValue = 0.0,
    this.totalRequiredSlots = 0,
    this.totalAssignedSlots = 0,
    this.coveragePct = 0.0,
    this.executedVia,
    this.deficitExplanations = const [],
    this.employeeSummaries = const [],
    this.restViolations = const [],
    this.domainLogs = const [],
  });

  factory SolverExplanation.fromJson(Map<String, dynamic> json) =>
      SolverExplanation(
        solverStatus: json['solver_status']?.toString() ?? 'UNKNOWN',
        solveDurationSec:
            (json['solve_duration_sec'] as num?)?.toDouble() ?? 0.0,
        variablesCount: (json['variables_count'] as num?)?.toInt() ?? 0,
        objectiveTermsCount:
            (json['objective_terms_count'] as num?)?.toInt() ?? 0,
        objectiveValue: (json['objective_value'] as num?)?.toDouble() ?? 0.0,
        totalRequiredSlots:
            (json['total_required_slots'] as num?)?.toInt() ?? 0,
        totalAssignedSlots:
            (json['total_assigned_slots'] as num?)?.toInt() ??
            (json['assigned_count'] as num?)?.toInt() ??
            0,
        coveragePct: (json['coverage_pct'] as num?)?.toDouble() ?? 0.0,
        executedVia: json['executed_via']?.toString(),
        deficitExplanations:
            (json['deficit_explanations'] as List? ?? [])
                .map(
                  (e) => SolverDeficitExplanation.fromJson(
                    Map<String, dynamic>.from(e as Map),
                  ),
                )
                .toList(),
        employeeSummaries:
            (json['employee_summaries'] as List? ?? [])
                .map(
                  (e) => SolverEmployeeSummary.fromJson(
                    Map<String, dynamic>.from(e as Map),
                  ),
                )
                .toList(),
        restViolations:
            (json['rest_violations'] as List? ?? [])
                .map(
                  (e) => SolverRestViolation.fromJson(
                    Map<String, dynamic>.from(e as Map),
                  ),
                )
                .toList(),
        domainLogs:
            (json['domain_logs'] as List? ?? [])
                .map((e) => e.toString())
                .toList(),
      );
}

class ShiftAuditLogEntry {
  final int id;
  final int restaurantId;
  final String shiftId;
  final String? scheduleId;
  final int? shiftDefId;
  final DateTime? date;
  final String? changedByUserId;
  final String? changedByUserName;
  final String action;
  final String? oldValue;
  final String? newValue;
  final DateTime createdAt;
  final String? shiftNameSnapshot;
  final String? roleNameSnapshot;
  final String? targetUserName;
  final String? actorName;
  final String? summary;

  ShiftAuditLogEntry({
    required this.id,
    required this.restaurantId,
    required this.shiftId,
    this.scheduleId,
    this.shiftDefId,
    this.date,
    this.changedByUserId,
    this.changedByUserName,
    required this.action,
    this.oldValue,
    this.newValue,
    required this.createdAt,
    this.shiftNameSnapshot,
    this.roleNameSnapshot,
    this.targetUserName,
    this.actorName,
    this.summary,
  });

  factory ShiftAuditLogEntry.fromJson(Map<String, dynamic> json) =>
      ShiftAuditLogEntry(
        id: (json['id'] as num?)?.toInt() ?? 0,
        restaurantId: (json['restaurant_id'] as num?)?.toInt() ?? 0,
        shiftId: json['shift_id']?.toString() ?? '',
        scheduleId: json['schedule_id']?.toString(),
        shiftDefId: (json['shift_def_id'] as num?)?.toInt(),
        date:
            json['date'] != null
                ? DateTime.tryParse(json['date'].toString())
                : null,
        changedByUserId: json['changed_by_user_id']?.toString(),
        changedByUserName: json['changed_by_user_name']?.toString(),
        action: json['action']?.toString() ?? 'UNKNOWN',
        oldValue: json['old_value']?.toString(),
        newValue: json['new_value']?.toString(),
        createdAt:
            json['created_at'] != null
                ? DateTime.tryParse(json['created_at'].toString()) ??
                    DateTime.now()
                : DateTime.now(),
        shiftNameSnapshot: json['shift_name_snapshot']?.toString(),
        roleNameSnapshot: json['role_name_snapshot']?.toString(),
        targetUserName: json['target_user_name']?.toString(),
        actorName: json['actor_name']?.toString(),
        summary: json['summary']?.toString(),
      );
}

class WfmBottleneckItem {
  final String date;
  final String dayName;
  final int shiftDefId;
  final String shiftName;
  final int roleId;
  final String roleName;
  final int requiredCount;
  final int availableCount;
  final int availableWithinTargetCount;
  final int deficit;
  final String severity;
  final String scope;
  final String message;

  WfmBottleneckItem({
    required this.date,
    required this.dayName,
    required this.shiftDefId,
    required this.shiftName,
    required this.roleId,
    required this.roleName,
    required this.requiredCount,
    required this.availableCount,
    required this.availableWithinTargetCount,
    required this.deficit,
    required this.severity,
    required this.scope,
    required this.message,
  });

  factory WfmBottleneckItem.fromJson(Map<String, dynamic> json) =>
      WfmBottleneckItem(
        date: json['date']?.toString() ?? '',
        dayName: json['day_name']?.toString() ?? '',
        shiftDefId: (json['shift_def_id'] as num?)?.toInt() ?? 0,
        shiftName: json['shift_name']?.toString() ?? '',
        roleId: (json['role_id'] as num?)?.toInt() ?? 0,
        roleName: json['role_name']?.toString() ?? '',
        requiredCount: (json['required_count'] as num?)?.toInt() ?? 0,
        availableCount: (json['available_count'] as num?)?.toInt() ?? 0,
        availableWithinTargetCount:
            (json['available_within_target_count'] as num?)?.toInt() ?? 0,
        deficit: (json['deficit'] as num?)?.toInt() ?? 0,
        severity: json['severity']?.toString() ?? 'WARNING',
        scope: json['scope']?.toString() ?? 'WEEK',
        message: json['message']?.toString() ?? '',
      );
}

class WfmEmployeeTargetRisk {
  final String userId;
  final String userName;
  final double? targetHoursPerMonth;
  final double scheduledHours;
  final double remainingHoursToTarget;
  final double potentialAvailableHours;
  final int leaveDaysInHorizon;
  final String riskLevel;
  final String? message;

  WfmEmployeeTargetRisk({
    required this.userId,
    required this.userName,
    this.targetHoursPerMonth,
    required this.scheduledHours,
    required this.remainingHoursToTarget,
    required this.potentialAvailableHours,
    required this.leaveDaysInHorizon,
    required this.riskLevel,
    this.message,
  });

  factory WfmEmployeeTargetRisk.fromJson(Map<String, dynamic> json) =>
      WfmEmployeeTargetRisk(
        userId: json['user_id']?.toString() ?? '',
        userName: json['user_name']?.toString() ?? '',
        targetHoursPerMonth:
            (json['target_hours_per_month'] as num?)?.toDouble(),
        scheduledHours: (json['scheduled_hours'] as num?)?.toDouble() ?? 0.0,
        remainingHoursToTarget:
            (json['remaining_hours_to_target'] as num?)?.toDouble() ?? 0.0,
        potentialAvailableHours:
            (json['potential_available_hours'] as num?)?.toDouble() ?? 0.0,
        leaveDaysInHorizon:
            (json['leave_days_in_horizon'] as num?)?.toInt() ?? 0,
        riskLevel: json['risk_level']?.toString() ?? 'LOW',
        message: json['message']?.toString(),
      );
}

class WfmShiftDriftItem {
  final int shiftDefId;
  final String shiftName;
  final String plannedStartTime;
  final String plannedEndTime;
  final String avgActualEndTime;
  final double avgEndDriftMinutes;
  final double avgDurationDriftMinutes;
  final int sampleCount;
  final bool isDrifting;
  final String? message;

  WfmShiftDriftItem({
    required this.shiftDefId,
    required this.shiftName,
    required this.plannedStartTime,
    required this.plannedEndTime,
    required this.avgActualEndTime,
    required this.avgEndDriftMinutes,
    required this.avgDurationDriftMinutes,
    required this.sampleCount,
    required this.isDrifting,
    this.message,
  });

  factory WfmShiftDriftItem.fromJson(Map<String, dynamic> json) =>
      WfmShiftDriftItem(
        shiftDefId: (json['shift_def_id'] as num?)?.toInt() ?? 0,
        shiftName: json['shift_name']?.toString() ?? '',
        plannedStartTime: json['planned_start_time']?.toString() ?? '',
        plannedEndTime: json['planned_end_time']?.toString() ?? '',
        avgActualEndTime: json['avg_actual_end_time']?.toString() ?? '',
        avgEndDriftMinutes:
            (json['avg_end_drift_minutes'] as num?)?.toDouble() ?? 0.0,
        avgDurationDriftMinutes:
            (json['avg_duration_drift_minutes'] as num?)?.toDouble() ?? 0.0,
        sampleCount: (json['sample_count'] as num?)?.toInt() ?? 0,
        isDrifting: json['is_drifting'] == true,
        message: json['message']?.toString(),
      );
}

class WfmMonthlyDriftProjection {
  final String month;
  final double plannedHours;
  final double projectedActualHours;
  final double projectedOvertimeDriftHours;
  final double plannedCost;
  final double projectedActualCost;
  final double projectedCostDriftDelta;

  WfmMonthlyDriftProjection({
    required this.month,
    required this.plannedHours,
    required this.projectedActualHours,
    required this.projectedOvertimeDriftHours,
    required this.plannedCost,
    required this.projectedActualCost,
    required this.projectedCostDriftDelta,
  });

  factory WfmMonthlyDriftProjection.fromJson(Map<String, dynamic> json) =>
      WfmMonthlyDriftProjection(
        month: json['month']?.toString() ?? '',
        plannedHours: (json['planned_hours'] as num?)?.toDouble() ?? 0.0,
        projectedActualHours:
            (json['projected_actual_hours'] as num?)?.toDouble() ?? 0.0,
        projectedOvertimeDriftHours:
            (json['projected_overtime_drift_hours'] as num?)?.toDouble() ?? 0.0,
        plannedCost: (json['planned_cost'] as num?)?.toDouble() ?? 0.0,
        projectedActualCost:
            (json['projected_actual_cost'] as num?)?.toDouble() ?? 0.0,
        projectedCostDriftDelta:
            (json['projected_cost_drift_delta'] as num?)?.toDouble() ?? 0.0,
      );
}

class WfmStabilityHotspot {
  final int shiftDefId;
  final String shiftName;
  final int dayOfWeek;
  final String dayName;
  final int giveawayCount;
  final int scheduledCount;
  final double rotationRatePct;
  final String message;

  WfmStabilityHotspot({
    required this.shiftDefId,
    required this.shiftName,
    required this.dayOfWeek,
    required this.dayName,
    required this.giveawayCount,
    required this.scheduledCount,
    required this.rotationRatePct,
    required this.message,
  });

  factory WfmStabilityHotspot.fromJson(Map<String, dynamic> json) =>
      WfmStabilityHotspot(
        shiftDefId: (json['shift_def_id'] as num?)?.toInt() ?? 0,
        shiftName: json['shift_name']?.toString() ?? '',
        dayOfWeek: (json['day_of_week'] as num?)?.toInt() ?? 0,
        dayName: json['day_name']?.toString() ?? '',
        giveawayCount: (json['giveaway_count'] as num?)?.toInt() ?? 0,
        scheduledCount: (json['scheduled_count'] as num?)?.toInt() ?? 0,
        rotationRatePct: (json['rotation_rate_pct'] as num?)?.toDouble() ?? 0.0,
        message: json['message']?.toString() ?? '',
      );
}

class LaborCostRoleItem {
  final int roleId;
  final String roleName;
  final String colorHex;
  final double plannedHours;
  final double projectedHoursWithDrift;
  final double plannedCost;
  final double projectedCostWithDrift;
  final int shiftsCount;

  LaborCostRoleItem({
    required this.roleId,
    required this.roleName,
    required this.colorHex,
    required this.plannedHours,
    this.projectedHoursWithDrift = 0.0,
    required this.plannedCost,
    required this.projectedCostWithDrift,
    required this.shiftsCount,
  });

  factory LaborCostRoleItem.fromJson(Map<String, dynamic> json) =>
      LaborCostRoleItem(
        roleId: (json['role_id'] as num?)?.toInt() ?? 0,
        roleName: json['role_name']?.toString() ?? '',
        colorHex: json['color_hex']?.toString() ?? '#607D8B',
        plannedHours: (json['planned_hours'] as num?)?.toDouble() ?? 0.0,
        projectedHoursWithDrift:
            (json['projected_hours_with_drift'] as num?)?.toDouble() ?? 0.0,
        plannedCost: (json['planned_cost'] as num?)?.toDouble() ?? 0.0,
        projectedCostWithDrift:
            (json['projected_cost_with_drift'] as num?)?.toDouble() ?? 0.0,
        shiftsCount: (json['shifts_count'] as num?)?.toInt() ?? 0,
      );
}

class LaborCostDailyItem {
  final String date;
  final int dayOfWeek;
  final String dayName;
  final String dayLabel;
  final double plannedHours;
  final double projectedHoursWithDrift;
  final double plannedCost;
  final double projectedCostWithDrift;
  final int shiftsCount;
  final bool isMostExpensive;

  LaborCostDailyItem({
    required this.date,
    this.dayOfWeek = 0,
    this.dayName = '',
    this.dayLabel = '',
    required this.plannedHours,
    this.projectedHoursWithDrift = 0.0,
    required this.plannedCost,
    required this.projectedCostWithDrift,
    required this.shiftsCount,
    required this.isMostExpensive,
  });

  factory LaborCostDailyItem.fromJson(Map<String, dynamic> json) =>
      LaborCostDailyItem(
        date: json['date']?.toString() ?? '',
        dayOfWeek: (json['day_of_week'] as num?)?.toInt() ?? 0,
        dayName: json['day_name']?.toString() ?? '',
        dayLabel:
            json['day_label']?.toString() ?? json['day_name']?.toString() ?? '',
        plannedHours: (json['planned_hours'] as num?)?.toDouble() ?? 0.0,
        projectedHoursWithDrift:
            (json['projected_hours_with_drift'] as num?)?.toDouble() ?? 0.0,
        plannedCost: (json['planned_cost'] as num?)?.toDouble() ?? 0.0,
        projectedCostWithDrift:
            (json['projected_cost_with_drift'] as num?)?.toDouble() ?? 0.0,
        shiftsCount: (json['shifts_count'] as num?)?.toInt() ?? 0,
        isMostExpensive: json['is_most_expensive'] == true,
      );
}

class LaborCostSimulation {
  final String startDate;
  final String endDate;
  final double totalPlannedHours;
  final double totalProjectedHoursWithDrift;
  final double estimatedPlannedCost;
  final double projectedCostWithDrift;
  final double driftCostDelta;
  final double avgHourlyCost;
  final List<LaborCostRoleItem> hoursByRole;
  final List<LaborCostDailyItem> dailyCosts;
  final Map<int, double> shiftDriftHoursMap;
  final double overallDriftRatio;

  LaborCostSimulation({
    this.startDate = '',
    this.endDate = '',
    required this.totalPlannedHours,
    required this.totalProjectedHoursWithDrift,
    required this.estimatedPlannedCost,
    required this.projectedCostWithDrift,
    this.driftCostDelta = 0.0,
    required this.avgHourlyCost,
    this.hoursByRole = const [],
    this.dailyCosts = const [],
    this.shiftDriftHoursMap = const {},
    this.overallDriftRatio = 1.0,
  });

  factory LaborCostSimulation.fromJson(Map<String, dynamic> json) {
    final rawDriftMap =
        json['shift_drift_hours_map'] as Map<String, dynamic>? ?? {};
    final parsedDriftMap = <int, double>{};
    for (final entry in rawDriftMap.entries) {
      final k = int.tryParse(entry.key);
      final v = (entry.value as num?)?.toDouble();
      if (k != null && v != null) {
        parsedDriftMap[k] = v;
      }
    }
    return LaborCostSimulation(
      startDate: json['start_date']?.toString() ?? '',
      endDate: json['end_date']?.toString() ?? '',
      totalPlannedHours:
          (json['total_planned_hours'] as num?)?.toDouble() ?? 0.0,
      totalProjectedHoursWithDrift:
          (json['total_projected_hours_with_drift'] as num?)?.toDouble() ??
          (json['total_projected_hours'] as num?)?.toDouble() ??
          0.0,
      estimatedPlannedCost:
          (json['estimated_planned_cost'] as num?)?.toDouble() ?? 0.0,
      projectedCostWithDrift:
          (json['projected_cost_with_drift'] as num?)?.toDouble() ?? 0.0,
      driftCostDelta: (json['drift_cost_delta'] as num?)?.toDouble() ?? 0.0,
      avgHourlyCost: (json['avg_hourly_cost'] as num?)?.toDouble() ?? 0.0,
      hoursByRole:
          ((json['hours_by_role'] ?? json['roles']) as List? ?? [])
              .map(
                (e) => LaborCostRoleItem.fromJson(
                  Map<String, dynamic>.from(e as Map),
                ),
              )
              .toList(),
      dailyCosts:
          ((json['daily_costs'] ?? json['daily']) as List? ?? [])
              .map(
                (e) => LaborCostDailyItem.fromJson(
                  Map<String, dynamic>.from(e as Map),
                ),
              )
              .toList(),
      shiftDriftHoursMap: parsedDriftMap,
      overallDriftRatio:
          (json['overall_drift_ratio'] as num?)?.toDouble() ?? 1.0,
    );
  }
}

class WfmPrediction {
  final String startDate;
  final String endDate;
  final List<WfmBottleneckItem> bottlenecks;
  final int weekBottlenecksCount;
  final int monthBottlenecksCount;
  final List<WfmEmployeeTargetRisk> employeeTargetRisks;
  final List<WfmShiftDriftItem> shiftDrifts;
  final List<WfmShiftDriftItem> driftingShifts;
  final WfmMonthlyDriftProjection? monthlyDriftProjection;
  final int totalGiveaways;
  final List<WfmStabilityHotspot> stabilityHotspots;
  final LaborCostSimulation? laborCostSimulation;

  WfmPrediction({
    required this.startDate,
    required this.endDate,
    this.bottlenecks = const [],
    this.weekBottlenecksCount = 0,
    this.monthBottlenecksCount = 0,
    this.employeeTargetRisks = const [],
    this.shiftDrifts = const [],
    this.driftingShifts = const [],
    this.monthlyDriftProjection,
    this.totalGiveaways = 0,
    this.stabilityHotspots = const [],
    this.laborCostSimulation,
  });

  factory WfmPrediction.fromJson(Map<String, dynamic> json) {
    final bf = json['bottleneck_forecast'] as Map<String, dynamic>? ?? {};
    final ad = json['attendance_drift'] as Map<String, dynamic>? ?? {};
    final ss = json['shift_stability'] as Map<String, dynamic>? ?? {};
    final lcs = json['labor_cost_simulation'] as Map<String, dynamic>?;
    final mp = ad['monthly_projection'] as Map<String, dynamic>?;

    return WfmPrediction(
      startDate: json['start_date']?.toString() ?? '',
      endDate: json['end_date']?.toString() ?? '',
      bottlenecks:
          (bf['bottlenecks'] as List? ?? [])
              .map(
                (e) => WfmBottleneckItem.fromJson(
                  Map<String, dynamic>.from(e as Map),
                ),
              )
              .toList(),
      weekBottlenecksCount: (bf['week_bottlenecks_count'] as num?)?.toInt() ?? 0,
      monthBottlenecksCount:
          (bf['month_bottlenecks_count'] as num?)?.toInt() ?? 0,
      employeeTargetRisks:
          (bf['employee_target_risks'] as List? ?? [])
              .map(
                (e) => WfmEmployeeTargetRisk.fromJson(
                  Map<String, dynamic>.from(e as Map),
                ),
              )
              .toList(),
      shiftDrifts:
          (ad['shift_drifts'] as List? ?? [])
              .map(
                (e) => WfmShiftDriftItem.fromJson(
                  Map<String, dynamic>.from(e as Map),
                ),
              )
              .toList(),
      driftingShifts:
          (ad['drifting_shifts'] as List? ?? [])
              .map(
                (e) => WfmShiftDriftItem.fromJson(
                  Map<String, dynamic>.from(e as Map),
                ),
              )
              .toList(),
      monthlyDriftProjection:
          mp != null ? WfmMonthlyDriftProjection.fromJson(mp) : null,
      totalGiveaways: (ss['total_giveaways'] as num?)?.toInt() ?? 0,
      stabilityHotspots:
          (ss['hotspots'] as List? ?? [])
              .map(
                (e) => WfmStabilityHotspot.fromJson(
                  Map<String, dynamic>.from(e as Map),
                ),
              )
              .toList(),
      laborCostSimulation:
          lcs != null ? LaborCostSimulation.fromJson(lcs) : null,
    );
  }
}



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

  JobRole({required this.id, required this.name, required this.colorHex});

  factory JobRole.fromJson(Map<String, dynamic> json) {
    return JobRole(
      id: json['id'],
      name: json['name'],
      colorHex: json['color_hex'],
    );
  }

  Map<String, dynamic> toJson() {
    return {'id': id, 'name': name, 'color_hex': colorHex};
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

  EmployeeScheduleEntry({
    required this.id,
    required this.date,
    required this.shiftName,
    required this.roleName,
    required this.startTime,
    required this.endTime,
    this.isOnGiveaway = false,
    this.coworkers = const [],
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

  UserStats({
    required this.totalShiftsCompleted,
    required this.totalHoursWorked,
    required this.monthlyShifts,
  });

  factory UserStats.fromJson(Map<String, dynamic> json) {
    return UserStats(
      totalShiftsCompleted: json['total_shifts_completed'],
      totalHoursWorked: (json['total_hours_worked'] as num).toDouble(),
      monthlyShifts:
          (json['monthly_shifts'] as List).cast<Map<String, dynamic>>(),
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

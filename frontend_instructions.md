# Frontend Agent Instructions

Two features to implement. Follow existing patterns: Riverpod for state, `ApiService` via `ref.read(apiServiceProvider)`, `GoogleFonts.inter`/`GoogleFonts.outfit` for typography, Material 3 design tokens.

> [!IMPORTANT]
> The app language is **Polish**. All user-facing strings must be in Polish.

---

## Feature 1: Vacation / Leave Requests

### 1.1 Data Models — [MODIFY] [models.dart](file:///c:/Users/matte/Desktop/PlannerV2/frontend/lib/models/models.dart)

Add at the end of the file:

```dart
// --- Leave Requests ---

class LeaveRequest {
  final String id;
  final String userId;
  final String userName;
  final String startDate;  // "YYYY-MM-DD"
  final String endDate;
  final String? reason;
  final String status;     // PENDING, APPROVED, REJECTED, CANCELLED
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
```

### 1.2 API Service Methods — [MODIFY] [api_service.dart](file:///c:/Users/matte/Desktop/PlannerV2/frontend/lib/services/api_service.dart)

Add these methods inside `ApiService`:

```dart
// --- Leave Requests (Employee) ---
Future<List<LeaveRequest>> getMyLeaveRequests({String? status}) async {
  final params = <String, dynamic>{};
  if (status != null) params['status'] = status;
  final response = await _dio.get('/employee/leave-requests', queryParameters: params);
  return (response.data as List).map((e) => LeaveRequest.fromJson(e)).toList();
}

Future<void> createLeaveRequest(DateTime startDate, DateTime endDate, String? reason) async {
  await _dio.post('/employee/leave-requests', data: {
    'start_date': startDate.toIso8601String().split('T')[0],
    'end_date': endDate.toIso8601String().split('T')[0],
    'reason': reason,
  });
}

Future<void> cancelLeaveRequest(String requestId) async {
  await _dio.delete('/employee/leave-requests/$requestId');
}

// --- Leave Requests (Manager) ---
Future<List<LeaveRequest>> getAllLeaveRequests({String? status}) async {
  final params = <String, dynamic>{};
  if (status != null) params['status'] = status;
  final response = await _dio.get('/manager/leave-requests', queryParameters: params);
  return (response.data as List).map((e) => LeaveRequest.fromJson(e)).toList();
}

Future<void> approveLeaveRequest(String requestId) async {
  await _dio.post('/manager/leave-requests/$requestId/approve');
}

Future<void> rejectLeaveRequest(String requestId) async {
  await _dio.post('/manager/leave-requests/$requestId/reject');
}

Future<List<LeaveCalendarEntry>> getLeaveCalendar(int year, int month) async {
  final response = await _dio.get('/manager/leave-requests/calendar', queryParameters: {
    'year': year,
    'month': month,
  });
  return (response.data['entries'] as List).map((e) => LeaveCalendarEntry.fromJson(e)).toList();
}
```

### 1.3 Employee: "Wnioski urlopowe" Tab — [MODIFY] [employee_dashboard.dart](file:///c:/Users/matte/Desktop/PlannerV2/frontend/lib/screens/employee/employee_dashboard.dart)

Currently the employee has 3 bottom navigation tabs:
- 0 = Mój Grafik
- 1 = Dostępność
- 2 = Obecność

**Change the "Dostępność" tab (index 1) to use a `DefaultTabController` with two internal tabs:**

| Sub-tab | Label | Content |
|---------|-------|---------|
| 0 | Dyspozycja | Existing `AvailabilityGrid` widget (move current code here) |
| 1 | Wnioski urlopowe | New `LeaveRequestsTab` widget |

Implementation:
- Wrap the "Dostępność" content in a `Column` with a `TabBar` at the top and a `TabBarView` below.
- Keep the week selector (`_selectedWeekStart`, arrows) only for the "Dyspozycja" sub-tab.

### 1.4 Employee: Leave Request Widget — [NEW] [leave_requests_tab.dart](file:///c:/Users/matte/Desktop/PlannerV2/frontend/lib/screens/employee/leave_requests_tab.dart)

Create a new widget `LeaveRequestsTab` (ConsumerStatefulWidget):

**UI Structure:**
```
┌─────────────────────────────────┐
│ [+ Złóż wniosek]   FloatingActionButton or button at top
├─────────────────────────────────┤
│ List of LeaveRequest cards:     │
│ ┌─────────────────────────────┐ │
│ │ 📅 15.03 – 22.03.2026      │ │
│ │ Powód: Wakacje rodzinne     │ │
│ │ Status: 🟡 Oczekuje         │ │
│ │                [Anuluj]     │ │
│ └─────────────────────────────┘ │
│ ┌─────────────────────────────┐ │
│ │ 📅 01.04 – 05.04.2026      │ │
│ │ Status: ✅ Zaakceptowany     │ │
│ └─────────────────────────────┘ │
└─────────────────────────────────┘
```

**"Złóż wniosek" dialog:**
- `showDateRangePicker` to pick start/end dates
- `TextField` for reason (optional)
- Submit calls `api.createLeaveRequest(start, end, reason)`
- Refresh list on success

**Status badges (use `Chip` or colored `Container`):**
- `PENDING` → 🟡 amber — "Oczekuje"
- `APPROVED` → ✅ green — "Zaakceptowany"
- `REJECTED` → 🔴 red — "Odrzucony"
- `CANCELLED` → ⚫ grey — "Anulowany"

**"Anuluj" button** visible only for `PENDING` requests. Calls `api.cancelLeaveRequest(id)`.

### 1.5 Manager: "Urlopy" Sub-Tab — [MODIFY] [attendance_approval_tab.dart](file:///c:/Users/matte/Desktop/PlannerV2/frontend/lib/screens/manager/attendance_approval_tab.dart)

Currently `AttendanceApprovalTab` is a single screen. **Convert it to use `DefaultTabController` with two sub-tabs:**

| Sub-tab | Label | Content |
|---------|-------|---------|
| 0 | Obecności | Existing attendance approval content |
| 1 | Urlopy | New leave management widget |

### 1.6 Manager: Leave Management Widget — [NEW] [leave_management_tab.dart](file:///c:/Users/matte/Desktop/PlannerV2/frontend/lib/screens/manager/leave_management_tab.dart)

Create `LeaveManagementTab` (ConsumerStatefulWidget) with **two sections stacked vertically**:

**Section A: Pending Requests List**
```
┌───────────────────────────────────────┐
│ Oczekujące wnioski (3)                │
├───────────────────────────────────────┤
│ ┌───────────────────────────────────┐ │
│ │ 👤 Anna Kowalska                  │ │
│ │ 📅 15.03 – 22.03.2026 (8 dni)    │ │
│ │ Powód: Wakacje                    │ │
│ │         [✅ Akceptuj] [❌ Odrzuć]  │ │
│ └───────────────────────────────────┘ │
└───────────────────────────────────────┘
```

**Section B: Mini Calendar Heatmap**

Build a custom month grid (like `TableCalendar` but simpler — just a `GridView` of day cells):
- Month/year selector with arrows (like the existing week selector pattern)
- 7 columns (Pn, Wt, Śr, Cz, Pt, Sob, Nd)
- Each day cell is colored based on how many employees are on leave:
  - 0 → default/white
  - 1 → light yellow
  - 2 → light orange
  - 3+ → red/coral
- Tapping a day shows a tooltip/bottom sheet with the names of employees on leave

Data source: `api.getLeaveCalendar(year, month)` → loop through entries, for each day count how many approved leaves overlap.

> [!TIP]
> Use this coloring logic:
> ```dart
> Color _getHeatColor(int count) {
>   if (count == 0) return Colors.transparent;
>   if (count == 1) return Colors.amber.shade100;
>   if (count == 2) return Colors.orange.shade200;
>   return Colors.red.shade200;
> }
> ```

---

## Feature 2: Enhanced Availability Hints in Manual Assignment

### 2.1 Redesign Assignment Dialog — [MODIFY] [scheduler_tab.dart](file:///c:/Users/matte/Desktop/PlannerV2/frontend/lib/screens/manager/scheduler_tab.dart)

The existing [_showAddAssignmentDialog](file:///c:/Users/matte/Desktop/PlannerV2/frontend/lib/screens/manager/scheduler_tab.dart#L175-L305) already fetches `teamAvailability` and sorts users by status. **Enhance it:**

Currently the dialog uses a `DropdownButtonFormField<String>` for employee selection. Replace it with a scrollable `ListView` of employee tiles grouped by status:

```
┌─────────────────────────────────────┐
│ Dodaj przypisanie                   │
│ Poniedziałek, 3 mar - Zmiana Rano  │
├─────────────────────────────────────┤
│ 🟢 Chcą pracować (2)               │
│ ┌─────────────────────────────────┐ │
│ │ ⭐ Anna Kowalska                │ │
│ │   Barista, Kelner  •  42/160h  │ │
│ └─────────────────────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │ ⭐ Jan Nowak                    │ │
│ │   Kucharz  •  38/160h          │ │
│ └─────────────────────────────────┘ │
│                                     │
│ 🔴 Nie mogą (1)                     │
│ ┌─────────────────────────────────┐ │
│ │ 🚫 Maria Wiśniewska (opacity)  │ │
│ │   Kelner  •  52/160h           │ │
│ └─────────────────────────────────┘ │
├─────────────────────────────────────┤
│ Rola:  [Dropdown]                   │
│              [Anuluj]  [Dodaj]      │
└─────────────────────────────────────┘
```

**Key changes:**
1. **Grouped list** instead of flat dropdown — section headers: "Chcą pracować", "Neutralni", "Nie mogą", "Już przypisani"
2. **Role badges** — small colored chips next to each name showing their job roles (use `color_hex` from the role)
3. **Hours info** — show `hoursThisMonth / targetHoursPerMonth` (e.g. "42/160h"). If no target, show just hours (e.g. "42h").  Grey out (reduce priority) employees who are over target.
4. **Selectable tile** — tap to select employee (highlight with primary color border). This replaces the dropdown.
5. **Unavailable employees** — show at reduced opacity (0.5), non-selectable, with a strike-through or dimmed style.

> [!NOTE]
> The backend will return the new fields `job_roles`, `target_hours`, `hours_this_month` from the `get_available_employees_for_shift` endpoint. Use `getTeamAvailability` for the availability status as before, and call the new endpoint data for the extra info. **Or** switch to using `GET /manager/schedules/available-employees?date=...&shift_def_id=...` which already returns sorted results with all the new data. This would simplify the frontend because you'd only need one API call instead of two.

---

## Verification Plan

```bash
cd frontend
flutter analyze
flutter run -d web-server --web-hostname=127.0.0.1 --web-port=5000
```

Test manually:
1. Employee: Go to Dostępność → "Wnioski urlopowe" tab → create a request → verify it shows in list
2. Manager: Go to Obecności → "Urlopy" tab → see pending request → approve → verify calendar heatmap
3. Manager: Go to Grafik → click "+" on a shift → verify employees are grouped with role badges and hours

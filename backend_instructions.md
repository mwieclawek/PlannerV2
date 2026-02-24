# Backend Agent Instructions

Two features to implement. Follow the existing code patterns: SQLModel for models, Pydantic `BaseModel` for schemas, `APIRouter` with `Depends`, and service classes.

---

## Feature 1: Vacation / Leave Requests

### 1.1 New Model & Enum — [MODIFY] [models.py](file:///c:/Users/matte/Desktop/PlannerV2/backend/app/models.py)

Add enum and model **after** the `ShiftGiveaway` class (line ~121):

```python
class LeaveStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

class LeaveRequest(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id")
    start_date: date
    end_date: date
    reason: Optional[str] = Field(default=None)
    status: LeaveStatus = Field(default=LeaveStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = Field(default=None)
    reviewed_by: Optional[UUID] = Field(default=None, foreign_key="user.id")

    user: User = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[LeaveRequest.user_id]"}
    )
```

> [!IMPORTANT]
> Import `LeaveStatus` in `schemas.py` alongside the other model imports.

### 1.2 Alembic Migration — [NEW]

Create a migration in `backend/alembic/versions/` following the naming convention `YYYYMMDD_HHMM_<hash>_add_leave_requests.py`. The migration should add a single table `leaverequest` with all columns from the model above.

### 1.3 New Schemas — [MODIFY] [schemas.py](file:///c:/Users/matte/Desktop/PlannerV2/backend/app/schemas.py)

Add at the end of the file:

```python
class LeaveRequestCreate(BaseModel):
    start_date: date_type
    end_date: date_type
    reason: Optional[str] = None

    @model_validator(mode='after')
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be >= start_date")
        return self

class LeaveRequestResponse(BaseModel):
    id: UUID
    user_id: UUID
    user_name: str          # ← populated from User.full_name in service
    start_date: date_type
    end_date: date_type
    reason: Optional[str]
    status: str             # LeaveStatus value
    created_at: datetime
    reviewed_at: Optional[datetime]
```

### 1.4 Employee Endpoints — [MODIFY] [employee.py](file:///c:/Users/matte/Desktop/PlannerV2/backend/app/routers/employee.py)

Add three endpoints:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/employee/leave-requests` | Create a new leave request |
| `GET` | `/employee/leave-requests` | List current user's leave requests (query params: `status` optional filter) |
| `DELETE` | `/employee/leave-requests/{request_id}` | Cancel a PENDING request (set status → CANCELLED) |

Implementation notes:
- Validate that start_date is in the future (or today).
- Validate no overlapping PENDING/APPROVED requests for the same user.
- Use `current_user.id` from `get_current_user` dependency.

### 1.5 Manager Endpoints — [MODIFY] [manager.py](file:///c:/Users/matte/Desktop/PlannerV2/backend/app/routers/manager.py)

Add four endpoints:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/manager/leave-requests` | List all leave requests (query params: `status` optional) |
| `POST` | `/manager/leave-requests/{request_id}/approve` | Approve a PENDING request |
| `POST` | `/manager/leave-requests/{request_id}/reject` | Reject a PENDING request |
| `GET` | `/manager/leave-requests/calendar` | Returns `{ "entries": [ { "user_id", "user_name", "start_date", "end_date", "status" } ] }` for a given `month` (int) and `year` (int) query params — used by the frontend calendar heatmap |

### 1.6 Auto-Set Availability on Approval

> [!CAUTION]
> This is the most critical piece of business logic.

When a leave request is **approved**, the backend must automatically create `Availability` records with status `UNAVAILABLE` for **every (date, shift_def)** combination in the leave period. Steps:

1. Fetch all `ShiftDefinition` records.
2. For each date in `[start_date … end_date]` and each shift, **upsert** an `Availability` row:
   - If exists → update status to `UNAVAILABLE`
   - If not exists → insert with status `UNAVAILABLE`
3. Commit all changes in the same transaction as the status update.

Put this logic inside a service method (either `EmployeeService` or a new `LeaveService`).

### 1.7 Tests — [NEW] [test_leave_requests.py](file:///c:/Users/matte/Desktop/PlannerV2/backend/tests/test_leave_requests.py)

Write tests covering:
- Employee creates a request → 201
- Employee lists own requests
- Employee cancels a PENDING request
- Manager approves → status changes + availability records created
- Manager rejects → status changes, no availability records
- Overlap validation (employee tries to create overlapping request → 400)
- Past date validation → 400

---

## Feature 2: Enhanced Availability Hints

### 2.1 Extend Response — [MODIFY] [manager_service.py](file:///c:/Users/matte/Desktop/PlannerV2/backend/app/services/manager_service.py)

In method [get_available_employees_for_shift](file:///c:/Users/matte/Desktop/PlannerV2/backend/app/services/manager_service.py#L602-L665), add to each result dict:

```python
result.append({
    "user_id": str(u.id),
    "full_name": u.full_name,
    "availability_status": status,
    # --- NEW fields ---
    "job_roles": [{"id": r.id, "name": r.name, "color_hex": r.color_hex} for r in u.job_roles],
    "target_hours": u.target_hours_per_month,
    "hours_this_month": calculate_hours_this_month(u.id),  # see below
})
```

Add a helper inside the method (or as a private method) that calculates hours already worked/scheduled this month for the employee:

```python
def calculate_hours_this_month(user_id):
    month_start = date_in.replace(day=1)
    schedules = self.session.exec(
        select(Schedule).where(
            Schedule.user_id == user_id,
            Schedule.date >= month_start,
            Schedule.date <= date_in
        )
    ).all()
    total = 0.0
    for s in schedules:
        shift = self.session.get(ShiftDefinition, s.shift_def_id)
        if shift:
            from datetime import datetime as dt, timedelta
            start_dt = dt.combine(date.today(), shift.start_time)
            end_dt = dt.combine(date.today(), shift.end_time)
            if end_dt <= start_dt:
                end_dt += timedelta(days=1)
            total += (end_dt - start_dt).total_seconds() / 3600
    return round(total, 1)
```

> [!NOTE]
> The frontend already uses `getTeamAvailability` in the assignment dialog. The new fields are just extra data — no new endpoint needed.

---

## Verification Plan

```bash
cd backend
python -m pytest tests/ -v
```

All existing tests must still pass. New `test_leave_requests.py` tests should all pass.

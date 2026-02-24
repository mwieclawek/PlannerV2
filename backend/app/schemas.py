from pydantic import BaseModel, field_validator, model_validator, ValidationInfo
from datetime import datetime, date as date_type, time
from typing import List, Optional
from uuid import UUID
from .models import RoleSystem, AvailabilityStatus, AttendanceStatus, GiveawayStatus

# ... (Previous imports remain, but need field_validator, ValidationInfo)

# --- Auth ---
class Token(BaseModel):
    access_token: str
    token_type: str

class UserBase(BaseModel):
    username: str
    full_name: str
    role_system: RoleSystem
    email: Optional[str] = None  # Optional for contact
    target_hours_per_month: Optional[int] = None
    target_shifts_per_month: Optional[int] = None
    is_active: bool = True

class UserCreate(UserBase):
    password: str
    manager_pin: Optional[str] = None

    @field_validator('username')
    @classmethod
    def username_must_be_valid(cls, v: str) -> str:
        if not v or len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        if ' ' in v:
            raise ValueError('Username cannot contain spaces')
        return v.lower()  # Normalize to lowercase

class GoogleAuthRequest(BaseModel):
    auth_code: str

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    role_system: Optional[RoleSystem] = None
    target_hours_per_month: Optional[int] = None
    target_shifts_per_month: Optional[int] = None
    is_active: Optional[bool] = None

    class Config:
        from_attributes = True

# --- New Features Schemas ---

class NextShiftInfo(BaseModel):
    date: date_type
    start_time: str # HH:MM
    end_time: str   # HH:MM
    shift_name: str
    role_name: str

class UserStats(BaseModel):
    total_shifts_completed: int
    total_hours_worked: float
    # Monthly breakdown for the last 6 months
    monthly_shifts: List[dict] # [{"month": "2023-01", "count": 10}, ...]

class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    job_roles: List[int] = []
    next_shift: Optional[NextShiftInfo] = None

    @model_validator(mode='before')
    @classmethod
    def extract_role_ids(cls, data):
        """Convert JobRole ORM objects to plain int IDs."""
        if hasattr(data, 'job_roles'):
            roles = data.job_roles
            if roles and hasattr(roles[0], 'id'):
                data.__dict__['job_roles'] = [r.id for r in roles]
        elif isinstance(data, dict) and 'job_roles' in data:
            roles = data['job_roles']
            if roles and hasattr(roles[0], 'id'):
                data['job_roles'] = [r.id for r in roles]
        return data

    class Config:
        from_attributes = True




# --- Roles ---
class JobRoleBase(BaseModel):
    name: str
    color_hex: str

class JobRoleCreate(JobRoleBase):
    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Name cannot be empty')
        return v

class JobRoleResponse(JobRoleBase):
    id: int

    class Config:
        from_attributes = True

# --- Shifts ---
class ShiftDefBase(BaseModel):
    name: str
    start_time: str # HH:MM - handled as string in input
    end_time: str   # HH:MM
    applicable_days: List[int] = [0, 1, 2, 3, 4, 5, 6]  # 0=Mon, 6=Sun, default all days

class ShiftDefCreate(ShiftDefBase):
    @field_validator('start_time', 'end_time')
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        # Try HH:MM first
        try:
            datetime.strptime(v, "%H:%M")
            return v
        except ValueError:
            pass
            
        # Try HH:MM:SS
        try:
            val = datetime.strptime(v, "%H:%M:%S")
            return val.strftime("%H:%M") # standardized to HH:MM
        except ValueError:
            raise ValueError("Time must be in HH:MM or HH:MM:SS format")

class ShiftDefResponse(BaseModel):
    id: int
    name: str
    start_time: time
    end_time: time
    applicable_days: List[int] = [0, 1, 2, 3, 4, 5, 6]

    @field_validator('applicable_days', mode='before')
    @classmethod
    def parse_applicable_days(cls, v):
        if isinstance(v, str):
            return [int(x) for x in v.split(',') if x.strip()]
        return v

    class Config:
        from_attributes = True

# --- Availability ---
class AvailabilityBase(BaseModel):
    date: date_type
    shift_def_id: int
    status: AvailabilityStatus

class AvailabilityUpdate(AvailabilityBase):
    pass

class AvailabilityResponse(AvailabilityBase):
    user_id: UUID

    class Config:
        from_attributes = True

# --- Requirements ---
class RequirementBase(BaseModel):
    date: Optional[date_type] = None
    day_of_week: Optional[int] = None
    shift_def_id: int
    role_id: int
    min_count: int

    @model_validator(mode='after')
    def check_date_or_day(self) -> 'RequirementBase':
        if self.date is None and self.day_of_week is None:
            raise ValueError('Either date or day_of_week must be provided')
        if self.date is not None and self.day_of_week is not None:
             raise ValueError('Cannot provide both date and day_of_week')
        return self

    @field_validator('day_of_week')
    @classmethod
    def validate_day(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 0 or v > 6):
            raise ValueError('day_of_week must be between 0 and 6')
        return v

class RequirementCreate(RequirementBase):
    @field_validator('min_count')
    @classmethod
    def min_count_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError('min_count must be non-negative')
        return v

class RequirementResponse(RequirementBase):
    id: UUID

    class Config:
        from_attributes = True

# --- Scheduler ---
class GenerateRequest(BaseModel):
    start_date: date_type
    end_date: date_type

class ScheduleBatchItem(BaseModel):
    date: date_type
    shift_def_id: int
    user_id: UUID
    role_id: int

class BatchSaveRequest(BaseModel):
    start_date: date_type
    end_date: date_type
    items: List[ScheduleBatchItem]

class ScheduleResponse(BaseModel):
    id: UUID
    date: date_type
    shift_def_id: int
    user_id: UUID
    role_id: int
    is_published: bool
    user_name: str
    role_name: str
    shift_name: str
    start_time: time
    end_time: time
    is_on_giveaway: bool = False

class EmployeeScheduleResponse(BaseModel):
    id: UUID
    date: date_type
    shift_name: str
    role_name: str
    start_time: str
    end_time: str
    is_on_giveaway: bool = False
    coworkers: List[str] = []

# --- Restaurant Config ---
class ConfigBase(BaseModel):
    name: str
    opening_hours: str
    address: Optional[str] = None

class ConfigUpdate(BaseModel):
    name: Optional[str] = None
    opening_hours: Optional[str] = None
    address: Optional[str] = None

class ConfigResponse(ConfigBase):
    id: int

    class Config:
        from_attributes = True

# --- User Management ---
class UserRolesUpdate(BaseModel):
    role_ids: List[int]

class PasswordReset(BaseModel):
    new_password: str

class UserPasswordChange(BaseModel):
    old_password: str
    new_password: str

class ManualAssignment(BaseModel):
    date: date_type
    shift_def_id: int
    user_id: UUID
    role_id: int

# --- Attendance ---
class AttendanceBase(BaseModel):
    user_id: UUID
    date: date_type
    check_in: time
    check_out: time
    was_scheduled: bool = True
    status: AttendanceStatus = AttendanceStatus.CONFIRMED
    schedule_id: Optional[UUID] = None

class AttendanceCreate(AttendanceBase):
    pass

class AttendanceResponse(AttendanceBase):
    id: UUID
    created_at: datetime
    user_name: Optional[str] = None

    class Config:
        from_attributes = True

# --- Shift Giveaway ---
class ShiftGiveawayResponse(BaseModel):
    id: UUID
    schedule_id: UUID
    offered_by: UUID
    offered_by_name: str = ""
    status: GiveawayStatus
    created_at: datetime
    taken_by: Optional[UUID] = None
    taken_by_name: Optional[str] = None
    # Schedule details
    date: Optional[date_type] = None
    shift_name: Optional[str] = None
    role_name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None

    class Config:
        from_attributes = True

class GiveawaySuggestion(BaseModel):
    user_id: UUID
    full_name: str
    availability_status: Optional[str] = None

class ShiftGiveawayWithSuggestions(ShiftGiveawayResponse):
    suggestions: List[GiveawaySuggestion] = []

class GiveawayReassignRequest(BaseModel):
    new_user_id: UUID

class DashboardHomeResponse(BaseModel):
    working_today: List[ScheduleResponse]
    missing_confirmations: List[AttendanceResponse]
    open_giveaways: List["ShiftGiveawayResponse"]

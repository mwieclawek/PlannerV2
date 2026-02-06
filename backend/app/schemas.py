from pydantic import BaseModel, field_validator, ValidationInfo
from datetime import datetime, date, time
from typing import List, Optional
from uuid import UUID
from .models import RoleSystem, AvailabilityStatus

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

class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    job_roles: List[int] = []

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
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError("Time must be in HH:MM format")
        return v

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
    date: date
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
    date: date
    shift_def_id: int
    role_id: int
    min_count: int

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
    start_date: date
    end_date: date

class ScheduleBatchItem(BaseModel):
    date: date
    shift_def_id: int
    user_id: UUID
    role_id: int

class BatchSaveRequest(BaseModel):
    start_date: date
    end_date: date
    items: List[ScheduleBatchItem]

class ScheduleResponse(BaseModel):
    id: UUID
    date: date
    shift_def_id: int
    user_id: UUID
    role_id: int
    is_published: bool
    user_name: str
    role_name: str
    shift_name: str

class EmployeeScheduleResponse(BaseModel):
    id: UUID
    date: date
    shift_name: str
    role_name: str
    start_time: str
    end_time: str

# --- Restaurant Config ---
class ConfigBase(BaseModel):
    name: str
    opening_hours: str
    address: Optional[str] = None

class ConfigUpdate(ConfigBase):
    pass

class ConfigResponse(ConfigBase):
    id: int

    class Config:
        from_attributes = True

# --- User Management ---
class UserRolesUpdate(BaseModel):
    role_ids: List[int]

class PasswordReset(BaseModel):
    new_password: str

class ManualAssignment(BaseModel):
    date: date
    shift_def_id: int
    user_id: UUID
    role_id: int

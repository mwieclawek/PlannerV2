from datetime import datetime, date as date_type
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from ..models import RoleSystem
from .base import _validate_password_strength


# --- Auth ---
class LoginRequest(BaseModel):
    """Login request supporting both email and username+tenant_slug."""
    username: str  # Can be email or username
    password: str
    tenant_slug: Optional[str] = None  # Required when logging in with username (not email)


class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# --- Users ---
class UserBase(BaseModel):
    username: str
    full_name: str
    role_system: RoleSystem
    email: Optional[str] = None  # Optional for contact
    target_hours_per_month: Optional[int] = None
    target_shifts_per_month: Optional[int] = None
    hourly_rate: Optional[float] = None
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

    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


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
    hourly_rate: Optional[float] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None


class NextShiftInfo(BaseModel):
    date: date_type
    start_time: str  # HH:MM
    end_time: str    # HH:MM
    shift_name: str
    role_name: str


class UserStats(BaseModel):
    total_shifts_completed: int
    total_hours_worked: float
    # Monthly breakdown for the last 6 months
    monthly_shifts: List[dict]  # [{"month": "2023-01", "count": 10, "hours": 80.0}, ...]
    selected_month: Optional[str] = None
    selected_month_worked_hours: float = 0.0
    selected_month_planned_hours: float = 0.0
    selected_month_shifts: int = 0
    target_hours_per_month: Optional[int] = None


class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    job_roles: List[int] = []
    job_role_names: List[str] = []
    next_shift: Optional[NextShiftInfo] = None
    tenant_id: Optional[int] = None
    tenant_slug: Optional[str] = None
    tenant_name: Optional[str] = None
    # Read-only. Intentionally absent from UserCreate/UserUpdate: ManagerService.update_user
    # applies every submitted field via setattr, so exposing it there would let any
    # restaurant manager promote themselves to system owner.
    is_superadmin: bool = False
    # Computed flag. The Google tokens themselves (access/refresh/expiry) and password hashes
    # are NEVER part of any response schema.
    is_google_calendar_connected: bool = False

    @model_validator(mode='before')
    @classmethod
    def extract_role_ids(cls, data):
        """Convert JobRole ORM objects to plain int IDs and derive the Google-connected flag."""
        if hasattr(data, 'encrypted_google_access_token') or hasattr(data, 'encrypted_google_refresh_token'):
            data.__dict__['is_google_calendar_connected'] = bool(
                getattr(data, 'encrypted_google_access_token', None)
                or getattr(data, 'encrypted_google_refresh_token', None)
            )
        if hasattr(data, 'job_roles'):
            roles = data.job_roles
            if roles and hasattr(roles[0], 'id'):
                data.__dict__['job_role_names'] = [r.name for r in roles if hasattr(r, 'name')]
                data.__dict__['job_roles'] = [r.id for r in roles]
        elif isinstance(data, dict) and 'job_roles' in data:
            roles = data['job_roles']
            if roles and hasattr(roles[0], 'id'):
                data['job_role_names'] = [r.name for r in roles if hasattr(r, 'name')]
                data['job_roles'] = [r.id for r in roles]
        return data

    model_config = ConfigDict(from_attributes=True)


# --- Roles ---
class JobRoleBase(BaseModel):
    name: str
    color_hex: str
    hourly_rate: Optional[float] = None


class JobRoleCreate(JobRoleBase):
    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Name cannot be empty')
        return v


class JobRoleResponse(JobRoleBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# --- User Management ---
class UserRolesUpdate(BaseModel):
    role_ids: List[int]


class PasswordReset(BaseModel):
    new_password: str

    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class UserPasswordChange(BaseModel):
    old_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)

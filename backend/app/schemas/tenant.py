from datetime import datetime, date as date_type
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from ..models import RoleSystem
from .base import _SLUG_RE, _EMAIL_RE, _validate_password_strength


# --- Tenant ---
class TenantBase(BaseModel):
    name: str
    slug: str


class TenantCreate(TenantBase):
    @field_validator('slug')
    @classmethod
    def slug_must_be_valid(cls, v: str) -> str:
        import re
        if not v or len(v) < 2:
            raise ValueError('Slug must be at least 2 characters')
        if not re.match(r'^[a-z0-9][a-z0-9-]*$', v):
            raise ValueError('Slug must contain only lowercase letters, digits, and hyphens')
        return v.lower()


class TenantResponse(TenantBase):
    id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Restaurant Config ---
class ConfigBase(BaseModel):
    name: str
    opening_hours: str
    address: Optional[str] = None


class ConfigUpdate(BaseModel):
    name: Optional[str] = None
    opening_hours: Optional[str] = None
    address: Optional[str] = None
    pos_enabled: Optional[bool] = None
    require_attendance_registration: Optional[bool] = None
    attendance_required_from: Optional[date_type] = None
    require_checklists: Optional[bool] = None
    enable_tip_pool: Optional[bool] = None
    enable_daily_closeout: Optional[bool] = None


class ConfigResponse(ConfigBase):
    id: int
    pos_enabled: bool = False
    require_attendance_registration: bool = False
    attendance_required_from: Optional[date_type] = None
    require_checklists: bool = True
    enable_tip_pool: bool = True
    enable_daily_closeout: bool = True
    tenant_id: Optional[int] = None

    @model_validator(mode='before')
    @classmethod
    def extract_opening_hours(cls, data):
        if hasattr(data, 'opening_hours') and not isinstance(data.opening_hours, str):
            import json
            hours_dict = {}
            for h in data.opening_hours:
                hours_dict[str(h.day_of_week)] = {
                    "open": h.open_time.strftime("%H:%M"),
                    "close": h.close_time.strftime("%H:%M")
                }
            if not isinstance(data, dict):
                return {
                    "id": getattr(data, "id", None),
                    "name": getattr(data, "name", ""),
                    "opening_hours": json.dumps(hours_dict),
                    "address": getattr(data, "address", None),
                    "pos_enabled": getattr(data, "pos_enabled", False),
                    "require_attendance_registration": getattr(data, "require_attendance_registration", False),
                    "attendance_required_from": getattr(data, "attendance_required_from", None),
                    "require_checklists": getattr(data, "require_checklists", True),
                    "enable_tip_pool": getattr(data, "enable_tip_pool", True),
                    "enable_daily_closeout": getattr(data, "enable_daily_closeout", True),
                    "tenant_id": getattr(data, "tenant_id", getattr(data, "id", None)),
                }
        return data

    model_config = ConfigDict(from_attributes=True)


# --- System Settings (Kill Switch / Maintenance Mode) ---
class SystemSettingsResponse(BaseModel):
    is_login_enabled: bool = True
    blocked_login_message: str
    tenant_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class SystemSettingsUpdate(BaseModel):
    is_login_enabled: Optional[bool] = None
    blocked_login_message: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
#  SysAdmin (global system-owner panel)
# ═══════════════════════════════════════════════════════════════════════════════

class SysAdminRestaurantCreate(BaseModel):
    """Create a new restaurant (tenant). `login_id` is accepted as an alias of `slug`."""
    name: str
    slug: Optional[str] = None
    login_id: Optional[str] = None

    @field_validator('name')
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError('Name must be at least 2 characters')
        return v

    @model_validator(mode='after')
    def resolve_slug(self):
        import re
        raw = (self.slug or self.login_id or '').strip().lower()
        if not raw:
            raise ValueError('slug (login_id) is required')
        if not re.match(_SLUG_RE, raw):
            raise ValueError(
                'slug (login_id) must be 2-63 chars: lowercase letters, digits and hyphens, '
                'starting with a letter or digit'
            )
        self.slug = raw
        self.login_id = raw
        return self


class SysAdminRestaurantStatusUpdate(BaseModel):
    is_active: bool


class SysAdminRestaurantUpdate(BaseModel):
    """Partial update of a restaurant. `login_id` is accepted as an alias of `slug`."""
    name: Optional[str] = None
    slug: Optional[str] = None
    login_id: Optional[str] = None

    @field_validator('name')
    @classmethod
    def name_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if len(v) < 2:
            raise ValueError('Name must be at least 2 characters')
        return v

    @model_validator(mode='after')
    def resolve_slug(self):
        import re
        raw = self.slug if self.slug is not None else self.login_id
        if raw is None:
            return self
        raw = raw.strip().lower()
        if not re.match(_SLUG_RE, raw):
            raise ValueError(
                'slug (login_id) must be 2-63 chars: lowercase letters, digits and hyphens, '
                'starting with a letter or digit'
            )
        self.slug = raw
        self.login_id = raw
        return self


class SysAdminUserResponse(BaseModel):
    id: UUID
    username: str
    full_name: str
    email: Optional[str] = None
    role_system: RoleSystem
    is_active: bool
    created_at: Optional[datetime] = None


class SysAdminPasswordReset(BaseModel):
    new_password: str

    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class SysAdminRestaurantResponse(BaseModel):
    id: int
    name: str
    slug: str
    is_active: bool
    created_at: Optional[datetime] = None
    user_count: int = 0      # active users attached to the restaurant
    manager_count: int = 0   # active users with RoleSystem.MANAGER


class SysAdminManagerCreate(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str

    @field_validator('email')
    @classmethod
    def email_valid(cls, v: str) -> str:
        import re
        v = v.strip().lower()
        if not re.match(_EMAIL_RE, v):
            raise ValueError('Invalid email address')
        return v

    @field_validator('first_name', 'last_name')
    @classmethod
    def names_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Field cannot be empty')
        return v

    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class SysAdminManagerResponse(BaseModel):
    user_id: UUID
    email: str
    username: str
    full_name: str
    tenant_id: int
    role_system: RoleSystem
    created: bool  # False => an existing account in this restaurant was promoted
    message: str


class SysAdminLogEntry(BaseModel):
    timestamp: str
    level: str
    category: str = "SYSTEM"
    logger: str = ""
    message: str = ""
    event_title: Optional[str] = None
    details: Optional[Any] = None
    traceback: Optional[str] = None
    actor_id: Optional[str] = None
    actor_name: Optional[str] = "System"
    tenant_id: Optional[int] = None
    tenant_name: Optional[str] = None
    restaurant_name: Optional[str] = None
    restaurant_slug: Optional[str] = None


class SysAdminLogsResponse(BaseModel):
    total: int
    items: List[SysAdminLogEntry]
    available_levels: List[str]
    available_categories: List[str] = []

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Float, Integer, UniqueConstraint
from sqlalchemy import false as sa_false

from .base import register_tenant_listener

if TYPE_CHECKING:
    from .tenant import RestaurantConfig
    from .scheduling import ShiftDefinition, Availability, Schedule


class RoleSystem(str, Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    EMPLOYEE = "EMPLOYEE"


# Join table for User and JobRole
class UserJobRoleLink(SQLModel, table=True):
    user_id: Optional[UUID] = Field(default=None, foreign_key="user.id", primary_key=True)
    role_id: Optional[int] = Field(default=None, foreign_key="jobrole.id", primary_key=True)


class ShiftRoleLink(SQLModel, table=True):
    shift_def_id: Optional[int] = Field(default=None, foreign_key="shiftdefinition.id", primary_key=True)
    role_id: Optional[int] = Field(default=None, foreign_key="jobrole.id", primary_key=True)


class JobRole(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="restaurantconfig.id", index=True)
    name: str
    color_hex: str
    hourly_rate: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))

    users: List["User"] = Relationship(back_populates="job_roles", link_model=UserJobRoleLink)
    shifts: List["ShiftDefinition"] = Relationship(back_populates="allowed_roles", link_model=ShiftRoleLink)


class User(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("tenant_id", "username", name="uq_user_tenant_username"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="restaurantconfig.id", index=True)
    username: str = Field(index=True)
    email: Optional[str] = Field(default=None, index=True)  # Optional, for contact only
    password_hash: str
    full_name: str
    role_system: RoleSystem = Field(default=RoleSystem.EMPLOYEE)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    target_hours_per_month: Optional[int] = Field(default=None, sa_column=Column(Integer, nullable=True))
    target_shifts_per_month: Optional[int] = Field(default=None, sa_column=Column(Integer, nullable=True))
    hourly_rate: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))
    manager_pin: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    # Global system-owner flag (cross-tenant). NOT the same as RoleSystem.ADMIN/MANAGER,
    # which are scoped to a single restaurant. Never settable through tenant-level endpoints.
    is_superadmin: bool = Field(default=False, sa_column_kwargs={"server_default": sa_false()})
    encrypted_google_access_token: Optional[str] = Field(default=None)
    encrypted_google_refresh_token: Optional[str] = Field(default=None)

    restaurant_config: Optional["RestaurantConfig"] = Relationship(back_populates="users")

    @property
    def tenant(self) -> Optional["RestaurantConfig"]:
        return self.restaurant_config

    job_roles: List[JobRole] = Relationship(back_populates="users", link_model=UserJobRoleLink)
    availabilities: List["Availability"] = Relationship(back_populates="user")
    schedules: List["Schedule"] = Relationship(back_populates="user")
    devices: List["UserDevice"] = Relationship(back_populates="user")

    @property
    def google_access_token(self) -> Optional[str]:
        if not self.encrypted_google_access_token:
            return None
        import os
        from cryptography.fernet import Fernet
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            return self.encrypted_google_access_token
        try:
            f = Fernet(key.encode())
            return f.decrypt(self.encrypted_google_access_token.encode()).decode()
        except Exception:
            return self.encrypted_google_access_token

    @google_access_token.setter
    def google_access_token(self, value: Optional[str]):
        if not value:
            self.encrypted_google_access_token = None
            return
        import os
        from cryptography.fernet import Fernet
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            self.encrypted_google_access_token = value
            return
        f = Fernet(key.encode())
        self.encrypted_google_access_token = f.encrypt(value.encode()).decode()

    @property
    def google_refresh_token(self) -> Optional[str]:
        if not self.encrypted_google_refresh_token:
            return None
        import os
        from cryptography.fernet import Fernet
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            return self.encrypted_google_refresh_token
        try:
            f = Fernet(key.encode())
            return f.decrypt(self.encrypted_google_refresh_token.encode()).decode()
        except Exception:
            return self.encrypted_google_refresh_token

    @google_refresh_token.setter
    def google_refresh_token(self, value: Optional[str]):
        if not value:
            self.encrypted_google_refresh_token = None
            return
        import os
        from cryptography.fernet import Fernet
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            self.encrypted_google_refresh_token = value
            return
        f = Fernet(key.encode())
        self.encrypted_google_refresh_token = f.encrypt(value.encode()).decode()


class Notification(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    title: str = Field(max_length=200)
    body: str = Field(max_length=1000)
    is_read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserDevice(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    fcm_token: str = Field(unique=True, index=True)
    last_active: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    user: User = Relationship(back_populates="devices")


register_tenant_listener(User, JobRole)

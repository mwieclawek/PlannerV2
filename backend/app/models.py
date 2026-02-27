from datetime import time, date, datetime, date as date_type
from typing import Optional, List
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, Date, Integer
from enum import Enum

class RoleSystem(str, Enum):
    MANAGER = "MANAGER"
    EMPLOYEE = "EMPLOYEE"

class AvailabilityStatus(str, Enum):
    UNAVAILABLE = "UNAVAILABLE"
    AVAILABLE = "AVAILABLE"

# Join table for User and JobRole
class UserJobRoleLink(SQLModel, table=True):
    user_id: Optional[UUID] = Field(default=None, foreign_key="user.id", primary_key=True)
    role_id: Optional[int] = Field(default=None, foreign_key="jobrole.id", primary_key=True)

class JobRole(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    color_hex: str
    
    users: List["User"] = Relationship(back_populates="job_roles", link_model=UserJobRoleLink)

class User(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: Optional[str] = Field(default=None)  # Optional, for contact only
    password_hash: str
    full_name: str
    role_system: RoleSystem = Field(default=RoleSystem.EMPLOYEE)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    target_hours_per_month: Optional[int] = Field(default=None, sa_column=Column(Integer, nullable=True))
    target_shifts_per_month: Optional[int] = Field(default=None, sa_column=Column(Integer, nullable=True))
    manager_pin: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    encrypted_google_access_token: Optional[str] = Field(default=None)
    encrypted_google_refresh_token: Optional[str] = Field(default=None)

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

class ShiftDefinitionDayLink(SQLModel, table=True):
    shift_def_id: Optional[int] = Field(default=None, foreign_key="shiftdefinition.id", primary_key=True)
    day_of_week: int = Field(primary_key=True)

class ShiftDefinition(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    start_time: time
    end_time: time
    days: List["ShiftDefinitionDayLink"] = Relationship()

class Availability(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id")
    date: date
    shift_def_id: int = Field(foreign_key="shiftdefinition.id")
    status: AvailabilityStatus

    user: User = Relationship(back_populates="availabilities")

class StaffingRequirement(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    shift_def_id: int = Field(foreign_key="shiftdefinition.id")
    role_id: int = Field(foreign_key="jobrole.id")
    min_count: int
    date: Optional[date_type] = Field(default=None, sa_column=Column(Date, nullable=True))
    day_of_week: Optional[int] = Field(default=None, sa_column=Column(Integer, nullable=True))  # 0=Monday, 6=Sunday

class Schedule(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    date: date
    shift_def_id: int = Field(foreign_key="shiftdefinition.id")
    user_id: UUID = Field(foreign_key="user.id")
    role_id: int = Field(foreign_key="jobrole.id")
    is_published: bool = Field(default=False)


    user: User = Relationship(back_populates="schedules")

class RestaurantOpeningHour(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    config_id: int = Field(foreign_key="restaurantconfig.id")
    day_of_week: int
    open_time: time
    close_time: time

    config: "RestaurantConfig" = Relationship(back_populates="opening_hours")

class RestaurantConfig(SQLModel, table=True):
    id: int = Field(default=1, primary_key=True)
    name: str
    address: Optional[str] = None
    
    opening_hours: List["RestaurantOpeningHour"] = Relationship(back_populates="config")

class AttendanceStatus(str, Enum):
    PENDING = "PENDING"       # Waiting for manager approval (unscheduled)
    CONFIRMED = "CONFIRMED"   # Confirmed attendance
    REJECTED = "REJECTED"     # Rejected by manager

class Attendance(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id")
    date: date
    check_in: time
    check_out: time
    was_scheduled: bool = Field(default=True)  # Was this person scheduled that day?
    status: AttendanceStatus = Field(default=AttendanceStatus.CONFIRMED)
    schedule_id: Optional[UUID] = Field(default=None, foreign_key="schedule.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    user: User = Relationship()


class GiveawayStatus(str, Enum):
    OPEN = "OPEN"
    TAKEN = "TAKEN"
    CANCELLED = "CANCELLED"

class ShiftGiveaway(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    schedule_id: UUID = Field(foreign_key="schedule.id")
    offered_by: UUID = Field(foreign_key="user.id")
    status: GiveawayStatus = Field(default=GiveawayStatus.OPEN)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    taken_by: Optional[UUID] = Field(default=None, foreign_key="user.id")

    schedule: Schedule = Relationship()

class LeaveStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

class LeaveRequest(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    start_date: date
    end_date: date
    reason: str = Field(max_length=500)
    status: LeaveStatus = Field(default=LeaveStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[UUID] = Field(default=None, foreign_key="user.id")

    user: User = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[LeaveRequest.user_id]"}
    )

class Notification(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    title: str = Field(max_length=200)
    body: str = Field(max_length=1000)
    is_read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserDevice(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    fcm_token: str = Field(unique=True, index=True)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    
    user: User = Relationship(back_populates="devices")

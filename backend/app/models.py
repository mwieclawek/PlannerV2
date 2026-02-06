from datetime import time, date, datetime
from typing import Optional, List
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Relationship
from enum import Enum

class RoleSystem(str, Enum):
    MANAGER = "MANAGER"
    EMPLOYEE = "EMPLOYEE"

class AvailabilityStatus(str, Enum):
    PREFERRED = "PREFERRED"
    NEUTRAL = "NEUTRAL"
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

    job_roles: List[JobRole] = Relationship(back_populates="users", link_model=UserJobRoleLink)
    availabilities: List["Availability"] = Relationship(back_populates="user")
    schedules: List["Schedule"] = Relationship(back_populates="user")

class ShiftDefinition(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    start_time: time
    end_time: time
    applicable_days: str = Field(default="0,1,2,3,4,5,6")  # Comma-separated: 0=Mon, 6=Sun

class Availability(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id")
    date: date
    shift_def_id: int = Field(foreign_key="shiftdefinition.id")
    status: AvailabilityStatus

    user: User = Relationship(back_populates="availabilities")

class StaffingRequirement(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    date: date
    shift_def_id: int = Field(foreign_key="shiftdefinition.id")
    role_id: int = Field(foreign_key="jobrole.id")
    min_count: int

class Schedule(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    date: date
    shift_def_id: int = Field(foreign_key="shiftdefinition.id")
    user_id: UUID = Field(foreign_key="user.id")
    role_id: int = Field(foreign_key="jobrole.id")
    is_published: bool = Field(default=False)


    user: User = Relationship(back_populates="schedules")

class RestaurantConfig(SQLModel, table=True):
    id: int = Field(default=1, primary_key=True)
    name: str
    opening_hours: str = Field(default="{}") # JSON string for flexibility
    address: Optional[str] = None

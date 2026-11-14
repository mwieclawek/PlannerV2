from datetime import datetime, date, time, date as date_type, timezone
from enum import Enum
from typing import Optional, List
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Date, ForeignKey, Integer, String

from .base import register_tenant_listener
from .users import User, JobRole, ShiftRoleLink


class AvailabilityStatus(str, Enum):
    UNAVAILABLE = "UNAVAILABLE"
    AVAILABLE = "AVAILABLE"


class ShiftDefinitionDayLink(SQLModel, table=True):
    shift_def_id: Optional[int] = Field(default=None, foreign_key="shiftdefinition.id", primary_key=True)
    day_of_week: int = Field(primary_key=True)


class ShiftDefinition(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="restaurantconfig.id", index=True)
    name: str
    start_time: time
    end_time: time
    days: List["ShiftDefinitionDayLink"] = Relationship()
    allowed_roles: List["JobRole"] = Relationship(back_populates="shifts", link_model=ShiftRoleLink)


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


# Alias Shift to Schedule for consistency across models and routers
Shift = Schedule


class ShiftAuditLog(SQLModel, table=True):
    __tablename__ = "shiftauditlog"
    id: Optional[int] = Field(default=None, primary_key=True)
    restaurant_id: int = Field(foreign_key="restaurantconfig.id", index=True)
    shift_id: str = Field(index=True)
    schedule_id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(ForeignKey("schedule.id", ondelete="SET NULL"), nullable=True, index=True),
    )
    shift_def_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("shiftdefinition.id", ondelete="SET NULL"), nullable=True, index=True),
    )
    date: Optional[date_type] = Field(
        default=None,
        sa_column=Column(Date, nullable=True, index=True),
    )
    changed_by_user_id: Optional[UUID] = Field(default=None, foreign_key="user.id")
    action: str
    old_value: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    new_value: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Snapshot & human-readable summary fields
    shift_name_snapshot: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    role_name_snapshot: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    target_user_name: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    actor_name: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    summary: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))

    changed_by_user: Optional[User] = Relationship()

    @property
    def tenant_id(self) -> int:
        return self.restaurant_id

    @tenant_id.setter
    def tenant_id(self, val: int):
        self.restaurant_id = val


class GiveawayStatus(str, Enum):
    OPEN = "OPEN"
    TAKEN = "TAKEN"
    CANCELLED = "CANCELLED"


class ShiftGiveaway(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    schedule_id: UUID = Field(foreign_key="schedule.id")
    offered_by: UUID = Field(foreign_key="user.id")
    status: GiveawayStatus = Field(default=GiveawayStatus.OPEN)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    taken_by: Optional[UUID] = Field(default=None, foreign_key="user.id")
    target_shift_id: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))

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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[UUID] = Field(default=None, foreign_key="user.id")

    user: User = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[LeaveRequest.user_id]"}
    )


register_tenant_listener(ShiftDefinition, ShiftAuditLog)

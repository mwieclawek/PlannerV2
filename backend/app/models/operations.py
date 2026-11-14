from datetime import datetime, date, time, date as date_type, timezone
from enum import Enum
from typing import Optional, List
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Float, String, UniqueConstraint

from .base import register_tenant_listener
from .users import User, JobRole


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
    checklist_skip_reason: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    is_absent: bool = Field(default=False)
    absence_reason: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    user: User = Relationship()


# ── Module A: Payroll, Daily Closeout & Tip Pooling ───────────────────────────

class DailyCloseout(SQLModel, table=True):
    """Daily revenue and tip pool entered by manager at day closeout."""
    __tablename__ = "dailycloseout"
    __table_args__ = (
        UniqueConstraint("tenant_id", "date", name="uq_dailycloseout_tenant_date"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="restaurantconfig.id", index=True)
    date: date_type = Field(index=True)
    daily_revenue: float = Field(default=0.0)
    tip_pool: float = Field(default=0.0)
    notes: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    created_by: Optional[UUID] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Module B: Operational Checklists & Digital HACCP Registry ─────────────────

class ShiftPeriodType(str, Enum):
    OPENING = "OPENING"
    CLOSING = "CLOSING"
    ALL = "ALL"


class ChecklistTemplate(SQLModel, table=True):
    """Checklist template assigned to a role or shift period (Opening / Closing)."""
    __tablename__ = "checklisttemplate"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="restaurantconfig.id", index=True)
    title: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    role_id: Optional[int] = Field(default=None, foreign_key="jobrole.id", index=True)
    shift_period: ShiftPeriodType = Field(default=ShiftPeriodType.OPENING)
    is_mandatory: bool = Field(default=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    items: List["ChecklistTemplateItem"] = Relationship(back_populates="template")
    role: Optional[JobRole] = Relationship()


class ChecklistTemplateItem(SQLModel, table=True):
    """Single task item inside a ChecklistTemplate."""
    __tablename__ = "checklisttemplateitem"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    template_id: UUID = Field(foreign_key="checklisttemplate.id", index=True)
    title: str = Field(max_length=300)
    is_mandatory: bool = Field(default=True)
    sort_order: int = Field(default=0)

    template: Optional[ChecklistTemplate] = Relationship(back_populates="items")


class ChecklistCompletion(SQLModel, table=True):
    """Records an employee checking off a checklist item on a specific date."""
    __tablename__ = "checklistcompletion"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="restaurantconfig.id", index=True)
    template_id: UUID = Field(foreign_key="checklisttemplate.id", index=True)
    item_id: UUID = Field(foreign_key="checklisttemplateitem.id", index=True)
    date: date_type = Field(index=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    is_completed: bool = Field(default=True)
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    user: Optional[User] = Relationship()


class HaccpDevice(SQLModel, table=True):
    """Cooling device or sanitation station monitored in the Digital HACCP Registry."""
    __tablename__ = "haccpdevice"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="restaurantconfig.id", index=True)
    name: str = Field(max_length=200)
    min_temp: float = Field(default=0.0)
    max_temp: float = Field(default=4.0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HaccpLogType(str, Enum):
    TEMPERATURE = "TEMPERATURE"
    SANITATION = "SANITATION"


class HaccpLog(SQLModel, table=True):
    """Temperature measurement or sanitation schedule confirmation with digital signature."""
    __tablename__ = "haccplog"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="restaurantconfig.id", index=True)
    log_type: HaccpLogType = Field(default=HaccpLogType.TEMPERATURE)
    device_id: Optional[UUID] = Field(default=None, foreign_key="haccpdevice.id", index=True)
    device_name: str = Field(max_length=200)
    min_temp: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))
    max_temp: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))
    measured_temp: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))
    is_within_norm: bool = Field(default=True)
    corrective_action: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    user_id: UUID = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    user: Optional[User] = Relationship()


# ── Module C: Announcement Board with Read Receipts ───────────────────────────

class Announcement(SQLModel, table=True):
    """Internal venue announcement published by a manager."""
    __tablename__ = "announcement"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="restaurantconfig.id", index=True)
    author_id: UUID = Field(foreign_key="user.id", index=True)
    title: str = Field(max_length=200)
    content: str = Field(max_length=5000)
    is_pinned: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    author: Optional[User] = Relationship()
    receipts: List["AnnouncementReadReceipt"] = Relationship(back_populates="announcement")


class AnnouncementReadReceipt(SQLModel, table=True):
    """Confirmation that an employee has read an announcement."""
    __tablename__ = "announcementreadreceipt"
    __table_args__ = (
        UniqueConstraint("announcement_id", "user_id", name="uq_announcement_user_receipt"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="restaurantconfig.id", index=True)
    announcement_id: UUID = Field(foreign_key="announcement.id", index=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    read_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    announcement: Optional[Announcement] = Relationship(back_populates="receipts")
    user: Optional[User] = Relationship()


class WorkerJobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class WorkerJobType(str, Enum):
    SOLVER = "SOLVER"
    PREDICTION = "PREDICTION"
    LABOR_COST_SIMULATION = "LABOR_COST_SIMULATION"


class WorkerJob(SQLModel, table=True):
    __tablename__ = "worker_job"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    job_id: str = Field(index=True, unique=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="restaurantconfig.id", index=True)
    job_type: str = Field(default=WorkerJobType.SOLVER.value, index=True)
    status: str = Field(default=WorkerJobStatus.PENDING.value, index=True)
    payload_json: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    result_summary_json: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    error_message: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    started_at: Optional[datetime] = Field(default=None, index=True)
    finished_at: Optional[datetime] = Field(default=None)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


register_tenant_listener(
    DailyCloseout,
    ChecklistTemplate,
    ChecklistCompletion,
    HaccpDevice,
    HaccpLog,
    Announcement,
    AnnouncementReadReceipt,
)

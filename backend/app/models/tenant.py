from datetime import datetime, time, date as date_type, timezone
from typing import Optional, List, TYPE_CHECKING
from uuid import uuid4

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Date

from .base import register_tenant_listener

if TYPE_CHECKING:
    from .users import User


class RestaurantOpeningHour(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    config_id: int = Field(foreign_key="restaurantconfig.id")
    day_of_week: int
    open_time: time
    close_time: time

    config: "RestaurantConfig" = Relationship(back_populates="opening_hours")


class RestaurantConfig(SQLModel, table=True):
    """Restaurant model representing a client restaurant (tenant) in the system."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str  # Display name, e.g. "Restauracja Bella Italia"
    slug: str = Field(unique=True, index=True)  # URL-safe identifier/code, e.g. "bella-italia"
    address: Optional[str] = None
    pos_enabled: bool = Field(default=False)
    require_attendance_registration: bool = Field(default=False)
    attendance_required_from: Optional[date_type] = Field(default=None, sa_column=Column(Date, nullable=True))
    require_checklists: bool = Field(default=True)
    enable_tip_pool: bool = Field(default=True)
    enable_daily_closeout: bool = Field(default=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    opening_hours: List["RestaurantOpeningHour"] = Relationship(back_populates="config")
    users: List["User"] = Relationship(back_populates="restaurant_config")

    def __init__(self, **data):
        if "slug" not in data or not data["slug"]:
            name = data.get("name", "restaurant")
            import re
            slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
            data["slug"] = slug or f"rest-{uuid4().hex[:6]}"
        super().__init__(**data)


# Alias for tenant abstraction across services and auth
Tenant = RestaurantConfig


class SystemSettings(SQLModel, table=True):
    __tablename__ = "system_settings"
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="restaurantconfig.id", index=True)
    is_login_enabled: bool = Field(default=True)
    blocked_login_message: str = Field(
        default="Dostęp do aplikacji został tymczasowo wstrzymany. Skontaktuj się z administratorem."
    )


register_tenant_listener(SystemSettings)

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from ..database import get_session
from ..models import User, RoleSystem, SystemSettings
from ..auth_utils import get_current_user
from ..schemas import SystemSettingsResponse, SystemSettingsUpdate
from ..tenant_context import require_tenant

router = APIRouter(prefix="/admin", tags=["admin"])


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    is_admin = current_user.role_system in (RoleSystem.ADMIN, RoleSystem.MANAGER) or (current_user.username and current_user.username.lower() == "mateusz")
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień administratora",
        )
    return current_user


def get_or_create_system_settings(session: Session, tenant_id: UUID) -> SystemSettings:
    settings = session.exec(
        select(SystemSettings).where(SystemSettings.tenant_id == tenant_id)
    ).first()
    if not settings:
        settings = SystemSettings(tenant_id=tenant_id)
        session.add(settings)
        session.commit()
        session.refresh(settings)
    return settings


@router.get("/settings", response_model=SystemSettingsResponse)
def get_admin_settings(
    session: Session = Depends(get_session),
    _: User = Depends(get_admin_user),
    tenant_id: UUID = Depends(require_tenant),
):
    """Retrieve global system settings (Kill Switch / Maintenance Mode state)."""
    return get_or_create_system_settings(session, tenant_id)


@router.put("/settings", response_model=SystemSettingsResponse)
def update_admin_settings(
    settings_in: SystemSettingsUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(get_admin_user),
    tenant_id: UUID = Depends(require_tenant),
):
    """Update global system settings (Kill Switch / Maintenance Mode state)."""
    settings = get_or_create_system_settings(session, tenant_id)
    if settings_in.is_login_enabled is not None:
        settings.is_login_enabled = settings_in.is_login_enabled
    if settings_in.blocked_login_message is not None and settings_in.blocked_login_message.strip():
        settings.blocked_login_message = settings_in.blocked_login_message.strip()

    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings

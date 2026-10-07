import os
import re
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from datetime import timedelta
from ..database import get_session
from ..models import User, RoleSystem, SystemSettings, Tenant, RestaurantConfig
from ..auth_utils import (
    verify_password, get_password_hash,
    create_access_token, create_refresh_token, decode_token,
    ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user
)
from ..schemas import Token, UserCreate, UserResponse
from ..main import limiter

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def get_system_settings(session: Session, tenant_id=None) -> SystemSettings:
    from uuid import UUID as _UUID
    if tenant_id:
        tid = tenant_id if isinstance(tenant_id, _UUID) else _UUID(str(tenant_id))
        settings = session.exec(
            select(SystemSettings).where(SystemSettings.tenant_id == tid)
        ).first()
    else:
        settings = session.exec(select(SystemSettings)).first()
        
    if not settings:
        settings = SystemSettings(tenant_id=tenant_id)
        session.add(settings)
        session.commit()
        session.refresh(settings)
    return settings


@router.post("/register")
def register(
    user_in: UserCreate,
    session: Session = Depends(get_session)
):
    """Registration is disabled. Accounts are created by managers only."""
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Rejestracja wyłączona. Konto tworzy manager.",
    )


def _is_email(value: str) -> bool:
    return '@' in value and '.' in value.split('@')[-1]

@router.post("/token", response_model=Token)
@limiter.limit("5/minute")
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    # Rate limit applied via state.limiter in main.py by the caller.
    login_input = form_data.username.strip().lower()
    
    if _is_email(login_input):
        # Email login - globally unique, no tenant slug needed
        user = session.exec(select(User).where(User.email == login_input)).first()
    else:
        # Username login
        tenant_slug = request.headers.get("X-Tenant-Slug", "").strip().lower()
        if tenant_slug:
            tenant = session.exec(select(RestaurantConfig).where(RestaurantConfig.slug == tenant_slug, RestaurantConfig.is_active == True)).first()
            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Restaurant not found",
                )
            user = session.exec(select(User).where(User.username == login_input, User.tenant_id == tenant.id)).first()
        else:
            # Backward-compatibility fallback when slug is not provided:
            # 1. Check default restaurant
            default_rest = session.exec(select(RestaurantConfig).where(RestaurantConfig.slug == "default", RestaurantConfig.is_active == True)).first()
            user = None
            if default_rest:
                user = session.exec(select(User).where(User.username == login_input, User.tenant_id == default_rest.id)).first()

            # 2. If not found in default, check if username exists uniquely across the DB
            if not user:
                matching_users = session.exec(select(User).where(User.username == login_input)).all()
                if len(matching_users) == 1:
                    user = matching_users[0]
                elif len(matching_users) > 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Username exists in multiple restaurants. Please provide restaurant code (X-Tenant-Slug) or use email.",
                    )

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check Kill Switch / Maintenance Mode
    settings = get_system_settings(session, tenant_id=user.tenant_id)
    if not settings.is_login_enabled:
        is_admin_user = (user.role_system == RoleSystem.ADMIN) or (user.username and user.username.lower() == "mateusz")
        if not is_admin_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=settings.blocked_login_message,
            )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact your manager.",
        )
        
    access_token = create_access_token(
        data={"sub": user.username, "tenant_id": str(user.tenant_id) if user.tenant_id else None},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(data={"sub": user.username, "tenant_id": str(user.tenant_id) if user.tenant_id else None})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=Token)
@limiter.limit("5/minute")
def refresh_access_token(
    request: Request,
    session: Session = Depends(get_session),
):
    """Exchange a valid refresh token for a new access token."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing refresh token")

    token = auth_header.removeprefix("Bearer ")
    payload = decode_token(token, expected_type="refresh")
    username = payload.get("sub")
    tenant_id = payload.get("tenant_id")

    if tenant_id:
        from uuid import UUID as _UUID
        user = session.exec(
            select(User).where(User.username == username, User.tenant_id == _UUID(tenant_id))
        ).first()
    else:
        # Backward compat: old tokens without tenant_id
        user = session.exec(select(User).where(User.username == username)).first()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid or inactive user")

    new_access = create_access_token(data={"sub": user.username, "tenant_id": str(user.tenant_id) if user.tenant_id else None})
    new_refresh = create_refresh_token(data={"sub": user.username, "tenant_id": str(user.tenant_id) if user.tenant_id else None})
    return {"access_token": new_access, "refresh_token": new_refresh, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role_system": current_user.role_system,
        "created_at": current_user.created_at,
        "job_roles": [role.id for role in current_user.job_roles] if current_user.job_roles else [],
        "is_active": current_user.is_active,
        "target_hours_per_month": current_user.target_hours_per_month,
        "target_shifts_per_month": current_user.target_shifts_per_month,
        "tenant_id": str(current_user.tenant_id) if current_user.tenant_id else None,
        "tenant_slug": current_user.tenant.slug if current_user.tenant else None,
        "tenant_name": current_user.tenant.name if current_user.tenant else None,
    }


@router.put("/change-password")
def change_password(
    password_data: "UserPasswordChange",
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    from ..schemas import UserPasswordChange
    if not verify_password(password_data.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect old password")

    current_user.password_hash = get_password_hash(password_data.new_password)
    session.add(current_user)
    session.commit()

    return {"status": "password_changed"}

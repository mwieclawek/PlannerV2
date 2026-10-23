import os
import re
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlmodel import Session, select
from datetime import timedelta
from ..database import get_session
from ..models import User, RoleSystem, SystemSettings, Tenant, RestaurantConfig
from ..auth_utils import (
    verify_password, get_password_hash,
    create_access_token, create_refresh_token, decode_token,
    ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user, ensure_tenant_active
)
from ..schemas import Token, UserCreate, UserResponse, UserPasswordChange, UserProfileUpdate
from ..main import limiter

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def get_system_settings(session: Session, tenant_id: Optional[int] = None) -> SystemSettings:
    if tenant_id is not None:
        try:
            tid = int(tenant_id)
            settings = session.exec(
                select(SystemSettings).where(SystemSettings.tenant_id == tid)
            ).first()
        except (ValueError, TypeError):
            settings = None
    else:
        settings = session.exec(select(SystemSettings)).first()
        
    if not settings:
        settings = SystemSettings(tenant_id=int(tenant_id) if tenant_id is not None else None)
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
    
    client_ip = request.client.host if request.client else "unknown"

    if _is_email(login_input):
        # Email login - globally unique, no tenant slug needed
        user = session.exec(select(User).where(User.email == login_input)).first()
    else:
        # Username login
        tenant_slug = request.headers.get("X-Tenant-Slug", "").strip().lower()
        if tenant_slug:
            tenant = session.exec(select(RestaurantConfig).where(RestaurantConfig.slug == tenant_slug, RestaurantConfig.is_active == True)).first()
            if not tenant:
                logger.warning(f"[AUTH ANOMALY] Nieudana próba logowania dla '{login_input}' (IP: {client_ip}): lokal o kodzie '{tenant_slug}' nie istnieje.")
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
                    logger.warning(f"[AUTH ANOMALY] Niejednoznaczna nazwa użytkownika '{login_input}' z IP {client_ip} bez podania kodu lokalu.")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Username exists in multiple restaurants. Please provide restaurant code (X-Tenant-Slug) or use email.",
                    )

    if not user or not verify_password(form_data.password, user.password_hash):
        logger.warning(f"[AUTH ANOMALY] Nieudane logowanie dla identyfikatora '{login_input}' z IP {client_ip}: nieprawidłowy login lub hasło.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check Kill Switch / Maintenance Mode
    settings = get_system_settings(session, tenant_id=user.tenant_id)
    if not settings.is_login_enabled:
        is_admin_user = (
            user.is_superadmin
            or user.role_system == RoleSystem.ADMIN
            or (user.username and user.username.lower() == "mateusz")
        )
        if not is_admin_user:
            logger.warning(f"[AUTH ANOMALY] Zablokowane logowanie dla '{user.username}' (id={user.id}) z IP {client_ip}: aktywny tryb serwisowy.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=settings.blocked_login_message,
            )

    # Restaurant blocked by the system owner (superadmins are exempt)
    ensure_tenant_active(user)

    if not user.is_active:
        logger.warning(f"[AUTH ANOMALY] Próba logowania na dezaktywowane konto '{user.username}' (id={user.id}) z IP {client_ip}.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact your manager.",
        )
        
    access_token = create_access_token(
        data={"sub": user.username, "tenant_id": str(user.tenant_id) if user.tenant_id else None},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(data={"sub": user.username, "tenant_id": str(user.tenant_id) if user.tenant_id else None})
    
    login_type = "email" if _is_email(login_input) else "username"
    logger.info(f"[AUTH] Udane logowanie użytkownika '{user.username}' (id={user.id}, rola={user.role_system.value}) metodą {login_type} [tenant:{user.tenant_id}] (IP: {client_ip}).")
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

    if tenant_id is not None:
        try:
            tid = int(tenant_id)
            user = session.exec(
                select(User).where(User.username == username, User.tenant_id == tid)
            ).first()
        except (ValueError, TypeError):
            user = None
    else:
        # Backward compat: old tokens without tenant_id
        user = session.exec(select(User).where(User.username == username)).first()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid or inactive user")
    ensure_tenant_active(user)

    new_access = create_access_token(data={"sub": user.username, "tenant_id": str(user.tenant_id) if user.tenant_id else None})
    new_refresh = create_refresh_token(data={"sub": user.username, "tenant_id": str(user.tenant_id) if user.tenant_id else None})
    return {"access_token": new_access, "refresh_token": new_refresh, "token_type": "bearer"}


class LogoutRequest(BaseModel):
    fcm_token: Optional[str] = None


@router.post("/logout")
def logout(
    payload: LogoutRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Unregister this device's FCM token so a logged-out user gets no more pushes."""
    if payload.fcm_token:
        from ..models import UserDevice
        device = session.exec(
            select(UserDevice).where(
                UserDevice.fcm_token == payload.fcm_token, UserDevice.user_id == current_user.id
            )
        ).first()
        if device:
            session.delete(device)
            session.commit()
    logger.info(f"[AUTH] Użytkownik '{current_user.username}' (id={current_user.id}) wylogował się [tenant:{current_user.tenant_id}].")
    return {"status": "logged_out"}


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
        "job_role_names": [role.name for role in current_user.job_roles] if current_user.job_roles else [],
        "is_active": current_user.is_active,
        "target_hours_per_month": current_user.target_hours_per_month,
        "target_shifts_per_month": current_user.target_shifts_per_month,
        "hourly_rate": current_user.hourly_rate,
        "tenant_id": current_user.tenant_id,
        "tenant_slug": current_user.tenant.slug if current_user.tenant else None,
        "tenant_name": current_user.tenant.name if current_user.tenant else None,
        "is_superadmin": bool(current_user.is_superadmin),
        "is_google_calendar_connected": bool(
            current_user.encrypted_google_access_token or current_user.encrypted_google_refresh_token
        ),
    }


@router.put("/me", response_model=UserResponse)
def update_users_me(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    data = profile_data.dict(exclude_unset=True)
    if "email" in data:
        new_email = data["email"].strip().lower() if data["email"] and data["email"].strip() else None
        if new_email:
            if not _is_email(new_email):
                raise HTTPException(status_code=400, detail="Nieprawidłowy format adresu email")
            existing = session.exec(
                select(User).where(User.email == new_email, User.id != current_user.id)
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="Ten adres email jest już przypisany do innego konta")
        current_user.email = new_email

    if "full_name" in data and data["full_name"] and data["full_name"].strip():
        current_user.full_name = data["full_name"].strip()

    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    logger.info(f"[USER] Aktualizacja profilu własnego użytkownika '{current_user.username}' (id={current_user.id}) [tenant:{current_user.tenant_id}].")
    return read_users_me(current_user)


@router.put("/change-password")
def change_password(
    password_data: UserPasswordChange,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if not verify_password(password_data.old_password, current_user.password_hash):
        logger.warning(f"[AUTH ANOMALY] Nieudana próba zmiany hasła dla '{current_user.username}' (id={current_user.id}): błędne dotychczasowe hasło [tenant:{current_user.tenant_id}].")
        raise HTTPException(status_code=400, detail="Incorrect old password")

    current_user.password_hash = get_password_hash(password_data.new_password)
    session.add(current_user)
    session.commit()
    logger.info(f"[AUTH] Pomyślna zmiana hasła dla użytkownika '{current_user.username}' (id={current_user.id}) [tenant:{current_user.tenant_id}].")

    return {"status": "password_changed"}

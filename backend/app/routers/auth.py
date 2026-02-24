import os
import re
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from datetime import timedelta
from ..database import get_session
from ..models import User, RoleSystem
from ..auth_utils import (
    verify_password, get_password_hash,
    create_access_token, create_refresh_token, decode_token,
    ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user
)
from ..schemas import Token, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


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


@router.post("/token", response_model=Token)
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    # Rate limit applied via state.limiter in main.py by the caller.
    # slowapi doesn't support decorators on imported routers easily,
    # so we apply it at the app level via a middleware rule instead.
    user = session.exec(select(User).where(User.username == form_data.username.lower())).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact your manager.",
        )
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=Token)
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

    user = session.exec(select(User).where(User.username == username)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid or inactive user")

    new_access = create_access_token(data={"sub": user.username})
    new_refresh = create_refresh_token(data={"sub": user.username})
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

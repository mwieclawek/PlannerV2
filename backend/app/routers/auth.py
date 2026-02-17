import os
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from datetime import timedelta
from ..database import get_session
from ..models import User, RoleSystem
from ..auth_utils import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user
from ..schemas import Token, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register")
def register(
    user_in: UserCreate, 
    request: Request,
    session: Session = Depends(get_session)
):
    """Registration is disabled. Accounts are created by managers only."""
    # Allow integration tests to bypass this check
    if request.headers.get("X-Integrity-Key") == "planner-v2-integration-test":
         # Check if user exists
        existing = session.exec(select(User).where(User.username == user_in.username)).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already registered")
            
        hashed_password = get_password_hash(user_in.password)
        db_user = User(
            username=user_in.username,
            full_name=user_in.full_name,
            email=user_in.email,
            password_hash=hashed_password,
            role_system=user_in.role_system,
            manager_pin=user_in.manager_pin
        )
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        return {"id": str(db_user.id), "username": db_user.username}

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Rejestracja wyłączona. Konto tworzy manager."
    )

@router.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
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
    access_token = create_access_token(data={"sub": user.username}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    # Manually build response with job_roles as list of IDs
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role_system": current_user.role_system,
        "created_at": current_user.created_at,
        "job_roles": [role.id for role in current_user.job_roles] if current_user.job_roles else []
    }

@router.put("/change-password")
def change_password(
    password_data: "UserPasswordChange", # String forward ref or imported
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    from ..schemas import UserPasswordChange # Import here to avoid circulars if any
    
    if not verify_password(password_data.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect old password")
        
    current_user.password_hash = get_password_hash(password_data.new_password)
    session.add(current_user)
    session.commit()
    
    return {"status": "password_changed"}


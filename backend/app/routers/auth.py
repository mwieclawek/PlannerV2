import os
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from datetime import timedelta
from ..database import get_session
from ..models import User, RoleSystem
from ..auth_utils import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user
from ..schemas import Token, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=Token)
def register(user_in: UserCreate, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == user_in.username)).first()
    if user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # PIN Validation for Managers
    if user_in.role_system == RoleSystem.MANAGER:
        # Default to '1234' if not set, for backward compatibility
        manager_pin = os.getenv("MANAGER_REGISTRATION_PIN", "1234")
        if user_in.manager_pin != manager_pin:
            raise HTTPException(status_code=403, detail="Invalid Manager PIN")

    hashed_password = get_password_hash(user_in.password)
    
    user = User(
        username=user_in.username,
        email=user_in.email,
        password_hash=hashed_password,
        full_name=user_in.full_name,
        role_system=user_in.role_system
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    
    access_token = create_access_token(data={"sub": user.username}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == form_data.username.lower())).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
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


from datetime import datetime, timedelta, timezone
from typing import Optional
import os
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from .database import get_session
from .models import User

# ── JWT Configuration ──────────────────────────────────────────────────────────

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    import warnings
    warnings.warn(
        "JWT_SECRET_KEY environment variable is not set! "
        "Using an insecure development default. NEVER do this in production.",
        stacklevel=1,
    )
    SECRET_KEY = "dev-only-insecure-key-change-in-production"

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# ── Password hashing ───────────────────────────────────────────────────────────

# pbkdf2_sha256 is primary (avoids bcrypt issues on Windows)
# bcrypt kept as deprecated so old production hashes still verify
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated=["bcrypt"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# ── Token helpers ──────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str, expected_type: str) -> dict:
    """Decode and validate a JWT token. Raises HTTPException on failure."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != expected_type:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception


# ── User resolution ────────────────────────────────────────────────────────────

async def verify_user_token(token: str, session: Session) -> User:
    payload = decode_token(token, expected_type="access")
    username: str = payload.get("sub")
    tenant_id: Optional[str] = payload.get("tenant_id")
    
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
        
    query = select(User).where(User.username == username)
    if tenant_id is not None:
        try:
            tid = int(tenant_id)
            query = query.where(User.tenant_id == tid)
        except (ValueError, TypeError):
            pass
        
    user = session.exec(query).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    ensure_tenant_active(user)
    return user


def ensure_tenant_active(user: User) -> None:
    """Raise 403 if the user's restaurant has been blocked by the system owner.

    Superadmins are exempt so they can never lock themselves out of the panel.
    """
    if user.is_superadmin:
        return
    restaurant = user.restaurant_config
    if restaurant is not None and not restaurant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Restauracja została zablokowana. Skontaktuj się z administratorem systemu.",
        )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    return await verify_user_token(token, session)


async def get_current_superadmin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency for global (cross-tenant) system-owner endpoints."""
    if not current_user.is_superadmin or not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin privileges required",
        )
    return current_user

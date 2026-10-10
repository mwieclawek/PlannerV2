"""
SysAdmin router - global (cross-tenant) panel for the system owner.

Every endpoint here is protected by `get_current_superadmin`, which requires
`User.is_superadmin == True`. These endpoints intentionally do NOT use
`require_tenant`: they operate across all restaurants.
"""
import logging
import re
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from ..auth_utils import get_current_superadmin, get_password_hash
from ..database import get_session
from ..models import RestaurantConfig, RoleSystem, SystemSettings, User
from ..schemas import (
    SysAdminManagerCreate,
    SysAdminManagerResponse,
    SysAdminRestaurantCreate,
    SysAdminRestaurantResponse,
    SysAdminRestaurantStatusUpdate,
    SysAdminRestaurantUpdate,
    SysAdminUserResponse,
    SysAdminPasswordReset,
)

router = APIRouter(
    prefix="/sysadmin",
    tags=["sysadmin"],
    dependencies=[Depends(get_current_superadmin)],
)
logger = logging.getLogger(__name__)


# ── helpers ────────────────────────────────────────────────────────────────────

def _get_restaurant_or_404(session: Session, restaurant_id: int) -> RestaurantConfig:
    restaurant = session.get(RestaurantConfig, restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")
    return restaurant


def _count_by_tenant(session: Session, *extra_filters) -> Dict[int, int]:
    query = (
        select(User.tenant_id, func.count(User.id))
        .where(User.is_active == True, User.tenant_id.is_not(None), *extra_filters)  # noqa: E712
        .group_by(User.tenant_id)
    )
    return {tenant_id: count for tenant_id, count in session.exec(query).all()}


def _to_response(
    restaurant: RestaurantConfig, user_count: int = 0, manager_count: int = 0
) -> SysAdminRestaurantResponse:
    return SysAdminRestaurantResponse(
        id=restaurant.id,
        name=restaurant.name,
        slug=restaurant.slug,
        is_active=restaurant.is_active,
        created_at=restaurant.created_at,
        user_count=user_count,
        manager_count=manager_count,
    )


def _generate_unique_username(session: Session, tenant_id: int, email: str) -> str:
    """Derive a username from the e-mail local part, unique within the restaurant."""
    base = re.sub(r"[^a-z0-9._-]", "", email.split("@", 1)[0].lower())
    if len(base) < 3:
        base = f"{base}manager"
    candidate, suffix = base, 2
    while session.exec(
        select(User.id).where(User.tenant_id == tenant_id, User.username == candidate)
    ).first():
        candidate = f"{base}{suffix}"
        suffix += 1
    return candidate


# ── endpoints ──────────────────────────────────────────────────────────────────

@router.get("/restaurants", response_model=List[SysAdminRestaurantResponse])
def list_restaurants(session: Session = Depends(get_session)):
    """All restaurants with basic stats (active users / managers)."""
    restaurants = session.exec(select(RestaurantConfig).order_by(RestaurantConfig.id)).all()
    user_counts = _count_by_tenant(session)
    manager_counts = _count_by_tenant(session, User.role_system == RoleSystem.MANAGER)
    return [
        _to_response(r, user_counts.get(r.id, 0), manager_counts.get(r.id, 0))
        for r in restaurants
    ]


@router.post(
    "/restaurants",
    response_model=SysAdminRestaurantResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_restaurant(
    payload: SysAdminRestaurantCreate,
    session: Session = Depends(get_session),
    superadmin: User = Depends(get_current_superadmin),
):
    existing = session.exec(
        select(RestaurantConfig).where(RestaurantConfig.slug == payload.slug)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Restauracja z identyfikatorem '{payload.slug}' już istnieje",
        )

    restaurant = RestaurantConfig(name=payload.name, slug=payload.slug, is_active=True)
    session.add(restaurant)
    session.flush()  # assigns restaurant.id
    # Per-tenant settings row (kill switch etc.) so the tenant starts fully configured
    session.add(SystemSettings(tenant_id=restaurant.id))
    session.commit()
    session.refresh(restaurant)

    logger.info(
        "SYSADMIN %s created restaurant id=%s slug=%s",
        superadmin.email or superadmin.username, restaurant.id, restaurant.slug,
    )
    return _to_response(restaurant)


@router.put("/restaurants/{restaurant_id}/status", response_model=SysAdminRestaurantResponse)
def update_restaurant_status(
    restaurant_id: int,
    payload: SysAdminRestaurantStatusUpdate,
    session: Session = Depends(get_session),
    superadmin: User = Depends(get_current_superadmin),
):
    """Activate / block a restaurant. Blocked restaurants cannot log in (superadmins exempt)."""
    restaurant = _get_restaurant_or_404(session, restaurant_id)
    restaurant.is_active = payload.is_active
    session.add(restaurant)
    session.commit()
    session.refresh(restaurant)

    logger.info(
        "SYSADMIN %s set restaurant id=%s is_active=%s",
        superadmin.email or superadmin.username, restaurant.id, restaurant.is_active,
    )
    user_count = _count_by_tenant(session).get(restaurant.id, 0)
    manager_count = _count_by_tenant(
        session, User.role_system == RoleSystem.MANAGER
    ).get(restaurant.id, 0)
    return _to_response(restaurant, user_count, manager_count)


@router.post(
    "/restaurants/{restaurant_id}/managers",
    response_model=SysAdminManagerResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_restaurant_manager(
    restaurant_id: int,
    payload: SysAdminManagerCreate,
    session: Session = Depends(get_session),
    superadmin: User = Depends(get_current_superadmin),
):
    """
    Create a manager account for the restaurant, or promote an existing one.

    E-mail is the global login identifier, so it must be unique across the system.
    The current data model binds a user to exactly ONE restaurant (User.tenant_id),
    therefore an e-mail already used in a *different* restaurant is rejected (409).
    """
    restaurant = _get_restaurant_or_404(session, restaurant_id)

    existing = session.exec(
        select(User).where(func.lower(User.email) == payload.email)
    ).first()

    if existing:
        if existing.tenant_id != restaurant.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Konto z tym adresem e-mail jest już przypisane do innej restauracji",
            )
        # Same restaurant: promote to manager, keep the user's current password.
        existing.role_system = RoleSystem.MANAGER
        existing.is_active = True
        session.add(existing)
        session.commit()
        session.refresh(existing)
        logger.info(
            "SYSADMIN %s promoted user %s to MANAGER in restaurant id=%s",
            superadmin.email or superadmin.username, existing.id, restaurant.id,
        )
        return SysAdminManagerResponse(
            user_id=existing.id,
            email=existing.email,
            username=existing.username,
            full_name=existing.full_name,
            tenant_id=restaurant.id,
            role_system=existing.role_system,
            created=False,
            message="Istniejące konto zostało awansowane na managera (hasło nie zostało zmienione)",
        )

    user = User(
        tenant_id=restaurant.id,
        username=_generate_unique_username(session, restaurant.id, payload.email),
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        full_name=f"{payload.first_name} {payload.last_name}".strip(),
        role_system=RoleSystem.MANAGER,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    logger.info(
        "SYSADMIN %s created MANAGER %s in restaurant id=%s",
        superadmin.email or superadmin.username, user.id, restaurant.id,
    )
    return SysAdminManagerResponse(
        user_id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        tenant_id=restaurant.id,
        role_system=user.role_system,
        created=True,
        message="Utworzono konto managera",
    )

@router.put("/restaurants/{restaurant_id}", response_model=SysAdminRestaurantResponse)
def update_restaurant(
    restaurant_id: int,
    payload: SysAdminRestaurantUpdate,
    session: Session = Depends(get_session),
    superadmin: User = Depends(get_current_superadmin),
):
    """Update a restaurant (name, slug)."""
    restaurant = _get_restaurant_or_404(session, restaurant_id)
    
    new_slug = payload.slug or payload.login_id
    if new_slug:
        existing = session.exec(
            select(RestaurantConfig).where(RestaurantConfig.slug == new_slug, RestaurantConfig.id != restaurant_id)
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Restauracja z identyfikatorem '{new_slug}' już istnieje",
            )
        restaurant.slug = new_slug
    
    if payload.name:
        restaurant.name = payload.name
        
    session.add(restaurant)
    session.commit()
    session.refresh(restaurant)

    logger.info(
        "SYSADMIN %s updated restaurant id=%s slug=%s",
        superadmin.email or superadmin.username, restaurant.id, restaurant.slug,
    )
    user_count = _count_by_tenant(session).get(restaurant.id, 0)
    manager_count = _count_by_tenant(
        session, User.role_system == RoleSystem.MANAGER
    ).get(restaurant.id, 0)
    return _to_response(restaurant, user_count, manager_count)

@router.get("/restaurants/{restaurant_id}/users", response_model=List[SysAdminUserResponse])
def get_restaurant_users(
    restaurant_id: int,
    session: Session = Depends(get_session),
    superadmin: User = Depends(get_current_superadmin),
):
    """List all users of a restaurant."""
    _get_restaurant_or_404(session, restaurant_id)
    
    users = session.exec(
        select(User)
        .where(User.tenant_id == restaurant_id)
    ).all()
    
    users.sort(key=lambda u: (0 if u.role_system == RoleSystem.MANAGER else 1, 0 if u.is_active else 1, u.username))
    return users

from uuid import UUID

@router.put("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: UUID,
    payload: SysAdminPasswordReset,
    session: Session = Depends(get_session),
    superadmin: User = Depends(get_current_superadmin),
):
    """Reset any user's password."""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    user.password_hash = get_password_hash(payload.new_password)
    session.add(user)
    session.commit()
    
    logger.info(
        "SYSADMIN %s reset password for user %s",
        superadmin.email or superadmin.username, user.id,
    )
    return {"message": "Hasło zostało zmienione"}

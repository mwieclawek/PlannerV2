"""
Tenant Context and Dependency System

This module provides context variables and FastAPI dependencies to manage
multi-tenancy throughout the application. It allows retrieving the current
tenant context safely and provides dependency injection mechanisms to extract
and validate tenant information from authenticated users.
"""

from contextvars import ContextVar
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select

from .auth_utils import get_current_user
from .models import Tenant, User

_current_tenant_id: ContextVar[Optional[UUID]] = ContextVar('current_tenant_id', default=None)

def get_current_tenant_id() -> Optional[UUID]:
    """Get the current tenant ID from request context."""
    return _current_tenant_id.get()

def set_current_tenant_id(tenant_id: UUID) -> None:
    """Set the current tenant ID in request context."""
    _current_tenant_id.set(tenant_id)

from .database import get_session

async def require_tenant(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> UUID:
    """FastAPI dependency that extracts and validates tenant_id from the authenticated user."""
    if not current_user.tenant_id:
        tenant = session.exec(select(Tenant).where(Tenant.is_active == True)).first()
        if not tenant:
            tenant = Tenant(name="Default Restaurant", slug="default")
            session.add(tenant)
            session.commit()
            session.refresh(tenant)
        current_user.tenant_id = tenant.id
        session.add(current_user)
        session.commit()
        session.refresh(current_user)

    set_current_tenant_id(current_user.tenant_id)
    return current_user.tenant_id

def get_tenant_by_slug(slug: str, session: Session) -> Optional[Tenant]:
    """Look up a tenant by its URL-safe slug."""
    return session.exec(select(Tenant).where(Tenant.slug == slug, Tenant.is_active == True)).first()

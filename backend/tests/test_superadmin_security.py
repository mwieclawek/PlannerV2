import pytest
from httpx import AsyncClient
from sqlmodel import Session, select
from app.models import User, RoleSystem
from app.auth_utils import get_password_hash, create_access_token
import uuid

@pytest.fixture
def superadmin(session: Session, test_tenant) -> User:
    user = User(
        tenant_id=test_tenant.id,
        username="owner",
        email="owner@restoplan.pl",
        password_hash=get_password_hash("Secret123"),
        full_name="Owner",
        role_system=RoleSystem.MANAGER,
        is_superadmin=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@pytest.fixture
def superadmin_headers(superadmin) -> dict:
    token = create_access_token(data={"sub": superadmin.username, "tenant_id": str(superadmin.tenant_id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_superadmin_password_reset_enforces_policy(client: AsyncClient, session: Session, superadmin_headers, test_tenant):
    # Tworzymy managera jako ofiarę
    victim = User(
        tenant_id=test_tenant.id,
        username="victim_manager",
        email="victim@restoplan.pl",
        password_hash=get_password_hash("Secret123"),
        full_name="Victim",
        role_system=RoleSystem.MANAGER
    )
    session.add(victim)
    session.commit()
    session.refresh(victim)

    # Próba ustawienia słabego hasła przez superadmina powinna dać 422
    resp = await client.put(
        f"/sysadmin/users/{victim.id}/reset-password",
        json={"new_password": "123"},
        headers=superadmin_headers
    )
    assert resp.status_code == 422
    assert "Password must be at least 8 characters" in resp.text

    # Ustawienie prawidłowego
    resp = await client.put(
        f"/sysadmin/users/{victim.id}/reset-password",
        json={"new_password": "StrongPassword123!"},
        headers=superadmin_headers
    )
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_manager_cannot_reset_password_via_sysadmin(client: AsyncClient, session: Session, auth_headers, test_tenant):
    resp = await client.put(
        f"/sysadmin/users/{uuid.uuid4()}/reset-password",
        json={"new_password": "StrongPassword123!"},
        headers=auth_headers
    )
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_superadmin_cannot_set_invalid_slug_in_update(client: AsyncClient, session: Session, superadmin_headers, test_tenant):
    resp = await client.put(
        f"/sysadmin/restaurants/{test_tenant.id}",
        json={"slug": "invalid slug with spaces"},
        headers=superadmin_headers
    )
    assert resp.status_code == 422
    assert "lowercase letters, digits and hyphens" in resp.text

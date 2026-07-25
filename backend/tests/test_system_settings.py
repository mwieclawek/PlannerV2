import pytest
from httpx import AsyncClient
from sqlmodel import Session
from app.models import User, RoleSystem, SystemSettings
from app.auth_utils import get_password_hash, create_access_token


@pytest.mark.asyncio
async def test_normal_user_blocked_when_login_disabled(client: AsyncClient, session: Session):
    # 1. Setup system settings: login disabled with custom message
    custom_msg = "Przerwa techniczna w systemie. Zapraszamy po 20:00."
    settings = session.get(SystemSettings, 1)
    if not settings:
        settings = SystemSettings(id=1, is_login_enabled=False, blocked_login_message=custom_msg)
    else:
        settings.is_login_enabled = False
        settings.blocked_login_message = custom_msg
    session.add(settings)

    # 2. Setup standard employee user
    user = User(
        username="jan_kowalski",
        password_hash=get_password_hash("Password123!"),
        full_name="Jan Kowalski",
        role_system=RoleSystem.EMPLOYEE,
        is_active=True
    )
    session.add(user)
    session.commit()

    # 3. Attempt login
    response = await client.post(
        "/auth/token",
        data={"username": "jan_kowalski", "password": "Password123!"}
    )
    assert response.status_code == 403
    assert response.json()["detail"] == custom_msg


@pytest.mark.asyncio
async def test_admin_and_mateusz_can_login_when_login_disabled(client: AsyncClient, session: Session):
    # 1. Disable login globally
    settings = session.get(SystemSettings, 1)
    if not settings:
        settings = SystemSettings(id=1, is_login_enabled=False, blocked_login_message="Maintenance")
    else:
        settings.is_login_enabled = False
    session.add(settings)

    # 2. Create user 'mateusz'
    mateusz = User(
        username="mateusz",
        password_hash=get_password_hash("AdminPass123!"),
        full_name="Mateusz Admin",
        role_system=RoleSystem.MANAGER,
        is_active=True
    )
    # 3. Create user with RoleSystem.ADMIN
    admin_role_user = User(
        username="super_admin",
        password_hash=get_password_hash("AdminPass123!"),
        full_name="Super Admin",
        role_system=RoleSystem.ADMIN,
        is_active=True
    )
    session.add_all([mateusz, admin_role_user])
    session.commit()

    # 4. Attempt login for mateusz
    resp_mateusz = await client.post(
        "/auth/token",
        data={"username": "mateusz", "password": "AdminPass123!"}
    )
    assert resp_mateusz.status_code == 200
    assert "access_token" in resp_mateusz.json()

    # 5. Attempt login for admin_role_user
    resp_admin = await client.post(
        "/auth/token",
        data={"username": "super_admin", "password": "AdminPass123!"}
    )
    assert resp_admin.status_code == 200
    assert "access_token" in resp_admin.json()


@pytest.mark.asyncio
async def test_admin_settings_get_and_put(client: AsyncClient, session: Session):
    # 1. Create admin user 'mateusz'
    user = User(
        username="mateusz",
        password_hash=get_password_hash("AdminPass123!"),
        full_name="Mateusz Admin",
        role_system=RoleSystem.MANAGER,
        is_active=True
    )
    session.add(user)
    session.commit()

    token = create_access_token(data={"sub": "mateusz"})
    headers = {"Authorization": f"Bearer {token}"}

    # 2. GET current settings
    get_resp = await client.get("/api/admin/settings", headers=headers)
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert "is_login_enabled" in data
    assert "blocked_login_message" in data

    # 3. PUT new settings
    new_message = "System poddawany pracom konserwacyjnym."
    put_resp = await client.put(
        "/api/admin/settings",
        json={"is_login_enabled": False, "blocked_login_message": new_message},
        headers=headers
    )
    assert put_resp.status_code == 200
    put_data = put_resp.json()
    assert put_data["is_login_enabled"] is False
    assert put_data["blocked_login_message"] == new_message


@pytest.mark.asyncio
async def test_non_admin_cannot_access_admin_settings(client: AsyncClient, session: Session):
    # 1. Create employee user
    user = User(
        username="zwykly_user",
        password_hash=get_password_hash("Password123!"),
        full_name="Zwykły Pracownik",
        role_system=RoleSystem.EMPLOYEE,
        is_active=True
    )
    session.add(user)
    session.commit()

    token = create_access_token(data={"sub": "zwykly_user"})
    headers = {"Authorization": f"Bearer {token}"}

    # 2. GET admin settings should fail with 403
    get_resp = await client.get("/api/admin/settings", headers=headers)
    assert get_resp.status_code == 403

    # 3. PUT admin settings should fail with 403
    put_resp = await client.put(
        "/api/admin/settings",
        json={"is_login_enabled": False},
        headers=headers
    )
    assert put_resp.status_code == 403

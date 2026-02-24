import pytest
from httpx import AsyncClient
from sqlmodel import Session, select
from app.models import User, RoleSystem
from app.auth_utils import get_password_hash

@pytest.mark.asyncio
async def test_create_user_success(client: AsyncClient, manager_token_headers, session: Session):
    response = await client.post(
        "/manager/users",
        headers=manager_token_headers,
        json={
            "username": "newuser",
            "password": "Password123",
            "full_name": "New User",
            "role_system": "EMPLOYEE",
            "email": "newuser@example.com"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newuser"
    assert data["full_name"] == "New User"
    assert "id" in data
    
    # Verify in DB
    user = session.exec(select(User).where(User.username == "newuser")).first()
    assert user is not None
    assert user.email == "newuser@example.com"

@pytest.mark.asyncio
async def test_create_user_not_manager(client: AsyncClient, employee_token_headers):
    response = await client.post(
        "/manager/users",
        headers=employee_token_headers,
        json={
            "username": "hacker",
            "password": "Password123",
            "full_name": "Hacker",
            "role_system": "MANAGER"
        }
    )
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_create_user_duplicate_username(client: AsyncClient, manager_token_headers, session: Session):
    # Create valid user first
    user = User(
        username="existing",
        password_hash=get_password_hash("pass"),
        full_name="Existing",
        role_system=RoleSystem.EMPLOYEE
    )
    session.add(user)
    session.commit()
    
    response = await client.post(
        "/manager/users",
        headers=manager_token_headers,
        json={
            "username": "existing",
            "password": "Password123",
            "full_name": "Duplicate",
            "role_system": "EMPLOYEE"
        }
    )
    assert response.status_code == 400
    assert "Username already exists" in response.json()["detail"]

@pytest.mark.asyncio
async def test_create_user_duplicate_email(client: AsyncClient, manager_token_headers, session: Session):
    # Create valid user first
    user = User(
        username="user1",
        email="email@example.com",
        password_hash=get_password_hash("pass"),
        full_name="User 1",
        role_system=RoleSystem.EMPLOYEE
    )
    session.add(user)
    session.commit()
    
    response = await client.post(
        "/manager/users",
        headers=manager_token_headers,
        json={
            "username": "user2",
            "email": "email@example.com",
            "password": "Password123",
            "full_name": "User 2",
            "role_system": "EMPLOYEE"
        }
    )
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]

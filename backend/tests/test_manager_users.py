import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.models import User, RoleSystem
from app.auth_utils import get_password_hash

def test_create_user_success(client: TestClient, manager_token_headers, session: Session):
    response = client.post(
        "/manager/users",
        headers=manager_token_headers,
        json={
            "username": "newuser",
            "password": "password123",
            "full_name": "New User",
            "role_system": "employee",
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

def test_create_user_not_manager(client: TestClient, employee_token_headers):
    response = client.post(
        "/manager/users",
        headers=employee_token_headers,
        json={
            "username": "hacker",
            "password": "password123",
            "full_name": "Hacker",
            "role_system": "manager"
        }
    )
    assert response.status_code == 403

def test_create_user_duplicate_username(client: TestClient, manager_token_headers, session: Session):
    # Create valid user first
    user = User(
        username="existing",
        password_hash=get_password_hash("pass"),
        full_name="Existing",
        role_system=RoleSystem.EMPLOYEE
    )
    session.add(user)
    session.commit()
    
    response = client.post(
        "/manager/users",
        headers=manager_token_headers,
        json={
            "username": "existing",
            "password": "password123",
            "full_name": "Duplicate",
            "role_system": "employee"
        }
    )
    assert response.status_code == 400
    assert "Username already exists" in response.json()["detail"]

def test_create_user_duplicate_email(client: TestClient, manager_token_headers, session: Session):
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
    
    response = client.post(
        "/manager/users",
        headers=manager_token_headers,
        json={
            "username": "user2",
            "email": "email@example.com",
            "password": "password123",
            "full_name": "User 2",
            "role_system": "employee"
        }
    )
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]

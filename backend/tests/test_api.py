import pytest
from httpx import AsyncClient
from datetime import date

# 1. AUTH TESTS
@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient, session):
    # Register
    response = await client.post("/auth/register", json={
        "email": "new@test.com",
        "password": "pass",
        "full_name": "New User"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    
    # Login
    login_response = await client.post("/auth/token", data={
        "username": "new@test.com",
        "password": "pass"
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    assert token is not None

# 2. MANAGER FLOW
@pytest.mark.asyncio
async def test_create_role(client: AsyncClient, auth_headers):
    response = await client.post("/manager/roles", json={
        "name": "Barista Test",
        "color_hex": "#000000"
    }, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Barista Test"
    
    # Check if list has it
    list_response = await client.get("/manager/roles", headers=auth_headers)
    assert len(list_response.json()) > 0

@pytest.mark.asyncio
async def test_create_shift(client: AsyncClient, auth_headers):
    response = await client.post("/manager/shifts", json={
        "name": "Morning",
        "start_time": "08:00",
        "end_time": "16:00"
    }, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Morning"

# 3. EMPLOYEE FLOW
@pytest.mark.asyncio
async def test_set_availability(client: AsyncClient, employee_headers, auth_headers):
    # First, manager creates shift
    shift_res = await client.post("/manager/shifts", json={
        "name": "Shift1", "start_time": "08:00", "end_time": "16:00"
    }, headers=auth_headers)
    shift_id = shift_res.json()["id"]
    
    # Employee sets availability
    today = date.today().isoformat()
    response = await client.post("/employee/availability", json=[{
        "date": today,
        "shift_def_id": shift_id,
        "status": "PREFERRED"
    }], headers=employee_headers)
    
    assert response.status_code == 200
    
    # Verify get
    get_res = await client.get(f"/employee/availability?start_date={today}&end_date={today}", headers=employee_headers)
    assert get_res.status_code == 200
    assert len(get_res.json()) == 1
    assert get_res.json()[0]["status"] == "PREFERRED"

# 4. SCHEDULER TEST
@pytest.mark.asyncio
async def test_generate_schedule(client: AsyncClient, auth_headers):
    # Just check if it runs without crashing, output depends on constraints
    today = date.today().isoformat()
    response = await client.post("/scheduler/generate", json={
        "start_date": today,
        "end_date": today
    }, headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "count" in data

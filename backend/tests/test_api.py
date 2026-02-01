"""
Backend API Tests for PlannerV2
Run with: pytest backend/tests/test_api.py -v
For Jenkins: pytest backend/tests/test_api.py --junitxml=test-results/backend.xml
"""
import pytest
import httpx
from datetime import date, timedelta
import uuid

BASE_URL = "http://127.0.0.1:8000"

def get_unique_email(prefix="user"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}@test.com"

# --- Test Data Helpers ---
def get_employee_data():
    return {
        "email": get_unique_email("employee"),
        "password": "testpass123",
        "full_name": "Test Employee",
        "role_system": "EMPLOYEE"
    }

MANAGER_EMAIL = get_unique_email("manager")
TEST_MANAGER = {
    "email": MANAGER_EMAIL,
    "password": "testpass123",
    "full_name": "Test Manager",
    "role_system": "MANAGER",
    "manager_pin": "1234"
}

@pytest.fixture(scope="module")
def client():
    return httpx.Client(base_url=BASE_URL, timeout=30.0)

@pytest.fixture(scope="module")
def manager_token(client):
    """Create manager account and return token"""
    # Try register first
    response = client.post("/auth/register", json=TEST_MANAGER)
    # Ignore error if exists (unlikely with unique email but safe)
    
    response = client.post("/auth/token", data={
        "username": TEST_MANAGER["email"],
        "password": TEST_MANAGER["password"]
    })
    
    if response.status_code == 200:
        return response.json()["access_token"]
    
    pytest.fail(f"Could not get manager token: {response.text}")

@pytest.fixture(scope="module")
def auth_headers(manager_token):
    return {"Authorization": f"Bearer {manager_token}"}


class TestHealthCheck:
    """Basic connectivity tests"""
    def test_api_reachable(self, client):
        response = client.get("/docs")
        assert response.status_code == 200


class TestAuthentication:
    """Auth endpoint tests"""
    
    def test_register_employee(self, client):
        data = get_employee_data()
        response = client.post("/auth/register", json=data)
        assert response.status_code == 200
        assert "access_token" in response.json()
    
    def test_register_manager_without_pin_fails(self, client):
        data = get_employee_data() # Use fresh email
        data["role_system"] = "MANAGER"
        # No pin provided
        response = client.post("/auth/register", json=data)
        assert response.status_code == 403 or "Invalid" in response.text
    
    def test_register_manager_wrong_pin_fails(self, client):
        data = get_employee_data()
        data["role_system"] = "MANAGER"
        data["manager_pin"] = "0000"
        response = client.post("/auth/register", json=data)
        assert response.status_code == 403
    
    def test_login_success(self, client):
        # Ensure manager exists first
        client.post("/auth/register", json=TEST_MANAGER)
        response = client.post("/auth/token", data={
            "username": TEST_MANAGER["email"],
            "password": TEST_MANAGER["password"]
        })
        assert response.status_code == 200
    
    def test_login_wrong_password(self, client):
        # Ensure manager exists first
        client.post("/auth/register", json=TEST_MANAGER)
        response = client.post("/auth/token", data={
            "username": TEST_MANAGER["email"],
            "password": "wrongpassword"
        })
        assert response.status_code == 401


class TestManagerEndpoints:
    """Manager-only endpoint tests"""
    
    def test_create_role(self, client, auth_headers):
        response = client.post("/manager/roles", headers=auth_headers, json={
            "name": f"Role {uuid.uuid4().hex[:4]}",
            "color_hex": "#FF0000"
        })
        assert response.status_code == 200
        assert "id" in response.json()
        return response.json() # Return for use
    
    def test_create_shift(self, client, auth_headers):
        # Use random hours AND minutes to avoid conflict
        import random
        start_h = random.randint(0, 10)
        start_m = random.randint(0, 59)
        response = client.post("/manager/shifts", headers=auth_headers, json={
            "name": f"Shift {uuid.uuid4().hex[:4]}",
            "start_time": f"{start_h:02d}:{start_m:02d}",
            "end_time": f"{start_h+8:02d}:{start_m:02d}"
        })
        assert response.status_code == 200
        return response.json()

    def test_create_duplicate_shift_fails(self, client, auth_headers):
        # Create one unique shift
        s_h = 13
        name = f"Unique {uuid.uuid4().hex[:4]}"
        
        # Ensure we don't conflict with existing
        client.post("/manager/shifts", headers=auth_headers, json={
            "name": name,
            "start_time": f"{s_h}:00",
            "end_time": f"{s_h+1}:00"
        })
        
        # Now try creating SAME time (different name)
        res_dup = client.post("/manager/shifts", headers=auth_headers, json={
            "name": name + " Dup",
            "start_time": f"{s_h}:00",
            "end_time": f"{s_h+1}:00"
        })
        assert res_dup.status_code == 400
        assert "already exists" in res_dup.json()["detail"]


class TestSolverLogic:
    """Complex scenario: Setup data and verify solver generation"""
    
    @pytest.fixture(scope="class")
    def setup_data(self, client, auth_headers):
        # 1. Create Role
        role = client.post("/manager/roles", headers=auth_headers, json={
            "name": f"SolverRole_{uuid.uuid4().hex[:4]}",
            "color_hex": "#00FF00"
        }).json()
        
        # 2. Create Shift
        # Use weird hour to ensure uniqueness for test stability
        shift = client.post("/manager/shifts", headers=auth_headers, json={
            "name": "SolverShift",
            "start_time": "04:30",
            "end_time": "12:30"
        })
        if shift.status_code == 400: # Exists
            all_shifts = client.get("/manager/shifts", headers=auth_headers).json()
            shift = next(s for s in all_shifts if s["start_time"] == "04:30:00" and s["end_time"] == "12:30:00")
        else:
            shift = shift.json()
            
        # 3. Create Employee
        emp_data = get_employee_data()
        emp_reg = client.post("/auth/register", json=emp_data)
        emp_token = emp_reg.json()["access_token"]
        
        # Get emp ID
        emp_me = client.get("/auth/me", headers={"Authorization": f"Bearer {emp_token}"}).json()
        emp_id = emp_me["id"]
        
        # 4. Assign Role to Employee using PUT endpoint
        client.put(f"/manager/users/{emp_id}/roles", headers=auth_headers, json={
            "role_ids": [role["id"]]
        })
        
        return {
            "role": role,
            "shift": shift,
            "emp_id": emp_id,
            "emp_token": emp_token
        }

    def test_full_generation_flow(self, client, auth_headers, setup_data):
        role_id = setup_data["role"]["id"]
        shift_id = setup_data["shift"]["id"]
        
        # 1. Set Requirement (Need 1 person tomorrow)
        tomorrow = date.today() + timedelta(days=1)
        client.post("/manager/requirements", headers=auth_headers, json=[{
            "date": str(tomorrow),
            "shift_def_id": shift_id,
            "role_id": role_id,
            "min_count": 1
        }])
        
        # 2. Generate
        res = client.post("/scheduler/generate", headers=auth_headers, json={
            "start_date": str(tomorrow),
            "end_date": str(tomorrow)
        })
        
        assert res.status_code == 200
        data = res.json()
        
        # Should be feasible
        assert data["status"] == "success"
        # Should have found 1 assignment (since we have 1 employee with role)
        # Verify result contains the correct assignment
        assert data["count"] >= 1
        
        assignments = data["schedules"]
        emp_id_str = str(setup_data["emp_id"])
        my_assignment = next((a for a in assignments if str(a["user_id"]) == emp_id_str), None)
        # Note: API might return UUID as string or as object, ensure check handles both
            
        assert my_assignment is not None, f"No assignment found for emp_id={emp_id_str}. Assignments: {assignments}"
        assert my_assignment["shift_def_id"] == shift_id
        assert my_assignment["role_id"] == role_id

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

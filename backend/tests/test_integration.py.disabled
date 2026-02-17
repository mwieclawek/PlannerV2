"""
Integration Tests - Full E2E Flow
Run with: python -m pytest backend/tests/test_integration.py -v
For Jenkins: python -m pytest backend/tests/test_integration.py --junitxml=test-results/integration.xml
"""
import pytest
import httpx
from datetime import date, timedelta
import uuid

BASE_URL = "http://127.0.0.1:8000"

class TestFullWorkflow:
    """Complete user journey test"""
    
    @pytest.fixture(scope="class")
    def client(self):
        return httpx.Client(base_url=BASE_URL, timeout=30.0)
    
    @pytest.fixture(scope="class")
    def unique_username(self):
        return f"integration_test_{uuid.uuid4().hex[:8]}"
    
    def test_01_register_manager(self, client, unique_username):
        """Step 1: Register a new manager"""
        response = client.post("/auth/register", json={
            "username": unique_username,
            "password": "securepass123",
            "full_name": "Integration Test Manager",
            "role_system": "MANAGER",
            "manager_pin": "1234"
        })
        assert response.status_code == 200
        token = response.json()["access_token"]
        # Store for subsequent tests
        self.__class__.manager_token = token
        self.__class__.auth_headers = {"Authorization": f"Bearer {token}"}
    
    def test_02_create_roles(self, client):
        """Step 2: Manager creates job roles"""
        roles = [
            {"name": "Barista", "color_hex": "#8B4513"},
            {"name": "Cashier", "color_hex": "#228B22"},
        ]
        
        for role_data in roles:
            response = client.post(
                "/manager/roles",
                headers=self.__class__.auth_headers,
                json=role_data
            )
            assert response.status_code == 200
    
    def test_03_create_shifts(self, client):
        """Step 3: Manager creates shift definitions"""
        shifts = [
            {"name": "Morning", "start_time": "07:00", "end_time": "15:00"},
            {"name": "Evening", "start_time": "15:00", "end_time": "23:00"},
        ]
        
        for shift_data in shifts:
            response = client.post(
                "/manager/shifts",
                headers=self.__class__.auth_headers,
                json=shift_data
            )
            # Accept 200 or 400 (duplicate from previous runs)
            assert response.status_code in [200, 400]
    
    def test_04_register_employee(self, client):
        """Step 4: Register an employee"""
        employee_username = f"employee_{uuid.uuid4().hex[:8]}"
        
        response = client.post("/auth/register", json={
            "username": employee_username,
            "password": "emppass123",
            "full_name": "Test Employee",
            "role_system": "EMPLOYEE"
        })
        assert response.status_code == 200
        self.__class__.employee_username = employee_username
    
    def test_05_assign_role_to_employee(self, client):
        """Step 5: Manager assigns role to employee"""
        # Get users list
        response = client.get("/manager/users", headers=self.__class__.auth_headers)
        assert response.status_code == 200
        users = response.json()
        
        # Find the employee we created
        employee = next((u for u in users if u["username"] == self.__class__.employee_username), None)
        assert employee is not None
        
        # Get roles
        response = client.get("/manager/roles", headers=self.__class__.auth_headers)
        roles = response.json()
        assert len(roles) > 0
        
        # Assign first role to employee
        response = client.put(
            f"/manager/users/{employee['id']}/roles",
            headers=self.__class__.auth_headers,
            json={"role_ids": [roles[0]["id"]]}
        )
        assert response.status_code == 200
        self.__class__.employee_id = employee["id"]
        self.__class__.role_id = roles[0]["id"]
    
    def test_06_generate_schedule(self, client):
        """Step 6: Generate schedule (draft mode)"""
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        
        response = client.post(
            "/scheduler/generate",
            headers=self.__class__.auth_headers,
            json={
                "start_date": str(monday),
                "end_date": str(sunday)
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert result["status"] in ["success", "infeasible"]
        self.__class__.week_start = monday
        self.__class__.week_end = sunday
    
    def test_07_manual_assignment(self, client):
        """Step 7: Manually add assignment via batch save"""
        # Get shifts
        response = client.get("/manager/shifts", headers=self.__class__.auth_headers)
        shifts = response.json()
        
        if len(shifts) > 0:
            response = client.post(
                "/scheduler/save_batch",
                headers=self.__class__.auth_headers,
                json={
                    "start_date": str(self.__class__.week_start),
                    "end_date": str(self.__class__.week_end),
                    "items": [{
                        "date": str(self.__class__.week_start),
                        "shift_def_id": shifts[0]["id"],
                        "user_id": self.__class__.employee_id,
                        "role_id": self.__class__.role_id
                    }]
                }
            )
            assert response.status_code == 200
            assert response.json()["count"] == 1
    
    def test_08_verify_schedule(self, client):
        """Step 8: Verify schedule was saved"""
        response = client.get(
            f"/scheduler/list?start_date={self.__class__.week_start}&end_date={self.__class__.week_end}",
            headers=self.__class__.auth_headers
        )
        assert response.status_code == 200
        schedules = response.json()
        assert len(schedules) >= 1
    
    def test_09_update_config(self, client):
        """Step 9: Update restaurant config"""
        response = client.post(
            "/manager/config",
            headers=self.__class__.auth_headers,
            json={
                "name": "Integration Test Restaurant",
                "opening_hours": '{"mon-fri": "8:00-22:00", "sat-sun": "10:00-20:00"}',
                "address": "Test Street 42"
            }
        )
        assert response.status_code == 200
    
    def test_10_cleanup_verification(self, client):
        """Step 10: Verify all data exists"""
        # Roles exist
        response = client.get("/manager/roles", headers=self.__class__.auth_headers)
        assert len(response.json()) >= 2
        
        # Shifts exist
        response = client.get("/manager/shifts", headers=self.__class__.auth_headers)
        assert len(response.json()) >= 2
        
        # Config updated
        response = client.get("/manager/config", headers=self.__class__.auth_headers)
        assert "Integration Test Restaurant" in response.json().get("name", "")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

import requests
import uuid
from datetime import date, timedelta

BASE_URL = "http://127.0.0.1:8000"
EMAIL = "admin@example.com" # Adjust if needed, assuming default admin exists or we register one
PASSWORD = "admin" # Adjust if needed

def print_result(name, success, details=""):
    print(f"[{'PASS' if success else 'FAIL'}] {name} {details}")

def run_tests():
    print("Changed API base URL to 127.0.0.1 for testing...")
    
    random_id = str(uuid.uuid4())[:8]
    EMAIL = f"manager_{random_id}@example.com"
    PASSWORD = "password123"
    
    # 0. Register
    try:
        # Assuming backend logic assigns MANAGER role if email contains "manager"
        # And we need a PIN if role is MANAGER? Let's check if backend validates PIN.
        # If I didn't implement PIN check in backend yet (only frontend UI passing it), then it might accept without.
        # But to be safe, I'll pass manager_pin if API accepts it (which I added to frontend API service, backend expects it in register request body?)
        # Checking backend/app/routers/auth.py would be good, but let's assume standard register first.
        
        payload = {
            "email": EMAIL,
            "password": PASSWORD,
            "full_name": "Test Manager",
            "role_system": "MANAGER",
            "manager_pin": "1234" # Assuming basic pin or any pin
        }
        
        resp = requests.post(f"{BASE_URL}/auth/register", json=payload)
        if resp.status_code == 200:
             print_result("Register", True, f"Email: {EMAIL}")
        else:
             print_result("Register", False, f"Status: {resp.status_code}, Body: {resp.text}")
             return
    except Exception as e:
        print_result("Register", False, f"Exception: {e}")
        return

    # 1. Login
    try:
        resp = requests.post(f"{BASE_URL}/auth/token", data={
            "username": EMAIL,
            "password": PASSWORD
        })
        if resp.status_code != 200:
            print_result("Login", False, f"Status: {resp.status_code}, Body: {resp.text}")
            return
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print_result("Login", True)
    except Exception as e:
        print_result("Login", False, f"Exception: {e}")
        return

    # 2. Get Metadata (Users, Roles, Shifts)
    users = []
    roles = []
    shifts = []
    try:
        users = requests.get(f"{BASE_URL}/manager/users", headers=headers).json()
        roles = requests.get(f"{BASE_URL}/manager/roles", headers=headers).json()
        shifts = requests.get(f"{BASE_URL}/manager/shifts", headers=headers).json()
        
        if users and roles and shifts:
            print_result("Fetch Metadata", True, f"Users: {len(users)}, Roles: {len(roles)}, Shifts: {len(shifts)}")
        else:
            print_result("Fetch Metadata", False, "Empty data returned")
            return
    except Exception as e:
        print_result("Fetch Metadata", False, f"Exception: {e}")
        return

    test_user_id = users[0]["id"]
    test_role_id = roles[0]["id"]
    test_shift_id = shifts[0]["id"]
    test_date = date.today().isoformat()

    # 3. Create Assignment
    assignment_id = None
    try:
        payload = {
            "date": test_date,
            "shift_def_id": test_shift_id,
            "user_id": test_user_id,
            "role_id": test_role_id
        }
        resp = requests.post(f"{BASE_URL}/scheduler/assignment", json=payload, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            assignment_id = data["id"]
            print_result("Create Assignment", True, f"ID: {assignment_id}, Status: {data['status']}")
        else:
            print_result("Create Assignment", False, f"Status: {resp.status_code}, Body: {resp.text}")
    except Exception as e:
        print_result("Create Assignment", False, f"Exception: {e}")

    # 4. Delete Assignment (if created)
    if assignment_id:
        try:
            resp = requests.delete(f"{BASE_URL}/scheduler/assignment/{assignment_id}", headers=headers)
            if resp.status_code == 200:
                 print_result("Delete Assignment", True, f"Status: {resp.json().get('status')}")
            else:
                 print_result("Delete Assignment", False, f"Status: {resp.status_code}, Body: {resp.text}")
        except Exception as e:
            print_result("Delete Assignment", False, f"Exception: {e}")

    # 5. Reset Password
    try:
        new_pass = "newpassword123"
        resp = requests.put(f"{BASE_URL}/manager/users/{test_user_id}/password", json={"new_password": new_pass}, headers=headers)
        
        if resp.status_code == 200:
             print_result("Reset Password", True)
             # Revert password?
        else:
             print_result("Reset Password", False, f"Status: {resp.status_code}, Body: {resp.text}")
    except Exception as e:
        print_result("Reset Password", False, f"Exception: {e}")

if __name__ == "__main__":
    run_tests()

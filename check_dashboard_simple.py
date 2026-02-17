import httpx
import sys

BASE_URL = "http://127.0.0.1:8000"

def check():
    print(f"Checking {BASE_URL}...")
    
    # 1. Login
    try:
        resp = httpx.post(f"{BASE_URL}/auth/token", data={
            "username": "manager", # Default manager
            "password": "managerpassword" # Default password ? Need to check createsuperuser or similar
        })
        if resp.status_code != 200:
            # Try the test manager credentials if default fails
            # Based on previous tests: "TopManager" / "testpass123" maybe?
            # Or "manager_..." / "testpass123"
            # Let's try to register a new manager to be sure
            print("Login failed, trying to register temp manager...")
            import uuid
            u = f"debug_mgr_{uuid.uuid4().hex[:4]}"
            resp = httpx.post(f"{BASE_URL}/auth/register", json={
                "username": u,
                "password": "testpass123",
                "email": f"{u}@test.com",
                "full_name": "Debug Manager",
                "role_system": "MANAGER",
                "manager_pin": "1234"
            })
            if resp.status_code != 200:
                print(f"Register failed: {resp.text}")
                return

            print(f"Registered {u}. Logging in...")
            resp = httpx.post(f"{BASE_URL}/auth/token", data={
                "username": u,
                "password": "testpass123"
            })
            
        token = resp.json()["access_token"]
        print("Got token.")
        
        # 2. Get Dashboard
        headers = {"Authorization": f"Bearer {token}"}
        resp = httpx.get(f"{BASE_URL}/manager/dashboard/home", headers=headers)
        
        if resp.status_code == 200:
            data = resp.json()
            print("Dashboard Data:")
            working = data.get("working_today", [])
            print(f"Working Today Count: {len(working)}")
            for w in working:
                print(f" - {w['user_name']} ({w['role_name']}): {w.get('start_time')} -> {w.get('end_time')}")
        else:
            print(f"Failed to get dashboard: {resp.status_code} {resp.text}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check()

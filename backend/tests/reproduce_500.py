import httpx
import uuid

BASE_URL = "http://127.0.0.1:8000"

def reproduce_500():
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)
    unique_email = f"test_{uuid.uuid4().hex[:8]}@test.com"
    
    print(f"Testing registration with email: {unique_email}")
    
    # Try sending with username and X-Integrity-Key header
    try:
        response = client.post("/auth/register", 
            headers={"X-Integrity-Key": "planner-v2-integration-test"},
            json={
                "username": f"user_{uuid.uuid4().hex[:8]}",
                "email": unique_email,
                "password": "securepass123",
                "full_name": "Integration Test Manager",
                "role_system": "MANAGER",
                "manager_pin": "1234"
            }
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    reproduce_500()

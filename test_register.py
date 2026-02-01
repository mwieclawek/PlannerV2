import requests

url = "http://localhost:8000/auth/register"
data = {
    "email": "test_new_user@example.com",
    "password": "password123",
    "full_name": "Test User",
    "role_system": "EMPLOYEE"
}

try:
    response = requests.post(url, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

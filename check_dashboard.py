
import requests
import sys

# Login to get token
try:
    auth_response = requests.post("http://localhost:8000/auth/token", data={"username": "admin", "password": "password"})
    if auth_response.status_code != 200:
        print(f"Login failed: {auth_response.status_code} {auth_response.text}")
        sys.exit(1)
    
    token = auth_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get dashboard home
    response = requests.get("http://localhost:8000/api/manager/dashboard/home", headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f"Working Today Count: {len(data.get('working_today', []))}")
        print("Working Today Items:")
        for item in data.get('working_today', []):
            print(item)
    else:
        print(f"Error: {response.status_code} {response.text}")

except Exception as e:
    print(f"Exception: {e}")

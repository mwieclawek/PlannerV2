import requests
import sys

BASE_URL = "http://localhost:8000"

def verify():
    # 1. Login
    print("Logging in...")
    try:
        resp = requests.post(f"{BASE_URL}/auth/token", data={
            "username": "debug_mgr_05ff",
            "password": "password"
        })
        if resp.status_code != 200:
            print(f"Login failed: {resp.status_code} {resp.text}")
            return
        
        token = resp.json()["access_token"]
        print("Login successful.")
        
        # 2. Get Dashboard Home for specific date
        target_date = "2026-02-16"
        print(f"Fetching dashboard for {target_date}...")
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{BASE_URL}/manager/dashboard/home", params={"date": target_date}, headers=headers)
        
        if resp.status_code != 200:
            print(f"Dashboard fetch failed: {resp.status_code} {resp.text}")
            return
            
        data = resp.json()
        working_today = data.get("working_today", [])
        print(f"Found {len(working_today)} entries for {target_date}:")
        for entry in working_today:
            print(f" - {entry['user_name']}: {entry['shift_name']} ({entry['start_time']} - {entry['end_time']})")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify()

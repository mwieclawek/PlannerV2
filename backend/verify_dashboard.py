import json
import requests
import sys

def test_dashboard():
    try:
        with open('token.json', 'r') as f:
            data = json.load(f)
            token = data['access_token']
        
        headers = {'Authorization': f'Bearer {token}'}
        # Test with specific date
        response = requests.get('http://localhost:8000/manager/dashboard/home?date=2026-02-16', headers=headers)
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            working_today = result.get('working_today', [])
            print(f"Working Today Count: {len(working_today)}")
            for w in working_today:
                print(f" - {w['user_name']} ({w['start_time']} - {w['end_time']})")
        else:
            print(f"Error: {response.text}")

    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_dashboard()

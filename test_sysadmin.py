import requests

response = requests.post(
    "http://127.0.0.1:8000/auth/token",
    data={"username": "manager@default.pl", "password": "Manager1"}
)
print("Login:", response.status_code, response.text)
token = response.json()["access_token"]

res = requests.post(
    "http://127.0.0.1:8000/sysadmin/restaurants",
    json={"name": "Test Restaurant", "login_id": "testrest"},
    headers={"Authorization": f"Bearer {token}"}
)
print("Create Restaurant:", res.status_code, res.text)

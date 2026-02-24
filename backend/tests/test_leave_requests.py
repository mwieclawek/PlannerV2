import pytest
from datetime import date, timedelta

def test_employee_create_leave_request(client, test_employee_token):
    headers = {"Authorization": f"Bearer {test_employee_token}"}
    today = date.today()
    payload = {
        "start_date": today.isoformat(),
        "end_date": (today + timedelta(days=2)).isoformat(),
        "reason": "Vacation"
    }
    resp = client.post("/employee/leave-requests", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "PENDING"
    assert data["reason"] == "Vacation"
    
def test_employee_list_leave_requests(client, test_employee_token):
    headers = {"Authorization": f"Bearer {test_employee_token}"}
    resp = client.get("/employee/leave-requests", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

def test_manager_approve_leave_request(client, test_manager_token, test_employee_token):
    emp_headers = {"Authorization": f"Bearer {test_employee_token}"}
    mgr_headers = {"Authorization": f"Bearer {test_manager_token}"}
    
    # clear existing request
    resp = client.get("/employee/leave-requests", headers=emp_headers)
    for req in resp.json():
        if req["status"] == "PENDING":
             client.delete(f"/employee/leave-requests/{req['id']}", headers=emp_headers)

    today = date.today()
    tomorrow = today + timedelta(days=1)
    payload = {
        "start_date": tomorrow.isoformat(),
        "end_date": (tomorrow + timedelta(days=1)).isoformat(),
        "reason": "Family"
    }
    resp = client.post("/employee/leave-requests", json=payload, headers=emp_headers)
    assert resp.status_code == 201
    req_id = resp.json()["id"]
    
    # approve request
    resp = client.post(f"/manager/leave-requests/{req_id}/approve", headers=mgr_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    
    # check status
    resp = client.get("/employee/leave-requests", headers=emp_headers)
    reqs = [r for r in resp.json() if r["id"] == req_id]
    assert reqs[0]["status"] == "APPROVED"

def test_employee_cancel_pending_request(client, test_employee_token):
    headers = {"Authorization": f"Bearer {test_employee_token}"}
    
    today = date.today()
    future = today + timedelta(days=5)
    payload = {
        "start_date": future.isoformat(),
        "end_date": (future + timedelta(days=1)).isoformat(),
        "reason": "To be cancelled"
    }
    resp = client.post("/employee/leave-requests", json=payload, headers=headers)
    assert resp.status_code == 201
    req_id = resp.json()["id"]
    
    resp = client.delete(f"/employee/leave-requests/{req_id}", headers=headers)
    assert resp.status_code == 200
    
    resp = client.get("/employee/leave-requests", headers=headers)
    reqs = [r for r in resp.json() if r["id"] == req_id]
    assert reqs[0]["status"] == "CANCELLED"

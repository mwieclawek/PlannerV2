"""
Seed script to populate the database with initial data.
Run this after starting the database and backend.
"""
import requests
from datetime import time

BASE_URL = "http://localhost:8000"

def create_manager():
    """Create a manager account"""
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "email": "manager@planner.com",
        "password": "manager123",
        "full_name": "Jan Kowalski",
        "role_system": "MANAGER"
    })
    if response.status_code == 200:
        print("✓ Manager account created")
        return response.json()["access_token"]
    else:
        print(f"✗ Failed to create manager: {response.text}")
        return None

def create_employee(email, name):
    """Create an employee account"""
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "email": email,
        "password": "employee123",
        "full_name": name,
        "role_system": "EMPLOYEE"
    })
    if response.status_code == 200:
        print(f"✓ Employee {name} created")
        return response.json()
    else:
        print(f"✗ Failed to create employee {name}: {response.text}")
        return None

def create_roles(token):
    """Create job roles"""
    headers = {"Authorization": f"Bearer {token}"}
    
    roles = [
        {"name": "Barista", "color_hex": "#10B981"},
        {"name": "Kucharz", "color_hex": "#F59E0B"},
        {"name": "Kelner", "color_hex": "#3B82F6"},
        {"name": "Bar-back", "color_hex": "#8B5CF6"},
    ]
    
    created_roles = []
    for role in roles:
        response = requests.post(f"{BASE_URL}/manager/roles", json=role, headers=headers)
        if response.status_code == 200:
            print(f"✓ Role {role['name']} created")
            created_roles.append(response.json())
        else:
            print(f"✗ Failed to create role {role['name']}: {response.text}")
    
    return created_roles

def create_shifts(token):
    """Create shift definitions"""
    headers = {"Authorization": f"Bearer {token}"}
    
    shifts = [
        {"name": "Poranna", "start_time": "06:00", "end_time": "14:00"},
        {"name": "Popołudniowa", "start_time": "14:00", "end_time": "22:00"},
    ]
    
    created_shifts = []
    for shift in shifts:
        response = requests.post(f"{BASE_URL}/manager/shifts", json=shift, headers=headers)
        if response.status_code == 200:
            print(f"✓ Shift {shift['name']} created")
            created_shifts.append(response.json())
        else:
            print(f"✗ Failed to create shift {shift['name']}: {response.text}")
    
    return created_shifts

def main():
    print("🌱 Seeding database...\n")
    
    # Create manager
    manager_token = create_manager()
    if not manager_token:
        print("\n❌ Failed to create manager. Exiting.")
        return
    
    print()
    
    # Create employees
    employees = [
        ("anna@planner.com", "Anna Nowak"),
        ("piotr@planner.com", "Piotr Wiśniewski"),
        ("maria@planner.com", "Maria Kowalczyk"),
    ]
    
    for email, name in employees:
        create_employee(email, name)
    
    print()
    
    # Create roles
    roles = create_roles(manager_token)
    
    print()
    
    # Create shifts
    shifts = create_shifts(manager_token)
    
    print("\n✅ Seeding complete!")
    print("\n📝 Login credentials:")
    print("   Manager: manager@planner.com / manager123")
    print("   Employee: anna@planner.com / employee123")
    print("   Employee: piotr@planner.com / employee123")
    print("   Employee: maria@planner.com / employee123")

if __name__ == "__main__":
    main()

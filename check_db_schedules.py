
from sqlmodel import Session, select, create_engine
from datetime import date
from backend.app.models import Schedule, User, JobRole, ShiftDefinition
# Adjust import path if necessary, or run as module
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Database URL (assuming sqlite)
sqlite_file_name = "planner.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url)

def check_schedules():
    with Session(engine) as session:
        today = date(2026, 2, 15)
        print(f"Checking schedules for: {today}")
        
        statement = select(Schedule).where(Schedule.date == today)
        results = session.exec(statement).all()
        
        print(f"Found {len(results)} schedules.")
        for sch in results:
            user = session.get(User, sch.user_id)
            shift = session.get(ShiftDefinition, sch.shift_def_id)
            role = session.get(JobRole, sch.role_id)
            
            print(f" - ID: {sch.id}")
            print(f"   User: {user.full_name if user else 'MISSING'}")
            print(f"   Shift: {shift.name if shift else 'MISSING'} (ID: {sch.shift_def_id})")
            print(f"   Role: {role.name if role else 'MISSING'} (ID: {sch.role_id})")

if __name__ == "__main__":
    try:
        check_schedules()
    except Exception as e:
        print(f"Error: {e}")

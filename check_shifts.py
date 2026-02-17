
from sqlmodel import Session, select, create_engine
from backend.app.models import ShiftDefinition
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Database URL
sqlite_file_name = "planner.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url)

def check_shifts():
    with Session(engine) as session:
        shifts = session.exec(select(ShiftDefinition)).all()
        print(f"Found {len(shifts)} shifts:")
        for s in shifts:
            print(f" - {s.name}: {s.start_time} - {s.end_time} (ID: {s.id})")

if __name__ == "__main__":
    check_shifts()

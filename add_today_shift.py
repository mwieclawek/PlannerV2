from sqlmodel import Session, select
from backend.app.database import engine
from backend.app.models import Schedule, User, ShiftDefinition, JobRole
from datetime import date
import uuid

def add_shift():
    with Session(engine) as session:
        today = date.today()
        print(f"Adding shift for today: {today}")
        
        # Get first user, shift, role
        user = session.exec(select(User)).first()
        shift = session.exec(select(ShiftDefinition)).first()
        role = session.exec(select(JobRole)).first()
        
        if not user or not shift or not role:
            print("Missing basic data (User/Shift/Role)")
            return

        # Check if already exists
        existing = session.exec(select(Schedule).where(
            Schedule.date == today,
            Schedule.user_id == user.id
        )).first()
        
        if existing:
            print("Schedule already exists for today.")
            return

        new_schedule = Schedule(
            date=today,
            shift_def_id=shift.id,
            user_id=user.id,
            role_id=role.id,
            is_published=True
        )
        session.add(new_schedule)
        session.commit()
        print(f"Added schedule for {user.full_name} on {today}")

if __name__ == "__main__":
    add_shift()

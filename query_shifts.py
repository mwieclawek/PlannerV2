from sqlmodel import Session, select, SQLModel, create_engine
import sys

engine = create_engine("sqlite:///C:/Users/matte/Desktop/PlannerV2/planner.db")
try:
    from backend.app.models import ShiftDefinition, Schedule, User
except ImportError:
    # Need to add to path
    sys.path.append("C:/Users/matte/Desktop/PlannerV2/backend")
    from app.models import ShiftDefinition, Schedule, User

with Session(engine) as session:
    shifts = session.exec(select(ShiftDefinition)).all()
    print("Shifts:")
    for s in shifts:
        print(f"ID: {s.id}, Name: {s.name}, Start: {s.start_time}, End: {s.end_time}")

    users = session.exec(select(User).where(User.full_name == "Mateusz Pracownik")).all()
    if users:
        print(f"\nUser: {users[0].full_name} (ID: {users[0].id})")
        # Find schedules on 2026-03-21
        from datetime import date
        d = date(2026, 3, 21)
        schedules = session.exec(select(Schedule).where(Schedule.date == d, Schedule.user_id == users[0].id)).all()
        for sched in schedules:
            print(f"Sched ID: {sched.id}, Shift ID: {sched.shift_def_id}, Role ID: {sched.role_id}")

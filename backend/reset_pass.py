from sqlmodel import Session, select
from app.models import User
from app.auth_utils import get_password_hash
import sys
import os

# Setup path
sys.path.append(os.getcwd())

from app.database import engine

def reset_password():
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == "debug_mgr_05ff")).first()
        if user:
            print(f"Resetting password for {user.username}")
            user.password_hash = get_password_hash("password")
            session.add(user)
            session.commit()
            print("Password reset successful")
        else:
            print("User not found")

if __name__ == "__main__":
    reset_password()

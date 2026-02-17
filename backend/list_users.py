from sqlmodel import Session, select, create_engine
from app.models import User
import sys
import os

# Setup path to import app modules
sys.path.append(os.getcwd())

from app.database import engine

def list_users():
    with Session(engine) as session:
        users = session.exec(select(User)).all()
        for u in users:
            print(f"User: {u.username}, Role: {u.role_system}, ID: {u.id}")

if __name__ == "__main__":
    list_users()

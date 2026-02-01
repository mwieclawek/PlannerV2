from sqlmodel import SQLModel, create_engine, Session
import os

# Use SQLite for local development seamlessly
DATABASE_URL = "sqlite:///./planner.db"
# If you really want Postgres, uncomment:
# DATABASE_URL = "postgresql://planner_user:planner_password@localhost:5432/planner_db"

engine = create_engine(DATABASE_URL, echo=True, connect_args={"check_same_thread": False})

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

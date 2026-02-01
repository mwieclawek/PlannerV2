from sqlmodel import SQLModel, create_engine, Session
import os

# Use SQLite for local development seamlessly, but allow override from env
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./planner.db")

connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, echo=True, connect_args=connect_args)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

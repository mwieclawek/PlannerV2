from sqlmodel import SQLModel, create_engine, Session
import os

# Use absolute path to ensure consistency regardless of CWD
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "planner.db")
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL or DATABASE_URL in ("sqlite:///./planner.db", "sqlite:///planner.db"):
    DATABASE_URL = f"sqlite:///{DB_PATH}"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
print(f"Using database at: {DATABASE_URL}")

connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args["check_same_thread"] = False

sql_echo = os.getenv("SQL_ECHO", "false").lower() in ("true", "1", "yes")
engine = create_engine(DATABASE_URL, echo=sql_echo, connect_args=connect_args)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

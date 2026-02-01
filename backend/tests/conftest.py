import pytest
from httpx import AsyncClient, ASGITransport
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool
from backend.app.main import app
from backend.app.database import get_session
from typing import AsyncGenerator, Generator
from datetime import timedelta
from backend.app.auth_utils import create_access_token

# Use in-memory SQLite for tests
DATABASE_URL = "sqlite://"

# Create engine
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)

@pytest.fixture(name="session")
def session_fixture() -> Generator[Session, None, None]:
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

@pytest.fixture(name="client")
async def client_fixture(session: Session) -> AsyncGenerator[AsyncClient, None]:
    # Override the dependency
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    
    # Use ASGITransport for testing FastAPI app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()

@pytest.fixture(name="manager_token")
def manager_token_fixture() -> str:
    return ""

@pytest.fixture(name="auth_headers")
def auth_headers_fixture(session: Session) -> dict:
    from backend.app.models import User, RoleSystem
    from backend.app.auth_utils import get_password_hash
    
    # Create user
    user = User(
        email="manager@test.com",
        password_hash=get_password_hash("secret"),
        full_name="Test Manager",
        role_system=RoleSystem.MANAGER
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    
    token = create_access_token(data={"sub": user.email})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(name="employee_headers")
def employee_headers_fixture(session: Session) -> dict:
    from backend.app.models import User, RoleSystem
    from backend.app.auth_utils import get_password_hash
    
    # Create user
    user = User(
        email="employee@test.com",
        password_hash=get_password_hash("secret"),
        full_name="Test Employee",
        role_system=RoleSystem.EMPLOYEE
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    
    token = create_access_token(data={"sub": user.email})
    return {"Authorization": f"Bearer {token}"}

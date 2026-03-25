import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

from app.main import app
from app.models import (
    User, RoleSystem, PosTable, Order, OrderItem, 
    OrderItemKDSStatus, KDSEventLog
)
from app.auth_utils import create_access_token
from app.database import get_session
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import select, Session, SQLModel

client = TestClient(app)

@pytest.fixture
def db_session():
    # True Isolated SQLite in-memory for testing
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        # Override the dependency for the API endpoints
        app.dependency_overrides[get_session] = lambda: session
        yield session
        # Cleanup
        app.dependency_overrides.clear()

@pytest.fixture
def manager_token_headers(db_session: Session):
    # Setup standard manager
    manager = User(
        id=uuid4(),
        username="integration_mgr",
        email="mgr@test.com",
        password_hash="hash",
        full_name="Mgr",
        role_system=RoleSystem.MANAGER,
        manager_pin="1234"
    )
    db_session.add(manager)
    db_session.commit()
    
    token = create_access_token({"sub": manager.username})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def kds_tablet_headers(db_session: Session):
    user = User(
        id=uuid4(),
        username="kds_tablet_api",
        email="kds_api@test.com",
        password_hash="hash",
        full_name="KDS Tablet API",
        role_system=RoleSystem.EMPLOYEE
    )
    db_session.add(user)
    db_session.commit()
    token = create_access_token({"sub": user.username})
    return {"Authorization": f"Bearer {token}"}


def test_kds_sync_endpoint(db_session: Session, kds_tablet_headers):
    # Seed Order Item
    table = PosTable(id=uuid4(), name="T1")
    db_session.add(table)
    
    from datetime import datetime, timezone
    order = Order(id=uuid4(), table_id=table.id, waiter_id=uuid4(), created_at=datetime(2026, 3, 25, tzinfo=timezone.utc))
    db_session.add(order)
    
    item = OrderItem(
        id=uuid4(),
        order_id=order.id,
        menu_item_id=uuid4(),
        course=1,
        item_name_snapshot="API Burger",
        unit_price_snapshot=15.0,
        kds_status=OrderItemKDSStatus.NEW,
        document_version=1
    )
    db_session.add(item)
    db_session.commit()
    
    # 1. Sync payload: NEW -> PREPARING
    payload = {
        "actions": [
            {
                "client_uuid": str(uuid4()),
                "order_item_id": str(item.id),
                "new_status": "PREPARING",
                "client_timestamp": "2026-03-25T01:00:00Z",
                "is_undo": False
            }
        ]
    }
    
    response = client.post("/pos/v2/kds/sync", json=payload, headers=kds_tablet_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["success"] is True
    assert data["results"][0]["applied_status"] == "PREPARING"
    
    # Verify the refreshed_items contains our item
    refreshed = data["refreshed_items"]
    assert any(i["id"] == str(item.id) for i in refreshed)
    
    # Verify Audit Log
    logs = db_session.exec(
        select(KDSEventLog).where(KDSEventLog.order_item_id == item.id)
    ).all()
    
    assert len(logs) == 1
    assert logs[0].new_state == "PREPARING"

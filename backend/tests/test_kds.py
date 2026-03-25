import pytest
from uuid import uuid4
from datetime import datetime, timezone
from sqlmodel import Session, select
from fastapi.testclient import TestClient

from app.models import (
    User, RoleSystem, PosTable, Order, OrderItem, 
    OrderItemKDSStatus, KDSEventLog
)
from app.services.kds_service import KDSService
from app.schemas import KDSSyncBatchPayload, KDSSyncAction

@pytest.fixture
def db_session():
    # True Isolated SQLite in-memory for testing
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool
    from sqlmodel import SQLModel, Session
    
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_calculate_pacing():
    # Setup dummy order items
    anchor_item = OrderItem(
        id=uuid4(),
        order_id=uuid4(),
        menu_item_id=uuid4(),
        course=1,
        prep_time_sec_snapshot=900, # 15 mins (ANCHOR)
        item_name_snapshot="Steak",
        unit_price_snapshot=25.0
    )
    
    fast_item = OrderItem(
        id=uuid4(),
        order_id=uuid4(),
        menu_item_id=uuid4(),
        course=1,
        prep_time_sec_snapshot=300, # 5 mins
        item_name_snapshot="Salad",
        unit_price_snapshot=10.0
    )
    
    # Needs to be passed into calculate_pacing
    items = [anchor_item, fast_item]
    result = KDSService.calculate_pacing(items)
    
    # Assert anchor item pacing logic
    assert result[str(anchor_item.id)]["is_anchor"] is True
    assert result[str(anchor_item.id)]["delay_start_sec"] == 0
    assert result[str(anchor_item.id)]["target_course_prep_time_sec"] == 900
    
    # Assert staggered start item pacing logic
    assert result[str(fast_item.id)]["is_anchor"] is False
    assert result[str(fast_item.id)]["delay_start_sec"] == 600 # 900 - 300 = 600 sec delay


def test_monotonic_sync_batch_validation(db_session: Session):
    # Setup
    user = User(
        id=uuid4(), username="kds_tablet1", email="kds@test.com", password_hash="hash",
        full_name="KDS Tablet 1", role_system=RoleSystem.EMPLOYEE
    )
    db_session.add(user)
    
    table = PosTable(id=uuid4(), name="T1")
    db_session.add(table)
    
    order = Order(id=uuid4(), table_id=table.id, waiter_id=user.id, created_at=datetime.now())
    db_session.add(order)
    
    item = OrderItem(
        id=uuid4(),
        order_id=order.id,
        menu_item_id=uuid4(),
        course=1,
        item_name_snapshot="Burger",
        unit_price_snapshot=15.0,
        kds_status=OrderItemKDSStatus.PREPARING, # Initial state
        document_version=1
    )
    db_session.add(item)
    db_session.commit()
    
    # Process stale update batch (should fail monotonic check)
    action = KDSSyncAction(
        client_uuid=uuid4(),
        order_item_id=item.id,
        new_status=OrderItemKDSStatus.NEW, # Backwards without UNDO flag
        client_timestamp=datetime.now(timezone.utc)
    )
    
    payload = KDSSyncBatchPayload(actions=[action])
    result = KDSService.process_sync_batch(db_session, payload, user)
    
    assert result["results"][0].success is False
    assert result["results"][0].error_code == "STALE_UPDATE_IGNORED"
    
    # Process forward update (PREPARING -> READY)
    action2 = KDSSyncAction(
        client_uuid=uuid4(),
        order_item_id=item.id,
        new_status=OrderItemKDSStatus.READY, 
        client_timestamp=datetime.now(timezone.utc)
    )
    payload2 = KDSSyncBatchPayload(actions=[action2])
    result2 = KDSService.process_sync_batch(db_session, payload2, user)
    
    assert result2["results"][0].success is True
    
    db_session.refresh(item)
    assert item.kds_status == OrderItemKDSStatus.READY
    assert item.ready_at is not None
    assert item.document_version == 2
    
    # Check KDSEventLog audit trail
    logs = db_session.exec(select(KDSEventLog).where(KDSEventLog.order_item_id == item.id)).all()
    assert len(logs) == 1
    assert logs[0].new_state == "READY"

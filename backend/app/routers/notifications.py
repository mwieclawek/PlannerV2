from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from typing import List
from ..database import get_session
from ..models import User, Notification, UserDevice
from .auth import get_current_user
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

@router.get("")
def get_user_notifications(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Fetch recent notifications for the current user."""
    notifications = session.exec(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    ).all()
    
    return [
        {
            "id": str(n.id),
            "title": n.title,
            "body": n.body,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat()
        } for n in notifications
    ]

@router.patch("/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Mark a notification as read."""
    n = session.get(Notification, notification_id)
    if n and n.user_id == current_user.id:
        n.is_read = True
        session.add(n)
        session.commit()
    return {"status": "ok"}

class DeviceToken(BaseModel):
    token: str

@router.post("/devices")
def register_device(
    payload: DeviceToken,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Register an FCM token for the current user."""
    existing = session.exec(select(UserDevice).where(UserDevice.fcm_token == payload.token)).first()
    if existing:
        if existing.user_id != current_user.id:
            existing.user_id = current_user.id
            existing.last_active = datetime.utcnow()
        else:
            existing.last_active = datetime.utcnow()
        session.add(existing)
    else:
        new_device = UserDevice(user_id=current_user.id, fcm_token=payload.token)
        session.add(new_device)
    session.commit()
    return {"status": "ok"}

@router.delete("/devices/{token}")
def unregister_device(
    token: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Remove an FCM token."""
    existing = session.exec(select(UserDevice).where(UserDevice.fcm_token == token)).first()
    if existing and existing.user_id == current_user.id:
        session.delete(existing)
        session.commit()
    return {"status": "ok"}

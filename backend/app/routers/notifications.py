from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from ..database import get_session
from ..models import User, Notification, UserDevice
from .auth import get_current_user
from pydantic import BaseModel, Field
from datetime import datetime, timezone

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
    try:
        nid = UUID(notification_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Notification not found")
    # Scoped to the owner AND the owner's restaurant
    n = session.exec(
        select(Notification)
        .join(User, Notification.user_id == User.id)
        .where(
            Notification.id == nid,
            Notification.user_id == current_user.id,
            User.tenant_id == current_user.tenant_id,
        )
    ).first()
    if n:
        n.is_read = True
        session.add(n)
        session.commit()
    return {"status": "ok"}

class DeviceToken(BaseModel):
    token: str = Field(min_length=1, max_length=4096)

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
            existing.last_active = datetime.now(timezone.utc)
        else:
            existing.last_active = datetime.now(timezone.utc)
        session.add(existing)
    else:
        new_device = UserDevice(user_id=current_user.id, fcm_token=payload.token)
        session.add(new_device)
    session.commit()
    return {"status": "ok"}

@router.post("/devices/unregister")
def unregister_device_post(
    payload: DeviceToken,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Remove an FCM token (body variant - keeps long tokens out of URLs/logs). Call on logout."""
    existing = session.exec(
        select(UserDevice).where(
            UserDevice.fcm_token == payload.token, UserDevice.user_id == current_user.id
        )
    ).first()
    if existing:
        session.delete(existing)
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

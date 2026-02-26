from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from typing import List

from ..database import get_session
from ..models import User, Notification
from .auth import get_current_user

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

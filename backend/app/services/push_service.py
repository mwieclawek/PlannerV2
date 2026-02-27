import os
import logging
from typing import List, Optional
from uuid import UUID
from sqlmodel import Session, select
import firebase_admin
from firebase_admin import credentials, messaging

from ..models import UserDevice

logger = logging.getLogger(__name__)

# Try to initialize Firebase Admin SDK
firebase_initialized = False

try:
    # If GOOGLE_APPLICATION_CREDENTIALS is set and valid, initialization will succeed.
    # Otherwise, it might fail or we might mock it.
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if cred_path and os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        firebase_initialized = True
        logger.info("Firebase Admin SDK initialized successfully.")
    else:
        logger.warning(
            "GOOGLE_APPLICATION_CREDENTIALS not set or file not found. "
            "Push notifications will be mocked."
        )
except Exception as e:
    logger.error(f"Failed to initialize Firebase Admin SDK: {e}. Push notifications will be mocked.")


class PushService:
    def __init__(self, session: Session):
        self.session = session

    def _get_user_tokens(self, user_id: UUID) -> List[str]:
        devices = self.session.exec(
            select(UserDevice).where(UserDevice.user_id == user_id)
        ).all()
        return [d.fcm_token for d in devices]

    def send_push_notification(self, user_id: UUID, title: str, body: str, data: Optional[dict] = None) -> None:
        """
        Sends a push notification to all devices registered for the user.
        If Firebase is not initialized, logs the intention instead.
        """
        tokens = self._get_user_tokens(user_id)
        send_push_to_tokens(tokens, title, body, data)

def send_push_to_tokens(tokens: List[str], title: str, body: str, data: Optional[dict] = None) -> None:
    if not tokens:
        return

    if not firebase_initialized:
        logger.info(f"[MOCK PUSH] Would send to {len(tokens)} devices - Title: '{title}', Body: '{body}'")
        return

    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=data or {},
        tokens=tokens,
    )

    try:
        response = messaging.send_each_for_multicast(message)
        logger.info(f"Push notification sent. {response.success_count} success, {response.failure_count} failures.")
        
        if response.failure_count > 0:
            responses = response.responses
            for idx, resp in enumerate(responses):
                if not resp.success:
                    logger.warning(f"Failed to send to token {tokens[idx]}: {resp.exception}")
                    
    except Exception as e:
        logger.error(f"Error sending push notification via FCM: {e}")

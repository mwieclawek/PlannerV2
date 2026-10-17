import json
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


def _ensure_firebase_initialized() -> bool:
    """
    Initializes Firebase Admin SDK from either:
    1. FIREBASE_CREDENTIALS_JSON (raw JSON string in memory - ideal for Docker-out-of-Docker CI/CD)
    2. GOOGLE_APPLICATION_CREDENTIALS (either a raw JSON string or a path to a JSON file, e.g. copied via docker cp)
    Safe to call multiple times (idempotent).
    """
    global firebase_initialized
    if firebase_initialized:
        return True
    if firebase_admin._apps:
        firebase_initialized = True
        return True

    try:
        cred_json = os.getenv("FIREBASE_CREDENTIALS_JSON", "").strip()
        cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()

        if cred_json.startswith("{"):
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            firebase_initialized = True
            logger.info("Firebase Admin SDK initialized from FIREBASE_CREDENTIALS_JSON in memory.")
            return True

        if cred_path.startswith("{"):
            cred_dict = json.loads(cred_path)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            firebase_initialized = True
            logger.info("Firebase Admin SDK initialized from inline JSON in GOOGLE_APPLICATION_CREDENTIALS.")
            return True

        if cred_path and os.path.isfile(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            firebase_initialized = True
            logger.info(f"Firebase Admin SDK initialized from file: {cred_path}")
            return True

        logger.warning(
            "Firebase credentials (FIREBASE_CREDENTIALS_JSON / GOOGLE_APPLICATION_CREDENTIALS) "
            "not set or file not found. Push notifications will be mocked."
        )
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}. Push notifications will be mocked.")
    return False


# Attempt initialization at import time
_ensure_firebase_initialized()


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
        send_push_to_tokens(tokens, title, body, data, session=self.session)


def _remove_stale_tokens(stale_tokens: List[str], session: Optional[Session] = None) -> None:
    if not stale_tokens:
        return
    try:
        if session is not None:
            devices = session.exec(
                select(UserDevice).where(UserDevice.fcm_token.in_(stale_tokens))
            ).all()
            for dev in devices:
                session.delete(dev)
            session.commit()
            logger.info(f"Removed {len(devices)} unregistered FCM token(s) from database.")
        else:
            from ..database import engine
            with Session(engine) as own_session:
                devices = own_session.exec(
                    select(UserDevice).where(UserDevice.fcm_token.in_(stale_tokens))
                ).all()
                for dev in devices:
                    own_session.delete(dev)
                own_session.commit()
                logger.info(f"Removed {len(devices)} unregistered FCM token(s) from database.")
    except Exception as cleanup_err:
        logger.error(f"Failed to remove stale FCM tokens: {cleanup_err}")


def send_push_to_tokens(
    tokens: List[str],
    title: str,
    body: str,
    data: Optional[dict] = None,
    session: Optional[Session] = None,
) -> None:
    if not tokens:
        return

    # FCM Admin SDK requires all keys and values in the `data` dictionary to be strings
    str_data = {str(k): str(v) for k, v in (data or {}).items() if v is not None}
    str_data.setdefault("title", str(title))
    str_data.setdefault("body", str(body))
    str_data.setdefault("tag", "plannerv2-push")

    if not _ensure_firebase_initialized():
        logger.info(f"[MOCK PUSH] Would send to {len(tokens)} devices - Title: '{title}', Body: '{body}'")
        return

    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=str(title),
            body=str(body),
        ),
        webpush=messaging.WebpushConfig(
            notification=messaging.WebpushNotification(
                title=str(title),
                body=str(body),
                icon="/icons/Icon-192.png",
                badge="/icons/Icon-192.png",
                tag=str_data.get("tag", "plannerv2-push"),
            ),
        ),
        data=str_data,
        tokens=tokens,
    )

    try:
        response = messaging.send_each_for_multicast(message)
        logger.info(f"Push notification sent. {response.success_count} success, {response.failure_count} failures.")

        if response.failure_count > 0:
            stale_tokens: List[str] = []
            responses = response.responses
            for idx, resp in enumerate(responses):
                if not resp.success:
                    exc = resp.exception
                    logger.warning(f"Failed to send to token {tokens[idx]}: {exc}")
                    exc_code = getattr(exc, "code", None)
                    if (
                        isinstance(exc, messaging.UnregisteredError)
                        or exc_code in ("UNREGISTERED", "NOT_FOUND")
                        or "Unregistered" in type(exc).__name__
                    ):
                        stale_tokens.append(tokens[idx])
            if stale_tokens:
                _remove_stale_tokens(stale_tokens, session=session)

    except Exception as e:
        logger.error(f"Error sending push notification via FCM: {e}")

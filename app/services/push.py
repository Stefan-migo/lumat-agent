"""Optional Web Push adapter; absence never blocks panel notifications."""

from pywebpush import WebPushException, webpush

from app.config import get_settings
from app.db import session_scope
from app.models import PushSubscription


class PushUnavailable(RuntimeError):
    """Raised when deployment/browser push support is not configured."""


def send_push(recipient: str, content: str) -> str:
    """Send to one stored subscription; recipient is its database id."""
    settings = get_settings()
    if not all((settings.vapid_public_key, settings.vapid_private_key, settings.vapid_subject)):
        raise PushUnavailable("VAPID credentials are not configured")

    try:
        subscription_id = int(recipient)
    except (TypeError, ValueError):
        raise PushUnavailable("push subscription is unavailable") from None

    with session_scope() as session:
        subscription = session.get(PushSubscription, subscription_id)
        if subscription is None or subscription.active is False:
            raise PushUnavailable("push subscription is unavailable")
        subscription_info = {
            "endpoint": subscription.endpoint,
            "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
        }
        try:
            webpush(
                subscription_info,
                data=content,
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": settings.vapid_subject},
            )
        except WebPushException as exc:
            if exc.response is not None and exc.response.status_code in (404, 410):
                subscription.active = False
                session.commit()
            raise
        return f"push:{subscription.id}"

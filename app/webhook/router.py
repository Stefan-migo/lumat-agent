"""WhatsApp webhook routes (specs WH-1..WH-3; persist stub until T1.1/T2.2).

GET  /webhook/whatsapp — verify handshake: 200 with the raw `hub.challenge`
     value, or 403 when mode/token mismatch (WH-1). Failed attempts are logged
     (audit_log lands in T1.2, SH-5).

POST /webhook/whatsapp — HMAC-SHA256 signature verified against the raw body:
     200 on valid signature, 403 + dropped payload on failure (WH-2).
     The 200 is returned before any processing (WH-3). Persistence of the
     payload is a debug-log stub until the `messages` table lands (T1.1/T2.2),
     per design — no storage is written in Batch 0.
"""

import logging

from fastapi import APIRouter, Request, Response, status

from app.config import get_settings
from app.webhook.verify import verify_handshake, verify_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook/whatsapp", tags=["webhook"])


@router.get("")
def verify_get(request: Request) -> Response:
    """WH-1: Meta subscribe handshake — return hub.challenge or 403."""
    settings = get_settings()
    challenge = verify_handshake(request.query_params, settings.verify_token)
    if challenge is None:
        logger.warning(
            "webhook GET verify rejected: mode=%s token=%s",
            request.query_params.get("hub.mode"),
            "<present>" if request.query_params.get("hub.verify_token") else "<missing>",
        )
        # TODO(T1.2): record failed handshake in audit_log (SH-5) — logged stub.
        return Response(status_code=status.HTTP_403_FORBIDDEN)
    return Response(content=challenge, media_type="text/plain")


@router.post("")
async def verify_post(request: Request) -> Response:
    """WH-2/WH-3: signature check over the raw body, then immediate 200."""
    settings = get_settings()
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_signature(raw_body, signature, settings.app_secret):
        logger.warning("webhook POST rejected: invalid X-Hub-Signature-256")
        # TODO(T1.2): record rejected attempt in audit_log (SH-5) — logged stub.
        return Response(status_code=status.HTTP_403_FORBIDDEN)

    # WH-3: acknowledge before any processing — the 200 never waits on work.
    # WH-4 persist stub (full ingest in T2.2): payload only logged at debug
    # level; nothing is written to storage in Batch 0.
    logger.debug(
        "webhook POST accepted (persist stub): %s",
        raw_body.decode("utf-8", errors="replace"),
    )
    return Response(status_code=status.HTTP_200_OK)

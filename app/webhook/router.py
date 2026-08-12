"""WhatsApp webhook routes (specs WH-1..WH-7).

GET  /webhook/whatsapp — verify handshake: 200 with the raw `hub.challenge`
     value, or 403 when mode/token mismatch (WH-1). Failed attempts are logged
     (audit_log lands in T1.2, SH-5).

POST /webhook/whatsapp — HMAC-SHA256 signature verified against the raw body:
     403 + dropped payload on failure (WH-2). Accepted payloads go through the
     ingest pipeline: filter unsupported events (WH-6) -> normalize -> persist
     as `received` (WH-4, WH-5 dedup by wamid) -> 200 BEFORE any processing
     (WH-3). Processing (media download / conversation graph) runs afterwards
     via FastAPI BackgroundTask, and a startup sweep recovers anything left
     `received` after a crash (design Webhook Pipeline).
"""

import json
import logging

from fastapi import APIRouter, BackgroundTasks, Request, Response, status

from app.config import get_settings
from app.webhook.ingest import ingest_payload, sweep_received
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
async def verify_post(request: Request, background_tasks: BackgroundTasks) -> Response:
    """WH-2..WH-7: signature gate, persist-before-process, 200-first."""
    settings = get_settings()
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_signature(raw_body, signature, settings.app_secret):
        logger.warning("webhook POST rejected: invalid X-Hub-Signature-256")
        # TODO(T1.2): record rejected attempt in audit_log (SH-5) — logged stub.
        return Response(status_code=status.HTTP_403_FORBIDDEN)

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.warning("webhook POST accepted with non-JSON body; acknowledged and dropped")
        return Response(status_code=status.HTTP_200_OK)

    # WH-4: persist accepted messages before anything else runs. Unsupported
    # events (WH-6) and duplicates (WH-5) are filtered inside ingest_payload.
    inserted = ingest_payload(payload)

    # WH-3: acknowledge before processing — the 200 never waits on the graph
    # run / media download. Processing happens after the response.
    background_tasks.add_task(sweep_received)
    logger.debug("webhook POST accepted: inserted=%d", inserted)
    return Response(status_code=status.HTTP_200_OK)

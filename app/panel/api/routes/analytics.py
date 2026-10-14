"""Panel JSON API chatbot analytics (Frente 2, unit 5 — UI).

Admin-only read-only JSON wrappers over `app/services/analytics.py`
(`chatbot_metrics`, `chatbot_conversations`) — thin, no new business logic:

- GET /analytics/chatbot               -> chatbot_metrics(window_days)
- GET /analytics/chatbot/conversations -> chatbot_conversations(window_days, signal, limit)

Role enforcement server-side (PDW-API-4): `require_admin_json` -> operador 403
JSON; unauthenticated 401 {"detail":"unauthorized"} no redirect (D4,
PDW-AUTH-1). Errors are always JSON {"detail": ...} (PDW-API-3).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.models import User
from app.panel.api.deps import require_admin_json
from app.panel.deps import get_db
from app.services import analytics

router = APIRouter(tags=["panel-api-analytics"])


@router.get("/analytics/chatbot")
def chatbot_metrics_route(
    window_days: int = Query(default=7, ge=1, le=90),
    session: Session = Depends(get_db),
    _user: User = Depends(require_admin_json),
) -> dict:
    """Chatbot performance metrics over a bounded UTC window."""
    return analytics.chatbot_metrics(session, window_days)


@router.get("/analytics/chatbot/conversations")
def chatbot_conversations_route(
    signal: str = Query(default="any"),
    window_days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=10, ge=1, le=100),
    session: Session = Depends(get_db),
    _user: User = Depends(require_admin_json),
) -> dict:
    """Conversations that tripped a chatbot failure signal in the window."""
    if signal not in analytics.CHATBOT_SIGNALS:
        raise HTTPException(status_code=422, detail="unknown chatbot signal")
    return analytics.chatbot_conversations(session, window_days, signal, limit)

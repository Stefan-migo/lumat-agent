"""Panel JSON API settings admin (B4/T4.2; PDW-API-2, PDW-API-3, PDW-API-4, D1, D4).

Admin-only JSON wrappers over `app/services/settings.py` + `app/services/costs.py`
(thin, no new business logic; every save flows through `set_setting` which
upserts the KV row AND audits with the acting admin, SH-5):

- GET /settings -> all sections + spend snapshot (design #18):
  {"scope_rules", "keywords", "tone", "messages", "conversation_limit",
  "daily_limit", "meta_cost", "snapshot"}
- POST /settings/{section} -> per-section KV upsert + audit (design #19, #18):
  scope  {"rules": {cat: mode}}           -> scope_rules
  keywords {"keywords": [str]}            -> emergency.keywords
  tone   {"tone": str}                    -> tone.style
  messages {"greeting": str, ...}         -> messages.*
  limits {"conversation_limit": n, "daily_limit": n} (>= 0) -> cost.*
  meta   {"service_message_cost": n}      -> meta_pricing

Section names mirror the Jinja POST routes (/panel/settings/{scope,keywords,
tone,limits,meta}); an unknown section is a 400 (PDW-API-3). Role enforcement
server-side (PDW-API-4): `require_admin_json` -> operador 403; unauthenticated
401 {"detail":"unauthorized"} no redirect (D4, PDW-AUTH-1). No CORS (D1).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models import User
from app.panel.api.deps import require_admin_json
from app.panel.deps import get_db
from app.services import costs, model_secrets, settings as settings_service
from app.services.deepseek_key import (
    InvalidApiKeyError,
    KeyValidationUnavailableError,
    validate_deepseek_key,
)

router = APIRouter(tags=["panel-api-settings"])


def _number(value: float, key: str, *, minimum: float = 0.0) -> float:
    """Reject NaN/Inf/negative limit values loud and clear (SS-3 guard)."""
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise HTTPException(status_code=400, detail=f"{key} must be a number")
    if not parsed.is_finite() or parsed < Decimal(str(minimum)):
        raise HTTPException(status_code=400, detail=f"{key} must be >= {minimum}")
    return float(parsed)


class ScopeBody(BaseModel):
    rules: dict[str, str]


class KeywordsBody(BaseModel):
    keywords: list[str]


class ToneBody(BaseModel):
    tone: str


class MessagesBody(BaseModel):
    greeting: str
    cannot_answer: str
    clarification: str
    farewell: str
    out_of_hours: str


class HoursBody(BaseModel):
    timezone: Any
    schedule: Any


class LimitsBody(BaseModel):
    conversation_limit: float
    daily_limit: float


class MetaBody(BaseModel):
    service_message_cost: float


class ModelApiKeyBody(BaseModel):
    api_key: str


def _save(session: Session, key: str, value, current: User) -> None:
    settings_service.set_setting(
        session,
        key,
        value,
        updated_by=current.id,
        actor=current.username,
    )


def _parse_scope(body: ScopeBody) -> dict[str, str]:
    rules: dict[str, str] = {}
    for category, mode in body.rules.items():
        if mode not in settings_service.SCOPE_MODES:
            raise HTTPException(
                status_code=400,
                detail=f"mode must be one of {settings_service.SCOPE_MODES}",
            )
        rules[category.strip()] = mode.strip()
    return rules


def _parse_tone(body: ToneBody) -> str:
    tone = body.tone.strip()
    if tone not in settings_service.TONE_STYLES:
        raise HTTPException(
            status_code=400,
            detail=f"tone must be one of {settings_service.TONE_STYLES}",
        )
    return tone


def _parse_hours(body: HoursBody) -> tuple[str, list[dict[str, Any]]]:
    if not isinstance(body.timezone, str):
        raise HTTPException(status_code=400, detail="timezone must be a valid IANA timezone")
    try:
        ZoneInfo(body.timezone)
    except (TypeError, ValueError, ZoneInfoNotFoundError):
        raise HTTPException(status_code=400, detail="timezone must be a valid IANA timezone")

    if not isinstance(body.schedule, list):
        raise HTTPException(status_code=400, detail="schedule must be a list of objects")

    seen_days: set[int] = set()
    for entry in body.schedule:
        if not isinstance(entry, dict):
            raise HTTPException(status_code=400, detail="schedule must be a list of objects")
        days = entry.get("days")
        opening = entry.get("open")
        closing = entry.get("close")
        if (
            not isinstance(days, list)
            or not days
            or any(isinstance(day, bool) or not isinstance(day, int) or not 1 <= day <= 7 for day in days)
        ):
            raise HTTPException(status_code=400, detail="schedule days must be weekdays from 1 to 7")
        if len(set(days)) != len(days) or seen_days.intersection(days):
            raise HTTPException(status_code=400, detail="schedule weekdays must not repeat")
        seen_days.update(days)
        if (
            not isinstance(opening, str)
            or not isinstance(closing, str)
            or len(opening) != 5
            or len(closing) != 5
            or opening[2] != ":"
            or closing[2] != ":"
        ):
            raise HTTPException(status_code=400, detail="schedule times must use HH:MM")
        try:
            open_time = datetime.strptime(opening, "%H:%M").time()
            close_time = datetime.strptime(closing, "%H:%M").time()
        except ValueError:
            raise HTTPException(status_code=400, detail="schedule times must use HH:MM")
        if open_time >= close_time:
            raise HTTPException(status_code=400, detail="open must be before close")
    return body.timezone, body.schedule


@router.get("/settings")
def settings_get(
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    """All sections + spend snapshot (design #18; defaults out of the box)."""
    scope_rules = settings_service.get_setting(session, "scope_rules", default={})
    meta = settings_service.get_setting(session, "meta_pricing", default={})
    return {
        "scope_rules": scope_rules,
        "keywords": settings_service.get_emergency_keywords(session),
        "tone": settings_service.get_tone(session),
        "messages": {
            key: settings_service.get_message(session, key)
            for key in settings_service.MESSAGE_DEFAULTS
        },
        "hours": {
            "timezone": settings_service.get_hours_timezone(session),
            "schedule": settings_service.get_hours_schedule(session),
        },
        "conversation_limit": settings_service.get_setting(
            session, "cost.conversation_limit", default=1.50
        ),
        "daily_limit": settings_service.get_setting(
            session, "cost.daily_limit", default=5.00
        ),
        "meta_cost": (meta or {}).get("service_message_cost", 0.01),
        "snapshot": costs.spend_snapshot(session),
        "model_api_key": model_secrets.model_api_key_status(session),
    }


@router.post("/settings/model_api_key")
def settings_model_api_key(
    body: ModelApiKeyBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    key = body.api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="api key must not be empty")
    try:
        validation = validate_deepseek_key(key)
    except InvalidApiKeyError:
        raise HTTPException(status_code=400, detail="invalid api key")
    except KeyValidationUnavailableError:
        raise HTTPException(status_code=502, detail="could not validate the api key")
    model_secrets.set_model_api_key(
        session, key, actor=current.username, updated_by=current.id
    )
    session.commit()
    return {"ok": True, "validation": validation, "model_api_key": model_secrets.model_api_key_status(session)}


@router.delete("/settings/model_api_key")
def settings_model_api_key_clear(
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    model_secrets.clear_model_api_key(session, actor=current.username)
    session.commit()
    return {"ok": True, "model_api_key": model_secrets.model_api_key_status(session)}


@router.post("/settings/scope")
def settings_scope(
    body: ScopeBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    _save(session, "scope_rules", _parse_scope(body), current)
    session.commit()
    return {"ok": True}


@router.post("/settings/keywords")
def settings_keywords(
    body: KeywordsBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    _save(session, "emergency.keywords", [k.strip() for k in body.keywords], current)
    session.commit()
    return {"ok": True}


@router.post("/settings/tone")
def settings_tone(
    body: ToneBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    _save(session, "tone.style", _parse_tone(body), current)
    session.commit()
    return {"ok": True}


@router.post("/settings/messages")
def settings_messages(
    body: MessagesBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    for key, value in body.model_dump().items():
        _save(session, f"messages.{key}", value, current)
    session.commit()
    return {"ok": True}


@router.post("/settings/hours")
def settings_hours(
    body: HoursBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    timezone_name, schedule = _parse_hours(body)
    _save(session, "hours.timezone", timezone_name, current)
    _save(session, "hours.schedule", schedule, current)
    session.commit()
    return {"ok": True}


@router.post("/settings/limits")
def settings_limits(
    body: LimitsBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    _save(
        session,
        "cost.conversation_limit",
        _number(body.conversation_limit, "conversation_limit"),
        current,
    )
    _save(
        session,
        "cost.daily_limit",
        _number(body.daily_limit, "daily_limit"),
        current,
    )
    session.commit()
    return {"ok": True}


@router.post("/settings/meta")
def settings_meta(
    body: MetaBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    _save(
        session,
        "meta_pricing",
        {"service_message_cost": _number(body.service_message_cost, "service_message_cost")},
        current,
    )
    session.commit()
    return {"ok": True}


# Catch-all MUST stay registered AFTER the specific {scope,keywords,tone,limits,
# meta} POST routes above: FastAPI matches routes in registration order, so the
# literal sections win and anything else is an unknown section (PDW-API-3).
_KNOWN_SECTIONS = {"scope", "keywords", "tone", "messages", "hours", "limits", "meta"}


@router.post("/settings/{section}")
def settings_section_unknown(
    section: str,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    raise HTTPException(status_code=400, detail=f"unknown section {section!r} ({', '.join(sorted(_KNOWN_SECTIONS))})")

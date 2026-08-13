"""Settings panel views (T5.4; SS-1..5, SH-5).

Admin-only (require_admin — AP-2 server-side gate). Every save goes through
`settings.set_setting`, which upserts the KV row AND writes one audit entry
with the acting admin (SH-5 "settings change audited").

GET  /panel/settings              -> all sections + spend snapshot (SS-4)
POST /panel/settings/scope        -> scope_rules dict (SS-1)
POST /panel/settings/keywords     -> emergency keyword list (SS-2)
POST /panel/settings/tone         -> tone.style (SS-5)
POST /panel/settings/limits       -> cost.{conversation,daily}_limit (SS-3)
POST /panel/settings/meta         -> meta_pricing.service_message_cost (SS-4)

Emergency keywords take effect immediately: the T4.2 emergency_gate reads the
SS-2 list from settings and recompiles its regex on EVERY run (per-run
compile, no cache to invalidate) — saving here is the trigger (SS-2
"Keyword added ... detected immediately").
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.panel.deps import flash, get_db, require_admin, templates
from app.services import costs, settings as settings_service

router = APIRouter(tags=["panel-settings"])


def _pop_flash(request: Request) -> str | None:
    return request.session.pop("flash", None)


def _number(value: str, key: str, *, minimum: float = 0.0) -> float:
    """Parse a decimal form value; reject invalid/negative input loudly."""
    try:
        parsed = Decimal(value.strip())
    except (InvalidOperation, ValueError):
        raise HTTPException(status_code=400, detail=f"{key} must be a number")
    if parsed < Decimal(str(minimum)):
        raise HTTPException(status_code=400, detail=f"{key} must be >= {minimum}")
    return float(parsed)


@router.get("/settings")
def settings_view(
    request: Request,
    session=Depends(get_db),
    current=Depends(require_admin),
):
    scope_rules = settings_service.get_setting(session, "scope_rules", default={})
    keywords = settings_service.get_emergency_keywords(session)
    meta = settings_service.get_setting(session, "meta_pricing", default={})
    return templates.TemplateResponse(
        request,
        "settings/index.html",
        {
            "current_user": current,
            "flash": _pop_flash(request),
            "scope_rules_text": "\n".join(
                f"{category}={mode}" for category, mode in sorted(scope_rules.items())
            ),
            "keywords_text": "\n".join(keywords),
            "tone": settings_service.get_tone(session),
            "conversation_limit": settings_service.get_setting(
                session, "cost.conversation_limit", default=1.50
            ),
            "daily_limit": settings_service.get_setting(
                session, "cost.daily_limit", default=5.00
            ),
            "meta_cost": (meta or {}).get("service_message_cost", 0.01),
            "snapshot": costs.spend_snapshot(session),
        },
    )


def _save(session, request, key: str, value) -> None:
    settings_service.set_setting(
        session,
        key,
        value,
        updated_by=request.session.get("user_id"),
        actor=request.session.get("username", "unknown"),
    )
    flash(request, f"Saved {key}")


@router.post("/settings/scope")
def settings_scope(
    request: Request,
    rules: str = Form(""),
    session=Depends(get_db),
    current=Depends(require_admin),
):
    parsed: dict[str, str] = {}
    for line in rules.splitlines():
        line = line.strip()
        if not line:
            continue
        if "=" not in line:
            raise HTTPException(status_code=400, detail=f"invalid rule line: {line!r}")
        category, _, mode = line.partition("=")
        category, mode = category.strip(), mode.strip()
        if mode not in settings_service.SCOPE_MODES:
            raise HTTPException(
                status_code=400,
                detail=f"mode must be one of {settings_service.SCOPE_MODES}",
            )
        parsed[category] = mode
    _save(session, request, "scope_rules", parsed)
    return RedirectResponse("/panel/settings", status_code=303)


@router.post("/settings/keywords")
def settings_keywords(
    request: Request,
    keywords: str = Form(""),
    session=Depends(get_db),
    current=Depends(require_admin),
):
    keyword_list = [line.strip() for line in keywords.splitlines() if line.strip()]
    _save(session, request, "emergency.keywords", keyword_list)
    return RedirectResponse("/panel/settings", status_code=303)


@router.post("/settings/tone")
def settings_tone(
    request: Request,
    tone: str = Form(""),
    session=Depends(get_db),
    current=Depends(require_admin),
):
    _save(session, request, "tone.style", tone.strip())
    return RedirectResponse("/panel/settings", status_code=303)


@router.post("/settings/limits")
def settings_limits(
    request: Request,
    conversation_limit: str = Form(...),
    daily_limit: str = Form(...),
    session=Depends(get_db),
    current=Depends(require_admin),
):
    _save(session, request, "cost.conversation_limit", _number(conversation_limit, "conversation_limit"))
    _save(session, request, "cost.daily_limit", _number(daily_limit, "daily_limit"))
    return RedirectResponse("/panel/settings", status_code=303)


@router.post("/settings/meta")
def settings_meta(
    request: Request,
    service_message_cost: str = Form(...),
    session=Depends(get_db),
    current=Depends(require_admin),
):
    _save(
        session,
        request,
        "meta_pricing",
        {"service_message_cost": _number(service_message_cost, "service_message_cost")},
    )
    return RedirectResponse("/panel/settings", status_code=303)

"""Panel JSON API settings admin (B4/T4.2; PDW-API-2, PDW-API-3, PDW-API-4, D1, D4).

Admin-only JSON wrappers over `app/services/settings.py` + `app/services/costs.py`
(thin, no new business logic; every save flows through `set_setting` which
upserts the KV row AND audits with the acting admin, SH-5):

- GET /settings -> all sections + spend snapshot (design #18):
  {"scope_rules", "keywords", "tone", "messages", "templates",
  "conversation_limit", "daily_limit", "meta_cost", "snapshot"}
- POST /settings/{section} -> per-section KV upsert + audit (design #19, #18):
  scope  {"rules": {cat: mode}}           -> scope_rules
  keywords {"keywords": [str]}            -> emergency.keywords
  tone   {"tone": str}                    -> tone.style
  messages {"greeting": str, ...}         -> messages.*
  tarifa {"precios": {service: [range]}}  -> tarifa.precios (validated, S1)
  coverage {"communes": [str]}            -> coverage.communes (validated, S3)
  durations {"service_durations": {...}}  -> booking.service_durations (S4)
  capture-questions {"questions": {field: str}} -> capture.questions (S7)
  reply-texts {"texts": {key: str}}        -> reply.texts (S8)
  conduct {"conduct": {orden, redaccion, max_preguntas_por_mensaje,
                       derivaciones}}      -> chat.conduct (validated, S10)
  limits {"conversation_limit": n, "daily_limit": n} (>= 0) -> cost.*
  meta   {"service_message_cost": n}      -> meta_pricing
- POST /settings/message-templates -> validated additive message-template catalog
- POST /settings/email -> SMTP connection settings (WU-E): host/port/from/user/tls
- POST|DELETE /settings/email/password -> the encrypted SMTP password (write-only)

Section names mirror the Jinja POST routes (/panel/settings/{scope,keywords,
tone,limits,meta}); an unknown section is a 400 (PDW-API-3). Role enforcement
server-side (PDW-API-4): `require_admin_json` -> operador 403; unauthenticated
401 {"detail":"unauthorized"} no redirect (D4, PDW-AUTH-1). No CORS (D1).
"""

from __future__ import annotations

import difflib
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.chat.nodes.capture import CAPTURE_FIELD_ORDER
from app.models import Settings, User
from app.panel.api.deps import require_admin_json
from app.panel.deps import get_db
from app.services import costs, model_secrets, prompts, settings as settings_service, smtp
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
    greeting_short: str
    cannot_answer: str
    clarification: str
    farewell: str
    out_of_hours: str


class MessageTemplatesBody(BaseModel):
    templates: list[Any]


class HoursBody(BaseModel):
    timezone: Any
    schedule: Any


class TarifaBody(BaseModel):
    precios: dict[str, Any]


class CoverageBody(BaseModel):
    communes: list[Any]


class ServiceDurationsBody(BaseModel):
    service_durations: dict[str, Any]


class CaptureQuestionsBody(BaseModel):
    questions: dict[str, Any]


class ReplyTextsBody(BaseModel):
    texts: dict[str, Any]


class ConductBody(BaseModel):
    conduct: dict[str, Any]


class LimitsBody(BaseModel):
    conversation_limit: float
    daily_limit: float


class MetaBody(BaseModel):
    service_message_cost: float


class ModelApiKeyBody(BaseModel):
    api_key: str


class EmailBody(BaseModel):
    # `extra="forbid"`: the password has its own route, so a stray `password`
    # here must fail loudly instead of returning 200 with it silently dropped.
    model_config = ConfigDict(extra="forbid")

    host: str
    port: int
    from_address: str
    user: str = ""
    tls: str = "none"


class SmtpPasswordBody(BaseModel):
    password: str


class PersonaBody(BaseModel):
    # `extra="forbid"`: an unknown prompt key must fail loudly, not be dropped
    # with a 200 that looks like the write succeeded.
    model_config = ConfigDict(extra="forbid")

    orchestrator: str
    orchestrator_brief: str


class EmergencyProtocolBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    safety_instructions: list[str]
    contacts: list[str]
    notify_message: str


class VersionRestoreBody(BaseModel):
    version: int


def _email_payload(session: Session) -> dict:
    """Current SMTP config + password status; the plaintext never leaves here."""
    return {
        "host": settings_service.get_setting(
            session, "notify.smtp_host", default=settings_service.DEFAULT_SMTP_HOST
        ),
        "port": settings_service.get_setting(
            session, "notify.smtp_port", default=settings_service.DEFAULT_SMTP_PORT
        ),
        "from_address": settings_service.get_setting(
            session, "notify.smtp_from", default=settings_service.DEFAULT_SMTP_FROM
        ),
        "user": settings_service.get_setting(
            session, "notify.smtp_user", default=settings_service.DEFAULT_SMTP_USER
        ),
        "tls": settings_service.get_setting(
            session, "notify.smtp_tls", default=settings_service.DEFAULT_SMTP_TLS
        ),
        "password": smtp.smtp_password_status(session),
    }


def _parse_email(body: EmailBody) -> dict[str, object]:
    host = body.host.strip()
    if not host:
        raise HTTPException(status_code=400, detail="smtp host must not be empty")
    from_address = body.from_address.strip()
    if not from_address:
        raise HTTPException(status_code=400, detail="smtp from address must not be empty")
    if not 1 <= body.port <= 65535:
        raise HTTPException(status_code=400, detail="smtp port must be between 1 and 65535")
    if body.tls not in smtp.TLS_MODES:
        raise HTTPException(
            status_code=400, detail=f"tls must be one of {', '.join(smtp.TLS_MODES)}"
        )
    return {
        "host": host,
        "port": body.port,
        "from_address": from_address,
        "user": body.user.strip(),
        "tls": body.tls,
    }


_VERSION_SCOPES = {
    "persona": settings_service.PERSONA_TEXTS_KEY,
    "emergency": settings_service.EMERGENCY_PROTOCOL_KEY,
}


def _persona_payload(session: Session) -> dict:
    """Effective persona text (override or bundled file) + whether it is overridden."""
    stored = settings_service.get_persona_texts(session)
    return {
        "orchestrator": stored.get("personas/orchestrator.md")
        or prompts.load("personas/orchestrator.md"),
        "orchestrator_brief": stored.get("personas/orchestrator_brief.md")
        or prompts.load("personas/orchestrator_brief.md"),
        "customized": bool(stored),
    }


def _emergency_payload(session: Session) -> dict:
    """Effective safety protocol (override or built-in) + whether it is overridden."""
    return {
        **settings_service.get_emergency_protocol(session),
        "customized": session.get(Settings, settings_service.EMERGENCY_PROTOCOL_KEY)
        is not None,
    }


def _scope_key(scope: str) -> str:
    key = _VERSION_SCOPES.get(scope)
    if key is None:
        raise HTTPException(status_code=404, detail=f"unknown version scope: {scope}")
    return key


# The persona is stored under its prompt path (that is what `prompts.load`
# resolves) but exposed under a panel-friendly name: the API translates once,
# here, so the panel never has to know the repo layout.
_PERSONA_PUBLIC_KEYS = {
    "orchestrator": "personas/orchestrator.md",
    "orchestrator_brief": "personas/orchestrator_brief.md",
}


def _default_content(scope: str) -> dict:
    """Version 0: what the build ships (the files / the built-in protocol)."""
    if scope == "persona":
        return {key: prompts.load(key) for key in settings_service.PERSONA_PROMPT_KEYS}
    return settings_service.SETTINGS_DEFAULTS[settings_service.EMERGENCY_PROTOCOL_KEY]


def _public_content(scope: str, content: Any) -> dict:
    """A stored/default state in the same shape `GET /settings` exposes."""
    resolved = content if isinstance(content, dict) else _default_content(scope)
    if scope != "persona":
        return dict(resolved)
    return {public: resolved.get(key, "") for public, key in _PERSONA_PUBLIC_KEYS.items()}


def _version_texts(scope: str, content: Any) -> dict[str, str]:
    """One comparable string per field, so lists diff line by line."""
    return {
        field: "\n".join(value) if isinstance(value, list) else str(value)
        for field, value in _public_content(scope, content).items()
    }


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


def _parse_message_templates(body: MessageTemplatesBody) -> list[dict]:
    try:
        return settings_service.validate_message_templates(body.templates)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


def _parse_hours(body: HoursBody) -> tuple[str, list[dict[str, Any]]]:
    if not isinstance(body.timezone, str):
        raise HTTPException(status_code=400, detail="timezone must be a valid IANA timezone")
    try:
        ZoneInfo(body.timezone)
    except (TypeError, ValueError, ZoneInfoNotFoundError):
        raise HTTPException(status_code=400, detail="timezone must be a valid IANA timezone")

    try:
        settings_service.validate_hours_schedule(body.schedule)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
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
        "templates": settings_service.get_message_templates(session),
        "hours": {
            "timezone": settings_service.get_hours_timezone(session),
            "schedule": settings_service.get_hours_schedule(session),
        },
        "tarifa": settings_service.get_tarifa_precios(session),
        "persona": _persona_payload(session),
        "emergency": _emergency_payload(session),
        "coverage": settings_service.get_coverage_communes(session),
        "service_durations": settings_service.get_service_durations(session),
        "conversation_limit": settings_service.get_setting(
            session, "cost.conversation_limit", default=1.50
        ),
        "daily_limit": settings_service.get_setting(
            session, "cost.daily_limit", default=5.00
        ),
        "meta_cost": (meta or {}).get("service_message_cost", 0.01),
        "snapshot": costs.spend_snapshot(session),
        "model_api_key": model_secrets.model_api_key_status(session),
        "email": _email_payload(session),
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
    model_secrets.invalidate_model_key_cache()
    return {"ok": True, "validation": validation, "model_api_key": model_secrets.model_api_key_status(session)}


@router.delete("/settings/model_api_key")
def settings_model_api_key_clear(
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    model_secrets.clear_model_api_key(session, actor=current.username)
    session.commit()
    model_secrets.invalidate_model_key_cache()
    return {"ok": True, "model_api_key": model_secrets.model_api_key_status(session)}


@router.post("/settings/email")
def settings_email(
    body: EmailBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    """WU-E: the SMTP connection settings (host/port/from/user/tls).

    The password is a separate write-only route; it never travels with the
    connection settings so a config save can never blank a stored credential.
    """
    parsed = _parse_email(body)
    _save(session, "notify.smtp_host", parsed["host"], current)
    _save(session, "notify.smtp_port", parsed["port"], current)
    _save(session, "notify.smtp_from", parsed["from_address"], current)
    _save(session, "notify.smtp_user", parsed["user"], current)
    _save(session, "notify.smtp_tls", parsed["tls"], current)
    session.commit()
    return {"ok": True, "email": _email_payload(session)}


@router.post("/settings/email/password")
def settings_email_password(
    body: SmtpPasswordBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    """Store the SMTP password encrypted; only its masked tail is ever returned."""
    if body.password == "":
        raise HTTPException(status_code=400, detail="password must not be empty")
    smtp.set_smtp_password(
        session, body.password, actor=current.username, updated_by=current.id
    )
    session.commit()
    return {"ok": True, "email": {"password": smtp.smtp_password_status(session)}}


@router.delete("/settings/email/password")
def settings_email_password_clear(
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    smtp.clear_smtp_password(session, actor=current.username)
    session.commit()
    return {"ok": True, "email": {"password": smtp.smtp_password_status(session)}}


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


@router.post("/settings/message-templates")
def settings_message_templates(
    body: MessageTemplatesBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    parsed = _parse_message_templates(body)
    _save(session, settings_service.MESSAGE_TEMPLATES_KEY, parsed, current)
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


@router.post("/settings/coverage")
def settings_coverage(
    body: CoverageBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    try:
        communes = settings_service.validate_coverage_communes(body.communes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _save(session, settings_service.COVERAGE_COMMUNES_KEY, communes, current)
    session.commit()
    return {"ok": True}


@router.post("/settings/durations")
def settings_durations(
    body: ServiceDurationsBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    try:
        durations = settings_service.validate_service_durations(body.service_durations)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _save(session, settings_service.SERVICE_DURATIONS_KEY, durations, current)
    session.commit()
    return {"ok": True}


@router.post("/settings/capture-questions")
def settings_capture_questions(
    body: CaptureQuestionsBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    try:
        questions = settings_service.validate_capture_questions(
            body.questions, settings_service.get_conduct(session)["orden"]
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _save(session, settings_service.CAPTURE_QUESTIONS_KEY, questions, current)
    session.commit()
    return {"ok": True}


@router.post("/settings/reply-texts")
def settings_reply_texts(
    body: ReplyTextsBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    try:
        texts = settings_service.validate_reply_texts(body.texts)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _save(session, settings_service.REPLY_TEXTS_KEY, texts, current)
    session.commit()
    return {"ok": True}


@router.post("/settings/conduct")
def settings_conduct(
    body: ConductBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    try:
        conduct = settings_service.validate_conduct(body.conduct, CAPTURE_FIELD_ORDER)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _save(session, settings_service.CHAT_CONDUCT_KEY, conduct, current)
    session.commit()
    return {"ok": True}


@router.post("/settings/tarifa")
def settings_tarifa(
    body: TarifaBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    try:
        precios = settings_service.validate_tarifa_precios(body.precios)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _save(session, settings_service.TARIFA_PRECIOS_KEY, precios, current)
    session.commit()
    return {"ok": True}


@router.post("/settings/persona")
def settings_persona(
    body: PersonaBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    """S12: the editable persona. Both files save as one versioned unit."""
    try:
        texts = settings_service.validate_persona_texts(
            {
                "personas/orchestrator.md": body.orchestrator,
                "personas/orchestrator_brief.md": body.orchestrator_brief,
            }
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _save(session, settings_service.PERSONA_TEXTS_KEY, texts, current)
    session.commit()
    return {"ok": True}


@router.post("/settings/emergency")
def settings_emergency(
    body: EmergencyProtocolBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    """S13: the editable safety protocol, same version surface as the persona."""
    try:
        protocol = settings_service.validate_emergency_protocol(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _save(session, settings_service.EMERGENCY_PROTOCOL_KEY, protocol, current)
    session.commit()
    return {"ok": True}


@router.get("/settings/versions/{scope}")
def settings_versions(
    scope: str,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    """Oldest-first history of one scope; version 0 (the default) is implicit."""
    key = _scope_key(scope)
    return {
        "versions": [
            {
                **entry,
                "content": None
                if entry["content"] is None
                else _public_content(scope, entry["content"]),
            }
            for entry in settings_service.setting_versions(session, key)
        ]
    }


@router.get("/settings/versions/{scope}/diff")
def settings_version_diff(
    scope: str,
    from_version: int = Query(alias="from", ge=0),
    to_version: int = Query(alias="to", ge=0),
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    """Unified diff per field between two versions (0 = the built-in default)."""
    key = _scope_key(scope)
    try:
        before = settings_service.setting_version_content(session, key, from_version)
        after = settings_service.setting_version_content(session, key, to_version)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"unknown version: {exc.args[0]}")
    before_texts = _version_texts(scope, before)
    after_texts = _version_texts(scope, after)
    fields = dict.fromkeys([*before_texts, *after_texts])
    return {
        "diff": {
            field: "\n".join(
                difflib.unified_diff(
                    before_texts.get(field, "").splitlines(),
                    after_texts.get(field, "").splitlines(),
                    fromfile=f"v{from_version}",
                    tofile=f"v{to_version}",
                    lineterm="",
                )
            )
            for field in fields
        }
    }


@router.post("/settings/versions/{scope}/restore")
def settings_version_restore(
    scope: str,
    body: VersionRestoreBody,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    """Restore one version; version 0 deletes the row back to the built-in default."""
    key = _scope_key(scope)
    try:
        content = settings_service.setting_version_content(session, key, body.version)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown version: {body.version}")
    if content is None:
        settings_service.delete_setting(session, key, actor=current.username)
    else:
        try:
            validated = (
                settings_service.validate_persona_texts(content)
                if scope == "persona"
                else settings_service.validate_emergency_protocol(content)
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        _save(session, key, validated, current)
    session.commit()
    return {"ok": True}


# Catch-all MUST stay registered AFTER the specific POST routes above: FastAPI
# matches routes in registration order, so the
# literal sections win and anything else is an unknown section (PDW-API-3).
_KNOWN_SECTIONS = {"scope", "keywords", "tone", "messages", "hours", "limits", "meta", "email"}


@router.post("/settings/{section}")
def settings_section_unknown(
    section: str,
    session: Session = Depends(get_db),
    current: User = Depends(require_admin_json),
) -> dict:
    raise HTTPException(status_code=400, detail=f"unknown section {section!r} ({', '.join(sorted(_KNOWN_SECTIONS))})")

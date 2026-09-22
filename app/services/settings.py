"""Settings KV service (design: app/services/settings.py, D5; SS-1..5 storage).

All operational configuration lives in the single `settings` table (key PK,
value jsonb, updated_by FK->users, updated_at) — no per-domain config tables
(D5). This module provides the generic read/write surface:

- `get_setting`: stored value, else the built-in default for a known key, else
  the caller-provided default.
- `set_setting`: UPSERT + one audit entry per write (SH-5: who/what/when).

T4.1.2 adds the semantic accessors (scope rules / emergency keywords / tone /
standard messages) and their defaults on top of the generic KV surface:

- `get_scope_mode(session, category)` — SS-1: `bot_resolve` | `always_escalate`,
  default `bot_resolve` for any category not explicitly set.
- `get_emergency_keywords(session)` — SS-2: the EM-1 keyword list as plain
  strings, ready for T4.2's regex compiler; default list below.
- `get_tone(session)` / `get_message(session, key, default)` — SS-5: tone style
  and standard-message overrides.

All functions take an explicit session; the caller commits and closes (matches
app/services/customers.py / audit.py style).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.models import Settings
from app.services.audit import record_audit

logger = logging.getLogger(__name__)

# SS-1: the two legal scope modes per category. Anything else behaves as unset.
SCOPE_MODES: tuple[str, ...] = ("bot_resolve", "always_escalate")
DEFAULT_SCOPE_MODE = "bot_resolve"

# SS-5: validated tone styles and their prompt directives.
TONE_STYLES: tuple[str, ...] = ("cercano", "formal", "directo")
TONE_DIRECTIVES: dict[str, str] = {
    "cercano": "Responde con un tono cercano, amable y claro.",
    "formal": "Responde con un tono formal, profesional y preciso.",
    "directo": "Responde de forma directa, breve y clara.",
}
DEFAULT_TONE_STYLE = "cercano"

MESSAGE_DEFAULTS: dict[str, str] = {
    "greeting": (
        "Hola, soy el asistente virtual de Lumat, la empresa de gasfitería que te "
        "atiende. ¿En qué puedo ayudarte? Elige una opción:\n"
    ),
    "cannot_answer": (
        "Lo siento, no puedo responder con seguridad a eso. Un asesor de Lumat "
        "revisará tu consulta y te contactará."
    ),
    "clarification": (
        "No entendí tu mensaje. ¿Puedes elegir una opción del menú? "
        "(Calefont, Caldera, Calefacción, Solicitar visita, Valores, "
        "Postventa/Garantía, Emergencia, Hablar con una persona)"
    ),
}

# SS-2 (EM-1): default emergency expressions + obvious Spanish variants.
# Stored as a plain list[str] — T4.2 compiles the regex from these.
DEFAULT_EMERGENCY_KEYWORDS: list[str] = [
    "olor a gas",
    "huele a gas",  # variant
    "fuga",
    "fuga de gas",  # variant
    "humo",
    "incendio",
    "chispa",
    "chispas",  # variant
    "explosión",
    "monóxido",
    "intoxicación",
    "riesgo eléctrico",
    "filtración severa",
]

# EM-3 (T4.2): safety protocol content delivered by the emergency node —
# approved safety steps, emergency contacts and the technician-notified
# confirmation. Panel-editable via the generic settings KV surface.
DEFAULT_SAFETY_INSTRUCTIONS: list[str] = [
    "Corta el suministro de gas solo si puedes hacerlo de forma segura.",
    "Abre puertas y ventanas para ventilar el lugar.",
    "No enciendas ni apagues luces, interruptores ni electrodomésticos.",
    "Sal del lugar si el olor a gas es fuerte y avisa desde afuera.",
    "No intentes reparar el equipo tú mismo.",
]
DEFAULT_EMERGENCY_CONTACTS: list[str] = [
    "Emergencias: Bomberos 132 o Ambulancia 131.",
    "Distribuidor de gas: el número de emergencia está en tu boleta o medidor.",
    "Lumat: +56 9 1234 5678.",
]
DEFAULT_EMERGENCY_NOTIFY_MESSAGE: str = (
    "Un técnico de Lumat ha sido notificado y te contactará a la brevedad."
)

# EM-4 (T4.3): owner/technician notification channel defaults. The WhatsApp
# utility template goes to the owner number (business-initiated send outside
# any 24h window — design D9); the email fallback / reminders use owner_email.
DEFAULT_OWNER_EMAIL: str = "emergencias@lumat.cl"
DEFAULT_OWNER_WHATSAPP: str = "+56912345678"
DEFAULT_SMTP_HOST: str = "localhost"
DEFAULT_SMTP_FROM: str = "notificaciones@lumat.cl"

# SS-3: USD per million tokens. Sources/effective date are retained in the
# default so a pricing change is auditable without a second configuration table.
DEFAULT_LLM_RATES = {
    "gpt-4o-mini": {"input_per_1m": 0.15, "output_per_1m": 0.60},
    "deepseek-chat": {"input_per_1m": 0.27, "output_per_1m": 1.10},
    "_source": "OpenAI and DeepSeek public API pricing; verify at activation",
    "_effective_date": "2026-09-11",
}

# Built-in defaults for known keys. A missing row falls back to these instead
# of None, so unconfigured keys still behave (SS-1..5 "works out of the box").
# Message content defaults (`messages.greeting`, `messages.cannot_answer`, ...)
# intentionally live in the chat nodes, not here — `get_message` resolves
# overrides against the caller-provided default (single source of truth).
SETTINGS_DEFAULTS: dict[str, Any] = {
    # SS-4: Meta service-message unit cost (USD), effective 2026-10-01.
    # Reference placeholder until verified with Meta at activation (T4.5).
    "meta_pricing": {"service_message_cost": 0.01},
    # SS-3: cost guardrail limits (USD) — per conversation and per UTC day.
    # T4.5 consumes them via costs.conversation_cost_state/daily_cost_state.
    "cost.conversation_limit": 1.50,
    "cost.daily_limit": 5.00,
    "cost.llm_rates": DEFAULT_LLM_RATES,
    # SS-1: category -> "bot_resolve" | "always_escalate". Empty = all resolve.
    "scope_rules": {},
    # SS-2: emergency keyword list consumed by T4.2's regex compiler.
    "emergency.keywords": DEFAULT_EMERGENCY_KEYWORDS,
    # EM-3: safety protocol content delivered by the emergency node (T4.2).
    "emergency.safety_instructions": DEFAULT_SAFETY_INSTRUCTIONS,
    "emergency.contacts": DEFAULT_EMERGENCY_CONTACTS,
    "emergency.notify_message": DEFAULT_EMERGENCY_NOTIFY_MESSAGE,
    # EM-4: owner/technician notification channel (T4.3) — WhatsApp template
    # recipient + email fallback SMTP config. Panel-editable via the KV surface.
    "notify.owner_email": DEFAULT_OWNER_EMAIL,
    "notify.owner_whatsapp": DEFAULT_OWNER_WHATSAPP,
    "notify.smtp_host": DEFAULT_SMTP_HOST,
    "notify.smtp_from": DEFAULT_SMTP_FROM,
    # SS-5: tone style used by the chat nodes.
    "tone.style": DEFAULT_TONE_STYLE,
    "messages.greeting": MESSAGE_DEFAULTS["greeting"],
    "messages.cannot_answer": MESSAGE_DEFAULTS["cannot_answer"],
    "messages.clarification": MESSAGE_DEFAULTS["clarification"],
    "hours.timezone": "America/Santiago",
    "hours.schedule": [],
    # AP-8 (T5.5): dashboard KPI time window in days (SQL counts over the
    # last N days). Panel-editable via the generic settings KV surface.
    "kpi.window_days": 7,
}


def get_setting(session: Session, key: str, default: Any = None) -> Any:
    """Read one setting: stored value > built-in default > caller default."""
    row = session.get(Settings, key)
    if row is not None:
        return row.value
    if key in SETTINGS_DEFAULTS:
        return SETTINGS_DEFAULTS[key]
    return default


def set_setting(
    session: Session,
    key: str,
    value: Any,
    *,
    updated_by: int | None = None,
    actor: str = "system",
) -> Settings:
    """Upsert one setting and audit the change (SH-5). The caller commits."""
    # SessionLocal runs autoflush=False, so a row inserted by an earlier call in
    # this session would be invisible to session.get -> flush so the upsert
    # reads its own writes (two set_setting calls per session stay one row).
    session.flush()
    row = session.get(Settings, key)
    before = row.value if row is not None else None
    if row is None:
        row = Settings(key=key, value=value, updated_by=updated_by)
        session.add(row)
    else:
        row.value = value
        row.updated_by = updated_by
    record_audit(
        session,
        actor=actor,
        action="settings.change",
        entity="settings",
        entity_id=key,
        before={"value": before} if before is not None else None,
        after={"value": value},
    )
    return row


def get_scope_mode(session: Session, category: str) -> str:
    """SS-1: mode for one category; `bot_resolve` when unset or invalid.

    `scope_rules` is a single JSONB dict (category -> mode), one UPSERT + one
    audit entry per panel save. Categories absent from the dict default to
    `bot_resolve`; a stored value outside the two literals behaves as unset.
    """
    rules = get_setting(session, "scope_rules", default={})
    mode = rules.get(category)
    return mode if mode in SCOPE_MODES else DEFAULT_SCOPE_MODE


def get_emergency_keywords(session: Session) -> list[str]:
    """SS-2: emergency keyword list (list[str]) or the EM-1 defaults.

    T4.2 compiles its detection regex from this list. Contract: stored value
    must be a list of strings — a malformed value is the panel's responsibility.
    """
    return get_setting(session, "emergency.keywords", default=DEFAULT_EMERGENCY_KEYWORDS)


def get_tone(session: Session) -> str:
    """SS-5: valid tone style; invalid stored values degrade to the default."""
    tone = get_setting(session, "tone.style", default=DEFAULT_TONE_STYLE)
    return tone if tone in TONE_STYLES else DEFAULT_TONE_STYLE


def get_tone_directive(session: Session) -> str:
    """SS-5: prompt directive for the effective tone style."""
    return TONE_DIRECTIVES[get_tone(session)]


def get_hours_timezone(session: Session) -> str:
    """Return the configured IANA timezone, or the default when unusable."""
    timezone_name = get_setting(session, "hours.timezone", default="America/Santiago")
    return timezone_name if isinstance(timezone_name, str) else "America/Santiago"


def get_hours_schedule(session: Session) -> list[dict[str, Any]]:
    """Return the configured schedule, or the empty feature-off default."""
    schedule = get_setting(session, "hours.schedule", default=[])
    return schedule if isinstance(schedule, list) else []


def is_open_at(*, schedule: list, timezone_name: str, now: datetime) -> bool:
    """Evaluate a validated weekly schedule at an aware instant.

    Overnight windows are invalid because write-time validation requires
    ``open < close``; malformed entries fail open rather than closing chat.
    """
    if not schedule:
        return True

    try:
        local_now = now.astimezone(ZoneInfo(timezone_name))
    except (TypeError, ValueError, ZoneInfoNotFoundError) as exc:
        logger.warning("Unable to resolve hours timezone %r: %s", timezone_name, exc)
        return True

    parsed_entries: list[tuple[list[int], Any, Any]] = []
    for entry in schedule:
        try:
            if not isinstance(entry, dict):
                raise ValueError("entry is not an object")
            days = entry["days"]
            opening = entry["open"]
            closing = entry["close"]
            if (
                not isinstance(days, list)
                or not days
                or any(isinstance(day, bool) or not isinstance(day, int) or not 1 <= day <= 7 for day in days)
                or not isinstance(opening, str)
                or not isinstance(closing, str)
                or len(opening) != 5
                or len(closing) != 5
                or opening[2] != ":"
                or closing[2] != ":"
            ):
                raise ValueError("invalid days or HH:MM values")
            open_time = datetime.strptime(opening, "%H:%M").time()
            close_time = datetime.strptime(closing, "%H:%M").time()
            if open_time >= close_time:
                raise ValueError("open must be before close")
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Unable to parse hours schedule entry %r: %s", entry, exc)
            return True
        parsed_entries.append((days, open_time, close_time))

    weekday = local_now.isoweekday()
    local_time = local_now.time()
    return any(
        weekday in days and opening <= local_time < closing
        for days, opening, closing in parsed_entries
    )


def get_message(session: Session, key: str, default: str | None = None) -> str:
    """SS-5: override for `messages.<key>`, else the built-in default."""
    fallback = MESSAGE_DEFAULTS.get(key, default)
    return get_setting(session, f"messages.{key}", default=fallback)

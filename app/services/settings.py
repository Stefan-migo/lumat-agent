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
  and standard-message overrides. Message content defaults stay in the chat
  nodes (single source of truth); the accessor only resolves overrides and
  falls back to the caller-provided default.

All functions take an explicit session; the caller commits and closes (matches
app/services/customers.py / audit.py style).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import Settings
from app.services.audit import record_audit

# SS-1: the two legal scope modes per category. Anything else behaves as unset.
SCOPE_MODES: tuple[str, ...] = ("bot_resolve", "always_escalate")
DEFAULT_SCOPE_MODE = "bot_resolve"

# SS-5: default tone style (LumatRequest §1.12); panel-editable free string.
DEFAULT_TONE_STYLE = "warm-professional"

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

# Built-in defaults for known keys. A missing row falls back to these instead
# of None, so unconfigured keys still behave (SS-1..5 "works out of the box").
# Message content defaults (`messages.greeting`, `messages.cannot_answer`, ...)
# intentionally live in the chat nodes, not here — `get_message` resolves
# overrides against the caller-provided default (single source of truth).
SETTINGS_DEFAULTS: dict[str, Any] = {
    # SS-4: Meta service-message unit cost (USD), effective 2026-10-01.
    # Reference placeholder until verified with Meta at activation (T4.5).
    "meta_pricing": {"service_message_cost": 0.01},
    # SS-1: category -> "bot_resolve" | "always_escalate". Empty = all resolve.
    "scope_rules": {},
    # SS-2: emergency keyword list consumed by T4.2's regex compiler.
    "emergency.keywords": DEFAULT_EMERGENCY_KEYWORDS,
    # EM-3: safety protocol content delivered by the emergency node (T4.2).
    "emergency.safety_instructions": DEFAULT_SAFETY_INSTRUCTIONS,
    "emergency.contacts": DEFAULT_EMERGENCY_CONTACTS,
    "emergency.notify_message": DEFAULT_EMERGENCY_NOTIFY_MESSAGE,
    # SS-5: tone style used by the chat nodes (free string, panel-editable).
    "tone.style": DEFAULT_TONE_STYLE,
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
    """SS-5: tone style (`tone.style`), default `warm-professional`."""
    return get_setting(session, "tone.style", default=DEFAULT_TONE_STYLE)


def get_message(session: Session, key: str, default: str) -> str:
    """SS-5: override for `messages.<key>`, else the caller-provided default.

    Message content defaults live in the chat nodes (GREETING_HEADER,
    CANNOT_ANSWER_REPLY, ...); callers pass their constant as `default` so the
    settings module never duplicates node-owned content.
    """
    return get_setting(session, f"messages.{key}", default=default)

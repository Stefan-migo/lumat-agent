"""Settings KV service (design: app/services/settings.py, D5; SS-1..5 storage).

All operational configuration lives in the single `settings` table (key PK,
value jsonb, updated_by FK->users, updated_at) — no per-domain config tables
(D5). This module provides the generic read/write surface:

- `get_setting`: stored value, else the built-in default for a known key, else
  the caller-provided default.
- `set_setting`: UPSERT + one audit entry per write (SH-5: who/what/when).

T4.1.2 adds the semantic accessors (scope rules / emergency keywords / tone)
and their defaults; this module stays generic KV. `meta_pricing` is the first
known key and is already consumed by send.py (SS-4 reference cost).

All functions take an explicit session; the caller commits and closes (matches
app/services/customers.py / audit.py style).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import Settings
from app.services.audit import record_audit

# Built-in defaults for known keys. A missing row falls back to these instead
# of None, so unconfigured keys still behave (SS-1..5 "works out of the box").
# ponytail: only `meta_pricing` is known so far — T4.1.2 registers
# scope_rules / emergency_keywords / tone defaults here.
SETTINGS_DEFAULTS: dict[str, Any] = {
    # SS-4: Meta service-message unit cost (USD), effective 2026-10-01.
    # Reference placeholder until verified with Meta at activation (T4.5).
    "meta_pricing": {"service_message_cost": 0.01},
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

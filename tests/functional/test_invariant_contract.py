"""S19 — contract: the five invariants cannot be turned off from the panel.

The owner may ADJUST values inside an invariant (the cost thresholds, the words
that trigger the emergency protocol), but no setting or route may TURN ONE OFF:

1. the emergency gate always runs before the LLM,
2. the cost gate always has a limit,
3. consent is always asked before booking,
4. `<user_input>` is always data (anti-injection),
5. a human takeover always silences the bot.

The behaviour of each invariant is covered by its own suite (emergency, cost,
capture consent, injection, takeover). This file guards the configuration layer
that wraps them: a new writable key, or a value that switches the mechanism off,
must fail the contract before it ships.

Reading agreed with the owner (T19): "not disableable" means the mechanism, not
the number. `cost.*` and `emergency.keywords` stay editable; an empty keyword
list or a zero limit must not be accepted, because they are off switches spelled
as values.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from sqlalchemy import select

from app.chat.state import get_or_create_conversation  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    AuditLog,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
    Settings,
)
from app.services import costs, settings as settings_service  # noqa: E402
from app.services.customers import get_or_create_customer  # noqa: E402
from app.services.emergency import classify_emergency, compile_keywords  # noqa: E402

SETTINGS = "/panel/api/settings"
ROOT = Path(__file__).resolve().parents[2]
SETTINGS_ROUTER = ROOT / "app" / "panel" / "api" / "routes" / "settings.py"

# A key whose segment names a switch is an off switch no matter which invariant
# it belongs to. `_` and `.` are both segment boundaries, so compound names
# (`gate_enabled`, `skip_emergency`) cannot slip through. Values inside an
# invariant never look like this.
_TOGGLE_SEGMENT = re.compile(
    r"(^|[._])(enabled?|disabled?|enable|disable|bypass|skip|active|activo|activa|on|off)($|[._])",
    re.IGNORECASE,
)
# `_save(session, "literal")`, `_save(session, f"prefix.{key}")` and
# `_save(session, settings_service.CONSTANT)` are the three shapes the router
# uses; the catch-all's `_save(session, key, ...)` stays out (it always raises).
_WRITTEN_KEY = re.compile(
    r'_save\(\s*session\s*,\s*(?:"([^"]+)"|f"([^"]+)"|settings_service\.([A-Z_]+))'
)


def _login(client, username: str = "adm", password: str = "adm-pass") -> None:
    resp = client.post(
        "/panel/api/login",
        json={"username": username, "password": password},
        follow_redirects=False,
    )
    assert resp.status_code == 200, f"api login must succeed: {resp.status_code} {resp.text}"


def _last_audit(action: str) -> AuditLog | None:
    with SessionLocal() as session:
        return session.scalars(
            select(AuditLog)
            .where(AuditLog.action == action)
            .order_by(AuditLog.id.desc())
            .limit(1)
        ).first()


def _seed_setting(key: str, value) -> None:
    with SessionLocal() as session:
        session.add(Settings(key=key, value=value))
        session.commit()


def _seed_spend(cost: float, phone: str = "+56912345678") -> int:
    """One processed outbound message with the given LLM cost."""
    with SessionLocal() as session:
        customer = get_or_create_customer(session, phone)
        conversation = get_or_create_conversation(session, customer, phone)
        session.add(
            Message(
                conversation_id=conversation.id,
                direction=MessageDirection.OUTBOUND,
                msg_type=MessageType.TEXT,
                text="m",
                status=MessageStatus.PROCESSED,
                cost_llm=cost,
            )
        )
        session.commit()
        return conversation.id


# --- surface guard -----------------------------------------------------------


def _written_keys() -> set[str]:
    """Every settings key the panel router can write, from its own source.

    Literal keys come through as-is, `f"messages.{key}"` contributes its fixed
    prefix, and named constants are resolved through `settings_service` so the
    scan cannot go blind when a key moves behind a constant.
    """
    source = SETTINGS_ROUTER.read_text()
    keys: set[str] = set()
    unresolved: list[str] = []
    for literal, prefixed, constant in _WRITTEN_KEY.findall(source):
        if literal:
            keys.add(literal)
        elif prefixed:
            # `f"messages.{key}"` contributes its fixed text; the dynamic part
            # is a `messages.*` key chosen by the route, never a new section.
            keys.add(prefixed)
        else:
            value = getattr(settings_service, constant, None)
            if not isinstance(value, str):
                unresolved.append(constant)
            else:
                keys.add(value)
    assert unresolved == [], f"settings router writes unresolvable constants: {unresolved}"
    return keys


def test_no_panel_settings_route_writes_a_toggle_key():
    """The panel may set values, never a switch.

    Scans the live router source, so a new `_save(session, "cost.enabled", ...)`
    (or an `emergency.gate_enabled`) fails here even when nothing else in the
    suite reads it.
    """
    written = _written_keys()

    assert len(written) >= 15, f"the scan went blind: only found {sorted(written)}"
    toggles = sorted(key for key in written if _TOGGLE_SEGMENT.search(key))

    assert toggles == [], f"panel writes invariant switches: {toggles}"


@pytest.mark.parametrize(
    "key",
    [
        "cost.enabled",
        "emergency.gate_enabled",
        "skip_emergency",
        "bot_off",
        "cost.disable",
        "notify.bypass",
        "emergency.active",
    ],
)
def test_the_toggle_guard_catches_compound_switch_names(key):
    """The scan is only as good as this predicate — pin it to real shapes."""
    assert _TOGGLE_SEGMENT.search(key)


@pytest.mark.parametrize(
    "key",
    ["messages.out_of_hours", "cost.conversation_limit", "hours.timezone", "persona.texts"],
)
def test_the_toggle_guard_does_not_flag_ordinary_value_keys(key):
    assert not _TOGGLE_SEGMENT.search(key)


def test_unknown_settings_section_cannot_write_a_key(client, make_user):
    """The catch-all is the panel's open door: prove it stays shut."""
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post(f"{SETTINGS}/cost", json={"enabled": False}, follow_redirects=False)

    assert resp.status_code == 400
    assert "unknown section" in resp.json()["detail"]
    with SessionLocal() as session:
        assert session.get(Settings, "cost.enabled") is None


# --- invariant 2: the cost gate always has a limit ---------------------------


def test_shipped_cost_limits_are_positive():
    """Out of the box the cap exists; a default of 0 would be an off switch."""
    assert settings_service.SETTINGS_DEFAULTS["cost.conversation_limit"] > 0
    assert settings_service.SETTINGS_DEFAULTS["cost.daily_limit"] > 0


def test_panel_rejects_a_zero_cost_limit(client, make_user):
    """0 is how the panel used to spell "no cap" (`_percent` returned normal)."""
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    for body in (
        {"conversation_limit": 0, "daily_limit": 5.0},
        {"conversation_limit": 1.5, "daily_limit": 0},
    ):
        resp = client.post(f"{SETTINGS}/limits", json=body, follow_redirects=False)

        assert resp.status_code == 400, body
        assert resp.headers["content-type"].startswith("application/json")
        assert "unknown section" not in resp.json()["detail"]
        assert _last_audit("settings.change") is None, "invalid limit must not audit"

    with SessionLocal() as session:
        assert session.get(Settings, "cost.conversation_limit") is None
        assert session.get(Settings, "cost.daily_limit") is None


def test_cost_gate_fails_closed_on_a_non_positive_stored_limit():
    """A row written before this guard (or by hand) must not unlock the bot."""
    conversation_id = _seed_spend(cost=10.0)
    _seed_setting("cost.daily_limit", 0)
    _seed_setting("cost.conversation_limit", 0)

    with SessionLocal() as session:
        day_percent, day_mode = costs.daily_cost_state(session)
        conv_percent, conv_mode = costs.conversation_cost_state(session, conversation_id)

    # The fallback is the shipped limit ($5.00/day, $1.50/conversation), so
    # $10 of spend is over both caps: blocked, never "unlimited".
    assert day_mode == "blocked"
    assert conv_mode == "blocked"
    assert day_percent > 0
    assert conv_percent > 0


# --- invariant 1: the emergency gate always has keywords ---------------------


def test_panel_rejects_an_empty_emergency_keyword_list(client, make_user):
    """An empty list compiles to a pattern that matches nothing: the gate is off."""
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    for body in ({"keywords": []}, {"keywords": ["  ", ""]}):
        resp = client.post(f"{SETTINGS}/keywords", json=body, follow_redirects=False)

        assert resp.status_code == 400, body
        assert resp.headers["content-type"].startswith("application/json")
        assert "unknown section" not in resp.json()["detail"]
        assert _last_audit("settings.change") is None

    with SessionLocal() as session:
        assert session.get(Settings, "emergency.keywords") is None


def test_emergency_gate_fails_closed_on_an_empty_stored_keyword_list():
    """A stored `[]` must fall back to the shipped triggers, not disable them."""
    _seed_setting("emergency.keywords", [])

    with SessionLocal() as session:
        keywords = settings_service.get_emergency_keywords(session)

    assert keywords, "the gate lost every trigger"
    assert classify_emergency("hay olor a gas en la cocina", compile_keywords(keywords)) is not None

"""T4.5 integration tests — cost guardrails (SS-3, SS-4).

Scenarios mapped from openspec/.../settings-scope-limits/spec.md:

- SS-3 "Conversation limit reached": 80% -> owner alert + conservative mode;
  100% -> conversation escalates, no more LLM for it (blocked)
- SS-3 "Daily limit reached": 80% -> owner alert; 100% -> paid LLM blocked,
  deterministic fallback reply + escalate
- SS-4 "Spend visible": `spend_snapshot` exposes current/daily spend + limits
  + mode for the panel (T5.5 consumes it; no UI here)
- SS-4 Meta pricing: `send.meta_message_cost` flows through the settings
  service (`get_setting`) — consolidated in T4.5 (ponytail debt T4.1.1)

Part 1 (service): costs.py helpers — deterministic, DB-backed, no mocks
except smtplib for the owner alert email. Part 2 (graph): full-graph runs
with OpenAI mocked via respx (blocked/conservative paths must never call it
unless explicitly allowed).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

import psycopg
import pytest
from sqlalchemy import select

from app.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    AuditLog,
    Case,
    Conversation,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services import costs, send  # noqa: E402
from app.chat.state import get_or_create_conversation  # noqa: E402
from app.services.customers import get_or_create_customer  # noqa: E402
from app.services.settings import get_setting, set_setting  # noqa: E402

ADMIN_DB_URL = "postgresql://lumat:lumat@localhost:5432/lumat"


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    """Reset chat + settings tables before every test (shared test DB)."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, audit_log, conversation_events, cases, messages, "
            "conversations, customer_notes, customers RESTART IDENTITY CASCADE"
        )
    yield


# ---------------------------------------------------------------------------
# SMTP fakes — the owner alert email must never reach a real SMTP server.
# ---------------------------------------------------------------------------


def _capturing_smtp(sent_emails: list) -> Callable:
    """Return an smtplib.SMTP replacement recording (from, tos, msg) tuples."""

    def factory(*args, **kwargs):
        class _Fake:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def sendmail(self, from_addr, to_addrs, msg):
                sent_emails.append((from_addr, to_addrs, msg))

        return _Fake()

    return factory


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _seed_conv_costs(costs_list: list[float], phone: str = "+56912345678") -> int:
    """Create a conversation and attach processed messages with the costs."""
    with SessionLocal() as session:
        customer = get_or_create_customer(session, phone)
        conv = get_or_create_conversation(session, customer, phone)
        for i, cost in enumerate(costs_list):
            session.add(
                Message(
                    conversation_id=conv.id,
                    direction=MessageDirection.OUTBOUND,
                    msg_type=MessageType.TEXT,
                    text=f"m{i}",
                    status=MessageStatus.PROCESSED,
                    cost_llm=cost,
                )
            )
        session.commit()
        return conv.id


def _audit_actions() -> list[str]:
    """Audit actions limited to the cost-alert surface (seed noise excluded)."""
    with SessionLocal() as session:
        return list(
            session.scalars(
                select(AuditLog.action).where(AuditLog.action.like("cost.alert.%"))
            )
        )


# ---------------------------------------------------------------------------
# Part 1 — service: per-conversation + daily cost state (SS-3)
# ---------------------------------------------------------------------------


def test_cost_limit_defaults_registered_in_settings():
    """SS-3: $1.50 conversation / $5 daily defaults work without a settings row."""
    with SessionLocal() as session:
        assert get_setting(session, "cost.conversation_limit") == 1.50
        assert get_setting(session, "cost.daily_limit") == 5.00


def test_conversation_cost_state_normal_below_80():
    conv_id = _seed_conv_costs([0.75])
    with SessionLocal() as session:
        percent, mode = costs.conversation_cost_state(session, conv_id)
    assert percent == pytest.approx(50.0)
    assert mode == "normal"


def test_conversation_cost_state_conservative_at_80():
    conv_id = _seed_conv_costs([1.20])
    with SessionLocal() as session:
        percent, mode = costs.conversation_cost_state(session, conv_id)
    assert percent == pytest.approx(80.0)
    assert mode == "conservative"


def test_conversation_cost_state_blocked_at_100():
    conv_id = _seed_conv_costs([1.50])
    with SessionLocal() as session:
        percent, mode = costs.conversation_cost_state(session, conv_id)
    assert percent == pytest.approx(100.0)
    assert mode == "blocked"


def test_conversation_cost_state_uses_settings_limit():
    """Triangulation: a raised limit moves the same spend back to normal."""
    conv_id = _seed_conv_costs([1.50])
    with SessionLocal() as session:
        set_setting(session, "cost.conversation_limit", 3.00)
        session.commit()
    with SessionLocal() as session:
        percent, mode = costs.conversation_cost_state(session, conv_id)
    assert percent == pytest.approx(50.0)
    assert mode == "normal"


def test_daily_cost_state_thresholds():
    _seed_conv_costs([2.00], phone="+56911111111")
    _seed_conv_costs([2.00], phone="+56922222222")
    with SessionLocal() as session:
        percent, mode = costs.daily_cost_state(session)
    assert percent == pytest.approx(80.0)
    assert mode == "conservative"


def test_daily_cost_state_blocked_at_100():
    _seed_conv_costs([2.50], phone="+56911111111")
    _seed_conv_costs([2.50], phone="+56922222222")
    with SessionLocal() as session:
        percent, mode = costs.daily_cost_state(session)
    assert percent == pytest.approx(100.0)
    assert mode == "blocked"


def test_daily_cost_state_uses_settings_limit():
    _seed_conv_costs([5.00], phone="+56911111111")
    with SessionLocal() as session:
        set_setting(session, "cost.daily_limit", 10.00)
        session.commit()
    with SessionLocal() as session:
        percent, mode = costs.daily_cost_state(session)
    assert percent == pytest.approx(50.0)
    assert mode == "normal"


# ---------------------------------------------------------------------------
# Part 1 — service: spend_snapshot (SS-4, panel data — no UI in T4.5)
# ---------------------------------------------------------------------------


def test_spend_snapshot_exposes_spend_limits_and_mode():
    conv_id = _seed_conv_costs([1.20])
    with SessionLocal() as session:
        snapshot = costs.spend_snapshot(session, conversation_id=conv_id)
    assert snapshot["conversation_spend"] == pytest.approx(1.20)
    assert snapshot["conversation_limit"] == pytest.approx(1.50)
    assert snapshot["conversation_percent"] == pytest.approx(80.0)
    assert snapshot["daily_spend"] == pytest.approx(1.20)
    assert snapshot["daily_limit"] == pytest.approx(5.00)
    assert snapshot["daily_percent"] == pytest.approx(24.0)
    assert snapshot["mode"] == "conservative"  # worst of both scopes
    assert snapshot["date"] == datetime.now(timezone.utc).date().isoformat()


def test_spend_snapshot_without_conversation_scope():
    _seed_conv_costs([2.00])
    with SessionLocal() as session:
        snapshot = costs.spend_snapshot(session)
    assert snapshot["conversation_spend"] is None
    assert snapshot["conversation_percent"] is None
    assert snapshot["mode"] == "normal"  # daily only: 40%


# ---------------------------------------------------------------------------
# Part 1 — service: owner alert (SS-3), audit-deduped, email via notify
# ---------------------------------------------------------------------------


def test_maybe_alert_owner_below_threshold_is_noop(monkeypatch):
    sent_emails: list = []
    monkeypatch.setattr("app.services.notify.smtplib.SMTP", _capturing_smtp(sent_emails))
    conv_id = _seed_conv_costs([0.75])
    with SessionLocal() as session:
        alerted = costs.maybe_alert_owner(
            session, scope="conversation", entity_id=str(conv_id), percent=50.0,
            spend=0.75,
        )
        session.commit()
    assert alerted is False
    assert sent_emails == []
    assert _audit_actions() == []


def test_maybe_alert_owner_fires_once_per_threshold(monkeypatch):
    sent_emails: list = []
    monkeypatch.setattr("app.services.notify.smtplib.SMTP", _capturing_smtp(sent_emails))
    conv_id = _seed_conv_costs([1.20])
    with SessionLocal() as session:
        first = costs.maybe_alert_owner(
            session, scope="conversation", entity_id=str(conv_id), percent=80.0,
            spend=1.20,
        )
        session.commit()
        second = costs.maybe_alert_owner(
            session, scope="conversation", entity_id=str(conv_id), percent=85.0,
            spend=1.28,
        )
        session.commit()
    assert first is True
    assert second is False  # audit-deduped: one alert per crossing
    assert len(sent_emails) == 1
    assert _audit_actions() == ["cost.alert.conversation.80"]


def test_maybe_alert_owner_100_is_separate_alert(monkeypatch):
    sent_emails: list = []
    monkeypatch.setattr("app.services.notify.smtplib.SMTP", _capturing_smtp(sent_emails))
    conv_id = _seed_conv_costs([1.20])
    with SessionLocal() as session:
        costs.maybe_alert_owner(
            session, scope="conversation", entity_id=str(conv_id), percent=80.0,
            spend=1.20,
        )
        session.commit()
        blocked = costs.maybe_alert_owner(
            session, scope="conversation", entity_id=str(conv_id), percent=100.0,
            spend=1.50,
        )
        session.commit()
    assert blocked is True
    assert len(sent_emails) == 2
    assert sorted(_audit_actions()) == [
        "cost.alert.conversation.100",
        "cost.alert.conversation.80",
    ]


def test_maybe_alert_owner_daily_scoped_by_date(monkeypatch):
    """The daily alert is per UTC day: a new day re-alerts (new entity_id)."""
    sent_emails: list = []
    monkeypatch.setattr("app.services.notify.smtplib.SMTP", _capturing_smtp(sent_emails))
    with SessionLocal() as session:
        day1 = costs.maybe_alert_owner(
            session, scope="daily", entity_id="2026-08-13", percent=90.0, spend=4.5
        )
        session.commit()
        day1_again = costs.maybe_alert_owner(
            session, scope="daily", entity_id="2026-08-13", percent=95.0, spend=4.75
        )
        session.commit()
        day2 = costs.maybe_alert_owner(
            session, scope="daily", entity_id="2026-08-14", percent=90.0, spend=4.5
        )
        session.commit()
    assert day1 is True
    assert day1_again is False
    assert day2 is True
    assert len(sent_emails) == 2
    assert _audit_actions().count("cost.alert.daily.80") == 2


# ---------------------------------------------------------------------------
# Part 1 — service: Meta pricing through the settings service (T4.1.1 debt)
# ---------------------------------------------------------------------------


def test_meta_message_cost_uses_stored_settings_value():
    with SessionLocal() as session:
        set_setting(session, "meta_pricing", {"service_message_cost": 0.0234})
        session.commit()
    with SessionLocal() as session:
        assert send.meta_message_cost(session) == pytest.approx(0.0234)


def test_meta_message_cost_falls_back_to_reference_default():
    """No row / malformed dict -> the reference default (SS-4, pre-2026-10-01)."""
    with SessionLocal() as session:
        assert send.meta_message_cost(session) == pytest.approx(send.DEFAULT_META_COST)
    with SessionLocal() as session:
        set_setting(session, "meta_pricing", {"unit_label": "USD/mensaje"})
        session.commit()
    with SessionLocal() as session:
        # a pricing dict without service_message_cost still falls back
        assert send.meta_message_cost(session) == pytest.approx(send.DEFAULT_META_COST)

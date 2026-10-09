"""Functional proof that the development seed supports panel workflows."""

import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Appointment, Case, Conversation, ConversationState, Customer, Message, MessageDirection
from app.panel.seed_dev import MARKER
from app.services.dashboard import compute_kpis, today_projection, trend

REPO_ROOT = Path(__file__).resolve().parents[2]
MARKDOWN = re.compile(r"\*\*|__|^\s*(?:-\s|#)|`|\[[^]]+\]\([^)]+\)", re.MULTILINE)


def test_dev_seed_populates_dashboard_and_composer(migrated_db):
    env = os.environ.copy()
    env.pop("LUMAT_DEMO_SEED", None)
    command = [str(REPO_ROOT / ".venv" / "bin" / "python"), str(REPO_ROOT / "app/panel/seed_dev.py")]
    refused = subprocess.run(command, cwd=REPO_ROOT, env=env, capture_output=True, text=True)
    assert refused.returncode == 1
    assert "Target database:" in refused.stdout
    assert "Demo rows will be replaced." in refused.stdout
    assert "Refusing to write without explicit opt-in: pass --yes or set LUMAT_DEMO_SEED=1.\n" == refused.stderr

    nonlocal_env = env.copy()
    nonlocal_env.update(DATABASE_URL="postgresql+psycopg://user:secret@production.example/db",
        APP_SECRET="test-app-secret", VERIFY_TOKEN="test-verify-token", META_ACCESS_TOKEN="meta-test-token",
        META_PHONE_NUMBER_ID="123456789", PANEL_SESSION_SECRET="test-panel-session-secret")
    blocked = subprocess.run([*command, "--yes"], cwd=REPO_ROOT, env=nonlocal_env, capture_output=True, text=True)
    assert blocked.returncode == 1
    assert blocked.stdout == "Target database: postgresql+psycopg://user:***@production.example/db\nDemo rows will be replaced.\n"
    assert blocked.stderr == "Refusing to write to a non-development host: pass --allow-nonlocal to override this host check.\n"

    result = subprocess.run([*command, "--yes"], cwd=REPO_ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    def seeded_counts(session):
        customer_ids = select(Customer.id).where(Customer.phone_e164.like(f"+{MARKER}%"))
        conversation_ids = select(Conversation.id).where(Conversation.customer_id.in_(customer_ids))
        case_ids = select(Case.id).where(Case.customer_id.in_(customer_ids))
        return (
            session.scalar(select(func.count()).select_from(Conversation).where(Conversation.customer_id.in_(customer_ids))),
            session.scalar(select(func.count()).select_from(Message).where(Message.conversation_id.in_(conversation_ids))),
            session.scalar(select(func.count()).select_from(Case).where(Case.customer_id.in_(customer_ids))),
            session.scalar(select(func.count()).select_from(Appointment).where(Appointment.case_id.in_(case_ids))),
            session.scalar(select(func.count()).select_from(Customer).where(Customer.phone_e164.like(f"+{MARKER}%"))),
        )

    with SessionLocal() as session:
        counts = seeded_counts(session)
        assert counts == (12, 35, 12, 6, 12)
        assert all(not MARKDOWN.search(summary) for summary in session.scalars(
            select(Conversation.summary).join(Customer).where(Customer.phone_e164.like(f"+{MARKER}%"))
        ).all() if summary)
        assert all(not MARKDOWN.search(summary) for summary in session.scalars(select(Case.summary).join(Customer).where(Customer.phone_e164.like(f"+{MARKER}%"))).all() if summary)
        conversations = session.scalars(select(Conversation).join(Customer).where(Customer.phone_e164.like(f"+{MARKER}%"))).all()
        now = datetime.now(timezone.utc)
        human_recent = False
        bot_unanswered = False
        for conversation in conversations:
            messages = session.scalars(select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at)).all()
            if conversation.state == ConversationState.HUMAN:
                inbound = [message.created_at for message in messages if message.direction == MessageDirection.INBOUND]
                human_recent |= bool(inbound and max(inbound) >= now - timedelta(hours=24))
            if conversation.state == ConversationState.BOT and messages:
                bot_unanswered |= messages[-1].direction == MessageDirection.INBOUND
        assert human_recent
        assert bot_unanswered

    rerun = subprocess.run([*command, "--yes"], cwd=REPO_ROOT, env=env, capture_output=True, text=True)
    assert rerun.returncode == 0, f"{rerun.stdout}\n{rerun.stderr}"
    with SessionLocal() as session:
        assert seeded_counts(session) == counts
        for days in (7, 14, 30):
            kpis = compute_kpis(session, days)
            assert kpis["contacts"] > 0 and kpis["derived"] > 0 and kpis["visit_requests"] > 0 and kpis["motivos"]
            end = datetime.now(timezone.utc)
            buckets = trend(session, end - timedelta(days=days), end, "America/Santiago", "contacts")["buckets"]
            assert sum(bucket["count"] for bucket in buckets) > 0
        projection = today_projection(session, "America/Santiago")
        assert projection["appointments_today"]
        assert projection["unanswered_conversations"]
        assert projection["urgent_cases"]

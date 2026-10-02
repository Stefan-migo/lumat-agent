"""Functional proof that the dashboard demo seed satisfies its read predicates."""

import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Appointment, Case, Conversation, Customer, Message
from app.panel.seed_demo import MARKER
from app.services.dashboard import compute_kpis, today_projection, trend

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_demo_seed_populates_dashboard_windows_and_today(migrated_db):
    env = os.environ.copy()
    env.pop("LUMAT_DEMO_SEED", None)
    command = [str(REPO_ROOT / ".venv" / "bin" / "python"), str(REPO_ROOT / "app/panel/seed_demo.py")]
    refused = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert refused.returncode == 1
    assert "Target database:" in refused.stdout
    assert "Demo rows will be replaced." in refused.stdout
    assert "Refusing to write without explicit opt-in" in refused.stderr

    nonlocal_env = env.copy()
    nonlocal_env["DATABASE_URL"] = "postgresql+psycopg://user:secret@production.example/db"
    nonlocal_env.update(
        APP_SECRET="test-app-secret",
        VERIFY_TOKEN="test-verify-token",
        META_ACCESS_TOKEN="meta-test-token",
        META_PHONE_NUMBER_ID="123456789",
        PANEL_SESSION_SECRET="test-panel-session-secret",
    )
    nonlocal_refused = subprocess.run(
        [*command, "--yes"], cwd=REPO_ROOT, env=nonlocal_env, capture_output=True, text=True
    )
    assert nonlocal_refused.returncode == 1
    assert nonlocal_refused.stdout == (
        "Target database: postgresql+psycopg://user:***@production.example/db\n"
        "Demo rows will be replaced.\n"
    )
    assert nonlocal_refused.stderr == (
        "Refusing to write to a non-development host: pass --allow-nonlocal to override this host check.\n"
    )

    result = subprocess.run(
        [*command, "--yes"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert "Target database: postgresql+psycopg://app:***@localhost:" in result.stdout
    assert "Demo rows will be replaced." in result.stdout

    def seeded_counts(session):
        customer_ids = select(Customer.id).where(Customer.phone_e164.like(f"+{MARKER}%"))
        conversation_ids = select(Conversation.id).where(Conversation.customer_id.in_(customer_ids))
        case_ids = select(Case.id).where(Case.customer_id.in_(customer_ids))
        return (
            session.scalar(select(func.count()).select_from(Conversation).where(Conversation.customer_id.in_(customer_ids))),
            session.scalar(select(func.count()).select_from(Message).where(Message.conversation_id.in_(conversation_ids))),
            session.scalar(select(func.count()).select_from(Case).where(Case.customer_id.in_(customer_ids))),
            session.scalar(select(func.count()).select_from(Appointment).where(Appointment.case_id.in_(case_ids))),
        )

    with SessionLocal() as session:
        first_run_counts = seeded_counts(session)
    assert first_run_counts == (30, 30, 30, 1)

    rerun = subprocess.run(
        [*command, "--yes"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert rerun.returncode == 0, f"{rerun.stdout}\n{rerun.stderr}"

    with SessionLocal() as session:
        assert seeded_counts(session) == first_run_counts

        for days in (7, 14, 30):
            kpis = compute_kpis(session, days)
            assert kpis["contacts"] > 0, (days, kpis)
            assert kpis["derived"] > 0, (days, kpis)
            assert kpis["visit_requests"] > 0, (days, kpis)
            assert kpis["motivos"], (days, kpis)
            end = datetime.now(timezone.utc)
            buckets = trend(
                session,
                end - timedelta(days=days),
                end,
                "America/Santiago",
                "contacts",
            )["buckets"]
            assert sum(bucket["count"] for bucket in buckets) > 0, (days, buckets)

        projection = today_projection(session, "America/Santiago")
        assert projection["appointments_today"]
        assert projection["unanswered_conversations"]
        assert projection["urgent_cases"]

        seeded_customers = session.scalar(
            select(func.count()).select_from(Customer).where(
                Customer.phone_e164.like(f"+{MARKER}%")
            )
        )
        assert seeded_customers == 30

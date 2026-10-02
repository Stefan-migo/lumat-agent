"""Functional proof that the dashboard demo seed satisfies its read predicates."""

import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Customer
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

    result = subprocess.run(
        [*command, "--yes"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    rerun = subprocess.run(
        [*command, "--yes"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert rerun.returncode == 0, f"{rerun.stdout}\n{rerun.stderr}"

    with SessionLocal() as session:
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
                Customer.phone_e164.like("+5690000000%")
            )
        )
        assert seeded_customers == 30

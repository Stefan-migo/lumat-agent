"""Build a plain-text operational digest for the administrator."""

import argparse
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.chat.nodes.respond import list_unresolved_questions
from app.db import session_scope
from app.services import cases, costs


def build_digest(session: Session, *, period: str, now: datetime) -> str:
    """Return a plain-text operational digest for the admin."""
    if period not in {"daily", "weekly"}:
        raise ValueError("period must be 'daily' or 'weekly'")

    open_cases = len(cases.list_open_cases(session))
    unresolved_questions = len(list_unresolved_questions(session))
    if period == "daily":
        spend = costs.daily_spend(session, now.date())
        period_label = "diario"
    else:
        spend = sum(
            costs.daily_spend(session, now.date() - timedelta(days=offset))
            for offset in range(7)
        )
        period_label = "semanal"

    if not open_cases and not unresolved_questions and not spend:
        return f"Resumen {period_label}\nSin novedades para el período."

    amount = f"{spend:.6f}".rstrip("0").rstrip(".") or "0"
    return "\n".join((
        f"Resumen {period_label}",
        f"Casos abiertos: {open_cases}",
        f"Preguntas sin resolver: {unresolved_questions}",
        f"Gasto registrado: {amount}",
    ))


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description="Print the daily operational digest").parse_args(argv)
    with session_scope() as session:
        print(build_digest(session, period="daily", now=datetime.now(timezone.utc)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

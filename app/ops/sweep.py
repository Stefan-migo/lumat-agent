"""Bounded operational sweep entry point."""

from app.services.notifications import sweep_due_operations


def run(limit: int = 50) -> int:
    return sweep_due_operations(limit=limit)

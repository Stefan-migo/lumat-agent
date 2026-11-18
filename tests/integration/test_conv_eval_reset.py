"""`conv_eval.py --reset` must empty conversation state and nothing else.

The instrument truncates tables, so the failure that motivates this file is
structural: `TRUNCATE` refuses to run when a table outside the list points at one
inside it. That is deliberate (no `CASCADE`), and it means a new foreign key is
enough to break the reset even with no rows in the database.

Measured 2026-11-18: `commitments` referenced `messages` while `_RESET_TABLES` did
not name it, and every `--reset` run died with
`psycopg.errors.FeatureNotSupported: cannot truncate a table referenced in a
foreign key constraint` before the first scenario.
"""

import psycopg
import pytest
from sqlalchemy import func, select

from _testdb import admin_database_url

from app.db import SessionLocal
from app.models import Conversation, Customer, Settings
from app.services.customers import get_or_create_customer
from app.chat.state import get_or_create_conversation

ADMIN_DB_URL = admin_database_url()
PHONE = "+56912340001"


def _conv_eval():
    """Import the script module without importing `main`."""
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root / "scripts") not in sys.path:
        sys.path.insert(0, str(repo_root / "scripts"))
    import conv_eval

    return conv_eval


@pytest.fixture
def seeded(migrated_db):
    """One customer, one conversation and one setting, all before the reset."""
    with SessionLocal() as session:
        customer = get_or_create_customer(session, PHONE)
        get_or_create_conversation(session, customer, PHONE)
        session.merge(Settings(key="reset.probe", value="kept"))
        session.commit()
    yield
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute("TRUNCATE conversations, customers RESTART IDENTITY CASCADE")


def test_reset_empties_the_conversation_state(seeded):
    conv_eval = _conv_eval()

    tables = conv_eval.reset_business_state(ADMIN_DB_URL)

    assert "customers" in tables
    with SessionLocal() as session:
        assert session.scalar(select(func.count(Customer.id))) == 0
        assert session.scalar(select(func.count(Conversation.id))) == 0


def test_reset_keeps_the_configuration_the_next_run_needs(seeded):
    conv_eval = _conv_eval()

    conv_eval.reset_business_state(ADMIN_DB_URL)

    with SessionLocal() as session:
        kept = session.get(Settings, "reset.probe")
    assert kept is not None and kept.value == "kept"

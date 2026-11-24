"""The instrument relaxes its own session, never the database's guard.

Migration `070_session_safety` leaves `idle_in_transaction_session_timeout = 180s`
as the **database default**, because on 2026-11-21 a wedged assistant turn held
locks for sixteen minutes and the whole panel answered 500. That guard has to
live where the wedged process cannot bypass it.

The harness is the opposite case: a conversation turn is a transaction that spans
the model call *on purpose*, so a scenario longer than three minutes has its
connection killed by that same guard and is recorded as unmeasured — and the next
scenario fails in cascade. Measured 2026-11-23 (`odd/tasks/chatbot-conv-eval.md`
L20): `real-revision-bano-ruidoso` unmeasured by timeout,
`real-caldera-urgencia` unmeasured behind it.

So the fix is not `ALTER DATABASE` (that broke the guard's own test) and not a
shorter scenario: it is the instrument relaxing its own session options, which
this file pins from both sides — the harness's sessions get the long window, and
the database-level guard does not move.
"""

import psycopg

from _testdb import database_url, libpq_database_url

GUARD_QUERY = (
    "SELECT setconfig FROM pg_db_role_setting WHERE setdatabase = "
    "(SELECT oid FROM pg_database WHERE datname = current_database())"
)


def _conv_eval():
    """Import the script module without running it (same seam as the reset tests)."""
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root / "scripts") not in sys.path:
        sys.path.insert(0, str(repo_root / "scripts"))
    import conv_eval

    return conv_eval


def _database_guard() -> list[str]:
    with psycopg.connect(libpq_database_url(database_url())) as connection:
        (setconfig,) = connection.execute(GUARD_QUERY).fetchone()
    return list(setconfig)


def test_the_harness_relaxes_its_own_window_and_leaves_the_database_guard_alone(monkeypatch):
    """Both halves in one test on purpose: asking for a longer window is only
    correct while the guard a wedged process would hit still reads 180s."""
    module = _conv_eval()
    monkeypatch.delenv("PGOPTIONS", raising=False)

    from app.db import engine

    engine.dispose()
    assert module.session_idle_timeout_measurement() == (180.0, "database")

    module.relax_session_idle_timeout()
    # The pool only re-reads libpq options when it opens a new connection.
    engine.dispose()

    assert module.session_idle_timeout_measurement() == (900.0, "client")
    assert _database_guard() == ["idle_in_transaction_session_timeout=180s"]


def test_the_harness_reports_the_window_it_actually_got(monkeypatch):
    """The seal is the only thing that can tell a relaxed run from a killed one."""
    module = _conv_eval()
    monkeypatch.delenv("PGOPTIONS", raising=False)
    module.relax_session_idle_timeout()

    from app.db import engine

    engine.dispose()

    assert module.session_idle_timeout_seconds() == 900.0

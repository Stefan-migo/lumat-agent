"""S3 — the connection pool is sized by the environment, not by a hardcoded default.

The pool was `create_engine(url, pool_pre_ping=True)`, which is SQLAlchemy's
5 + 10 with a 30 s checkout wait. On 2026-11-21 fourteen queued turns were enough
to take every database-touching panel endpoint down with `QueuePool limit ...
reached`, and the operator had no way to widen it without editing code.
"""

from app.config import Settings


def test_pool_limits_come_from_the_environment(monkeypatch):
    monkeypatch.setenv("DB_POOL_SIZE", "7")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "3")
    monkeypatch.setenv("DB_POOL_TIMEOUT", "2.5")
    monkeypatch.setenv("DB_POOL_RECYCLE", "120")

    settings = Settings()

    assert settings.db_pool_size == 7
    assert settings.db_max_overflow == 3
    assert settings.db_pool_timeout == 2.5
    assert settings.db_pool_recycle == 120


def test_pool_defaults_leave_room_for_concurrent_turns():
    settings = Settings()

    # 5 + 10 was the entire pool: a handful of concurrent long turns was the
    # whole failure. 10 + 20 gives the API headroom and still sits far inside
    # the database's max_connections = 100.
    assert (settings.db_pool_size, settings.db_max_overflow) == (10, 20)
    # A request that cannot get a connection should fail while the operator is
    # still watching it, not after the driver's 30 s.
    assert settings.db_pool_timeout == 10.0
    # Recycle periodically so a long-lived connection eventually inherits a
    # database-level default changed underneath it (the 180 s idle guard).
    assert settings.db_pool_recycle == 1800

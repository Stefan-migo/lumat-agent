"""Database engine, session factory and declarative base (design: app/db.py).

Engine/session read `DATABASE_URL` from the env-only Settings (SH-2: secrets
never in the repo; the URL carries the `app` role credentials at runtime).
Migrations are applied by `db/migrate.sh`; SQLAlchemy never auto-creates the
schema (migrations are the source of truth).
"""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

def _pool_options(database_url: str, settings) -> dict:
    """QueuePool sizing, for the dialects that actually pool that way.

    The sizing is environment-driven because the 2026-11-21 exhaustion was only
    recoverable by editing code: SQLAlchemy's 5 + 10 with a 30 s checkout wait
    was fully consumed by a handful of queued turns.

    A non-PostgreSQL URL (the KB drift CLI imports this module with sqlite on
    purpose, because it must run without a database) is served by a pool class
    that rejects these arguments outright, so they are only sent where they
    apply.
    """
    if not database_url.startswith("postgresql"):
        return {"pool_recycle": settings.db_pool_recycle}
    return {
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
        "pool_timeout": settings.db_pool_timeout,
        "pool_recycle": settings.db_pool_recycle,
    }


_settings = get_settings()

engine = create_engine(
    _settings.database_url,
    pool_pre_ping=True,
    **_pool_options(_settings.database_url, _settings),
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def release_transaction(session: Session | None) -> None:
    """Commit pending work before external I/O, so no lock and no connection wait with it.

    A turn that keeps a transaction open while it waits on a provider or on a
    tool holds its row locks and one pooled connection for the whole wait. On
    2026-11-21 that lasted sixteen minutes: every writer queued behind it, the
    waiters exhausted the pool (5 + 10) and the panel answered 500 everywhere.
    """
    if session is None or not session.in_transaction():
        return
    session.commit()


class Base(DeclarativeBase):
    """Declarative base for all ORM models (mapped to the migrated schema)."""


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Context manager yielding a committed-on-success session (rollback on error)."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
        from app.services.realtime import dispatch_staged_events

        dispatch_staged_events(session)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

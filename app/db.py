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

engine = create_engine(get_settings().database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


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

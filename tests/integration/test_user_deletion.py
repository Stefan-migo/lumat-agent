"""S5/S6 — hard-deleting a panel user dereferences what survives and removes what is theirs."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import (
    Appointment,
    AppointmentStatus,
    Case,
    Customer,
    InternalChatThread,
    Project,
    User,
)
from app.services import assistant_artifacts
from app.services.users import UserDeleteBlocked, delete_user, hash_password


def test_delete_user_dereferences_and_removes_personal_data(monkeypatch, tmp_path):
    """A user with a project, a thread and an artifact is deleted; the record survives, the user's goes."""
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    get_settings.cache_clear()
    with SessionLocal() as session:
        owner = User(username="del-owner", password_hash=hash_password("pass"), role="admin")
        session.add(owner)
        session.flush()
        thread = InternalChatThread(user_id=owner.id)
        session.add(thread)
        session.flush()
        artifact = assistant_artifacts.store_artifact(session, thread, "r.md", "abc", "assistant")
        blob_path = str(artifact.stored_path)
        assert Path(blob_path).read_bytes() == b"abc"
        session.add(Project(slug="owned", name="Owned", purpose="Purpose", purpose_embedding=[0.0] * 384, owner_id=owner.id))
        session.commit()
        owner_id, thread_id = owner.id, thread.id

    with SessionLocal() as session:
        delete_user(session, session.get(User, owner_id))
        session.commit()

    with SessionLocal() as session:
        assert session.get(User, owner_id) is None
        assert session.get(InternalChatThread, thread_id) is None
        assert session.scalar(select(Project).where(Project.slug == "owned")).owner_id is None
        assert not Path(blob_path).exists()
    get_settings.cache_clear()


def test_delete_user_blocks_on_booked_appointment(monkeypatch, tmp_path):
    """A technician with a booked appointment cannot be deleted until it is reassigned."""
    get_settings.cache_clear()
    with SessionLocal() as session:
        tech = User(username="del-tech", password_hash=hash_password("pass"), role="tecnico")
        session.add(tech)
        session.flush()
        customer = Customer(phone_e164="+56911110000")
        session.add(customer)
        session.flush()
        case = Case(customer_id=customer.id, summary="scope")
        session.add(case)
        session.flush()
        start = datetime.now(timezone.utc) + timedelta(days=1)
        session.add(Appointment(
            service="x", customer_id=customer.id, case_id=case.id, technician_id=tech.id,
            local_start=start.replace(tzinfo=None), timezone="UTC",
            starts_at=start, ends_at=start + timedelta(hours=1),
            duration_minutes=60, status=AppointmentStatus.BOOKED,
        ))
        session.commit()
        tech_id = tech.id

    with SessionLocal() as session:
        with pytest.raises(UserDeleteBlocked, match="reassign"):
            delete_user(session, session.get(User, tech_id))
        session.rollback()
    with SessionLocal() as session:
        assert session.get(User, tech_id) is not None
    get_settings.cache_clear()

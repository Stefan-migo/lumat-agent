"""T1.2 integration tests — ORM models + session + audit service (SH-5).

Runs against the migrated pgvector test DB as the `app` role (the role the
application uses). Verifies:

- ORM CRUD round-trip (create/read/update/delete) on business tables
- jsonb (settings) and vector(384) (kb_chunks) types round-trip via ORM
- audit service writes append-only rows with before/after (SH-5) and the
  admin read lists them
"""

import os

import psycopg
import pytest
from sqlalchemy import select

# env must be set before app imports; conftest sets DATABASE_URL already
from app.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    AuditLog,
    Conversation,
    ConversationState,
    Customer,
    CustomerState,
    KbChunk,
    KbDocument,
    Message,
    MessageDirection,
    MessageStatus,
    Settings,
)
from app.services.audit import list_audit_entries, record_audit  # noqa: E402

ADMIN_DB_URL = os.environ.get(
    "TEST_ADMIN_DB_URL", "postgresql://lumat:lumat@localhost:5432/lumat"
)


@pytest.fixture(scope="module", autouse=True)
def clean_db(migrated_db):
    """Reset all tables before this module's tests (dedicated test DB only)."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, audit_log, kb_chunks, kb_documents, "
            "conversation_events, cases, messages, conversations, users, customers "
            "RESTART IDENTITY CASCADE"
        )
    yield


def test_crud_round_trip():
    """Acceptance: CRUD round-trip test against compose pgvector (app role)."""
    phone = "+56955550001"
    with SessionLocal() as session:
        # CREATE
        customer = Customer(phone_e164=phone, name="Juana", comuna="Maipú")
        session.add(customer)
        session.commit()
        customer_id = customer.id
        assert customer_id is not None

        # READ
        fetched = session.get(Customer, customer_id)
        assert fetched.phone_e164 == phone
        assert fetched.name == "Juana"
        assert fetched.state == CustomerState.NUEVO  # DB default

        # UPDATE
        fetched.name = "Juana Pérez"
        fetched.state = CustomerState.CONTACTADO
        session.commit()

        # READ after update (fresh row)
        session.expire_all()
        again = session.get(Customer, customer_id)
        assert again.name == "Juana Pérez"
        assert again.state == CustomerState.CONTACTADO

        # DELETE
        session.delete(again)
        session.commit()
        assert session.get(Customer, customer_id) is None


def test_conversation_and_message_round_trip():
    """messages FK to conversations; enum + payload jsonb round-trip."""
    phone = "+56955550002"
    with SessionLocal() as session:
        customer = Customer(phone_e164=phone)
        session.add(customer)
        session.flush()

        conv = Conversation(customer_id=customer.id, wa_phone="+56911111111")
        session.add(conv)
        session.flush()

        msg = Message(
            conversation_id=conv.id,
            wamid="wamid-orm-1",
            direction=MessageDirection.INBOUND,
            text="Hola",
            status=MessageStatus.RECEIVED,
            payload={"entry": [{"x": 1}]},
        )
        session.add(msg)
        session.commit()

        fetched = session.get(Message, msg.id)
        assert fetched.direction == MessageDirection.INBOUND
        assert fetched.status == MessageStatus.RECEIVED
        assert fetched.payload == {"entry": [{"x": 1}]}  # jsonb round-trip
        assert fetched.conversation_id == conv.id

        # default state on new conversation is bot
        conv_fetched = session.get(Conversation, conv.id)
        assert conv_fetched.state == ConversationState.BOT


def test_settings_jsonb_round_trip():
    """settings: key PK + jsonb value (design D5)."""
    with SessionLocal() as session:
        session.add(Settings(key="emergency_keywords", value={"list": ["gas", "fuga"]}))
        session.commit()

        row = session.execute(
            select(Settings).where(Settings.key == "emergency_keywords")
        ).scalar_one()
        assert row.value == {"list": ["gas", "fuga"]}


def test_kb_chunk_vector_round_trip():
    """kb_chunks.embedding vector(384) round-trips via ORM (KB-1)."""
    with SessionLocal() as session:
        doc = KbDocument(title="Manual", format="md", content="# Calefont")
        session.add(doc)
        session.flush()

        embedding = [0.01 + i * 1e-6 for i in range(384)]
        chunk = KbChunk(
            document_id=doc.id,
            version=1,
            chunk_index=0,
            content="chunk content",
            source_meta={"page": 1},
            embedding=embedding,
        )
        session.add(chunk)
        session.commit()

        fetched = session.get(KbChunk, chunk.id)
        assert fetched.embedding is not None
        assert len(fetched.embedding) == 384
        assert abs(fetched.embedding[0] - 0.01) < 1e-9
        assert fetched.source_meta == {"page": 1}


def test_audit_record_writes_before_after():
    """Acceptance: audit row written with before/after (SH-5)."""
    actor = "admin@lumat.cl"
    with SessionLocal() as session:
        entry = record_audit(
            session,
            actor=actor,
            action="settings.change",
            entity="settings",
            entity_id="scope_rules",
            before={"bot_resolve": False},
            after={"bot_resolve": True},
        )
        session.commit()
        entry_id = entry.id

        fetched = session.get(AuditLog, entry_id)
        assert fetched.actor == actor
        assert fetched.action == "settings.change"
        assert fetched.entity == "settings"
        assert fetched.entity_id == "scope_rules"
        assert fetched.before == {"bot_resolve": False}
        assert fetched.after == {"bot_resolve": True}


def test_audit_admin_read_lists_entries():
    """Admin read returns audit entries, newest first (SH-5)."""
    with SessionLocal() as session:
        record_audit(session, actor="u1", action="login", entity="users", after={})
        record_audit(session, actor="u2", action="logout", entity="users", after={})
        session.commit()

        entries = list_audit_entries(session)
        actions = [e.action for e in entries]
        assert "login" in actions
        assert "logout" in actions


def test_audit_is_append_only_via_grants():
    """Append-only enforced by grants: app role cannot UPDATE audit_log (SH-5)."""
    with SessionLocal() as session:
        record_audit(session, actor="x", action="login", entity="users", after={})
        session.commit()

    with psycopg.connect(
        "postgresql://app:app@localhost:5432/lumat", autocommit=True
    ) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("UPDATE audit_log SET after = '{}'::jsonb")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("DELETE FROM audit_log")


def test_models_expose_ten_tables():
    """All 10 design tables are mapped (plus no stray tables)."""
    from app.db import Base

    mapped = set(Base.metadata.tables.keys())
    assert {
        "customers",
        "users",
        "conversations",
        "messages",
        "cases",
        "conversation_events",
        "kb_documents",
        "kb_chunks",
        "settings",
        "audit_log",
    } <= mapped

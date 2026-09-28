"""T3.1 integration tests — customers service (CR-1..CR-6).

Scenarios mapped 1:1 from openspec/specs/customer-records/spec.md:

- CR-1 "First contact creates ficha": unknown phone -> customer row created
- CR-2 "Known customer returns" / "Different formatting": E.164 dedup
  (+56 9... vs 9... vs +569...)
- CR-3 "State progression" / "Invalid transition rejected": lifecycle enum +
  transition validation + audit on change
- CR-4 "Staff adds note": internal notes with author + timestamp
- CR-5 "History complete": conversations/cases/messages linked chronologically
- CR-6 "Captured data persisted": captured fields + consent stored on the ficha

Runs against the migrated pgvector test DB (conftest DATABASE_URL).
"""

import psycopg
import pytest
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy import func, select

from app.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Appointment,
    AuditLog,
    Case,
    Conversation,
    ConversationState,
    Customer,
    CustomerNote,
    CustomerEquipment,
    Memory,
    MemoryObservation,
    MemoryRelation,
    MemoryType,
    CustomerState,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
    User,
    UserRole,
)
from app.services import customers  # noqa: E402
from _testdb import admin_database_url  # noqa: E402

ADMIN_DB_URL = admin_database_url()


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    """Reset all customer-related tables before every test (shared test DB)."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE audit_log, conversation_events, memory_relations, "
            "memory_observations, memories, appointments, customer_equipment, "
            "cases, messages, conversations, customer_notes, customers, users "
            "RESTART IDENTITY CASCADE"
        )
    yield


def _count_customers() -> int:
    with SessionLocal() as session:
        return session.scalar(select(func.count(Customer.id)))


# ---------------------------------------------------------------------------
# CR-1 — Auto-Ficha on First Contact
# ---------------------------------------------------------------------------


def test_cr1_first_contact_creates_ficha():
    with SessionLocal() as session:
        customer = customers.get_or_create_customer(session, "56912345678")
        session.commit()
        assert customer.id is not None
        assert customer.phone_e164 == "+56912345678"
        assert customer.state == CustomerState.NUEVO
        assert customer.created_at is not None  # date/time registered


def test_cr1_unknown_phone_creates_exactly_one_row():
    assert _count_customers() == 0
    with SessionLocal() as session:
        customers.get_or_create_customer(session, "56987654321")
        session.commit()
    assert _count_customers() == 1


# ---------------------------------------------------------------------------
# CR-2 — Phone-Based Deduplication
# ---------------------------------------------------------------------------


def test_cr2_same_number_reuses_record():
    with SessionLocal() as session:
        first = customers.get_or_create_customer(session, "56912345678")
        second = customers.get_or_create_customer(session, "56912345678")
        session.commit()
        assert first.id == second.id
    assert _count_customers() == 1


def test_cr2_full_international_format_dedups():
    with SessionLocal() as session:
        first = customers.get_or_create_customer(session, "+56912345678")
        second = customers.get_or_create_customer(session, "56912345678")
        session.commit()
        assert first.id == second.id
    assert _count_customers() == 1


def test_cr2_different_formatting_dedups():
    """'+56 9 1234 5678' and Chilean local '912345678' hit the same ficha."""
    with SessionLocal() as session:
        spaced = customers.get_or_create_customer(session, "+56 9 1234 5678")
        local = customers.get_or_create_customer(session, "912345678")
        session.commit()
        assert spaced.id == local.id
    assert _count_customers() == 1


def test_cr2_empty_phone_rejected():
    with SessionLocal() as session:
        with pytest.raises(ValueError):
            customers.get_or_create_customer(session, "")


# ---------------------------------------------------------------------------
# CR-3 — Lifecycle States + Transition Validation
# ---------------------------------------------------------------------------


def test_cr3_valid_transition_updates_state():
    with SessionLocal() as session:
        customer = customers.get_or_create_customer(session, "56912345678")
        customers.set_customer_state(
            session, customer, CustomerState.PENDIENTE, actor="operador1"
        )
        session.commit()
        assert customer.state == CustomerState.PENDIENTE


def test_cr3_invalid_transition_rejected():
    with SessionLocal() as session:
        customer = customers.get_or_create_customer(session, "56912345678")
        with pytest.raises(customers.InvalidStateTransition):
            customers.set_customer_state(
                session, customer, CustomerState.POSTVENTA, actor="operador1"
            )
        session.rollback()
        assert customer.state == CustomerState.NUEVO  # unchanged


def test_cr3_postventa_reachable_only_after_finalizado():
    with SessionLocal() as session:
        customer = customers.get_or_create_customer(session, "56912345678")
        customers.set_customer_state(
            session, customer, CustomerState.AGENDADO, actor="operador1"
        )
        customers.set_customer_state(
            session, customer, CustomerState.FINALIZADO, actor="operador1"
        )
        customers.set_customer_state(
            session, customer, CustomerState.POSTVENTA, actor="operador1"
        )
        session.commit()
        assert customer.state == CustomerState.POSTVENTA


def test_cr3_state_change_audited():
    with SessionLocal() as session:
        customer = customers.get_or_create_customer(session, "56912345678")
        customers.set_customer_state(
            session, customer, CustomerState.AGENDADO, actor="operador1"
        )
        session.commit()
    from app.models import AuditLog

    with SessionLocal() as session:
        entry = session.scalar(select(AuditLog).order_by(AuditLog.id.desc()))
        assert entry is not None
        assert entry.actor == "operador1"
        assert entry.action == "customer.state_change"
        assert entry.entity == "customer"
        assert entry.before == {"state": "nuevo"}
        assert entry.after == {"state": "agendado"}


# ---------------------------------------------------------------------------
# CR-4 — Internal Notes
# ---------------------------------------------------------------------------


def test_cr4_add_note_stores_author_and_timestamp():
    with SessionLocal() as session:
        customer = customers.get_or_create_customer(session, "56912345678")
        note = customers.add_note(
            session, customer.id, "Cliente pide visita el viernes", actor="operador1"
        )
        session.commit()
        assert note.note == "Cliente pide visita el viernes"
        assert note.author == "operador1"
        assert note.created_at is not None


def test_cr4_list_notes_chronological():
    with SessionLocal() as session:
        customer = customers.get_or_create_customer(session, "56912345678")
        customers.add_note(session, customer.id, "primera", actor="operador1")
        customers.add_note(session, customer.id, "segunda", actor="admin")
        session.commit()
        notes = customers.list_notes(session, customer.id)
        assert [n.note for n in notes] == ["primera", "segunda"]
        assert [n.author for n in notes] == ["operador1", "admin"]


def test_cr4_notes_are_staff_only_no_customer_exposure():
    """Notes are internal: no column on the customer record exposes them."""
    with SessionLocal() as session:
        customer = customers.get_or_create_customer(session, "56912345678")
        customers.add_note(session, customer.id, "interna", actor="operador1")
        session.commit()
        stored = session.get(Customer, customer.id)
        assert not hasattr(stored, "note")
        assert session.scalar(select(func.count(CustomerNote.id))) == 1


# ---------------------------------------------------------------------------
# CR-5 — History Linkage
# ---------------------------------------------------------------------------


def _seed_history(session) -> Customer:
    customer = customers.get_or_create_customer(session, "56912345678")
    conv1 = Conversation(
        customer_id=customer.id, wa_phone="56912345678", state=ConversationState.CLOSED
    )
    conv2 = Conversation(customer_id=customer.id, wa_phone="56912345678")
    session.add_all([conv1, conv2])
    session.flush()
    session.add_all(
        [
            Message(
                conversation_id=conv1.id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text="hola",
                status=MessageStatus.PROCESSED,
            ),
            Message(
                conversation_id=conv1.id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text="segundo",
                status=MessageStatus.PROCESSED,
            ),
            Message(
                conversation_id=conv2.id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text="nuevo tema",
                status=MessageStatus.PROCESSED,
            ),
        ]
    )
    session.add(
        Case(
            conversation_id=conv2.id,
            customer_id=customer.id,
            service="calefont",
            priority="media",
            status="abierto",
        )
    )
    return customer


def test_cr5_history_lists_conversations_cases_messages():
    with SessionLocal() as session:
        customer = _seed_history(session)
        session.commit()
        history = customers.customer_history(session, customer.id)
        assert len(history["conversations"]) == 2
        assert len(history["cases"]) == 1
        case = history["cases"][0]
        assert case["service"] == "calefont"
        assert set(case) == {
            "id", "conversation_id", "customer_id", "created_at", "service",
            "amount", "priority", "status", "summary", "emergency", "responsible_id",
            "escalated_at", "closed_at", "acknowledged_at", "ack_by", "is_open",
        }
        assert case["customer_id"] == customer.id
        assert case["is_open"] is True
        assert len(history["messages"]) == 3
        assert [m["text"] for m in history["messages"]] == [
            "hola",
            "segundo",
            "nuevo tema",
        ]  # chronological
        assert {m["conversation_id"] for m in history["messages"]} == {
            history["conversations"][0]["id"],
            history["conversations"][1]["id"],
        }


# ---------------------------------------------------------------------------
# CR-6 — Data and Consent Recording
# ---------------------------------------------------------------------------


def test_cr6_captured_data_persisted_on_ficha():
    with SessionLocal() as session:
        customer = customers.get_or_create_customer(session, "56912345678")
        customers.update_captured_data(
            session,
            customer,
            name="Juan Pérez",
            email="juan@example.com",
            comuna="Providencia",
            address="Av. Siempre Viva 123",
        )
        session.commit()
        stored = session.get(Customer, customer.id)
        assert stored.name == "Juan Pérez"
        assert stored.email == "juan@example.com"
        assert stored.comuna == "Providencia"
        assert stored.address == "Av. Siempre Viva 123"


def test_cr6_consent_recorded_with_timestamp():
    with SessionLocal() as session:
        customer = customers.get_or_create_customer(session, "56912345678")
        customers.record_consent(session, customer, consent=True)
        session.commit()
        stored = session.get(Customer, customer.id)
        assert stored.consent_status is True
        assert stored.consent_at is not None


def test_cr6_consent_withdrawn():
    with SessionLocal() as session:
        customer = customers.get_or_create_customer(session, "56912345678")
        customers.record_consent(session, customer, consent=True)
        customers.record_consent(session, customer, consent=False)
        session.commit()
        stored = session.get(Customer, customer.id)
        assert stored.consent_status is False


def test_archived_customer_hidden_by_default_and_included_on_request():
    with SessionLocal() as session:
        active = customers.get_or_create_customer(session, "56912345678")
        archived = customers.get_or_create_customer(session, "56987654321")
        customers.archive_customer(session, archived, actor="operador1")
        session.commit()

        assert [c.id for c in customers.search_customers(session)] == [active.id]
        assert {c.id for c in customers.search_customers(session, include_archived=True)} == {
            active.id, archived.id
        }


def test_archive_and_unarchive_are_audited_and_idempotent():
    from app.models import AuditLog

    with SessionLocal() as session:
        customer = customers.get_or_create_customer(session, "56912345678")
        customers.archive_customer(session, customer, actor="operador1")
        archived_at = customer.archived_at
        customers.archive_customer(session, customer, actor="operador2")
        assert customer.archived_at == archived_at
        customers.unarchive_customer(session, customer, actor="operador1")
        customers.unarchive_customer(session, customer, actor="operador2")
        session.commit()

        audits = session.scalars(
            select(AuditLog).where(AuditLog.entity_id == str(customer.id))
        ).all()
        assert [(row.action, row.actor, row.before, row.after) for row in audits] == [
            ("customer.auto_created", "system", None,
             {"phone_e164": "+56912345678", "channel": "whatsapp"}),
            ("customer.archived", "operador1", {"archived_at": None},
             {"archived_at": archived_at.isoformat()}),
            ("customer.unarchived", "operador1",
             {"archived_at": archived_at.isoformat()}, {"archived_at": None}),
        ]


def test_get_or_create_auto_unarchives_archived_customer_once():
    from app.models import AuditLog

    with SessionLocal() as session:
        customer = customers.get_or_create_customer(session, "56912345678")
        customers.archive_customer(session, customer, actor="operador1")
        session.commit()
        customer_id = customer.id

    with SessionLocal() as session:
        customer = customers.get_or_create_customer(session, "56912345678")
        session.commit()
        assert customer.id == customer_id
        assert customer.archived_at is None
        audit = session.scalar(
            select(AuditLog).where(AuditLog.action == "customer.auto_unarchived")
        )
        assert audit is not None
        assert audit.actor == "system"
        assert audit.before["archived_at"] is not None
        assert audit.after == {"archived_at": None}


def test_create_customer_sets_defaults_and_audits_operator():
    from app.models import AuditLog

    with SessionLocal() as session:
        customer = customers.create_customer(
            session, "+56 9 1234 5678", name="Ana", actor="operador1"
        )
        session.commit()
        assert customer.phone_e164 == "+56912345678"
        assert customer.name == "Ana"
        assert customer.state == CustomerState.NUEVO
        assert customer.consent_status is False
        audit = session.scalar(
            select(AuditLog).where(AuditLog.action == "customer.created")
        )
        assert audit.actor == "operador1"
        assert audit.entity_id == str(customer.id)
        assert audit.after == {"phone_e164": "+56912345678", "channel": "panel"}


def test_create_customer_rejects_duplicate_without_adopting_existing():
    with SessionLocal() as session:
        existing = customers.get_or_create_customer(session, "56912345678")
        with pytest.raises(customers.PhoneAlreadyExists) as exc_info:
            customers.create_customer(session, "+56 9 1234 5678", actor="operador1")
        assert exc_info.value.customer_id == existing.id
        assert customers.get_or_create_customer(session, "56912345678").id == existing.id


def test_create_customer_rejects_archived_duplicate():
    with SessionLocal() as session:
        existing = customers.get_or_create_customer(session, "56912345678")
        customers.archive_customer(session, existing, actor="operador1")
        with pytest.raises(customers.PhoneAlreadyExists) as exc_info:
            customers.create_customer(session, "56912345678", actor="operador1")
        assert exc_info.value.customer_id == existing.id


def test_create_customer_rejects_unrecognized_phone():
    with SessionLocal() as session:
        with pytest.raises(ValueError, match="^phone cannot be normalized to E.164$"):
            customers.create_customer(session, "   ", actor="operador1")


def test_merge_customers_reassigns_linked_rows_and_audits():
    with SessionLocal() as session:
        survivor = customers.get_or_create_customer(session, "56911111111")
        loser = customers.get_or_create_customer(session, "56922222222")
        conv = Conversation(customer_id=loser.id, wa_phone=loser.phone_e164)
        session.add(conv)
        session.flush()
        case = Case(conversation_id=conv.id, customer_id=loser.id, service="repair",
                    priority="media", status="abierto", summary="case")
        session.add(case)
        session.flush()
        note = CustomerNote(customer_id=loser.id, note="note", author="operator")
        equipment = CustomerEquipment(customer_id=loser.id, equipment_type="boiler")
        technician = User(username=f"merge-tech-{uuid4().hex}", password_hash="unused", role=UserRole.TECNICO)
        session.add(technician)
        session.flush()
        appointment = Appointment(customer_id=loser.id, case_id=case.id, service="repair",
                                  technician_id=technician.id,
                                  local_start=datetime(2026, 10, 1, 10), timezone="UTC",
                                  starts_at=datetime(2026, 10, 1, 10, tzinfo=timezone.utc),
                                  ends_at=datetime(2026, 10, 1, 11, tzinfo=timezone.utc),
                                  duration_minutes=60)
        session.add_all([note, equipment, appointment])
        session.flush()

        result = customers.merge_customers(session, survivor, loser, actor="operator")
        session.commit()

        assert result.id == loser.id
        assert survivor.merged_into_customer_id == loser.id
        assert survivor.archived_at is not None
        assert conv.customer_id == case.customer_id == note.customer_id == equipment.customer_id == appointment.customer_id == loser.id
        audits = session.scalars(select(AuditLog).where(AuditLog.action == "customer.merged")).all()
        assert len(audits) == 1
        assert audits[0].entity == "customer"
        assert audits[0].entity_id == str(loser.id)


def test_merge_customers_chooses_more_active_customer_and_fills_scalars():
    with SessionLocal() as session:
        first = customers.get_or_create_customer(session, "56911111111")
        second = customers.get_or_create_customer(session, "56922222222")
        first.name, first.email = "Kept", "same@example.com"
        second.name, second.email = "Other", "different@example.com"
        second.comuna = "Providencia"
        session.add_all([
            Conversation(customer_id=second.id, wa_phone=second.phone_e164),
            Conversation(customer_id=second.id, wa_phone=second.phone_e164),
        ])
        session.flush()
        survivor = customers.merge_customers(session, first, second, actor="operator")
        session.commit()
        assert survivor.id == second.id
        assert survivor.name == "Other"
        assert survivor.comuna == "Providencia"
        audit = session.scalar(select(AuditLog).where(AuditLog.action == "customer.merged"))
        assert audit.after["scalar_conflicts"]


@pytest.mark.parametrize("guard", ["same", "tombstone"])
def test_merge_customers_rejects_invalid_pair(guard):
    with SessionLocal() as session:
        first = customers.get_or_create_customer(session, "56911111111")
        second = customers.get_or_create_customer(session, "56922222222")
        if guard == "same":
            second = first
        else:
            second.merged_into_customer_id = first.id
            session.flush()
        with pytest.raises(ValueError):
            customers.merge_customers(session, first, second, actor="operator")


def test_merge_customers_rekeys_customer_observations():
    with SessionLocal() as session:
        first = customers.get_or_create_customer(session, "56911111111")
        second = customers.get_or_create_customer(session, "56922222222")
        observation = MemoryObservation(scope="customer", entity_id=str(second.id),
                                       tipo="riesgo", detalle={})
        session.add(observation)
        session.flush()
        survivor = customers.merge_customers(session, first, second, actor="operator")
        session.commit()
        assert observation.entity_id == str(survivor.id)


def test_merge_customers_tie_uses_older_customer_and_archived_side_loses():
    from datetime import timedelta

    with SessionLocal() as session:
        older = customers.get_or_create_customer(session, "56911111111")
        newer = customers.get_or_create_customer(session, "56922222222")
        newer.created_at = older.created_at + timedelta(seconds=1)
        session.flush()
        assert customers.merge_customers(session, newer, older, actor="operator").id == older.id
        session.rollback()

    with SessionLocal() as session:
        active = customers.get_or_create_customer(session, "56933333333")
        archived = customers.get_or_create_customer(session, "56944444444")
        customers.archive_customer(session, archived, actor="operator")
        session.flush()
        session.add(Conversation(customer_id=archived.id, wa_phone=archived.phone_e164))
        session.flush()
        assert customers.merge_customers(session, archived, active, actor="operator").id == active.id


def test_merge_customers_deduplicates_equivalent_memories_and_records_content_conflict():
    with SessionLocal() as session:
        first = customers.get_or_create_customer(session, "56911111111")
        second = customers.get_or_create_customer(session, "56922222222")
        common = dict(scope="customer", tipo=MemoryType.CUSTOMER_MEMO,
                      embedding=[0.0] * 384, duplicate_count=2)
        kept = Memory(entity_id=str(first.id), topic_key="same", titulo="Same",
                      contenido="equal", **common)
        kept_conflict = Memory(entity_id=str(first.id), topic_key="different",
                               titulo="Survivor title", contenido="Survivor body",
                               scope="customer", tipo=MemoryType.CUSTOMER_MEMO,
                               embedding=[2.0] * 384)
        duplicate = Memory(entity_id=str(second.id), topic_key="same", titulo="Same",
                           contenido="equal", duplicate_count=3,
                           scope="customer", tipo=MemoryType.CUSTOMER_MEMO,
                           embedding=[0.0] * 384)
        loser_conflict = Memory(entity_id=str(second.id), topic_key="different",
                                titulo="Loser title", contenido="Loser body",
                                scope="customer", tipo=MemoryType.CUSTOMER_MEMO,
                                embedding=[1.0] * 384)
        session.add_all([kept, kept_conflict, duplicate, loser_conflict])
        session.flush()
        observation = MemoryObservation(memory_id=duplicate.id, scope="customer",
                                       entity_id=str(second.id), tipo="riesgo", detalle={})
        relation = MemoryRelation(id_a=duplicate.id, id_b=loser_conflict.id, relation="related")
        session.add_all([observation, relation])
        session.flush()

        survivor = customers.merge_customers(session, first, second, actor="operator")
        session.commit()

        assert session.get(Memory, kept.id).duplicate_count == 5
        assert session.get(Memory, duplicate.id) is None
        assert session.get(Memory, loser_conflict.id) is None
        assert observation.memory_id == kept.id
        assert relation.id_a == kept.id
        audit = session.scalar(select(AuditLog).where(AuditLog.action == "customer.merged"))
        assert audit.after["memory_conflicts"] == [{
            "topic_key": "different", "titulo": "Loser title", "contenido": "Loser body"
        }]
        assert audit.after["moved"]["customer_equipment"] == 0

"""T5/T6 address capture integration tests against the migrated database."""

from datetime import datetime, timezone

import psycopg
import pytest
from sqlalchemy import select

from app.chat.nodes import capture as capture_node
from app.chat.state import ConversationState, get_or_create_conversation
from app.db import SessionLocal
from app.models import Conversation, Customer
from app.services.customers import get_or_create_customer
from _testdb import admin_database_url

ADMIN_DB_URL = admin_database_url()


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    """Match the neighboring capture integration suite's database isolation."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, technician_availability, technician_weekly_schedule, "
            "kb_chunks, kb_documents, audit_log, conversation_events, "
            "cases, messages, conversations, customer_notes, customers "
            "RESTART IDENTITY CASCADE"
        )
    yield


@pytest.fixture(autouse=True)
def deterministic_capture_phrasing(monkeypatch):
    monkeypatch.setattr(
        capture_node, "phrase", lambda _session, _key, rendered, **_kwargs: rendered
    )


def _start_capture(*, stored_address=None, stored_state=None, consent=False):
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56912345678")
        customer.consent_status = consent
        if stored_address is not None:
            customer.address = stored_address
            customer.direccion_estado = stored_state or "validada"
            customer.direccion_fuente = "callejero" if customer.direccion_estado == "validada" else "cliente"
            customer.direccion_validada_at = datetime(2026, 11, 16, tzinfo=timezone.utc)
        conversation = get_or_create_conversation(session, customer, "+56912345678")
        session.commit()
        return customer.id, conversation.id


def _pending_address_state(
    customer_id, conversation_id, text, *, commune="Ñuñoa", captured=None, window=None
):
    data = {
        "failure": "no enciende", "equipment": "unknown", "comuna": commune,
        "availability": "mañana", "name": "Ana", "email": "ana@example.cl",
        "consent": "si", "_pending": ["address"], "_asked": {"address": 1},
    }
    data.update(captured or {})
    return ConversationState(
        customer_id=customer_id, conversation_id=conversation_id,
        phone="+56912345678", captured=data,
        extracted={"address": text}, window=window or [{"text": text}],
    )


def _read_customer(customer_id):
    """Read after the node's session is closed, proving the committed row."""
    with SessionLocal() as session:
        row = session.scalar(select(Customer).where(Customer.id == customer_id))
        return {
            "address": row.address,
            "direccion_estado": row.direccion_estado,
            "direccion_fuente": row.direccion_fuente,
            "direccion_validada_at": row.direccion_validada_at,
        }


def test_valid_address_persists_validated_outcome_in_database():
    customer_id, conversation_id = _start_capture()

    result = capture_node.capture(
        _pending_address_state(customer_id, conversation_id, "Avenida Irarrázaval 40")
    )
    stored = _read_customer(customer_id)

    assert result["captured"]["address"] == "Avenida Irarrázaval 40"
    assert stored["address"] == "Avenida Irarrázaval 40"
    assert stored["direccion_estado"] == "validada"
    assert stored["direccion_fuente"] == "callejero"
    assert stored["direccion_validada_at"] is not None


def test_wrong_number_reasks_and_keeps_previous_address_outcome_untouched():
    customer_id, conversation_id = _start_capture(
        stored_address="Avenida Irarrázaval 40", stored_state="validada"
    )
    before = _read_customer(customer_id)

    result = capture_node.capture(
        _pending_address_state(customer_id, conversation_id, "Avenida Irarrázaval 65")
    )
    after = _read_customer(customer_id)

    assert result["captured"].get("address") is None
    assert result["captured"]["_pending"] == ["address"]
    assert result["captured"]["_asked"]["address"] == 2
    assert any("dirección" in reply.lower() for reply in result["replies"])
    assert after == before


def test_second_failure_offers_pin_and_insistence_persists_client_state():
    customer_id, conversation_id = _start_capture()

    first = capture_node.capture(
        _pending_address_state(customer_id, conversation_id, "mi casa")
    )
    assert "pin" in first["replies"][0].lower() or "ubicación" in first["replies"][0].lower()
    assert first["captured"]["_pending"] == ["address"]

    second_state = _pending_address_state(
        customer_id, conversation_id, "mi casa", captured=first["captured"]
    )
    insisted = capture_node.capture(second_state)
    stored = _read_customer(customer_id)

    assert insisted["captured"]["address"] == "mi casa"
    assert stored["address"] == "mi casa"
    assert stored["direccion_estado"] == "cliente"
    assert stored["direccion_fuente"] == "cliente"
    assert stored["direccion_validada_at"] is not None


def test_repeating_the_pending_address_after_pin_offer_persists_client_state():
    customer_id, conversation_id = _start_capture()
    first_text = "Avenida Irarrázaval 65"
    first = capture_node.capture(
        _pending_address_state(customer_id, conversation_id, first_text)
    )
    assert "pin" in first["replies"][0].lower() or "ubicación" in first["replies"][0].lower()

    repeated = capture_node.capture(_pending_address_state(
        customer_id, conversation_id, first_text, captured=first["captured"],
        window=[{"text": first_text, "direction": "inbound"},
                {"text": first_text, "direction": "inbound"}],
    ))
    stored = _read_customer(customer_id)

    assert repeated["captured"]["address"] == first_text
    assert repeated["captured"]["direccion_estado"] == "cliente"
    assert stored["address"] == first_text
    assert stored["direccion_estado"] == "cliente"
    assert stored["direccion_fuente"] == "cliente"


def test_colina_persists_sin_referencia_not_no_encontrada():
    customer_id, conversation_id = _start_capture()

    capture_node.capture(
        _pending_address_state(
            customer_id, conversation_id, "Avenida Irarrázaval 40", commune="Colina"
        )
    )
    stored = _read_customer(customer_id)

    assert stored["direccion_estado"] == "sin_referencia"
    assert stored["direccion_estado"] != "no_encontrada"


def test_sin_referencia_attempt_does_not_relabel_the_stored_address():
    customer_id, conversation_id = _start_capture(
        stored_address="Avenida Irarrázaval 40", stored_state="validada", consent=True
    )
    state = _pending_address_state(
        customer_id, conversation_id, "Avenida Irarrázaval 42", commune="Colina",
    )

    with SessionLocal() as session:
        session.get(Customer, customer_id).comuna = "Ñuñoa"
        session.commit()
    capture_node.capture(state)
    stored = _read_customer(customer_id)

    assert stored["address"] == "Avenida Irarrázaval 40"
    assert stored["direccion_estado"] == "validada"
    assert stored["direccion_fuente"] == "callejero"


def test_corrected_address_after_stored_contact_offer_is_validated_and_persisted():
    customer_id, conversation_id = _start_capture(
        stored_address="Avenida Irarrázaval 40", stored_state="validada", consent=True
    )
    with SessionLocal() as session:
        customer = session.get(Customer, customer_id)
        customer.comuna = "Ñuñoa"
        customer.email = "ana@example.cl"
        customer.created_at = datetime.now(timezone.utc)
        session.commit()

    initial = {
        "failure": "no enciende", "equipment": "unknown", "availability": "mañana",
        "name": "Ana",
    }
    offered = capture_node._ask_next(initial, ConversationState(
        customer_id=customer_id, conversation_id=conversation_id, phone="+56912345678",
        captured=initial, extracted={}, window=[{"text": "quiero una visita"}],
    ))
    refused = capture_node.capture(ConversationState(
        customer_id=customer_id, conversation_id=conversation_id, phone="+56912345678",
        captured=offered["captured"], extracted={},
        window=[{"text": "no, me cambié de casa"}],
    ))
    comuna = capture_node.capture(ConversationState(
        customer_id=customer_id, conversation_id=conversation_id, phone="+56912345678",
        captured=refused["captured"], extracted={"comuna": "Ñuñoa"},
        window=[{"text": "Ñuñoa"}],
    ))
    email = capture_node.capture(ConversationState(
        customer_id=customer_id, conversation_id=conversation_id, phone="+56912345678",
        captured=comuna["captured"], extracted={"email": "ana@example.cl"},
        window=[{"text": "ana@example.cl"}],
    ))
    corrected = "Avenida Irarrázaval 42"
    result = capture_node.capture(_pending_address_state(
        customer_id, conversation_id, corrected, captured=email["captured"],
    ))
    stored = _read_customer(customer_id)

    assert result["captured"].get("direccion_estado") == "validada", result["captured"]
    assert stored["address"] == corrected
    assert stored["direccion_estado"] == "validada"
    assert stored["direccion_fuente"] == "callejero"


def test_recent_stored_validated_contact_is_still_offered_unchanged():
    customer_id, conversation_id = _start_capture(
        stored_address="Avenida Irarrázaval 40", stored_state="validada", consent=True
    )
    with SessionLocal() as session:
        customer = session.get(Customer, customer_id)
        customer.comuna = "Ñuñoa"
        customer.email = "ana@example.cl"
        customer.created_at = datetime.now(timezone.utc)
        session.commit()

    captured = {
        "failure": "no enciende", "equipment": "unknown", "availability": "mañana",
        "name": "Ana",
    }
    result = capture_node._ask_next(captured, ConversationState(
        customer_id=customer_id, conversation_id=conversation_id, phone="+56912345678",
        captured=captured, extracted={}, window=[{"text": "quiero una visita"}],
    ))

    assert result["captured"]["address"] == "Avenida Irarrázaval 40"
    assert "Avenida Irarrázaval 40" in result["replies"][0]
    assert result["captured"]["_pending"] == "confirm_contact"


def test_client_read_model_exposes_database_validation_fields():
    customer_id, _conversation_id = _start_capture(
        stored_address="Avenida Irarrázaval 40", stored_state="validada"
    )
    from app.panel.api.routes.clients import to_customer_dict

    with SessionLocal() as session:
        row = session.get(Customer, customer_id)
        read_model = to_customer_dict(row)

    assert read_model["direccion_estado"] == "validada"
    assert read_model["direccion_fuente"] == "callejero"
    assert read_model["direccion_validada_at"] is not None
    assert read_model["direccion_lat"] is None
    assert read_model["direccion_lon"] is None

"""Case lineage for the deterministic case lifecycle (T4, S4)."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Case, Conversation, Customer, CustomerState
from app.services.cases import case_is_open, create_manual_case, get_or_create_case


def _phone() -> str:
    return f"+569{uuid4().int % 100_000_000:08d}"


def _customer(session) -> Customer:
    customer = Customer(phone_e164=_phone(), state=CustomerState.NUEVO)
    session.add(customer)
    session.flush()
    return customer


def _conversation(session, customer: Customer) -> Conversation:
    conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
    session.add(conversation)
    session.flush()
    return conversation


def _prior_case(session, customer: Customer, **kwargs) -> Case:
    case = Case(customer_id=customer.id, **kwargs)
    session.add(case)
    session.flush()
    return case


def test_first_case_has_no_origin():
    with SessionLocal() as session:
        customer = _customer(session)
        conversation = _conversation(session, customer)

        case = get_or_create_case(session, conversation.id, customer.id)

        session.refresh(case)
        assert case.origin_case_id is None


def test_case_never_declares_itself():
    with SessionLocal() as session:
        customer = _customer(session)
        _prior_case(session, customer, service="Caso previo")
        case = create_manual_case(session, customer.id, "Caso nuevo")

        session.refresh(case)
        assert case.origin_case_id != case.id


def test_new_conversation_case_declares_previous_case():
    with SessionLocal() as session:
        customer = _customer(session)
        previous = _prior_case(session, customer, service="Mantención caldera")
        conversation = _conversation(session, customer)

        case = get_or_create_case(session, conversation.id, customer.id)

        session.refresh(case)
        assert case.origin_case_id == previous.id


def test_manual_case_declares_previous_case():
    with SessionLocal() as session:
        customer = _customer(session)
        previous = _prior_case(session, customer, service="Mantención caldera")

        case = create_manual_case(session, customer.id, "Caldera no calienta")

        session.refresh(case)
        assert case.origin_case_id == previous.id


def test_new_case_leaves_previous_closed_row_untouched():
    with SessionLocal() as session:
        customer = _customer(session)
        previous = _prior_case(
            session,
            customer,
            service="Mantención caldera",
            status="cerrado",
            summary="Trabajo terminado",
            closed_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
        conversation = _conversation(session, customer)
        before = (previous.status, previous.summary, previous.closed_at, previous.conversation_id)

        get_or_create_case(session, conversation.id, customer.id)
        session.flush()
        session.refresh(previous)

        assert (previous.status, previous.summary, previous.closed_at, previous.conversation_id) == before
        assert not case_is_open(previous)


def test_same_conversation_reuses_case_without_rewriting_origin():
    with SessionLocal() as session:
        customer = _customer(session)
        original = _prior_case(session, customer, service="Caso anterior")
        conversation = _conversation(session, customer)

        case = get_or_create_case(session, conversation.id, customer.id)
        declared_origin = case.origin_case_id
        again = get_or_create_case(session, conversation.id, customer.id)
        rows = session.scalars(
            select(Case).where(Case.conversation_id == conversation.id)
        ).all()

        assert again.id == case.id
        assert len(rows) == 1
        assert declared_origin == original.id
        assert again.origin_case_id == declared_origin


def test_origin_is_most_recent_previous_case_by_created_at_then_id():
    with SessionLocal() as session:
        customer = _customer(session)
        now = datetime.now(timezone.utc)
        _prior_case(session, customer, created_at=now - timedelta(days=2))
        _prior_case(session, customer, created_at=now - timedelta(days=1))
        newest = _prior_case(session, customer, created_at=now - timedelta(days=1))
        conversation = _conversation(session, customer)

        case = get_or_create_case(session, conversation.id, customer.id)

        session.refresh(case)
        assert case.origin_case_id == newest.id

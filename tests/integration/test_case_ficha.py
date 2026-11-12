"""Fase 3 "el caso existe" — schema de la ficha del caso (S4, S5).

Migration 065 adds the two facts the feature needs and nothing else:

- `cases.origin_case_id` (D5): a new case DECLARES which earlier case it comes
  from. Nullable, so every case created before this feature keeps working, and
  a real foreign key, so a declaration cannot point at a case that does not
  exist. The earlier case is never reopened or rewritten.
- `customers.decide_spending` (D7): one stored fact per person with default
  `si`; it only goes down when the conversation proves it. The database accepts
  exactly the three values, so a typo cannot become a fourth state.

Runs against the migrated pgvector test DB (conftest DATABASE_URL).
"""

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.db import SessionLocal
from app.models import Case, Customer, CustomerState


def _phone() -> str:
    return f"+569{uuid4().int % 100_000_000:08d}"


def _customer(session) -> Customer:
    customer = Customer(phone_e164=_phone(), state=CustomerState.NUEVO)
    session.add(customer)
    session.flush()
    return customer


def test_cases_origin_case_id_is_a_nullable_foreign_key():
    """Column exists, is nullable, and points at `cases.id` (S4)."""
    with SessionLocal() as session:
        columns = {
            row[0]: row
            for row in session.execute(
                text(
                    "SELECT column_name, is_nullable, data_type "
                    "FROM information_schema.columns "
                    "WHERE table_name = 'cases' AND column_name = 'origin_case_id'"
                )
            )
        }
        assert "origin_case_id" in columns, "cases.origin_case_id is missing (migration 065)"
        assert columns["origin_case_id"][1] == "YES"

        targets = {
            row[0]
            for row in session.execute(
                text(
                    "SELECT confrelid::regclass::text FROM pg_constraint "
                    "WHERE conrelid = 'cases'::regclass AND contype = 'f' "
                    "  AND conname = 'cases_origin_case_id_fkey'"
                )
            )
        }
        assert targets == {"cases"}


def test_origin_case_id_must_point_at_an_existing_case():
    """A declaration that names a case which does not exist is rejected (S4)."""
    with SessionLocal() as session:
        customer = _customer(session)
        session.add(Case(customer_id=customer.id, origin_case_id=999_999_999))
        with pytest.raises(IntegrityError):
            session.flush()


def test_origin_case_id_is_storable_and_leaves_the_prior_case_untouched():
    """The link persists and the prior case keeps every field it had (S4)."""
    with SessionLocal() as session:
        customer = _customer(session)
        prior = Case(customer_id=customer.id, service="Mantención caldera", status="cerrado")
        session.add(prior)
        session.flush()
        before = (prior.status, prior.summary, prior.closed_at, prior.conversation_id)

        following = Case(
            customer_id=customer.id,
            service="Caldera no calienta",
            origin_case_id=prior.id,
        )

        session.add(following)
        session.flush()
        session.commit()

        assert following.origin_case_id == prior.id
        session.refresh(prior)
        assert (prior.status, prior.summary, prior.closed_at, prior.conversation_id) == before
        # The prior case is not reopened: it stays closed, with no new work on it.
        assert prior.status == "cerrado"


def test_new_customer_decides_spending_by_default():
    """`decide_spending` defaults to `si` at the database level (S5)."""
    phone = _phone()
    with SessionLocal() as session:
        session.execute(
            text("INSERT INTO customers (phone_e164, state) VALUES (:phone, 'nuevo')"),
            {"phone": phone},
        )
        stored = session.execute(
            text("SELECT decide_spending FROM customers WHERE phone_e164 = :phone"),
            {"phone": phone},
        ).scalar_one()
        assert stored == "si"


def test_decide_spending_accepts_exactly_three_values():
    """`si`, `duda`, `no` are the only states; anything else is rejected (S5)."""
    with SessionLocal() as session:
        customer = _customer(session)
        for value in ("si", "duda", "no"):
            session.execute(
                text("UPDATE customers SET decide_spending = :value WHERE id = :id"),
                {"value": value, "id": customer.id},
            )
            assert session.execute(
                text("SELECT decide_spending FROM customers WHERE id = :id"),
                {"id": customer.id},
            ).scalar_one() == value

        with pytest.raises((IntegrityError, ProgrammingError)):
            session.execute(
                text("UPDATE customers SET decide_spending = 'quizas' WHERE id = :id"),
                {"id": customer.id},
            )
            session.flush()

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
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.db import SessionLocal
from app.models import Case, Customer, CustomerEquipment, CustomerState
from app.services.case_ficha import FICHA_MAX_CHARS, build_case_ficha


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


# --------------------------------------------------------------------------
# The ficha itself (S1, S3): deterministic, bounded, rebuilt from the database.
# --------------------------------------------------------------------------

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)


def _ficha_customer(session, *, address="Av. Siempre Viva 742", comuna="Maipú", decide_spending="si"):
    customer = Customer(
        phone_e164=_phone(),
        name="Pabla",
        comuna=comuna,
        address=address,
        state=CustomerState.NUEVO,
        decide_spending=decide_spending,
    )
    session.add(customer)
    session.flush()
    return customer


def _work(session, customer, *, service, days_ago, status="cerrado", address=None, summary=None):
    case = Case(
        customer_id=customer.id,
        service=service,
        status=status,
        summary=summary,
        created_at=NOW - timedelta(days=days_ago),
    )
    if address is not None:
        case.bundle = {"captured": {"address": address}}
    session.add(case)
    session.flush()
    return case


def test_ficha_names_the_property_and_the_equipment():
    """S1/S3: what equipment, at which property, in one bounded block."""
    with SessionLocal() as session:
        customer = _ficha_customer(session)
        session.add(
            CustomerEquipment(
                customer_id=customer.id,
                equipment_type="Calefont",
                brand="Junkers",
                model="Hydromax",
                age="8 años",
            )
        )
        session.flush()

        ficha = build_case_ficha(session, customer.id, now=NOW, timezone_name="America/Santiago")

        assert "Av. Siempre Viva 742" in ficha
        assert "Maipú" in ficha
        assert "Calefont" in ficha and "Junkers" in ficha


def test_ficha_lists_the_prior_work_with_its_date_and_status():
    """S1: what was intervened and when — the fact a 500-turn thread loses."""
    with SessionLocal() as session:
        customer = _ficha_customer(session)
        _work(session, customer, service="Mantención caldera", days_ago=41)

        ficha = build_case_ficha(session, customer.id, now=NOW, timezone_name="America/Santiago")

        assert "Mantención caldera" in ficha
        assert "02/10/2026" in ficha


def test_ficha_names_the_property_of_a_work_done_at_another_address():
    """S3: 8 of 34 real properties belong to someone else — never "mi casa"."""
    with SessionLocal() as session:
        customer = _ficha_customer(session)
        _work(
            session,
            customer,
            service="Mantención calefont",
            days_ago=10,
            address="Los Aromos 1150, Ñuñoa",
        )

        ficha = build_case_ficha(session, customer.id, now=NOW, timezone_name="America/Santiago")

        assert "Los Aromos 1150" in ficha
        assert "otra propiedad" in ficha.lower()


def test_ficha_states_the_warranty_window_of_a_published_service():
    """S1 + D3: maintenance: one year; red wash: six months; nothing invented."""
    with SessionLocal() as session:
        customer = _ficha_customer(session)
        _work(session, customer, service="Mantención caldera", days_ago=41)
        _work(session, customer, service="Lavado de red", days_ago=100)
        _work(session, customer, service="Cambio de caldera", days_ago=200)

        ficha = build_case_ficha(session, customer.id, now=NOW, timezone_name="America/Santiago")

        assert "02/10/2027" in ficha  # maintenance of 02/10/2026 + 1 year
        assert "04/02/2027" in ficha  # red wash of 04/08/2026 + 6 months
        # The unlisted service has no published warranty: no window is invented.
        assert ficha.count("garantía vigente") == 2


def test_ficha_lists_what_is_still_pending():
    """S1: "qué quedó pendiente" is the open case, not a guess."""
    with SessionLocal() as session:
        customer = _ficha_customer(session)
        _work(session, customer, service="Caldera no calienta", days_ago=1, status="abierto")

        ficha = build_case_ficha(session, customer.id, now=NOW, timezone_name="America/Santiago")

        assert "Caldera no calienta" in ficha
        assert "Pendiente" in ficha


def test_ficha_reports_who_decides_the_spending():
    """S5/S7: the fact travels inside the ficha that respond injects."""
    with SessionLocal() as session:
        tenant = _ficha_customer(session, decide_spending="no")
        owner = _ficha_customer(session, decide_spending="si")

        assert "no decide" in build_case_ficha(
            session, tenant.id, now=NOW, timezone_name="America/Santiago"
        ).lower()
        assert "decide" in build_case_ficha(
            session, owner.id, now=NOW, timezone_name="America/Santiago"
        ).lower()


def test_ficha_is_bounded_and_deterministic():
    """S1: a hard 1.500-character ceiling, and the same rows give the same text."""
    with SessionLocal() as session:
        customer = _ficha_customer(session)
        for index in range(3):
            session.add(
                CustomerEquipment(
                    customer_id=customer.id,
                    equipment_type="Calefont",
                    brand=f"Junkers {index}",
                    details="no enciende y pierde agua por la base",
                )
            )
        for index in range(8):
            # Eight real work lines plus three equipment lines cannot fit:
            # the ceiling has to cut, not the section limit.
            _work(
                session,
                customer,
                service=f"Trabajo {index} mantención de caldera y lavado de red",
                days_ago=index * 7 + 1,
            )

        first = build_case_ficha(session, customer.id, now=NOW, timezone_name="America/Santiago")
        second = build_case_ficha(session, customer.id, now=NOW, timezone_name="America/Santiago")

        assert len(first) <= FICHA_MAX_CHARS
        assert first == second
        # The cut is visible and honest: it says less than the data it holds.
        assert first.rstrip().endswith("…")
        assert "Trabajo 7" not in first


def test_ficha_is_empty_without_history():
    """A first contact with nothing stored injects no block at all."""
    with SessionLocal() as session:
        customer = Customer(phone_e164=_phone(), state=CustomerState.NUEVO)
        session.add(customer)
        session.flush()

        assert build_case_ficha(session, customer.id, now=NOW, timezone_name="America/Santiago") == ""

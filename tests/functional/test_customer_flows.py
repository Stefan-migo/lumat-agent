"""T6.2 functional tests — customer-records flows over the webhook (CR-1, CR-2).

End-to-end through the real pipeline: auto-ficha on first contact from an
unknown phone (CR-1) and E.164 phone-based dedup across delivery formats
(CR-2: `+56 9...` vs `9...` collapse to one record — never a duplicate).

Scenarios mapped 1:1 from openspec/specs/customer-records/spec.md:

- CR-1 "First contact creates ficha": unknown phone -> customer record created
- CR-2 "Known customer returns": existing ficha reused, no duplicate
- CR-2 "Different formatting": normalized comparison still matches

(The CR-3 invalid-transition rejection is covered at panel level in
tests/functional/test_clients.py — test_invalid_state_transition_rejected.)
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.db import SessionLocal  # noqa: E402
from app.models import AuditLog, Conversation, Customer  # noqa: E402
from tests.webhook_helpers import post_message


def _customer_rows() -> list[Customer]:
    with SessionLocal() as session:
        return list(session.scalars(select(Customer).order_by(Customer.id)))


@pytest.mark.spec("CR-1")
def test_cr1_auto_ficha_on_first_contact(client, mock_openai_chat, mock_meta_send):
    """Unknown phone -> ficha auto-created with the inbound E.164 number."""
    post_message(client, "wamid.cr1.1", "hola", sender="56998765432")

    customers = _customer_rows()
    assert len(customers) == 1
    assert customers[0].phone_e164 == "+56998765432"
    assert customers[0].state.value == "nuevo"  # CR-3 initial state

    # the auto-creation is audited (SH-5: who/what/when)
    with SessionLocal() as session:
        audit = session.scalars(
            select(AuditLog).where(AuditLog.action == "customer.auto_created")
        ).one()
        assert audit.after["phone_e164"] == "+56998765432"


@pytest.mark.spec("CR-2")
def test_cr2_phone_dedup_across_formats(client, mock_openai_chat, mock_meta_send):
    """Same number delivered in different formats -> ONE ficha, ONE conversation.

    Meta delivers wa_id as digits ("56912345678"); the CR-2 scenario covers a
    local mobile format ("912345678") arriving through the same channel —
    both normalize to +56912345678.
    """
    post_message(client, "wamid.cr2.1", "hola", sender="56912345678")
    post_message(client, "wamid.cr2.2", "sigo acá", sender="912345678")

    customers = _customer_rows()
    assert len(customers) == 1
    assert customers[0].phone_e164 == "+56912345678"

    with SessionLocal() as session:
        conversations = session.scalars(select(Conversation)).all()
        assert len(conversations) == 1  # same open conversation, no duplicates


@pytest.mark.spec("CR-2")
def test_cr2_known_customer_reuses_existing_ficha(
    client, seed_customer, mock_openai_chat, mock_meta_send
):
    """Pre-existing ficha -> the inbound message links to it, not a new row."""
    seed_customer("+56912345678")
    post_message(client, "wamid.cr2.3", "hola de nuevo", sender="56912345678")

    customers = _customer_rows()
    assert len(customers) == 1
    assert customers[0].phone_e164 == "+56912345678"


@pytest.mark.spec("CR-2")
def test_cr2_different_phone_creates_new_ficha(
    client, mock_openai_chat, mock_meta_send
):
    """Triangulation: a genuinely different number must create a SECOND ficha."""
    post_message(client, "wamid.cr2.4", "hola", sender="56912345678")
    post_message(client, "wamid.cr2.5", "hola", sender="56955556666")

    customers = _customer_rows()
    assert len(customers) == 2
    assert {c.phone_e164 for c in customers} == {"+56912345678", "+56955556666"}

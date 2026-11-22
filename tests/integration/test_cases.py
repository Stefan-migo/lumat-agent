from uuid import uuid4

from app.db import SessionLocal
from app.models import Case, Conversation, Customer
from app.services.cases import get_or_create_case, list_open_cases


def test_simulated_conversation_case_is_flagged_and_hidden_from_open_list():
    with SessionLocal() as session:
        customer = Customer(phone_e164=f"+569{uuid4().int % 10**8:08d}")
        session.add(customer)
        session.flush()
        conversation = Conversation(
            customer_id=customer.id, wa_phone=customer.phone_e164, simulated=True
        )
        session.add(conversation)
        session.flush()
        case = get_or_create_case(session, conversation.id, customer.id)
        case.status = "escalado"
        session.commit()
        case_id = case.id

    with SessionLocal() as session:
        assert session.get(Case, case_id).simulated is True
        assert all(row.id != case_id for row, _customer in list_open_cases(session))

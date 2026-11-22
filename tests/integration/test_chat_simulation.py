from datetime import datetime, timezone
from uuid import uuid4

from app.db import SessionLocal
from app.models import Conversation, ConversationState, Customer
from app.panel.api.routes.conversations import _queue_base


def test_panel_operational_conversation_query_excludes_simulations():
    with SessionLocal() as session:
        customer = Customer(phone_e164=f"+569{uuid4().int % 10**8:08d}")
        session.add(customer)
        session.flush()
        real = Conversation(
            customer_id=customer.id, wa_phone=customer.phone_e164,
            state=ConversationState.BOT, last_message_at=datetime.now(timezone.utc),
        )
        simulated = Conversation(
            customer_id=customer.id, wa_phone=customer.phone_e164,
            state=ConversationState.BOT, last_message_at=datetime.now(timezone.utc), simulated=True,
        )
        session.add_all([real, simulated])
        session.flush()

        rows = session.execute(
            _queue_base(session, q=None, state=None, responsible_id=None)
        ).all()

        ids = {row[0].id for row in rows}
        assert real.id in ids
        assert simulated.id not in ids

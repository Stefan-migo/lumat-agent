"""S3 integration tests — close event memo + observations (MEM-4, MEM-5, CM-9).

Scenarios mapped 1:1 from openspec/specs:

- MEM-4 "Close writes memo": a conversation that transitions to CLOSED via
  `set_conversation_state` upserts a customer_memo under the customer, reusing
  the CM-5 acta content (conversation.summary) verbatim.
- CM-9 "Close triggers memo": the close handler consumes the acta, it does not
  rewrite it.
- MEM-5 "Observation persisted": the patterns fire at close producing a
  `memory_observations` row with type + detail.
- MEM-5 "Recurrence threshold": recurrencia appears only when the configured
  window/count is reached.
- Patterns: sin_respuesta (inbound w/o bot reply within the configured hours),
  riesgo (escalated emergency case), oportunidad (case still without a ticket).

The observación criteria use the design thresholds exposed as configurable
constants in `Settings` (OBS_RECUR_WINDOW/OBS_RECUR_COUNT/OBS_NO_REPLY_HOURS) —
flagged for product sanity before S3 is merged (open design question).

Runs against the migrated pgvector test DB with the deterministic fake
embedder (autouse in tests/integration/conftest.py). Most tests call
`set_conversation_state` directly — the panel owns the close action in T5.3 and
the close hook lives in that helper, so we exercise the same production path.
"""

import psycopg
import pytest
from sqlalchemy import select

from app.chat.state import (  # noqa: E402
    get_or_create_conversation,
    set_conversation_state,
)
from app.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Case,
    Conversation,
    ConversationState as ConvState,
    MemoryType,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
    ObservationType,
)
from app.services import memory as memory_service  # noqa: E402
from app.services.customers import get_or_create_customer  # noqa: E402
from _testdb import admin_database_url  # noqa: E402

ADMIN_DB_URL = admin_database_url()

ACTA = (
    "Acta: cliente con calefont en Providencia, se solicita visita tecnica "
    "para la proxima semana."
)


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    """Reset chat + memory tables before every test (shared test DB)."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE memories, memory_observations, memory_relations, "
            "settings, audit_log, conversation_events, cases, messages, "
            "conversations, customer_notes, customers RESTART IDENTITY CASCADE"
        )
    yield


def _start_conversation(
    summary: str | None = None,
    phone: str = "+56912345678",
) -> tuple[int, int]:
    """Create a customer + open conversation; returns (conversation, customer)."""
    with SessionLocal() as session:
        customer = get_or_create_customer(session, phone)
        conv = get_or_create_conversation(session, customer, phone)
        if summary is not None:
            conv.summary = summary
        session.commit()
        return conv.id, customer.id


def _close(conv_id: int, cause: str = "resolved") -> None:
    """Transition the conversation to CLOSED through the production helper."""
    with SessionLocal() as session:
        conv = session.get(Conversation, conv_id)
        set_conversation_state(session, conv, ConvState.CLOSED, cause=cause)
        session.commit()


def _add_inbound(conv_id: int, text: str, *, wamid: str = "wamid.s3") -> None:
    from datetime import datetime, timedelta, timezone

    with SessionLocal() as session:
        session.add(
            Message(
                wamid=wamid,
                conversation_id=conv_id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text=text,
                status=MessageStatus.RECEIVED,
                created_at=datetime.now(timezone.utc) - timedelta(hours=3),
            )
        )
        session.commit()


def _memo_text(customer_id: int) -> str | None:
    with SessionLocal() as session:
        rows = memory_service.list_for_entity(
            session, scope="customer", entity_id=str(customer_id)
        )
        for m in rows:
            if m.topic_key == "customer_memo":
                return m.contenido
        return None


def _obs(customer_id: int, tipo: ObservationType) -> list:
    from app.models import MemoryObservation

    with SessionLocal() as session:
        return list(
            session.execute(
                select(MemoryObservation).where(
                    MemoryObservation.scope == "customer",
                    MemoryObservation.entity_id == str(customer_id),
                    MemoryObservation.tipo == tipo,
                )
            ).scalars()
        )


# ---------------------------------------------------------------------------
# MEM-4 / CM-9 — close writes the customer memo reusing the acta verbatim
# ---------------------------------------------------------------------------


def test_s3_close_writes_customer_memo_verbatim():
    conv_id, customer_id = _start_conversation(summary=ACTA)

    _close(conv_id)

    assert _memo_text(customer_id) == ACTA  # MEM-4/CM-9: acta reused verbatim


def test_s3_close_refreshes_existing_memo_with_current_acta():
    """Closing upserts: the close-time acta wins over any stale prior memo."""
    conv_id, customer_id = _start_conversation(summary=ACTA)
    with SessionLocal() as session:
        memory_service.upsert(
            session,
            scope="customer",
            entity_id=str(customer_id),
            topic_key="customer_memo",
            tipo=MemoryType.CUSTOMER_MEMO,
            titulo="customer_memo",
            contenido="Acta previa ya al almacenado.",
        )
        session.commit()

    _close(conv_id)

    assert _memo_text(customer_id) == ACTA  # current acta replaces the stale one


def test_s3_close_without_acta_degrades_to_empty_memo():
    """A close with no summary still writes an empty memo (never fabricated)."""
    conv_id, customer_id = _start_conversation(summary=None)

    _close(conv_id)

    # MEM-4/CM-9: no summary -> no invented content; the memo row exists empty.
    with SessionLocal() as session:
        rows = memory_service.list_for_entity(
            session, scope="customer", entity_id=str(customer_id)
        )
    assert len(rows) == 1
    assert rows[0].topic_key == "customer_memo"
    assert rows[0].contenido == ""


# ---------------------------------------------------------------------------
# MEM-5 — typed observations on close
# ---------------------------------------------------------------------------


def test_s3_no_recurrencia_below_threshold():
    """A single close produces no recurrencia observation (MEM-5 threshold)."""
    conv_id, customer_id = _start_conversation(summary=ACTA)
    _close(conv_id)

    assert _obs(customer_id, ObservationType.RECURRENCIA) == []


def test_s3_recurrencia_fires_at_threshold():
    """A second close within the window raises a recurrencia observation."""
    conv1, customer_id = _start_conversation(summary=ACTA, phone="+56911111111")
    _close(conv1)
    conv2, _ = _start_conversation(summary=ACTA, phone="+56911111111")
    _close(conv2)

    assert len(_obs(customer_id, ObservationType.RECURRENCIA)) == 1


def test_s3_sin_respuesta_on_unanswered_inbound():
    """An inbound with no bot reply within the window yields sin_respuesta."""
    conv_id, customer_id = _start_conversation(summary=ACTA)
    _add_inbound(conv_id, "necesito ayuda con mi caldera")

    _close(conv_id)

    assert len(_obs(customer_id, ObservationType.SIN_RESPUESTA)) == 1


def test_s3_no_sin_respuesta_when_bot_replied():
    """An inbound that got a subsequent bot reply yields no sin_respuesta."""
    conv_id, customer_id = _start_conversation(summary=ACTA)
    _add_inbound(conv_id, "necesito ayuda con mi caldera", wamid="wamid.asked")
    with SessionLocal() as session:
        session.add(
            Message(
                wamid="wamid.answered",
                conversation_id=conv_id,
                direction=MessageDirection.OUTBOUND,
                msg_type=MessageType.TEXT,
                text="Claro, un momento por favor.",
                status=MessageStatus.PROCESSED,
            )
        )
        session.commit()

    _close(conv_id)

    # the outbound reply follows the inbound, so the customer was answered
    assert _obs(customer_id, ObservationType.SIN_RESPUESTA) == []


def test_s3_riesgo_on_flaged_emergency_case():
    """An escalated emergency case yields a riesgo observation on close."""
    conv_id, customer_id = _start_conversation(summary=ACTA)
    with SessionLocal() as session:
        case = Case(
            conversation_id=conv_id,
            customer_id=customer_id,
            emergency=True,
            status="escalado",
        )
        session.add(case)
        session.commit()

    _close(conv_id)

    assert len(_obs(customer_id, ObservationType.RIESGO)) == 1


def test_s3_no_riesgo_without_emergency_flag():
    """A normal (non-emergency) case yields no riesgo observation."""
    conv_id, customer_id = _start_conversation(summary=ACTA)
    with SessionLocal() as session:
        case = Case(
            conversation_id=conv_id,
            customer_id=customer_id,
            emergency=False,
            status="abierto",
        )
        session.add(case)
        session.commit()

    _close(conv_id)

    assert _obs(customer_id, ObservationType.RIESGO) == []


def test_s3_oportunidad_on_case_without_ticket():
    """A case still open with no ticket yields an oportunidad observation."""
    conv_id, customer_id = _start_conversation(summary=ACTA)
    _add_inbound(conv_id, "me interesa conocer los valores de mantenimiento")

    _close(conv_id)

    assert len(_obs(customer_id, ObservationType.OPORTUNIDAD)) == 1


def test_s3_no_oportunidad_when_ticket_issued():
    """A case with a ticket issued yields no oportunidad observation."""
    conv_id, customer_id = _start_conversation(summary=ACTA)
    with SessionLocal() as session:
        case = Case(
            conversation_id=conv_id,
            customer_id=customer_id,
            emergency=False,
            status="resuelto",
        )
        session.add(case)
        session.commit()

    _close(conv_id)

    assert _obs(customer_id, ObservationType.OPORTUNIDAD) == []

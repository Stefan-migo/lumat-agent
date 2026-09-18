"""S2 integration tests — per-turn memory pipeline (CM-7, CM-8).

Scenarios mapped 1:1 from openspec/specs/conversation-manager/spec.md:

- CM-7 "Context injected": returning customer's memories are present in the
  state before the respond node runs (asserted via the <memory> block injected
  into the respond LLM call).
- CM-7 "No memory yet": first contact -> empty memory context, reply flow
  continues normally (not blocked).
- CM-8 "Persist before END": a run that produced replies flushes a session
  memory that a subsequent turn sees without data loss.

Runs the full graph per turn. OpenAI chat mocked via respx; the embedder is the
deterministic fake (mounted by mock_openai_chat) so the suite never downloads
the model. Runs against the migrated pgvector test DB.
"""

import psycopg
import pytest
from sqlalchemy import select

from app.chat.graph import run_conversation  # noqa: E402
from app.chat.state import get_or_create_conversation  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Conversation,
    DocumentFormat,
    MemoryType,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services import kb as kb_service  # noqa: E402
from app.services.customers import get_or_create_customer  # noqa: E402
from app.services import memory as memory_service  # noqa: E402
from _testdb import admin_database_url  # noqa: E402

ADMIN_DB_URL = admin_database_url()


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    """Reset chat + KB + memory tables before every test (shared test DB)."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE memories, memory_relations, memory_observations, "
            "settings, kb_chunks, kb_documents, audit_log, conversation_events, "
            "cases, messages, conversations, customer_notes, customers "
            "RESTART IDENTITY CASCADE"
        )
    yield


def _seed_kb_doc(text: str) -> None:
    # H2 (PR 2, AO-7): the valores query is answered by the scoped
    # research_triage sub-graph, which only retrieves chunks whose
    # source_meta.category is in its kb_scope — seed the category so the
    # scoped retrieve finds it and respond (which injects <memory>) runs.
    with SessionLocal() as session:
        kb_service.ingest_document(
            session,
            title="Manual",
            fmt=DocumentFormat.MD,
            content=text.encode(),
            source_meta={"category": "valores"},
        )
        session.commit()


def _seed_customer_memo(customer_id: int, contenido: str) -> None:
    with SessionLocal() as session:
        memory_service.upsert(
            session,
            scope="customer",
            entity_id=str(customer_id),
            topic_key="customer_memo",
            tipo=MemoryType.CUSTOMER_MEMO,
            titulo="customer_memo",
            contenido=contenido,
        )
        session.commit()


def _start_conversation() -> tuple[int, int]:
    """Create a customer + open conversation; returns (conversation, customer)."""
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56912345678")
        conv = get_or_create_conversation(session, customer, "+56912345678")
        session.commit()
        return conv.id, customer.id


def _turn(conv_id: int, text: str, wamid: str) -> list[str]:
    """Append an inbound message and run the graph (replies persisted)."""
    with SessionLocal() as session:
        session.add(
            Message(
                wamid=wamid,
                conversation_id=conv_id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text=text,
                status=MessageStatus.RECEIVED,
            )
        )
        session.commit()
        message = session.scalars(
            select(Message).where(
                Message.conversation_id == conv_id, Message.wamid == wamid
            )
        ).one()
        replies = run_conversation(session, message)
        session.commit()
        return replies


def _respond_user_content(mock_openai_chat: list[dict]) -> str:
    """The user content of the LAST respond LLM call (after classify)."""
    return mock_openai_chat[-1]["messages"][-1]["content"]


# ---------------------------------------------------------------------------
# CM-7 — memory context injected before respond
# ---------------------------------------------------------------------------


def test_cm7_context_injected_for_returning_customer(mock_openai_chat):
    _seed_kb_doc("cuanto cuesta la revision anual 15000")
    conv_id, customer_id = _start_conversation()
    _seed_customer_memo(customer_id, "Cliente comento que ya intento varias reparaciones")

    replies = _turn(conv_id, "cuanto cuesta la revision anual", "wamid.mem0")

    assert replies  # the reply flow completed and was not blocked
    user = _respond_user_content(mock_openai_chat)
    assert "<memory>" in user
    assert "</memory>" in user
    assert "reparaciones" in user  # the memo content reached the LLM prompt


def test_cm7_empty_context_on_first_contact_not_blocked(mock_openai_chat):
    _seed_kb_doc("cuanto cuesta la revision anual 15000")
    conv_id, _ = _start_conversation()

    replies = _turn(conv_id, "cuanto cuesta la revision anual", "wamid.mem1")

    assert replies  # first contact: reply flow continues normally (CM-7)
    user = _respond_user_content(mock_openai_chat)
    assert "<memory>" not in user  # nothing stored -> no memory block injected


# ---------------------------------------------------------------------------
# CM-8 — per-turn persistence flushed and seen on the next turn
# ---------------------------------------------------------------------------


def test_cm8_session_persisted_and_seen_next_turn(mock_openai_chat):
    _seed_kb_doc("cuanto cuesta la revision anual 15000")
    conv_id, customer_id = _start_conversation()

    _turn(conv_id, "cuanto cuesta la revision anual", "wamid.p1")

    # MEM/CM-8: the turn's session memory was flushed before END
    with SessionLocal() as session:
        session_memory = memory_service.get_by_key(
            session, scope="customer", entity_id=str(customer_id), topic_key="session"
        )
        assert session_memory is not None, "per-turn session memory not persisted"

    # a subsequent turn sees the previous exchange in its context (CM-8)
    _turn(conv_id, "cuanto cuesta la revision anual tambien", "wamid.p2")

    user = _respond_user_content(mock_openai_chat)
    assert "<memory>" in user
    assert "revision anual" in user  # previous turn's content is present

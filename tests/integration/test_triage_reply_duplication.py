"""Regression: the customer must receive the CM-1 greeting once, not twice.

Why this file exists
--------------------
`build_graph` adds the compiled `research_triage` sub-graph as a node with no explicit
input schema (`app/chat/graph.py:192`), and the sub-graph is compiled over the **same**
`ConversationState` (`app/chat/subgraphs/research_triage.py:152`). `replies` carries an
`add` reducer (`app/chat/state.py:175`), so LangGraph hands the sub-graph the parent's
`replies` — already holding the greeting — and merging the sub-graph's final state back
re-adds them.

Measured on the real path: 7 of 52 turns returned `[greeting, greeting, reply]`, 5 of them
answers. `receive` was instrumented and runs once, so this is the state merge and not node
execution. See `odd/tasks/triage-reply-duplication.md` (F9) and
`odd/tasks/kb-answer-fidelity.md`.
"""

import psycopg
import pytest
from sqlalchemy import select

from app.chat.graph import run_conversation  # noqa: E402
from app.chat.state import get_or_create_conversation  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    DocumentFormat,
    KbVisibility,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services import kb as kb_service  # noqa: E402
from app.services.customers import get_or_create_customer  # noqa: E402
from app.services.settings import MESSAGE_DEFAULTS  # noqa: E402
from _testdb import admin_database_url  # noqa: E402

ADMIN_DB_URL = admin_database_url()
# A turn that states a need gets the short greeting, fused with the answer (CM-1).
GREETING = MESSAGE_DEFAULTS["greeting_short"]
GROUNDED_MARKER = "Segun el manual de Lumat"

# Phrases the mocked classifier maps to intents (`tests/integration/conftest.py:120-141`).
# `valores` routes through the research_triage sub-graph; `calefont` routes to capture and
# never enters it. The pair is what separates "the merge was fixed" from "greetings were
# suppressed".
VALORES_QUERY = "cuanto cuesta la revision anual"
CALEFONT_QUERY = "mi calefont no enciende"
VALORES_DOC = "cuanto cuesta la revision anual de calefont: 15000 pesos"


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    """Reset chat + KB tables before every test (shared test DB)."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE settings, kb_chunks, kb_documents, audit_log, conversation_events, "
            "cases, messages, conversations, customer_notes, customers "
            "RESTART IDENTITY CASCADE"
        )
    yield


def _seed_kb_doc(text: str) -> None:
    """Ingest the way the panel does: no `source_meta`."""
    with SessionLocal() as session:
        kb_service.ingest_document(
            session,
            title="Manual",
            fmt=DocumentFormat.MD,
            content=text.encode(),
            visibility=KbVisibility.CUSTOMER,
        )
        session.commit()


def _start_conversation() -> int:
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56912345678")
        conv = get_or_create_conversation(session, customer, "+56912345678")
        session.commit()
        return conv.id


def _turn(conv_id: int, text: str, wamid: str) -> list[str]:
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


def test_valores_turn_greets_once_and_still_answers(mock_openai_chat):
    """The regression: the sub-graph path must not duplicate the parent's replies.

    Before the fix this turn returned `[greeting, greeting, answer]`. Under the
    first-turn contract (CM-1) the greeting and the answer travel as ONE message,
    so the guard is that neither is duplicated inside it — a "fix" that dropped
    the answer would fail the marker assertion too.
    """
    _seed_kb_doc(VALORES_DOC)
    conv_id = _start_conversation()
    replies = _turn(conv_id, VALORES_QUERY, "wamid.dup.1")

    assert len(replies) == 1, f"expected one fused message: {replies!r}"
    assert replies[0].count(GREETING) == 1, f"greeting duplicated: {replies!r}"
    assert replies[0].count(GROUNDED_MARKER) == 1, f"answer duplicated: {replies!r}"
    assert replies[0].startswith(GREETING + "\n\n"), f"greeting not fused: {replies!r}"


def test_non_subgraph_turn_is_unchanged(mock_openai_chat):
    """Control: a turn that never enters the sub-graph returns one fused message.

    Its job is to fail if the fix flattens every path instead of correcting the
    boundary — the capture prompt proves the answer survived the fusion.
    """
    conv_id = _start_conversation()
    replies = _turn(conv_id, CALEFONT_QUERY, "wamid.dup.2")

    assert len(replies) == 1, f"expected one fused message: {replies!r}"
    assert replies[0].count(GREETING) == 1, f"greeting duplicated: {replies!r}"
    assert "¿Cuál es tu nombre?" in replies[0], f"the capture prompt was lost: {replies!r}"

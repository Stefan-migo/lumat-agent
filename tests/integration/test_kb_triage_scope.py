"""Regression: the valores/postventa KB must be reachable from the production path.

Why this file exists
--------------------
The `research_triage` sub-graph owns the `valores`/`postventa` intents and used to
pass `scope=["valores", "postventa"]` into `kb.retrieve`, which filters chunks on
`source_meta["category"]`. No production path writes that field — the panel upload
calls `ingest_document` with no `source_meta`
(`app/panel/api/routes/kb.py:143-145`), and every new version is stored with
`source_meta=None` (`app/services/kb.py:235`). The filter therefore returned zero
chunks for every document a client could upload, and every price or warranty question
escalated to a human. Silently: nothing errored, and the customer received the
ordinary handoff message.

Every existing test that covered this path seeded the category by hand, so the suite
proved the filter worked and never exercised whether anything satisfied it. This file
covers the **production shape** instead: the document is ingested exactly as the panel
ingests it, with no category at all.

See `odd/tasks/kb-triage-scope.md` (the fix) and `odd/tasks/kb-answer-fidelity.md`
(F2, the measurement that found it).
"""

from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import select

from app.chat.graph import run_conversation  # noqa: E402
from app.chat.nodes import respond as respond_node  # noqa: E402
from app.chat.state import ConversationState, get_or_create_conversation  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    DocumentFormat,
    KbChunk,
    KbVisibility,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
    Project,
)
from app.services import kb as kb_service  # noqa: E402
from app.services.customers import get_or_create_customer  # noqa: E402
from _testdb import admin_database_url  # noqa: E402

ADMIN_DB_URL = admin_database_url()

# The mocked respond call echoes the <kb> block (`tests/integration/conftest.py:166-168`).
GROUNDED_MARKER = "Segun el manual de Lumat"
# D18's configured default — what a customer sees when the KB has no answer.
KB_MISS_OFFER = "No tengo ese dato. ¿Prefieres que te tome los datos para coordinar una visita, o que te atienda una persona?"

# A phrase the mocked classifier maps to intent `valores`
# (`tests/integration/conftest.py:135-136`), which routes through research_triage.
VALORES_QUERY = "cuanto cuesta la revision anual"
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


def _seed_like_panel(
    text: str, source_meta: dict | None = None, project_id: int | None = None
) -> None:
    """Ingest a document the way the panel upload does.

    `app/panel/api/routes/kb.py:143-145` passes title, fmt, content, actor and
    visibility and nothing else. `source_meta` is left at its default so the
    production shape — no category — is what this file exercises.
    """
    with SessionLocal() as session:
        kb_service.ingest_document(
            session,
            title="Manual",
            fmt=DocumentFormat.MD,
            content=text.encode(),
            actor="panel-test",
            visibility=KbVisibility.CUSTOMER,
            source_meta=source_meta,
            project_id=project_id,
        )
        session.commit()


def _stored_category() -> str | None:
    with SessionLocal() as session:
        chunk = session.scalars(select(KbChunk).limit(1)).first()
        return (chunk.source_meta or {}).get("category")


def _start_conversation() -> int:
    with SessionLocal() as session:
        customer = get_or_create_customer(session, "+56912345678")
        conv = get_or_create_conversation(session, customer, "+56912345678")
        session.commit()
        return conv.id


def _start_project() -> int:
    with SessionLocal() as session:
        project = Project(
            slug=f"customer-kb-test-{uuid4().hex}",
            name="Customer KB test",
            purpose="Test customer KB isolation",
            purpose_embedding=[0.0] * kb_service.EMBED_DIMS,
        )
        session.add(project)
        session.flush()
        project_id = project.id
        session.commit()
        return project_id


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


def test_valores_intent_reaches_the_kb_from_the_panel_upload_shape(mock_openai_chat):
    """The regression: an uncategorized document must still answer a `valores` query.

    Before the fix this turn produced `HANDOFF_REPLY` with `escalate_reason=kb_miss`,
    even though unscoped retrieval scored the chunk above `min_sim`. The category
    assertion is not decoration — it is the production shape that the scope filter
    required and nothing supplied.
    """
    _seed_like_panel(VALORES_DOC)
    assert _stored_category() is None

    conv_id = _start_conversation()
    replies = _turn(conv_id, VALORES_QUERY, "wamid.scope.1")

    assert any(GROUNDED_MARKER in reply for reply in replies), (
        "the valores intent never reached the KB; replies=" + repr(replies)
    )
    assert KB_MISS_OFFER not in replies


def test_a_category_outside_the_old_scope_no_longer_hides_the_document(mock_openai_chat):
    """Distinguishes 'the scope is gone' from 'the category happened to match'.

    `comunas` was never in `research_triage.kb_scope`, so under the old filter this
    document was unreachable for a `valores` question *even when categorized* — which
    is what made populating the category a partial fix rather than a complete one.
    """
    _seed_like_panel(VALORES_DOC, source_meta={"category": "comunas"})
    assert _stored_category() == "comunas"

    conv_id = _start_conversation()
    replies = _turn(conv_id, VALORES_QUERY, "wamid.scope.2")

    assert any(GROUNDED_MARKER in reply for reply in replies), (
        "a non-matching category still hides the document; replies=" + repr(replies)
    )


def test_customer_paths_exclude_project_documents(mock_openai_chat):
    project_id = _start_project()
    _seed_like_panel(VALORES_DOC, project_id=project_id)
    conv_id = _start_conversation()

    triage_replies = _turn(conv_id, VALORES_QUERY, "wamid.project-only.triage")
    # D18: project-only content stays hidden and the KB miss offers both paths.
    assert triage_replies[-1].endswith(KB_MISS_OFFER)
    assert not any(GROUNDED_MARKER in reply for reply in triage_replies)

    with SessionLocal() as session:
        state = ConversationState.from_db(session, conv_id)
    response = respond_node.respond(state)
    assert response["replies"] == [KB_MISS_OFFER]
    assert "escalate" not in response
    assert not any(
        GROUNDED_MARKER in reply for reply in response.get("replies", [])
    )

"""Runtime coverage for the approval-gated assistant KB write tool (S1).

The WhatsApp bot retrieves with `audience=customer` and `global_only=True`
(`app/chat/nodes/respond.py:305`), so a document the assistant proposes only
changes customer answers when it is customer-visible and global. These tests pin
that consequence instead of the storage shape.
"""

import pytest
from sqlalchemy import select

from app.chat.assistant.approval import consume_approval, issue_approval
from app.chat.assistant.tools.registry import ToolValidationError, execute_tool
from app.db import SessionLocal
from app.models import AuditLog, KbDocument, KbVisibility
from app.services import kb
from app.services.prompts import load_assistant_config

TOOL = "kb.propose_document"
PHRASE = "calefont en departamento revisar piso ventilacion seguridad"


def _whitelist() -> set[str]:
    return set(load_assistant_config().tools_whitelist)


def _approval(arguments: dict) -> dict:
    from app.chat.assistant.tools.registry import get_tool

    # Mirror the planner: it issues the approval over the arguments the boundary will
    # digest, so a tool with a defaulted field would otherwise never match.
    normalized = get_tool(TOOL).args_model.model_validate(arguments).model_dump()
    plan = {"tool": TOOL, "arguments": normalized}
    approval = issue_approval(plan)
    assert consume_approval(approval, approval["token"]) is True
    return approval


def test_kb_propose_document_ingests_an_approved_customer_document(fake_embedder):
    arguments = {"title": "Calefont en departamento", "content": PHRASE, "visibility": "customer"}
    with SessionLocal() as session:
        result = execute_tool(
            session,
            TOOL,
            arguments,
            approval=_approval(arguments),
            whitelist=_whitelist(),
            role="admin",
        )
        session.commit()

    assert result["status"] == "completed"
    assert result["read_only"] is False
    assert result["result"]["visible_to_whatsapp"] is True
    assert result["result"]["chunks"] >= 1
    document_id = result["result"]["document_id"]

    with SessionLocal() as session:
        doc = session.get(KbDocument, document_id)
        assert doc.visibility is KbVisibility.CUSTOMER
        assert doc.project_id is None
        assert session.scalar(
            select(AuditLog).where(
                AuditLog.action == "kb.document_ingest", AuditLog.actor == "assistant"
            )
        ) is not None
        # The bot's own retrieval filters: customer audience, global only.
        hits = kb.retrieve(
            session, PHRASE, audience=KbVisibility.CUSTOMER, global_only=True
        )

    assert document_id in {hit["document_id"] for hit in hits}


def test_kb_propose_document_without_approval_writes_nothing(fake_embedder):
    arguments = {"title": "Sin aprobación", "content": PHRASE, "visibility": "customer"}
    with SessionLocal() as session:
        with pytest.raises(ToolValidationError) as refused:
            execute_tool(
                session,
                TOOL,
                arguments,
                whitelist=_whitelist(),
                role="admin",
            )
        assert "requires consumed exact approval" in str(refused.value)
        assert session.scalar(select(KbDocument)) is None


def test_kb_propose_document_internal_document_stays_out_of_the_customer_audience(
    fake_embedder,
):
    arguments = {
        "title": "Calefont interno",
        "content": PHRASE,
        "visibility": "internal",
    }
    with SessionLocal() as session:
        result = execute_tool(
            session,
            TOOL,
            arguments,
            approval=_approval(arguments),
            whitelist=_whitelist(),
            role="admin",
        )
        session.commit()

    assert result["result"]["visible_to_whatsapp"] is False
    document_id = result["result"]["document_id"]

    with SessionLocal() as session:
        customer_hits = kb.retrieve(
            session, PHRASE, audience=KbVisibility.CUSTOMER, global_only=True
        )
        internal_hits = kb.retrieve(session, PHRASE, audience=None)

    assert document_id not in {hit["document_id"] for hit in customer_hits}
    assert document_id in {hit["document_id"] for hit in internal_hits}


def test_kb_propose_document_refuses_a_duplicate_title(fake_embedder):
    arguments = {"title": "Calefont en departamento", "content": PHRASE, "visibility": "customer"}
    with SessionLocal() as session:
        execute_tool(
            session,
            TOOL,
            arguments,
            approval=_approval(arguments),
            whitelist=_whitelist(),
            role="admin",
        )
        session.commit()

    with SessionLocal() as session:
        with pytest.raises(ToolValidationError) as refused:
            execute_tool(
                session,
                TOOL,
                arguments,
                approval=_approval(arguments),
                whitelist=_whitelist(),
                role="admin",
            )
        assert "already exists" in str(refused.value)
        assert len(list(session.scalars(select(KbDocument)))) == 1

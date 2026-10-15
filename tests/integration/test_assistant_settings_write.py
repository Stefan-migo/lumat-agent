"""Runtime coverage for the approval-gated assistant settings write tool."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.chat.assistant.approval import consume_approval, issue_approval
from app.chat.assistant.tools.registry import ToolValidationError, execute_tool
from app.db import SessionLocal
from app.models import AuditLog, InternalChatMessage, InternalChatThread, User
from app.services.agent_chat import approve_plan
from app.services.prompts import load_assistant_config
from app.services.settings import get_setting
from app.services.users import hash_password


def _whitelist() -> set[str]:
    return set(load_assistant_config().tools_whitelist)


def _approval(arguments: dict) -> dict:
    plan = {"tool": "settings.update", "arguments": arguments}
    approval = issue_approval(plan)
    assert consume_approval(approval, approval["token"]) is True
    return approval


def test_settings_update_applies_an_approved_change_and_audits(migrated_db):
    with SessionLocal() as session:
        arguments = {"key": "tone.style", "value": "formal"}
        result = execute_tool(
            session,
            "settings.update",
            arguments,
            approval=_approval(arguments),
            whitelist=_whitelist(),
            role="admin",
        )
        session.commit()

        assert result["status"] == "completed"
        assert result["read_only"] is False
        assert result["result"] == {"key": "tone.style", "value": "formal", "updated": True}
        assert get_setting(session, "tone.style") == "formal"
        audit = session.scalar(
            select(AuditLog).where(
                AuditLog.action == "settings.change", AuditLog.entity_id == "tone.style"
            )
        )
        assert audit is not None
        assert audit.actor == "assistant"
        assert audit.after == {"value": "formal"}


def test_settings_update_without_approval_is_refused(migrated_db):
    with SessionLocal() as session:
        with pytest.raises(ToolValidationError):
            execute_tool(
                session,
                "settings.update",
                {"key": "tone.style", "value": "formal"},
                whitelist=_whitelist(),
                role="admin",
            )
        assert get_setting(session, "tone.style") == "cercano"


def test_settings_update_refuses_a_key_outside_the_allowlist(migrated_db):
    with SessionLocal() as session:
        arguments = {"key": "cost.daily_limit", "value": 0}
        with pytest.raises(ToolValidationError):
            execute_tool(
                session,
                "settings.update",
                arguments,
                approval=_approval(arguments),
                whitelist=_whitelist(),
                role="admin",
            )
        assert get_setting(session, "cost.daily_limit") == 5.00


def test_settings_update_refuses_an_invalid_value(migrated_db):
    with SessionLocal() as session:
        arguments = {"key": "hours.timezone", "value": "Marte/Crater"}
        with pytest.raises(ToolValidationError):
            execute_tool(
                session,
                "settings.update",
                arguments,
                approval=_approval(arguments),
                whitelist=_whitelist(),
                role="admin",
            )
        assert get_setting(session, "hours.timezone") == "America/Santiago"


def test_settings_update_is_denied_to_non_admin_roles(migrated_db):
    with SessionLocal() as session:
        arguments = {"key": "tone.style", "value": "formal"}
        approval = _approval(arguments)
        with pytest.raises(ToolValidationError):
            execute_tool(
                session,
                "settings.update",
                arguments,
                approval=approval,
                whitelist=_whitelist(),
                role="operador",
            )


def test_settings_update_applies_through_the_approval_loop(migrated_db):
    suffix = uuid4().hex[:10]
    with SessionLocal() as session:
        user = User(
            username=f"settings-loop-{suffix}",
            password_hash=hash_password("pass"),
            role="admin",
        )
        session.add(user)
        session.flush()
        run_id = f"settings-loop-{suffix}"
        plan = {
            "tool": "settings.update",
            "arguments": {"key": "messages.farewell", "value": "Nos vemos."},
            "requires_approval": True,
        }
        approval = issue_approval(plan)
        thread = InternalChatThread(
            user_id=user.id,
            active_run_id=run_id,
            current_plan=plan,
            assistant_state={"stage": "approval_pending", "approval": approval, "actor_role": "admin"},
        )
        session.add(thread)
        session.flush()
        session.add(
            InternalChatMessage(
                thread_id=thread.id,
                author="admin",
                content="change the farewell",
                status="approval_pending",
                assistant_metadata={"run_id": run_id, "approval": approval},
            )
        )
        session.commit()

        message = approve_plan(session, thread, user, run_id, approval["token"])
        session.commit()

        assert message is not None
        assert get_setting(session, "messages.farewell") == "Nos vemos."


def test_settings_update_refuses_an_approval_bound_to_other_arguments(migrated_db):
    with SessionLocal() as session:
        approval = _approval({"key": "tone.style", "value": "formal"})
        with pytest.raises(ToolValidationError):
            execute_tool(
                session,
                "settings.update",
                {"key": "messages.farewell", "value": "HACKED"},
                approval=approval,
                whitelist=_whitelist(),
                role="admin",
            )
        assert get_setting(session, "messages.farewell") != "HACKED"


def test_settings_update_refuses_an_unconsumed_approval(migrated_db):
    with SessionLocal() as session:
        plan = {"tool": "settings.update", "arguments": {"key": "tone.style", "value": "formal"}}
        with pytest.raises(ToolValidationError):
            execute_tool(
                session,
                "settings.update",
                plan["arguments"],
                approval=issue_approval(plan),
                whitelist=_whitelist(),
                role="admin",
            )
        assert get_setting(session, "tone.style") == "cercano"


def test_approved_write_reenters_the_graph_and_responds(migrated_db, monkeypatch):
    """T1: the approval path re-enters the assistant graph, so an approved write ends
    with a responder-produced message instead of the canned `Tool ... completed.` line."""
    from app.chat.assistant import nodes as assistant_nodes

    class _Completions:
        def create(self, **kwargs):
            if kwargs.get("stream"):
                return [SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Listo, actualicé la despedida."))])]
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="{}"))])

    fake = SimpleNamespace(chat=SimpleNamespace(completions=_Completions()))
    monkeypatch.setattr(assistant_nodes, "_assistant_client", lambda: fake)

    suffix = uuid4().hex[:10]
    with SessionLocal() as session:
        user = User(username=f"settings-reentry-{suffix}", password_hash=hash_password("pass"), role="admin")
        session.add(user)
        session.flush()
        run_id = f"settings-reentry-{suffix}"
        plan = {
            "tool": "settings.update",
            "arguments": {"key": "messages.farewell", "value": "Nos vemos."},
            "requires_approval": True,
        }
        approval = issue_approval(plan)
        thread = InternalChatThread(
            user_id=user.id,
            active_run_id=run_id,
            current_plan=plan,
            assistant_state={"stage": "approval_pending", "approval": approval, "actor_role": "admin"},
        )
        session.add(thread)
        session.flush()
        session.add(InternalChatMessage(
            thread_id=thread.id, author="admin", content="change the farewell",
            status="approval_pending", assistant_metadata={"run_id": run_id, "approval": approval},
        ))
        session.commit()

        message = approve_plan(session, thread, user, run_id, approval["token"])
        session.commit()

        assert message is not None
        assert get_setting(session, "messages.farewell") == "Nos vemos."
        agent_message = session.scalar(
            select(InternalChatMessage).where(
                InternalChatMessage.thread_id == thread.id, InternalChatMessage.author == "agent"
            )
        )
        assert agent_message is not None
        assert agent_message.content == "Listo, actualicé la despedida."

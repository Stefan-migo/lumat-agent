"""Runtime coverage for the approved assistant automation tool path."""

from uuid import uuid4

from sqlalchemy import select

from app.chat.assistant.approval import issue_approval
from app.db import SessionLocal
from app.models import AuditLog, AutomationRule, InternalChatMessage, InternalChatThread, User
from app.services import automation
from app.services.agent_chat import approve_plan
from app.services.events import publish_event
from app.services.users import hash_password


def test_approved_assistant_rule_is_persisted_audited_and_worker_visible(migrated_db):
    suffix = uuid4().hex[:10]
    assistant_rule_args = {
        "name": f"Assistant rule {suffix}",
        "event_type": "message.received",
        "conditions": {"text": "assistant-runtime"},
        "channel": "whatsapp",
        "template_event": "message.received",
        "cooldown_seconds": 0,
    }
    ui_rule_args = {
        **assistant_rule_args,
        "name": f"UI rule {suffix}",
        "conditions": {"text": "ui-runtime"},
    }

    with SessionLocal() as session:
        user = User(username=f"assistant-runtime-{suffix}", password_hash=hash_password("pass"), role="admin")
        session.add(user)
        session.flush()
        automation.create_rule(session, ui_rule_args, actor=user.username)

        run_id = f"runtime-{suffix}"
        plan = {"tool": "automation.create_rule", "arguments": assistant_rule_args, "requires_approval": True}
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
            thread_id=thread.id,
            author="admin",
            content="create this automation",
            status="approval_pending",
            assistant_metadata={"run_id": run_id, "approval": approval},
        ))
        session.commit()

        message = approve_plan(session, thread, user, run_id, approval["token"])
        assert message is not None
        session.commit()

        assistant_rule = session.scalar(
            select(AutomationRule).where(AutomationRule.name == assistant_rule_args["name"])
        )
        assert assistant_rule is not None
        assert assistant_rule.created_by == "assistant"
        names = session.scalars(select(AutomationRule.name).order_by(AutomationRule.name)).all()
        assert names == sorted([ui_rule_args["name"], assistant_rule_args["name"]])
        audit = session.scalar(
            select(AuditLog).where(
                AuditLog.action == "automation.rule.create",
                AuditLog.entity_id == str(assistant_rule.id),
            )
        )
        assert audit is not None
        assert audit.actor == "assistant"

        event = publish_event(
            session,
            event_type="message.received",
            entity_type="message",
            entity_id=f"runtime-{suffix}",
            payload={"phone": "+56911111111", "text": "assistant-runtime"},
            dedupe_key=f"runtime:{suffix}",
        )
        assert automation.evaluate_event(session, event) == [assistant_rule.id]
        session.commit()

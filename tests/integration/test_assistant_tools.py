"""Runtime coverage for the approved assistant automation tool path."""

from uuid import uuid4

from sqlalchemy import select

from app.chat.assistant.approval import issue_approval
from app.db import SessionLocal
from app.models import AuditLog, AutomationInstallation, AutomationRule, InternalChatMessage, InternalChatThread, User
from app.services import automation
from app.services.agent_chat import approve_plan
from app.services.events import publish_event
from app.services.users import hash_password


def test_approved_assistant_rule_is_persisted_audited_and_worker_visible(migrated_db):
    suffix = uuid4().hex[:10]
    assistant_rule_args = {"recipe_id": "appointment_confirmation", "parameters": {"channel": "whatsapp"}}

    with SessionLocal() as session:
        user = User(username=f"assistant-runtime-{suffix}", password_hash=hash_password("pass"), role="admin")
        session.add(user)
        session.flush()
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

        installation = session.scalar(select(AutomationInstallation).where(
            AutomationInstallation.recipe_id == "appointment_confirmation"
        ))
        assert installation is not None
        assert installation.enabled is True
        assistant_rule = session.scalar(select(AutomationRule).where(AutomationRule.installation_id == installation.id))
        assert assistant_rule is not None
        assert assistant_rule.installation_id == installation.id
        assert assistant_rule.enabled is True
        assert assistant_rule.created_by == "assistant"
        audit = session.scalar(
            select(AuditLog).where(
                AuditLog.action == "automation.installation.create",
                AuditLog.entity_id == str(installation.id),
            )
        )
        assert audit is not None
        assert audit.actor == "assistant"

        event = publish_event(
            session,
            event_type="appointment.booked",
            entity_type="appointment",
            entity_id=f"runtime-{suffix}",
            payload={"phone": "+56911111111"},
            dedupe_key=f"runtime:{suffix}",
        )
        assert automation.evaluate_event(session, event) == [assistant_rule.id]
        session.commit()

"""Runtime coverage for approval-gated assistant settings history reverts (S5)."""

import pytest

from app.chat.assistant.approval import consume_approval, issue_approval
from app.chat.assistant.tools.registry import ToolValidationError, execute_tool
from app.db import SessionLocal
from app.services import settings as settings_service
from app.services.prompts import load_assistant_config

TOOL = "settings.revert"


def _whitelist() -> set[str]:
    return set(load_assistant_config().tools_whitelist)


def _approval(arguments: dict) -> dict:
    plan = {"tool": TOOL, "arguments": arguments}
    approval = issue_approval(plan)
    assert consume_approval(approval, approval["token"]) is True
    return approval


def _revert(session, arguments: dict):
    return execute_tool(
        session,
        TOOL,
        arguments,
        approval=_approval(arguments),
        whitelist=_whitelist(),
        role="admin",
    )


def test_revert_restores_recorded_version_read_by_chat_accessor(migrated_db):
    with SessionLocal() as session:
        settings_service.set_setting(session, "tone.style", "formal", actor="test")
        settings_service.set_setting(session, "tone.style", "directo", actor="test")
        session.commit()

        result = _revert(session, {"key": "tone.style", "version": 1})
        session.commit()

        assert result["status"] == "completed"
        assert result["read_only"] is False
        assert result["result"] == {
            "key": "tone.style", "version": 1, "value": "formal", "reverted": True,
        }
        assert settings_service.get_tone(session) == "formal"


def test_revert_version_zero_deletes_row_and_restores_builtin_default(migrated_db):
    with SessionLocal() as session:
        settings_service.set_setting(session, "tone.style", "formal", actor="test")
        session.commit()

        result = _revert(session, {"key": "tone.style", "version": 0})
        session.commit()

        assert result["result"] == {
            "key": "tone.style", "version": 0, "value": None, "reverted": True,
        }
        assert settings_service.get_setting(session, "tone.style") == settings_service.SETTINGS_DEFAULTS["tone.style"]


def test_revert_refusals_leave_stored_value_unchanged(migrated_db):
    with SessionLocal() as session:
        settings_service.set_setting(session, "tone.style", "formal", actor="test")
        settings_service.set_setting(session, "tone.style", "directo", actor="test")
        session.commit()
        before = settings_service.get_setting(session, "tone.style")

        with pytest.raises(ToolValidationError, match="setting key is not assistant-writable"):
            _revert(session, {"key": "notify.smtp_host", "version": 1})
        assert settings_service.get_setting(session, "tone.style") == before

        with pytest.raises(ToolValidationError, match="version.*not recorded|not recorded.*version"):
            _revert(session, {"key": "tone.style", "version": 99})
        assert settings_service.get_setting(session, "tone.style") == before


def test_revert_without_approval_writes_nothing(migrated_db):
    with SessionLocal() as session:
        settings_service.set_setting(session, "tone.style", "formal", actor="test")
        session.commit()
        before = settings_service.get_setting(session, "tone.style")

        with pytest.raises(ToolValidationError):
            execute_tool(
                session,
                TOOL,
                {"key": "tone.style", "version": 0},
                whitelist=_whitelist(),
                role="admin",
            )

        assert settings_service.get_setting(session, "tone.style") == before

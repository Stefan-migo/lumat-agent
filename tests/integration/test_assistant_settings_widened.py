"""Runtime coverage for the widened assistant settings allowlist (S2).

Each test proposes one of the fourteen new behaviour levers through the same
approval-gated tool and then reads the effect through the public accessor the
chat nodes themselves use, so a stored row that nothing reads cannot pass.
"""

import pytest

from app.chat.assistant.approval import consume_approval, issue_approval
from app.chat.assistant.tools.registry import ToolValidationError, execute_tool
from app.db import SessionLocal
from app.models import AuditLog
from app.services import settings as settings_service
from app.services.prompts import load_assistant_config

TOOL = "settings.update"


def _whitelist() -> set[str]:
    return set(load_assistant_config().tools_whitelist)


def _approval(arguments: dict) -> dict:
    plan = {"tool": TOOL, "arguments": arguments}
    approval = issue_approval(plan)
    assert consume_approval(approval, approval["token"]) is True
    return approval


def _propose(session, key: str, value):
    arguments = {"key": key, "value": value}
    return execute_tool(
        session,
        TOOL,
        arguments,
        approval=_approval(arguments),
        whitelist=_whitelist(),
        role="admin",
    )


def test_scope_rules_change_redirects_that_category():
    with SessionLocal() as session:
        assert settings_service.get_scope_mode(session, "instalacion") == "bot_resolve"
        result = _propose(session, "scope_rules", {"instalacion": "always_escalate"})
        session.commit()

        assert result["status"] == "completed"
        assert settings_service.get_scope_mode(session, "instalacion") == "always_escalate"
        assert settings_service.get_scope_mode(session, "consulta") == "bot_resolve"


def test_emergency_keywords_change_reaches_the_gate_list():
    with SessionLocal() as session:
        _propose(session, "emergency.keywords", ["piloto apagado", "olor a gas"])
        session.commit()

        assert settings_service.get_emergency_keywords(session) == [
            "piloto apagado",
            "olor a gas",
        ]


def test_conduct_change_reorders_the_capture_and_is_audited():
    order = ["failure", "comuna", "equipment", "availability", "name", "email", "address"]
    with SessionLocal() as session:
        previous = settings_service.get_conduct(session)
        _propose(
            session,
            "chat.conduct",
            {
                "orden": order,
                "redaccion": "llm",
                "max_preguntas_por_mensaje": 1,
                "derivaciones": previous["derivaciones"],
            },
        )
        session.commit()

        conduct = settings_service.get_conduct(session)
        assert conduct["orden"] == order
        assert conduct["redaccion"] == "llm"
        audit = session.query(AuditLog).filter_by(entity_id="chat.conduct").one()
        assert audit.actor == "assistant"


def test_capture_questions_change_is_read_by_its_accessor():
    with SessionLocal() as session:
        fields = settings_service.get_conduct(session)["orden"]
        questions = {field: f"Pregunta para {field}" for field in fields}
        _propose(session, "capture.questions", questions)
        session.commit()

        assert settings_service.get_capture_questions(session) == questions


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("scope_rules", {"instalacion": "bot_resolve_typo"}),
        ("emergency.keywords", []),
        ("emergency.keywords", ["  "]),
        ("chat.conduct", {"orden": ["failure"], "redaccion": "llm", "max_preguntas_por_mensaje": 1}),
        ("cost.daily_limit", 0),
        ("booking.lead_minutes", 0),
    ],
)
def test_a_value_the_panel_would_refuse_is_refused_here(key, value):
    with SessionLocal() as session:
        before = settings_service.get_setting(session, key)
        with pytest.raises(ToolValidationError):
            _propose(session, key, value)
        assert settings_service.get_setting(session, key) == before


@pytest.mark.parametrize("key", ["notify.smtp_host", "smtp_password", "meta_pricing"])
def test_keys_outside_the_allowlist_stay_unwritable(key):
    with SessionLocal() as session:
        with pytest.raises(ToolValidationError) as refused:
            _propose(session, key, "leak")
        assert "not assistant-writable" in str(refused.value)

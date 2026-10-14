"""The planning facilitator overlay applies only to an active planning session (S2)."""

from app.chat.assistant.nodes import _effective_persona
from app.services.prompts import load_assistant_config

ACTIVE = {
    "slug": "budget-review-1",
    "topic": "Budget review",
    "status": "active",
    "opened_at": "2026-10-14T00:00:00Z",
    "closed_at": None,
    "report_key": None,
}
CLOSED = {**ACTIVE, "status": "closed"}


def _state(cortex=None):
    state = {"effective": {"instructions": ""}}
    if cortex is not None:
        state["cortex_session"] = cortex
    return state


def test_active_planning_session_injects_the_facilitator_overlay():
    config = load_assistant_config()

    persona = _effective_persona(_state(ACTIVE), config)

    assert config.persona in persona
    assert "guided brainstorming" in persona
    assert "Do not offer to close" in persona
    assert "Offer the handoff" in persona


def test_absent_or_closed_session_has_no_overlay():
    config = load_assistant_config()

    for state in (_state(), _state(CLOSED)):
        assert "guided brainstorming" not in _effective_persona(state, config)

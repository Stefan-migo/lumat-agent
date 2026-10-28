"""Legacy planning state never overlays the assistant persona."""

from app.chat.assistant.nodes import _effective_persona
from app.services.prompts import load_assistant_config


def test_legacy_cortex_state_does_not_change_effective_persona():
    config = load_assistant_config()
    state = {
        "effective": {"instructions": ""},
        "cortex_session": {"status": "active", "topic": "Legacy topic"},
    }

    assert _effective_persona(state, config) == config.persona

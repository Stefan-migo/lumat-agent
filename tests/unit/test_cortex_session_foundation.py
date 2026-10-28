"""Retired Cortex runtime state is not part of assistant turn validation."""

import app.chat.assistant.state as assistant_state


def test_cortex_session_validator_and_models_are_removed():
    assert not hasattr(assistant_state, "validate_cortex_session")
    assert not hasattr(assistant_state, "CortexSession")
    assert not hasattr(assistant_state, "CortexDecision")
    assert not hasattr(assistant_state, "CortexNote")

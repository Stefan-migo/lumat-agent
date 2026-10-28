"""SDB request wiring remains independent from the retired Cortex runtime."""

from inspect import signature

from app.chat.assistant.graph import run_assistant


def test_sdb_handoff_signal_remains_in_assistant_turn_contract():
    parameters = signature(run_assistant).parameters
    assert "sdb_requested" in parameters
    assert "cortex_session" not in parameters

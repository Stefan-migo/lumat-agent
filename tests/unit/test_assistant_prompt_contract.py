"""Contract guard for the panel assistant persona/prompts (act-first, KB as one source).

The grounding gate lives in the graph nodes (`retrieve_kb`, `guardrails`), not in these prompts
(see `tests/unit/test_assistant_grounding_gate.py`). These assertions pin the prompt-level reversal:
the planner prefers a tool over asking, and the responder no longer gates on `<kb>` alone.
"""

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return " ".join((ROOT / "agent" / rel).read_text(encoding="utf-8").split())


def test_plan_prompt_prefers_tool_over_asking():
    prompt = _read("prompts/assistant_plan.md")
    assert 'Prefer `kind: "tool"`' in prompt
    assert "instead of asking permission" in prompt


def test_respond_prompt_no_longer_gates_on_kb_alone():
    prompt = _read("prompts/assistant_respond.md")
    assert "not a gate" in prompt
    assert "answer only from the bounded evidence in" not in prompt


def test_persona_is_act_first_and_chilean():
    persona = _read("personas/assistant.md")
    assert "CALL THE TOOLS" in persona
    assert "CHILEAN SPANISH" in persona
    assert "never load or execute skills" not in persona


def test_memory_skill_documents_the_handoff_marker():
    skill = _read("skills/assistant/memoria-tukulpan.md")
    assert '"handoff":false' in skill
    assert "continuation point" in skill


def test_persona_tells_when_to_mark_handoff():
    persona = _read("personas/assistant.md")
    assert "handoff" in persona
    assert "continuation point" in persona

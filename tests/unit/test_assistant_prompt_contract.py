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


def test_persona_documents_the_chain_across_a_write():
    """The owner's decision (2026-10-15) reversed the read-only-only loop: the chain now
    crosses a class-A write, so the standing persona must say so."""
    persona = _read("personas/assistant.md")
    assert "read-only steps run in-loop" in persona
    assert "a class-A write pauses for the owner's approval and then continues to the next step" in persona


def test_plan_prompt_carries_follow_up_through_a_write():
    prompt = _read("prompts/assistant_plan.md")
    assert "a later step that depends on what this step" in prompt
    assert "A write step still pauses for the owner's approval" in prompt


def test_tools_skill_documents_the_per_write_approval():
    skill = _read("skills/assistant/tools.md")
    assert "Each write of a chain is approved on its own" in skill
    assert "an approval never carries over to the following plan" in skill


def test_persona_lists_durable_memory_capture_triggers_and_runtime_capture():
    persona = _read("personas/assistant.md")
    for trigger in (
        "completed fix",
        "decision",
        "discovery",
        "configuration change",
        "established pattern",
        "owner preference",
    ):
        assert trigger in persona
    assert "runtime also captures turns deterministically" in persona
    assert "write what is durable, not transcripts" in persona
    assert "You are the Lumat internal executive operator, LumatAgent" in persona
    assert "approval before any write operation except" in persona
    for tool in ("memory.write", "memory.update", "memory.delete", "artifact.save"):
        assert f"`{tool}`" in persona
    assert "When `web.fetch` evidence is present, state only what the fetched page text says and cite the URL that evidence reports after redirects." in persona


def test_memory_skill_lists_write_triggers_and_documents_user_axis():
    skill = _read("skills/assistant/memoria-tukulpan.md")
    for trigger in (
        "completed fix",
        "decision",
        "discovery",
        "configuration change",
        "established pattern",
        "owner preference",
    ):
        assert trigger in skill
    assert 'visibility="user"' in skill
    assert "person's memory" in skill
    assert "readable across projects" in skill
    assert "never another user's memory" in skill
    assert '"handoff":false' in skill


def test_persona_routes_person_facts_to_user_axis_and_project_facts_to_project_axis():
    persona = _read("personas/assistant.md")
    assert "A fact about the person" in persona
    assert "user axis" in persona
    assert "fact about a project" in persona
    assert "project axis" in persona


def test_plan_prompt_allows_memory_write_and_follow_up_together():
    prompt = _read("prompts/assistant_plan.md")
    assert "`memory.write` runs without approval" in prompt
    assert "A turn can both write memory and answer by setting `follow_up: true`" in prompt

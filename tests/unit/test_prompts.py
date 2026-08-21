"""PR 1 tests — `agent/` declarative tree (config-agente-lumat).

Assertions, mapped to requirements:

- AC-3 / AC-6: every `agent/personas/*.md` file is byte-identical to the
  untouched node constant it replaces (`respond.SYSTEM_PROMPT`,
  `respond.BRIEF_MODE_SUFFIX`, `classify_intent.SYSTEM_PROMPT`,
  `summary.SYSTEM_PROMPT`). No node file is edited in this PR, so the constants
  are the frozen source of truth for our equality tests.
- AC-1 / AC-5: `agent/prompts/*.md` templates exist with `{{}}` slots.
- AC-6: `agent/skills/*.md` references exist for the four deterministic gate
  skills and are declared reference-only (never rendered into a prompt slot).
- AC-4: `agent/registry.yaml` parses with pyyaml to exactly one agent
  `orchestrator` and carries the D-A7 schema fields; nothing instantiates a
  tools/KB/memory rule from it (there is no runtime registry consumer).

All assertions read real files from the `agent/` tree relative to the repo
root, so they fail (FileNotFoundError / mismatch) until the tree exists — this
is the RED state for PR 1.
"""

import logging
import pathlib

import pytest
import yaml


def _read(repo_root: pathlib.Path, rel: str) -> str:
    return (repo_root / "agent" / rel).read_text(encoding="utf-8")


# Loader itself: must resolve keys against the repo-root agent/ directory.
AGENT_KEYS = (
    "personas/orchestrator.md",
    "personas/orchestrator_brief.md",
    "personas/classify.md",
    "personas/summary.md",
    "prompts/respond.md",
    "prompts/classify.md",
    "prompts/summary.md",
)


# --- AC-3: personas byte-identical to untouched node constants ----------------

def test_personas_static_matches_node_constants(repo_root):
    from app.chat.nodes.respond import BRIEF_MODE_SUFFIX, SYSTEM_PROMPT

    assert _read(repo_root, "personas/orchestrator.md") == SYSTEM_PROMPT
    assert _read(repo_root, "personas/orchestrator_brief.md") == BRIEF_MODE_SUFFIX


def test_personas_classify_matches_node_constant(repo_root):
    from app.chat.nodes.classify_intent import SYSTEM_PROMPT

    assert _read(repo_root, "personas/classify.md") == SYSTEM_PROMPT


def test_personas_summary_matches_node_constant(repo_root):
    from app.chat.nodes.summary import SYSTEM_PROMPT

    assert _read(repo_root, "personas/summary.md") == SYSTEM_PROMPT


# --- AC-5: prompt templates are static files with {{}} slots -----------------

def test_prompt_respond_template(repo_root):
    assert _read(repo_root, "prompts/respond.md") == (
        "<kb>{{kb_text}}</kb>\n\n<user_input>{{user_input}}</user_input>"
    )


def test_prompt_classify_template(repo_root):
    assert _read(repo_root, "prompts/classify.md") == (
        "<user_input>{{user_input}}</user_input>"
    )


def test_prompt_summary_template_has_all_slots(repo_root):
    content = _read(repo_root, "prompts/summary.md")
    for slot in (
        "name",
        "phone",
        "conversation_id",
        "turn",
        "intent",
        "case",
        "captured",
        "escalate",
        "escalate_reason",
    ):
        assert "{{%s}}" % slot in content, f"missing {{{{{slot}}}}} slot in summary template"


def test_persona_files_have_no_slots(repo_root):
    # AC-5: personas are static — no {{}} placeholders.
    for rel in (
        "personas/orchestrator.md",
        "personas/orchestrator_brief.md",
        "personas/classify.md",
        "personas/summary.md",
    ):
        assert "{{" not in _read(repo_root, rel), f"persona {rel} must not contain slots"


# --- AC-6: skills are reference-only files, never rendered -------------------

def test_skill_reference_files_exist(repo_root):
    for rel in ("skills/sdb.md", "skills/emergency.md", "skills/handoff.md", "skills/capture.md"):
        assert _read(repo_root, rel).strip(), f"skill reference {rel} is empty"


# --- AC-4: registry.yaml data-only, exactly one orchestrator ------------------

def test_registry_declares_exactly_one_orchestrator(repo_root):
    with (repo_root / "agent" / "registry.yaml").open(encoding="utf-8") as fh:
        registry = yaml.safe_load(fh)

    assert isinstance(registry, dict)
    # D-A7 schema: a single `agent:` declaration (one orchestrator agent).
    agent = registry.get("agent")
    assert isinstance(agent, dict), "registry must declare exactly one agent"
    assert agent["name"] == "orchestrator"
    assert agent["persona"] == "personas/orchestrator.md"
    assert set(agent["skills"]) == {"sdb", "emergency", "handoff", "capture"}
    assert isinstance(agent["tools_whitelist"], list)
    for key in ("kb_scope", "memoria_scope"):
        assert key in agent
    assert agent.get("model")


def test_registry_has_no_runtime_consumer(repo_root):
    # AC-4: the registry must not enforce anything today — there is no loader
    # importing it. Guard against a runtime reader being wired in this PR.
    for prog in ("app/services/prompts.py", "app/chat/nodes/respond.py"):
        path = repo_root / prog
        if path.exists():
            text = path.read_text(encoding="utf-8")
            assert "registry.yaml" not in text, f"{prog} must not read registry"


# --- PR 2: loader (app/services/prompts.py) --------------------------------

from app.services import prompts  # noqa: E402  (loader not yet implemented → RED)


def test_load_returns_file_verbatim(repo_root):
    # AC-2 "File present": load() returns the agent/ file byte-for-byte.
    for key in AGENT_KEYS:
        assert prompts.load(key) == _read(repo_root, key), f"load({key}) != file"


def test_load_missing_key_falls_back_to_literal(tmp_path, monkeypatch, caplog):
    # AC-2 "File missing": when an agent/ file is absent the loader returns the
    # frozen FALLBACKS literal and logs a warning (no partial-tree crash).
    # Point the loader at an empty dir so every known key reports "missing".
    key = "personas/orchestrator.md"
    monkeypatch.setattr(prompts, "_AGENT_DIR", tmp_path)
    prompts.load.cache_clear()

    with caplog.at_level(logging.WARNING, logger="app.services.prompts"):
        result = prompts.load(key)

    assert result == prompts.FALLBACKS[key]
    assert any(r.levelno == logging.WARNING for r in caplog.records)


def test_fallbacks_equal_agent_files(repo_root):
    # AC-3: the frozen FALLBACKS literals are byte-identical to agent/*.md.
    for key in AGENT_KEYS:
        assert prompts.FALLBACKS[key] == _read(repo_root, key), f"FALLBACKS {key} != file"


def test_render_substitutes_all_slots():
    # AC-5 "All variables provided": every {{name}} is replaced.
    out = prompts.render(
        "prompts/respond.md",
        kb_text="<kb text>",
        user_input="hola",
    )
    assert out == "<kb><kb text></kb>\n\n<user_input>hola</user_input>"


def test_render_missing_var_raises():
    # AC-5 "Missing variable": rendering without a required var raises.
    with pytest.raises(KeyError):
        prompts.render("prompts/respond.md", kb_text="x")


def test_render_unknown_var_raises():
    # AC-5: a typo'd extra var is rejected too.
    with pytest.raises(KeyError):
        prompts.render("prompts/classify.md", user_input="hola", bogus="x")


def test_render_missing_key_raises():
    # render() is for templates; a unknown key with no {{}} is valid only when
    # the key resolves, so an unknown key must raise (fail fast).
    with pytest.raises(KeyError):
        prompts.render("prompts/does_not_exist.md")


def test_render_persona_static_returns_verbatim():
    # AC-5 persona-static guarantee: no {{}} → content returned unchanged.
    persona = prompts.load("personas/summary.md")
    assert "{{" not in persona
    assert prompts.render("personas/summary.md") == persona


def test_render_no_slots_returns_verbatim():
    # A template with zero {{}} returns the file verbatim even with vars given.
    assert prompts.render("personas/classify.md") is not None
    assert prompts.render("personas/classify.md") == prompts.load("personas/classify.md")

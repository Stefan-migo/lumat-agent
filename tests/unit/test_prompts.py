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

import pathlib

import yaml


def _read(repo_root: pathlib.Path, rel: str) -> str:
    return (repo_root / "agent" / rel).read_text(encoding="utf-8")


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

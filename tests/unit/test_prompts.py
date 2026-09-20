"""`agent/` declarative tree + loader coverage (config-agente-lumat).

PR 1 asserted the `agent/*.md` personas matched the then-untouched node
constants. PR 3 deletes those constants (nodes now read through
`prompts.load`/`prompts.render`), so the surviving equality proofs are:

- AC-3: `prompts.FALLBACKS[key]` is byte-identical to each `agent/*.md` file
  (`test_fallbacks_equal_agent_files`) AND the nodes assemble their LLM
  messages from the loader (`test_*_persona_and_template` below).
- AC-1 / AC-5: `agent/prompts/*.md` templates exist with `{{}}` slots, personas
  are static.
- AC-6: `agent/skills/*.md` references exist and are never rendered.
- AC-4: `agent/registry.yaml` parses to exactly one `orchestrator`; no runtime
  registry consumer.
- Task 4.2 / AC-8: no node dead constants remain; the canned reply strings stay
  re-exportable.

Node-wiring tests mock the transient boundaries (openai_client, session_scope,
record_llm_cost) so they run DB-free in the unit suite; the DB-backed integration
and functional suites are the end-to-end behavior-preservation net (task 3.4).
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


# --- AC-3: personas byte-identical to the frozen FALLBACKS+files --------------
# (Node-constant equality lived in PR 1; PR 3 deleted the constants, so the
# surviving proof is FALLBACKS == agent/*.md == loader output, covered below by
# test_fallbacks_equal_agent_files plus the node wiring tests at the bottom.)

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


# --- PR 3: nodes wire their LLM messages through the loader (tasks 3.1-3.3) --
# These prove AC-3 wiring at unit level without a DB: the node assembles the
# exact system persona + rendered template that the loader supplies. The
# transient boundaries (openai_client, session_scope, record_llm_cost) are
# mocked; the DB-backed integration/functional suites are the end-to-end net.
#
# RED-first: `prompts.load`/`prompts.render` do not yet exist inside the node
# modules until task 3.1-3.3 wires them, so these tests fail to run the node
# path until the nodes reference the loader.

import contextlib  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from unittest import mock  # noqa: E402

from app.chat.nodes import classify_intent as _ci  # noqa: E402
from app.chat.nodes import respond as _rn  # noqa: E402
from app.chat.nodes import summary as _sm  # noqa: E402


class _FakeCompletion:
    def __init__(self, content: str):
        self.usage = mock.Mock(prompt_tokens=20, completion_tokens=10)
        self.choices = [mock.Mock(message=mock.Mock(content=content))]


class _FakeClient:
    """Mimics openai_client().chat.completions.create capturing the payload.

    The OpenAI client is a dotted attribute chain (`client.chat.completions
    .create(...)`), so `chat`/`completions` are attributes resolving to self.
    """

    def __init__(self, reply_content: str = "ok"):
        self.captured: list[dict] = []
        self._reply_content = reply_content
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        self.captured.append(kwargs)
        return _FakeCompletion(self._reply_content)


def _noop_session_scope():
    """Function-typed stand-in for `with session_scope() as session:`.

    Yielded object is a Mock so summary reads (`session.get`/`session.scalar`)
    and writes (`conv.summary = ...`) succeed without a real DB.
    """
    return contextlib.nullcontext(mock.Mock())


@pytest.fixture
def respond_client():
    """Mock the respond node's boundaries; returns the capturing fake client."""
    client = _FakeClient()
    with (
        mock.patch.object(_rn, "openai_client", return_value=client),
        mock.patch.object(_rn, "session_scope", _noop_session_scope),
        mock.patch.object(_rn, "record_llm_cost", return_value=0),
    ):
        yield client


def test_respond_answer_from_kb_persona_and_template(respond_client):
    # AC-3 static slot unchanged: system == orchestrator persona via loader.
    # AC-3 typed template identical: user == render(prompts/respond.md).
    _rn._answer_from_kb("hola", "chunk uno\nchunk dos", message_id=7)
    call = respond_client.captured[-1]
    assert call["messages"][0]["content"] == prompts.load("personas/orchestrator.md")
    assert call["messages"][1]["content"] == prompts.render(
        "prompts/respond.md", kb_text="chunk uno\nchunk dos", user_input="hola"
    )


def test_respond_answer_from_kb_brief_mode_appends_brief_persona(respond_client):
    # D-A5: brief (80%+ cost limit) appends the brief persona after the base.
    _rn._answer_from_kb("hola", "chunk", message_id=8, brief=True)
    call = respond_client.captured[-1]
    assert call["messages"][0]["content"] == (
        prompts.load("personas/orchestrator.md")
        + prompts.load("personas/orchestrator_brief.md")
    )


def test_respond_answer_from_kb_memory_block_injected(respond_client):
    # CM-7: a stored customer memory is injected as a read-only block beside kb.
    _rn._answer_from_kb(
        "hola", "chunk", message_id=9, memory_context="cliente probó varias reparaciones"
    )
    call = respond_client.captured[-1]
    assert "<memory>" in call["messages"][1]["content"]
    assert "reparaciones" in call["messages"][1]["content"]


@pytest.fixture
def classify_client():
    client = _FakeClient(reply_content='{"intent": "caldera", "service": "caldera", "priority": "media", "status": "abierto", "injection": false}')
    with (
        mock.patch.object(_ci, "openai_client", return_value=client),
        mock.patch.object(_ci, "session_scope", _noop_session_scope),
        mock.patch.object(_ci, "record_llm_cost", return_value=0),
    ):
        yield client


def test_classify_llm_classify_persona_and_template(classify_client):
    # AC-3 static slot unchanged + template identical: persona via loader,
    # user text inside the <user_input> slot (SH-4 input-as-data).
    result = _ci._llm_classify("necesito una caldera", message_id=5)
    call = classify_client.captured[-1]
    assert call["messages"][0]["content"] == prompts.load("personas/classify.md")
    assert call["messages"][1]["content"] == prompts.render(
        "prompts/classify.md", user_input="necesito una caldera"
    )
    assert result["intent"] == "caldera"
    assert result["injection"] is False


def _dummy_state(**overrides):
    base = dict(
        conversation_id=101,
        turn=3,
        intent="calefont",
        case={"id": 9, "service": "calefont"},
        captured={"marca": "Splendid"},
        escalate=True,
        escalate_reason="kb_miss",
        phone="+56911112222",
        window=[],  # unused by _summary_context
    )
    base.update(overrides)
    return mock.Mock(**base)


def test_summary_context_computes_slot_values():
    # Task 3.3: _summary_context returns the exact slot-value dict that render
    # feeds (name falls back to phone when customer has no name).
    customer = SimpleNamespace(name="Juan Perez")
    ctx = _sm._summary_context(_dummy_state(), customer)
    assert ctx["name"] == "Juan Perez"
    assert ctx["phone"] == "+56911112222"
    assert ctx["conversation_id"] == 101
    assert ctx["turn"] == 3
    assert ctx["intent"] == "calefont"
    assert ctx["case"] == {"id": 9, "service": "calefont"}
    assert ctx["captured"] == {"marca": "Splendid"}
    assert ctx["escalate"] is True
    assert ctx["escalate_reason"] == "kb_miss"


def test_summary_context_nameless_falls_back_to_phone():
    # Triangle: customer present but nameless → name uses the phone.
    ctx = _sm._summary_context(_dummy_state(), SimpleNamespace(name=None))
    assert ctx["name"] == "+56911112222"


def test_summary_context_roundtrips_through_template():
    # AC-3 template identical: render(prompts/summary.md, **_summary_context)
    # reproduces the pre-change f-string exactly.
    ctx = _sm._summary_context(_dummy_state(), SimpleNamespace(name="Juan Perez"))
    expected = (
        "Cliente: Juan Perez (telefono +56911112222)\n"
        "Conversacion 101, turno 3\n"
        "Intencion: calefont\n"
        "Clasificacion del caso: {'id': 9, 'service': 'calefont'}\n"
        "Datos capturados: {'marca': 'Splendid'}\n"
        "Escalada: True (kb_miss)"
    )
    assert prompts.render("prompts/summary.md", **ctx) == expected


def test_compose_fallback_summary_uses_fixed_field_order():
    state = _dummy_state(
        case={"service": "calefont"},
        captured={
            "equipment": "Splendid  tiro natural",
            "failure": "no enciende",
            "evidence": "video enviado",
            "availability": "manana en la tarde",
        },
    )

    assert _sm.compose_fallback_summary(state) == (
        "Servicio: calefont. Equipo: Splendid  tiro natural. Problema: no enciende. "
        "Evidencia: video enviado. Disponibilidad: manana en la tarde."
    )


def test_compose_fallback_summary_omits_unknown_and_internal_fields():
    state = _dummy_state(
        case={"service": "unknown"},
        captured={
            "equipment": "unknown",
            "failure": "fuga de agua",
            "evidence": "unknown",
            "availability": "_pending",
            "_pending": "failure",
            "name": "Ana",
            "comuna": "Santiago",
            "address": "Calle 1",
            "consent": True,
        },
        window=[{"text": "RAW-MESSAGE-MUST-NOT-APPEAR"}],
    )

    result = _sm.compose_fallback_summary(state)

    assert result == "Problema: fuga de agua."
    assert "RAW-MESSAGE-MUST-NOT-APPEAR" not in result
    assert "unknown" not in result
    assert all(value not in result for value in ("Ana", "Santiago", "Calle 1"))


def test_compose_fallback_summary_returns_literal_without_usable_fields():
    state = _dummy_state(case={}, captured={"failure": "unknown", "_pending": "failure"})

    assert _sm.compose_fallback_summary(state) == "Solicitud registrada sin detalle del problema."


@pytest.fixture
def summary_client():
    client = _FakeClient(reply_content="resumen del caso")
    with (
        mock.patch.object(_sm, "openai_client", return_value=client),
        mock.patch.object(_sm, "session_scope", _noop_session_scope),
        mock.patch.object(_sm, "record_llm_cost", return_value=0),
    ):
        yield client


def test_summary_generate_summary_persona_and_template(summary_client):
    # AC-3 wire: system == summary persona via loader; user == rendered context.
    state = _dummy_state()
    text = _sm.generate_summary(state, SimpleNamespace(name="Juan Perez"))
    call = summary_client.captured[-1]
    assert call["messages"][0]["content"] == prompts.load("personas/summary.md")
    assert call["messages"][1]["content"] == prompts.render(
        "prompts/summary.md", **_sm._summary_context(state, SimpleNamespace(name="Juan Perez"))
    )
    assert text == "resumen del caso"


def test_generate_summary_empty_model_content_uses_fallback(monkeypatch):
    empty_client = _FakeClient(reply_content="")
    monkeypatch.setattr(_sm, "openai_client", lambda: empty_client)
    monkeypatch.setattr(_sm, "session_scope", _noop_session_scope)
    monkeypatch.setattr(_sm, "record_llm_cost", lambda *args, **kwargs: 0)

    state = _dummy_state(case={"service": "calefont"}, captured={"failure": "no enciende"})

    assert _sm.generate_summary(state, SimpleNamespace(name="Juan Perez")) == (
        "Servicio: calefont. Problema: no enciende."
    )


# --- Task 4.2 / AC-8: no dead constants left; canned replies re-exported ------

def test_node_dead_constants_removed():
    # Task 4.2: the extracted prompt constants are gone from the nodes.
    assert not hasattr(_rn, "SYSTEM_PROMPT")
    assert not hasattr(_rn, "BRIEF_MODE_SUFFIX")
    assert not hasattr(_ci, "SYSTEM_PROMPT")
    assert not hasattr(_sm, "SYSTEM_PROMPT")


def test_canned_replies_still_reexported():
    # AC-8: canned customer-facing strings keep their unchanged values from the
    # same modules tests import them from (import compatibility).
    from app.chat.nodes.handoff import HANDOFF_REPLY

    assert _rn.CANNOT_ANSWER_REPLY.startswith("Lo siento, no puedo responder")
    assert _rn.CLARIFICATION_REPLY.startswith("No entendí tu mensaje")
    assert HANDOFF_REPLY  # import resolves; value non-empty

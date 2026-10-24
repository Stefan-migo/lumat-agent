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
        "<conversation>{{conversation}}</conversation>\n\n"
        "<booking>{{booking}}</booking>\n\n"
        "<fecha>{{fecha}}</fecha>\n\n"
        "<tarifario>{{tarifario}}</tarifario>\n\n"
        "<kb>{{kb_text}}</kb>\n\n"
        "<user_input>{{user_input}}</user_input>\n"
    )


def test_prompt_classify_template(repo_root):
    assert _read(repo_root, "prompts/classify.md") == (
        "<conversation>{{conversation}}</conversation>\n\n"
        "<templates>{{templates}}</templates>\n\n"
        "<user_input>{{user_input}}</user_input>\n"
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
    for rel in ("skills/emergency.md", "skills/handoff.md", "skills/capture.md"):
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
    assert set(agent["skills"]) == {"emergency", "handoff", "capture"}
    assert isinstance(agent["tools_whitelist"], list)
    for key in ("memoria_scope",):
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
    # The bundled-file read is the cached half; `load` is the override-aware
    # wrapper (S12), so the cache lives in `_load_bundled`.
    prompts._load_bundled.cache_clear()

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
        conversation="<prior turns>",
        booking="No booking.",
        fecha="2026-03-15",
        tarifario="Visita técnica: $30.000",
        kb_text="<kb text>",
        user_input="hola",
    )
    assert out == (
        "<conversation><prior turns></conversation>\n\n"
        "<booking>No booking.</booking>\n\n"
        "<fecha>2026-03-15</fecha>\n\n"
        "<tarifario>Visita técnica: $30.000</tarifario>\n\n"
        "<kb><kb text></kb>\n\n<user_input>hola</user_input>\n"
    )


def test_render_missing_var_raises():
    # AC-5 "Missing variable": rendering without a required var raises.
    with pytest.raises(KeyError):
        prompts.render("prompts/respond.md", conversation="", booking="", kb_text="x")


def test_render_unknown_var_raises():
    # AC-5: a typo'd extra var is rejected too.
    with pytest.raises(KeyError):
        prompts.render("prompts/classify.md", conversation="", user_input="hola", bogus="x")


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
from app.chat.state import conversation_transcript  # noqa: E402


def test_conversation_transcript_renders_six_prior_turns_and_excludes_current():
    window = [
        {"direction": "inbound", "text": f"cliente-{index}"}
        if index % 2 == 0
        else {"direction": "outbound", "text": f"asistente-{index}"}
        for index in range(8)
    ]

    assert conversation_transcript(window) == "\n".join(
        f"{'Cliente' if index % 2 == 0 else 'Asistente'}: "
        f"{'cliente' if index % 2 == 0 else 'asistente'}-{index}"
        for index in range(1, 7)
    )
    assert conversation_transcript([window[-1]]) == "(sin mensajes previos)"


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
    with mock.patch.object(
        _rn, "_tarifario_context", return_value=("2026-03-15", "Visita técnica: $30.000")
    ):
        _rn._answer_from_kb(
            "hola", "chunk uno\nchunk dos", message_id=7,
            conversation="(sin mensajes previos)",
            booking="El cliente no tiene ninguna visita agendada.",
        )
    call = respond_client.captured[-1]
    assert call["messages"][0]["content"] == (
        prompts.load("personas/orchestrator.md")
        + "\nResponde con un tono cercano, amable y claro."
    )
    assert call["messages"][1]["content"] == prompts.render(
        "prompts/respond.md", conversation="(sin mensajes previos)",
        booking="El cliente no tiene ninguna visita agendada.",
        fecha="2026-03-15", tarifario="Visita técnica: $30.000",
        kb_text="chunk uno\nchunk dos", user_input="hola"
    )


def test_respond_model_call_receives_conversation_and_booking(respond_client):
    state = SimpleNamespace(
        intent="consulta",
        window=[
            {"direction": "inbound", "text": "Quiero una visita"},
            {"direction": "outbound", "text": "¿Qué día?"},
            {"direction": "inbound", "id": 77, "text": "ya agendé una visita"},
        ],
        booking={"service": "Visita técnica", "label": "06/05/2030 a las 15:30", "status": "booked"},
        turn=3,
        cost_mode="normal",
        memory_context="",
        template_id=None,
        # S4: the turn reached `respond` without a prior retrieval.
        retrieval=None,
    )
    with mock.patch.object(_rn.kb, "retrieve", return_value=[{"content": "chunk"}]):
        _rn.respond(state)
    user_prompt = respond_client.captured[-1]["messages"][1]["content"]
    assert "<conversation>Cliente: Quiero una visita\nAsistente: ¿Qué día?</conversation>" in user_prompt
    assert "<booking>El cliente tiene una visita agendada: Visita técnica el 06/05/2030 a las 15:30 (estado booked).</booking>" in user_prompt


def test_respond_answer_from_kb_brief_mode_appends_brief_persona(respond_client):
    # D-A5: brief (80%+ cost limit) appends the brief persona after the base.
    _rn._answer_from_kb("hola", "chunk", message_id=8, brief=True)
    call = respond_client.captured[-1]
    assert call["messages"][0]["content"] == (
        prompts.load("personas/orchestrator.md")
        + prompts.load("personas/orchestrator_brief.md")
        + "\nResponde con un tono cercano, amable y claro."
    )


def test_respond_answer_from_kb_uses_the_configured_persona(respond_client, monkeypatch):
    # S12: a persona saved from the panel overrides the bundled file, per key.
    monkeypatch.setattr(
        _rn,
        "get_persona_texts",
        lambda session: {
            "personas/orchestrator.md": "Eres Max, versión del panel.",
            "personas/orchestrator_brief.md": "Responde en una línea.",
        },
    )
    _rn._answer_from_kb("hola", "chunk", message_id=11, brief=True)
    system = respond_client.captured[-1]["messages"][0]["content"]
    assert system == (
        "Eres Max, versión del panel."
        "Responde en una línea."
        "\nResponde con un tono cercano, amable y claro."
    )


def test_respond_answer_from_kb_appends_the_tone_directive(respond_client):
    _rn._answer_from_kb("hola", "chunk", message_id=10)
    assert respond_client.captured[-1]["messages"][0]["content"].endswith(
        "Responde con un tono cercano, amable y claro."
    )


def test_respond_answer_from_kb_memory_block_injected(respond_client):
    # CM-7: a stored customer memory is injected as a read-only block beside kb.
    _rn._answer_from_kb(
        "hola", "chunk", message_id=9, memory_context="cliente probó varias reparaciones"
    )
    call = respond_client.captured[-1]
    assert "<memory>" in call["messages"][1]["content"]
    assert "reparaciones" in call["messages"][1]["content"]


# --- T5: respond renders the preset message the classifier picked (D13/D9) ---


def _respond_state(**overrides):
    base = dict(
        intent="consulta",
        window=[{"id": 1, "text": "a qué hora abren"}],
        template_id=None,
        captured={},
        booking=None,
        turn=3,
        cost_mode="normal",
        memory_context="",
        # S4: "nobody retrieved yet" — the same value `from_db` leaves in a turn
        # that was routed straight to `respond`.
        retrieval=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_placeholders_returns_slot_names():
    assert prompts.placeholders("Hola {{nombre}}, visita {{visita}}") == {"nombre", "visita"}


def test_render_text_substitutes_and_is_strict():
    assert prompts.render_text("Hola {{nombre}}", nombre="Ana") == "Hola Ana"
    with pytest.raises(KeyError):
        prompts.render_text("Hola {{nombre}}")
    with pytest.raises(KeyError):
        prompts.render_text("Hola {{nombre}}", nombre="Ana", extra="x")


def test_respond_renders_picked_template_with_real_slots(monkeypatch):
    # The owner's text is the answer; the SYSTEM fills the slots from state (D8).
    catalog = [{"id": "horarios", "text": "Hola {{nombre}}, atendemos de {{disponibilidad}}."}]
    monkeypatch.setattr(_rn, "session_scope", _noop_session_scope)
    monkeypatch.setattr(_rn, "get_message_templates", lambda session: catalog)
    state = _respond_state(
        template_id="horarios",
        captured={"name": "Ana", "availability": "lunes a viernes"},
    )
    assert _rn.respond(state) == {"replies": ["Hola Ana, atendemos de lunes a viernes."]}


def test_respond_template_preempts_the_kb_path(monkeypatch):
    called = []
    monkeypatch.setattr(_rn, "session_scope", _noop_session_scope)
    monkeypatch.setattr(
        _rn, "get_message_templates", lambda session: [{"id": "x", "text": "Ok {{nombre}}."}]
    )
    monkeypatch.setattr(_rn.kb, "retrieve", lambda *a, **k: called.append(1) or [{"content": "c"}])
    state = _respond_state(template_id="x", captured={"name": "Ana"})
    assert _rn.respond(state) == {"replies": ["Ok Ana."]}
    assert called == []


def test_respond_template_with_an_empty_slot_is_skipped(monkeypatch):
    """S9: a missing, "unknown" or booking-less slot skips the preset.

    Rendering "" would send an incomplete text ("/Santiago/" or "Ana//…"), so the
    regular answer path takes the turn instead.
    """
    catalog = [{"id": "v", "text": "{{nombre}}/{{comuna}}/{{visita}}"}]
    skipped = []
    monkeypatch.setattr(_rn, "session_scope", _noop_session_scope)
    monkeypatch.setattr(_rn, "get_message_templates", lambda session: catalog)
    monkeypatch.setattr(_rn.kb, "retrieve", lambda *a, **k: [{"content": "chunk"}])
    monkeypatch.setattr(_rn, "_answer_from_kb", lambda *a, **k: skipped.append(1) or "kb answer")
    # captured "unknown" -> skipped; no booking -> skipped for {{visita}}
    assert _rn.respond(
        _respond_state(template_id="v", captured={"name": "unknown", "comuna": "Santiago"})
    ) == {"replies": ["kb answer"]}
    assert _rn.respond(
        _respond_state(
            template_id="v",
            captured={"name": "Ana", "comuna": "unknown"},
            booking={"service": "Visita", "label": "06/05 a las 15:30", "status": "booked"},
        )
    ) == {"replies": ["kb answer"]}
    assert skipped == [1, 1]
    # every slot filled: the preset renders, {{visita}} from the booking label
    assert _rn.respond(
        _respond_state(
            template_id="v",
            captured={"name": "Ana", "comuna": "Santiago"},
            booking={"service": "Visita", "label": "06/05 a las 15:30", "status": "booked"},
        )
    ) == {"replies": ["Ana/Santiago/06/05 a las 15:30"]}


def test_respond_missing_template_falls_back_to_kb(monkeypatch):
    # A stale id (catalog changed) must not crash: fall through to the normal path.
    answered = []
    monkeypatch.setattr(_rn, "session_scope", _noop_session_scope)
    monkeypatch.setattr(_rn, "get_message_templates", lambda session: [])
    monkeypatch.setattr(_rn.kb, "retrieve", lambda *a, **k: [{"content": "chunk"}])
    monkeypatch.setattr(_rn, "_answer_from_kb", lambda *a, **k: answered.append(1) or "kb answer")
    state = _respond_state(template_id="gone")
    assert _rn.respond(state) == {"replies": ["kb answer"]}
    assert answered == [1]


def test_respond_smalltalk_uses_configured_message_before_templates_and_kb(monkeypatch):
    looked_up = []
    retrieved = []
    monkeypatch.setattr(_rn, "session_scope", _noop_session_scope)
    monkeypatch.setattr(
        _rn, "get_message", lambda session, key, fallback=None: looked_up.append(key) or "Courtesy override"
    )
    monkeypatch.setattr(_rn.kb, "retrieve", lambda *args, **kwargs: retrieved.append(1))

    result = _rn.respond(_respond_state(intent="smalltalk", template_id="preset"))

    assert result == {"replies": ["Courtesy override"]}
    assert looked_up == ["smalltalk"]
    assert retrieved == []


def test_respond_unknown_intent_renders_picked_template(monkeypatch):
    # A picked preset answers even an unknown-intent turn (before clarification).
    monkeypatch.setattr(_rn, "session_scope", _noop_session_scope)
    monkeypatch.setattr(
        _rn, "get_message_templates", lambda session: [{"id": "h", "text": "Hola {{nombre}}."}]
    )
    state = _respond_state(intent="unknown", template_id="h", captured={"name": "Ana"})
    assert _rn.respond(state) == {"replies": ["Hola Ana."]}


@pytest.fixture
def classify_client():
    client = _FakeClient(reply_content='{"intent": "caldera", "service": "caldera", "priority": "media", "status": "abierto", "injection": false}')
    with (
        mock.patch.object(_ci, "openai_client", return_value=client),
        mock.patch.object(_ci, "session_scope", _noop_session_scope),
        mock.patch.object(_ci, "record_llm_cost", return_value=0),
    ):
        yield client


def test_classify_llm_classify_persona_and_template(classify_client, monkeypatch):
    # AC-3 static slot unchanged + template identical: persona via loader,
    # user text inside the <user_input> slot (SH-4 input-as-data). The catalog
    # is injected into the USER message as an inert <templates> DATA block.
    catalog = [{"id": "horarios", "text": "Atendemos de {{disponibilidad}}."}]
    monkeypatch.setattr(_ci, "get_message_templates", lambda session: catalog)
    result = _ci._llm_classify(
        "necesito una caldera", message_id=5, conversation="Cliente: Quiero agendar una visita"
    )
    call = classify_client.captured[-1]
    assert call["messages"][0]["content"] == prompts.load("personas/classify.md")
    assert call["messages"][1]["content"] == prompts.render(
        "prompts/classify.md", conversation="Cliente: Quiero agendar una visita",
        templates="- id=horarios: Atendemos de {{disponibilidad}}.",
        user_input="necesito una caldera",
    )
    assert result["intent"] == "caldera"
    assert result["injection"] is False


def _classify_result_client(monkeypatch, reply_content: str, catalog: list[dict]):
    """Spy the classifier's LLM boundaries with a catalog; returns the fake client."""
    client = _FakeClient(reply_content=reply_content)
    monkeypatch.setattr(_ci, "openai_client", lambda: client)
    monkeypatch.setattr(_ci, "session_scope", _noop_session_scope)
    monkeypatch.setattr(_ci, "record_llm_cost", lambda *args, **kwargs: 0)
    monkeypatch.setattr(_ci, "get_message_templates", lambda session: catalog)
    return client


def test_classify_llm_returns_selected_template_id(monkeypatch):
    # T4: the same classifier call returns the id it picked from the catalog.
    _classify_result_client(
        monkeypatch,
        '{"intent": "consulta", "template_id": "horarios", "injection": false}',
        [{"id": "horarios", "text": "Atendemos de {{disponibilidad}}."}],
    )
    result = _ci._llm_classify("a qué hora abren", message_id=1)
    assert result["template_id"] == "horarios"


def test_classify_llm_drops_template_id_outside_the_catalog(monkeypatch):
    # The LLM is untrusted: an id that was never offered must not survive.
    _classify_result_client(
        monkeypatch,
        '{"intent": "consulta", "template_id": "no-existe", "injection": false}',
        [{"id": "horarios", "text": "Atendemos de {{disponibilidad}}."}],
    )
    result = _ci._llm_classify("a qué hora abren", message_id=1)
    assert result["template_id"] is None


def test_classify_llm_empty_catalog_neutralizes_templates(monkeypatch):
    # No catalog -> no behaviour change: neutral block, no id picked.
    client = _classify_result_client(
        monkeypatch, '{"intent": "consulta", "injection": false}', []
    )
    result = _ci._llm_classify("a qué hora abren", message_id=1)
    assert result["template_id"] is None
    assert "(sin respuestas prediseñadas)" in client.captured[-1]["messages"][1]["content"]


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
    assert _rn.CLARIFICATION_REPLY.startswith("Disculpa, no te entendí bien")
    assert HANDOFF_REPLY  # import resolves; value non-empty

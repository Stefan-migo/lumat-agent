"""S5-S7: hard-gated capture phrasing stays safe and extractable."""
from types import SimpleNamespace

import pytest

from app.chat import phrasing


@pytest.mark.parametrize("draft", [
    "**¿En qué comuna estás?**",
    "# ¿En qué comuna estás?",
    "*¿En qué comuna estás?*",
    "`¿En qué comuna estás?`",
    "- ¿En qué comuna estás?",
    "¿En qué comuna estás? 😊",
    "¿En qué comuna estás? " + "x" * 240,
    "¿En qué comuna estás? El precio es $25.000.",
    "¿En qué comuna estás? Mañana 12/05/2027.",
    "¿En qué comuna estás y cuál es tu correo?",
    "¿En qué comuna estás, ana@example.cl?",
])
def test_validator_rejects_unsafe_or_off_contract_drafts(draft):
    assert not phrasing.validate(
        draft,
        template="¿En qué comuna te encuentras?",
        facts={"comuna": "Ñuñoa", "email": "ana@example.cl"},
        pending=["comuna"],
    )


def test_validator_accepts_natural_rewrites_that_mention_captured_facts():
    """A rewrite may name facts the customer already gave; only new asks are gated.

    A keyword table over every field rejected "tu caldera no enciende" and "para
    coordinar la visita" while asking the commune, so the model's output was
    discarded on nearly every turn and the feature paid a call to reply with the
    template. Mentioning a captured fact is the whole point of the rewrite.
    """
    facts = {"nombre": "Ana", "equipo": "caldera", "problema": "no enciende", "comuna": "Ñuñoa"}
    template = "¿En qué comuna te encuentras?"

    for draft in (
        "Entiendo, tu caldera no enciende. ¿En qué comuna está?",
        "Para coordinar la visita, ¿en qué comuna te encuentras?",
        "Gracias Ana. ¿Dónde queda la caldera?",
    ):
        assert phrasing.validate(draft, template=template, facts=facts, pending=["comuna"]), draft


def test_validator_keeps_the_question_count_of_the_template():
    template = "¿En qué comuna te encuentras?"
    facts = {"comuna": "Ñuñoa"}

    assert not phrasing.validate("Entiendo, tomo nota.", template=template, facts=facts, pending=["comuna"])
    assert not phrasing.validate(
        "¿En qué comuna estás? ¿Y a qué hora te sirve?",
        template=template,
        facts=facts,
        pending=["comuna"],
    )


def test_plantilla_mode_is_byte_identical_and_never_constructs_client(monkeypatch):
    monkeypatch.setattr(phrasing, "get_conduct", lambda _session: {"redaccion": "plantilla"})
    monkeypatch.setattr(phrasing.llm, "openai_client", lambda: pytest.fail("client constructed"))
    template = "  ¿En qué comuna?  \n"
    assert phrasing.phrase(object(), "capture_question", template, facts={}, pending=["comuna"]) == template


def test_only_the_capture_question_and_consent_steps_are_phraseable():
    """One model call per message: ack and evidence hints share it with the ask."""
    assert phrasing.PHRASEABLE_KEYS == {
        "capture_consent",
        "capture_consent_refused",
        "capture_consent_unclear",
        "capture_question",
    }


@pytest.mark.parametrize("outcome", ["exception", "timeout", "empty", "invalid"])
def test_llm_mode_falls_back_on_any_rewrite_failure(monkeypatch, outcome):
    monkeypatch.setattr(phrasing, "get_conduct", lambda _session: {"redaccion": "llm"})

    class Completions:
        def create(self, **_kwargs):
            if outcome == "exception":
                raise RuntimeError("provider down")
            if outcome == "timeout":
                raise TimeoutError("slow")
            text = "" if outcome == "empty" else "Te cobraremos $25.000, ¿en qué comuna estás?"
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])

    monkeypatch.setattr(phrasing.llm, "openai_client", lambda: SimpleNamespace(chat=SimpleNamespace(completions=Completions())))
    template = "¿En qué comuna te encuentras?"
    assert phrasing.phrase(object(), "capture_question", template, facts={}, pending=["comuna"]) == template


def test_llm_mode_returns_valid_rewrite(monkeypatch):
    monkeypatch.setattr(phrasing, "get_conduct", lambda _session: {"redaccion": "llm"})
    rewritten = "¿En qué comuna estás?"

    class Completions:
        def create(self, **_kwargs):
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=rewritten))])

    monkeypatch.setattr(phrasing.llm, "openai_client", lambda: SimpleNamespace(chat=SimpleNamespace(completions=Completions())))
    assert phrasing.phrase(object(), "capture_question", "¿En qué comuna te encuentras?", facts={}, pending=["comuna"]) == rewritten


def test_the_rewrite_gets_only_the_fact_just_captured(monkeypatch):
    """S1 (agenda-horarios): one fact, never the whole recap, on every turn.

    With `redaccion: llm` every capture question carried the history the customer
    had already given -- "Ramiro, para coordinar el calefont en Huechuraba el
    viernes despues del mediodia, cual es tu correo?" -- because `facts()` handed
    the rewrite every captured value on every turn. The owner read it as a tic.
    """
    captured = {
        "name": "Ramiro", "equipment": "calefont", "comuna": "Huechuraba",
        "availability": "viernes despues del mediodia",
        "_asked": {"failure": 1, "equipment": 1, "comuna": 1, "availability": 1},
    }

    offered = phrasing.facts(captured, ["email"])

    assert offered["pending"] == ["email"]
    assert [key for key in offered if key != "pending"] == ["disponibilidad"], offered


def test_a_fact_is_offered_once_and_never_again():
    captured = {"comuna": "Huechuraba", "_asked": {"comuna": 1}, "_facts_used": ["comuna"]}

    assert phrasing.facts(captured, ["availability"]) == {"pending": ["availability"]}


def test_no_fact_is_offered_when_none_was_captured():
    assert phrasing.facts({}, ["comuna"]) == {"pending": ["comuna"]}
    assert phrasing.facts({"comuna": "unknown"}, ["availability"]) == {
        "pending": ["availability"]
    }


def test_the_question_marks_the_fact_it_offered_so_the_next_turn_does_not(monkeypatch):
    """The capture node owns the marking; `facts()` stays pure."""
    from app.chat.nodes import capture as capture_node

    seen: list[dict] = []

    def fake_phrase(_session, _key, rendered, *, facts, pending):
        seen.append(facts)
        return rendered

    monkeypatch.setattr(capture_node, "phrase", fake_phrase)

    questions = {"availability": "¿Qué días y horarios te acomodan?", "email": "¿Cuál es tu correo?"}
    captured = {"comuna": "Huechuraba", "_asked": {"comuna": 1}}
    capture_node._phrase_question(object(), captured, ["availability"], questions)
    capture_node._phrase_question(object(), captured, ["email"], questions)

    assert [key for key in seen[0] if key != "pending"] == ["comuna"]
    assert [key for key in seen[1] if key != "pending"] == [], seen[1]


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        (
            "Cuéntame qué falla tiene la caldera: ¿no enciende?",
            "Entiendo. Cuéntame qué falla tiene la caldera: ¿no enciende?",
        ),
        (
            "Cuéntame qué pasa con el equipo: ¿no enciende?",
            "Entiendo, es un problema con tu caldera. Cuéntame qué pasa con el equipo: ¿no enciende?",
        ),
    ],
)
def test_failure_question_acknowledges_equipment_once(monkeypatch, question, expected):
    from app.chat.nodes import capture as capture_node

    monkeypatch.setattr(capture_node, "get_capture_ack", lambda _session: "Entiendo. ")
    monkeypatch.setattr(capture_node, "_field_questions", lambda _session: {})
    monkeypatch.setattr(capture_node, "_phrase_question", lambda *_args: question)
    captured = {"equipment_type": "caldera", "_asked": {"failure": 1}}

    reply = capture_node._render_capture_question(object(), captured, ["failure"])

    assert reply == expected
    assert reply.count("Entiendo") == 1
    assert reply.casefold().count("caldera") == 1
    if "qué pasa con el equipo" in question:
        assert captured["_acked"] == "Entiendo, es un problema con tu caldera."


def test_non_failure_question_keeps_configured_ack_with_equipment_on_record(monkeypatch):
    from app.chat.nodes import capture as capture_node

    monkeypatch.setattr(capture_node, "get_capture_ack", lambda _session: "Entiendo. ")
    monkeypatch.setattr(capture_node, "_field_questions", lambda _session: {})
    monkeypatch.setattr(capture_node, "_phrase_question", lambda *_args: "¿En qué comuna estás?")
    captured = {"equipment_type": "caldera", "_asked": {"failure": 1}}

    reply = capture_node._render_capture_question(object(), captured, ["comuna"])

    assert reply == "Entiendo. ¿En qué comuna estás?"
    assert reply.count("Entiendo") == 1
    assert "caldera" not in reply.casefold()


def test_capture_question_round_trip_keeps_extractor_field(monkeypatch):
    from contextlib import contextmanager
    from app.chat.nodes import capture as capture_node
    from app.chat.state import ConversationState
    from app.services.settings import REPLY_TEXT_DEFAULTS

    class Session:
        def get(self, *_args):
            return None

    @contextmanager
    def session_scope():
        yield Session()

    monkeypatch.setattr(capture_node, "session_scope", session_scope)
    monkeypatch.setattr(capture_node, "get_conduct", lambda _session: {
        "orden": ["comuna"], "max_preguntas_por_mensaje": 1, "derivaciones": []
    })
    monkeypatch.setattr(capture_node, "get_coverage_communes", lambda _session: ["Ñuñoa"])
    monkeypatch.setattr(capture_node, "get_reply_texts", lambda _session: dict(REPLY_TEXT_DEFAULTS))
    monkeypatch.setattr(capture_node, "get_capture_questions", lambda _session: {})
    monkeypatch.setattr(capture_node, "_persist_captured", lambda *_args: None)
    monkeypatch.setattr(capture_node, "_render_capture_ack", lambda *_args: "")
    monkeypatch.setattr(capture_node, "phrase", lambda _session, key, _rendered, **_kwargs: "¿En qué comuna estás?" if key == "capture_question" else _rendered)

    asked = capture_node.capture(ConversationState(
        customer_id=1, conversation_id=2, phone="", captured={}, extracted={},
        window=[{"text": "Quiero una visita"}],
    ))
    assert asked["replies"][0].startswith("¿En qué comuna estás?")
    def fake_extractor(question, answer):
        assert "comuna" in question.casefold()
        return {"comuna": answer}

    captured = capture_node.capture(ConversationState(
        customer_id=1, conversation_id=2, phone="", captured=asked["captured"],
        extracted=fake_extractor(asked["replies"][0], "Ñuñoa"), window=[{"text": "Ñuñoa"}],
    ))
    assert captured["captured"]["comuna"] == "Ñuñoa"

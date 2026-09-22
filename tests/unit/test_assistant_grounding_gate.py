from types import SimpleNamespace

import pytest

from app.chat.assistant.graph import _after_guardrails, build_assistant_graph
from app.chat.assistant import nodes
from app.chat.assistant.nodes import _is_conversational_turn, guardrails


def _respond_state(content="¿Cuáles son las tarifas?", **overrides):
    state = {
        "content": content,
        "session": SimpleNamespace(),
        "plan": {"kind": "respond", "tool": None, "requires_approval": False},
        "planner": {"valid": True},
    }
    state.update(overrides)
    return state


def test_grounding_graph_routes_knowledge_respond_to_retrieval():
    result = guardrails(_respond_state())

    assert result["guardrails"]["decision"] == "retrieve_kb"
    assert _after_guardrails({**_respond_state(), **result}) == "retrieve_kb"


def test_empty_kb_retrieval_returns_deterministic_clarification_without_responder(monkeypatch):
    responder_calls = []
    monkeypatch.setattr("app.chat.assistant.nodes._assistant_client", lambda: responder_calls.append(True))
    monkeypatch.setattr("app.services.kb.retrieve", lambda *args, **kwargs: [])

    result = nodes.retrieve_kb(_respond_state())

    assert result["response"] == "No encontré evidencia suficiente en la base de conocimiento para responder con seguridad. Reformula la consulta o aporta más contexto."
    assert result["status"] == "completed"
    assert result["evidence"][0]["tool"] == "kb.retrieve"
    assert responder_calls == []
    assert "escalate" not in result


def test_non_empty_kb_retrieval_reaches_responder_as_bounded_evidence(monkeypatch):
    chunks = [{"content": "Tarifa base: 100", "similarity": 0.91}]
    calls = []
    monkeypatch.setattr("app.services.kb.retrieve", lambda *args, **kwargs: calls.append((args, kwargs)) or chunks)

    result = nodes.retrieve_kb(_respond_state())

    assert result["kb_chunks"] == chunks
    assert calls[0][1] == {"top_k": 5, "min_sim": 0.50, "audience": None}
    assert result["guardrails"]["decision"] == "respond"
    assert _after_guardrails({**_respond_state(), **result}) == "respond_stream"


def test_short_social_turn_bypasses_grounding():
    result = guardrails(_respond_state(content="Hola"))

    assert result["guardrails"]["decision"] == "respond"
    assert _after_guardrails({**_respond_state(content="Hola"), **result}) == "respond_stream"


@pytest.mark.parametrize("content", [
    "buenos dias",
    "buenas tardes",
    "buenas noches",
    "muchas gracias",
    "por favor",
    "de nada",
    "chau",
    "adios",
    "hasta luego",
    "nos vemos",
    "que tal",
    "como estas",
    "todo bien",
    "ok",
    "gracias",
])
def test_common_short_social_messages_bypass_grounding(content):
    assert _is_conversational_turn(content) is True


@pytest.mark.parametrize("content", [
    "cuales son las tarifas",
    "dame los valores",
    "cuanto sale",
    "que hora es",
    "lista de clientes",
    "donde estan",
    "hola, cuales son las tarifas",
    "gracias, dame las tarifas",
])
def test_short_knowledge_questions_never_bypass_grounding(content):
    assert _is_conversational_turn(content) is False
    assert guardrails(_respond_state(content=content))["guardrails"]["decision"] == "retrieve_kb"


def test_greeting_prefixed_knowledge_question_does_not_bypass_grounding():
    result = guardrails(_respond_state(content="Hola, ¿cuáles son las tarifas?"))

    assert result["guardrails"]["decision"] == "retrieve_kb"


def test_tool_turn_keeps_existing_route():
    state = _respond_state(
        content="Busca a Ana",
        plan={"kind": "tool", "tool": "customers.search", "arguments": {}, "requires_approval": False},
    )

    result = guardrails(state)

    assert result["guardrails"]["decision"] == "execute"
    assert _after_guardrails({**state, **result}) == "execute_tool"


def test_grounding_graph_declares_retrieval_node():
    edges = {(edge.source, edge.target) for edge in build_assistant_graph().get_graph().edges}

    assert ("guardrails", "retrieve_kb") in edges
    assert ("retrieve_kb", "respond_stream") in edges

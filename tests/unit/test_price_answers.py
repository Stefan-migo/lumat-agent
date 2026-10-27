"""The published price answers a price question directly (L2 debt).

Prices live in the tariff, never in a customer KB document. Before this path a
KB miss on a published service answered "no tengo ese dato" while the tariff
already held the figure (`simple-precio-calefont`, measured live).
"""

from datetime import date
from types import SimpleNamespace

import pytest

from app.chat.nodes import respond
from app.chat.state import ConversationState
from app.services.settings import DEFAULT_TARIFA_PRECIOS, TARIFA_LABELS


def _state(text: str, *, intent: str = "valores") -> ConversationState:
    return ConversationState(
        customer_id=1,
        conversation_id=1,
        phone="+56912345678",
        turn=2,
        intent=intent,
        window=[{"id": 1, "text": text}],
    )


@pytest.mark.parametrize(
    ("question", "service"),
    [
        ("cuanto sale la mantencion de calefont?", "mantencion_calefont"),
        ("cuánto cuesta la mantención de calefón", "mantencion_calefont"),
        ("precio mantencion caldera", "mantencion_caldera"),
        ("hola, cuanto cuesta el lavado de red?", "lavado_red"),
        ("cuanto sale la visita tecnica", "visita_tecnica"),
    ],
)
def test_the_question_names_a_published_service(question, service):
    assert respond.tariff_service(question) == service


@pytest.mark.parametrize(
    "question",
    [
        "cuanto sale arreglar una fuga de agua",
        "cuanto cuesta el lavado de estanque solar",
        "cuanto cuesta una instalacion",
    ],
)
def test_an_unrecognised_service_names_nothing(question):
    """No figure is invented for a service the tariff does not publish."""
    assert respond.tariff_service(question) is None


def test_the_reply_uses_the_price_in_force_and_the_published_label(monkeypatch):
    monkeypatch.setattr(
        respond, "get_hours_timezone", lambda _session: "America/Santiago"
    )
    monkeypatch.setattr(
        respond, "get_tarifa_precios", lambda _session: DEFAULT_TARIFA_PRECIOS
    )

    reply = respond.tariff_price_reply(
        SimpleNamespace(), _state("cuanto sale la mantencion de calefont?")
    )

    assert reply == f"El precio vigente de {TARIFA_LABELS['mantencion_calefont']} es $50.000."


def test_a_service_without_a_price_in_force_is_not_quoted(monkeypatch):
    """A seasonal range that misses today's month yields no figure (no invention)."""
    monkeypatch.setattr(respond, "get_hours_timezone", lambda _session: "America/Santiago")
    monkeypatch.setattr(
        respond,
        "get_tarifa_precios",
        lambda _session: {"mantencion_calefont": [{"desde_mes": 1, "hasta_mes": 1, "valor": 50000}]},
    )
    monkeypatch.setattr(
        respond, "tarifa_vigente", lambda _tariff, _today: {}
    )

    assert (
        respond.tariff_price_reply(SimpleNamespace(), _state("cuanto sale la mantencion de calefont?"))
        is None
    )


def test_a_turn_that_is_not_a_price_intent_is_left_to_the_existing_path(monkeypatch):
    monkeypatch.setattr(respond, "get_tarifa_precios", lambda _session: DEFAULT_TARIFA_PRECIOS)

    assert (
        respond.tariff_price_reply(
            SimpleNamespace(), _state("cuanto sale la mantencion de calefont?", intent="consulta")
        )
        is None
    )

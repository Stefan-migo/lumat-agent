"""Shared service catalogue resolution for capture and retrieval (S14)."""

from app.chat.nodes import respond
from app.chat.state import ConversationState
from app.chat.service_catalogue import canonical_service


class _Session:
    pass


def _catalogue(monkeypatch, *, durations=None, tariffs=None):
    monkeypatch.setattr(
        "app.chat.service_catalogue.get_service_durations",
        lambda _session: durations or {},
    )
    monkeypatch.setattr(
        "app.chat.service_catalogue.get_tarifa_precios",
        lambda _session: tariffs or {},
    )


def _state(text, *, service, intent="consulta"):
    return ConversationState(
        customer_id=1,
        conversation_id=2,
        phone="+56912345678",
        intent=intent,
        case={"service": service},
        window=[{"text": text}],
    )


def test_bare_device_and_repair_service_resolve_to_same_fallback_query(monkeypatch):
    _catalogue(monkeypatch, tariffs={"mantencion_calefont": [], "visita_tecnica": []})
    session = _Session()
    text = "¿Atienden sábado?"

    bare_device = canonical_service(session, "calefont")
    repair = canonical_service(session, "reparación de calefont")

    assert bare_device == repair == "Visita técnica"
    assert respond.retrieval_queries(session, _state(text, service="calefont")) == [
        text,
        "Visita técnica",
    ]
    assert respond.retrieval_queries(
        session, _state(text, service="reparación de calefont")
    ) == [text, "Visita técnica"]


def test_typo_in_bare_device_resolves_to_same_generic_visit(monkeypatch):
    _catalogue(monkeypatch, tariffs={"mantencion_calefont": [], "visita_tecnica": []})

    assert canonical_service(_Session(), "calefonnt") == "Visita técnica"


def test_preventive_request_resolves_to_its_preventive_catalogue_label(monkeypatch):
    _catalogue(monkeypatch, tariffs={"mantencion_caldera": []})

    assert canonical_service(_Session(), "mantención de caldera") == "Mantención de caldera"
    assert canonical_service(_Session(), "manutencion de caldera") == "Mantención de caldera"


def test_visita_tecnica_is_not_preventive_and_device_substring_does_not_win(monkeypatch):
    _catalogue(
        monkeypatch,
        tariffs={
            "visita_tecnica": [],
            "mantencion_calefont": [],
        },
    )

    assert canonical_service(_Session(), "calefont") == "Visita técnica"
    assert canonical_service(_Session(), "necesito una visita técnica") == "Visita técnica"


def test_unknown_turn_does_not_append_service_fallback(monkeypatch):
    _catalogue(monkeypatch, tariffs={"visita_tecnica": []})

    assert respond.retrieval_queries(
        _Session(), _state("¿Atienden sábado?", service="calefont", intent="unknown")
    ) == ["¿Atienden sábado?"]


def test_no_catalogue_keeps_the_classifier_fallback(monkeypatch):
    """Without a catalogue there is nothing to normalize, but nothing to lose either.

    Returning the value unchanged keeps the pre-existing contract: a raw miss
    still falls back to the classified service. Only the preventive/generic
    resolution needs a catalogue.
    """
    _catalogue(monkeypatch)

    assert canonical_service(_Session(), "calefont") == "calefont"
    assert respond.retrieval_queries(
        _Session(), _state("¿Atienden sábado?", service="calefont")
    ) == ["¿Atienden sábado?", "calefont"]

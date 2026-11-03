"""A price question is answered from the configured tariff (L2 debt).

`simple-precio-calefont` was measured live: intent `valores`, empty KB hit on the
service, and the customer read "No tengo ese dato" while `tarifa.precios` already
held the published figure. These tests pin the two halves of the rule: the miss
path answers the configured price, and a KB hit keeps owning the turn.
"""

from app.chat.nodes.respond import respond
from app.chat.state import ConversationState
from app.db import SessionLocal
from app.models import DocumentFormat, KbVisibility
from app.services import kb as kb_service
from app.services.settings import TARIFA_PRECIOS_KEY, set_setting


def _state(text: str, *, intent: str = "valores") -> ConversationState:
    return ConversationState(
        customer_id=1,
        conversation_id=1,
        phone="+56912345678",
        turn=2,
        intent=intent,
        window=[{"id": 1, "text": text}],
    )


_CALENDAR_FREE_TARIFF = {
    # A whole-year range per service on purpose: the assertion below names a
    # figure, so the tariff it comes from must not depend on the month the suite
    # runs in. `tarifa.precios` must cover exactly the known services and every
    # service's ranges must partition months 1-12, so a partial dict would be
    # rejected and the reader would fall back to the seasonal default (measured
    # 2026-11-03: a partial tariff silently answered $40.000). The seasonal
    # default itself is pinned by tests/unit/test_tarifa_vigente.py.
    "visita_tecnica": [{"desde_mes": 1, "hasta_mes": 12, "valor": 30000}],
    "mantencion_calefont": [{"desde_mes": 1, "hasta_mes": 12, "valor": 50000}],
    "mantencion_caldera": [{"desde_mes": 1, "hasta_mes": 12, "valor": 80000}],
    "lavado_red": [{"desde_mes": 1, "hasta_mes": 12, "valor": 140000}],
}


def test_a_published_price_is_answered_instead_of_the_miss_offer():
    with SessionLocal() as session:
        set_setting(session, TARIFA_PRECIOS_KEY, _CALENDAR_FREE_TARIFF)
        session.commit()

    result = respond(_state("cuanto sale la mantencion de calefont?"))

    reply = result["replies"][0]
    assert "Mantención de calefont" in reply
    assert "$50.000" in reply
    assert "No tengo ese dato" not in reply
    assert result.get("escalate") is not True


def test_a_kb_hit_keeps_owning_the_turn(mock_openai_chat):
    """The tariff answers a miss; documented content still wins when it exists."""
    with SessionLocal() as session:
        kb_service.ingest_document(
            session,
            title="Lavado de red",
            fmt=DocumentFormat.MD,
            content=(
                "cuanto cuesta el lavado de red de calefaccion. El lavado de red "
                "elimina lodos y óxido del circuito y dura entre 3 y 6 horas."
            ).encode(),
            visibility=KbVisibility.CUSTOMER,
        )
        session.commit()

    result = respond(_state("cuanto cuesta el lavado de red?"))

    reply = result["replies"][0]
    assert "manual de Lumat" in reply
    assert "El precio vigente de Lavado de red" not in reply


def test_a_price_question_about_an_unpublished_service_still_gets_the_offer():
    result = respond(_state("¿cuánto cuesta el lavado de estanque solar?"))

    assert "No tengo ese dato" in result["replies"][0]

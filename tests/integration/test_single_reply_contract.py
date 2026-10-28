"""S17 — one informational reply per turn.

`respond` already earns this structurally: the preset path returns before any
retrieval, and each other branch returns a single text. These tests pin that
contract so a future branch cannot answer twice — the model text and a preset
are never both sent.
"""

from app.chat.nodes.respond import respond
from app.services.settings import MESSAGE_DEFAULTS
from app.chat.state import ConversationState
from app.db import SessionLocal
from app.services import settings as settings_service

PRESET = "Atendemos en Ñuñoa, Las Condes y Lo Barnechea."


def _state(**overrides) -> ConversationState:
    """A turn with no configuration answer and no KB match.

    The text used to be "¿atienden en Ñuñoa?", which is now answered from
    `coverage.communes` (S4 of `agenda-config-fuente`) before retrieval. The
    contract these tests pin is the single-reply shape of the miss path, so the
    vehicle moved to a question the configuration does not answer.
    """
    return ConversationState(
        customer_id=1,
        conversation_id=1,
        phone="+56912345678",
        turn=2,
        intent="consulta",
        window=[{"id": 1, "text": "¿hacen mantencion de estufas?"}],
        **overrides,
    )


def test_s17_a_preset_is_the_only_reply_and_the_model_is_not_called(mock_openai_chat):
    with SessionLocal() as session:
        settings_service.set_setting(
            session,
            settings_service.MESSAGE_TEMPLATES_KEY,
            [{"id": "cobertura", "text": PRESET}],
            actor="test",
        )
        session.commit()

    result = respond(_state(template_id="cobertura"))

    assert result["replies"] == [PRESET]
    assert mock_openai_chat == []


def test_s17_a_missed_kb_answers_once_and_offers(mock_openai_chat):
    """S17: one reply per turn. D18: that reply offers instead of deriving."""
    result = respond(_state())

    assert len(result["replies"]) == 1
    assert result["replies"][0] == MESSAGE_DEFAULTS["kb_miss_offer"]
    assert result.get("escalate") is not True

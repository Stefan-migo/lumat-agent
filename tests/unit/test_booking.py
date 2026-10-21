from app.chat.nodes.booking import _offer_text
from app.services.settings import REPLY_TEXT_DEFAULTS


def test_offer_text_formats_slots_for_customers():
    text = _offer_text([{"date": "2026-10-13", "time": "15:00:00.986884"}], REPLY_TEXT_DEFAULTS)

    assert "13/10/2026 a las 15:00" in text
    assert ".986884" not in text

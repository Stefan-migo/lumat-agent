from app.chat.nodes.booking import _offer_text


def test_offer_text_formats_slots_for_customers():
    text = _offer_text([{"date": "2026-10-13", "time": "15:00:00.986884"}])

    assert "13/10/2026 a las 15:00" in text
    assert ".986884" not in text

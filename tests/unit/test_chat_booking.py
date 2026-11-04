from datetime import date

from app.chat.nodes.booking import is_offer_answer


def test_hour_request_answers_an_open_offer_without_escalating():
    assert is_offer_answer("después de las 17 hrs", [], today=date(2026, 11, 4))
    assert is_offer_answer("cerca de las 17", [], today=date(2026, 11, 4))
    assert is_offer_answer("más tarde", [], today=date(2026, 11, 4))

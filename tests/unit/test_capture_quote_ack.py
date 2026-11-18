"""Unit coverage for the evaluation/quote acknowledgement decision (S1, S2, S4).

The integration tests drive the whole graph, which also routes by intent; these
pin the two functions the behaviour rests on, with no database and no model:

- `_is_quote_request` decides that a declaration is a request, and that a refusal
  or an absent budget is not.
- `_pick_ack` decides which acknowledgement speaks. It exists because the first
  implementation marked the quote ack as said while the preventive ack held the
  turn: the sentence was never sent and the customer never read it (conversation
  299, run `captura-eval`).
"""

from app.chat.nodes.capture import _is_quote_request, _pick_ack
from app.services.settings import SETTINGS_DEFAULTS

KEYWORDS = SETTINGS_DEFAULTS["capture.quote_keywords"]
QUOTE_ACK = "Entiendo, quieres una nueva evaluación con cotización. "
PREVENTIVE_ACK = "Entiendo, quieres hacer mantención de caldera. "


def test_a_declared_evaluation_is_a_quote_request():
    assert _is_quote_request(
        "por eso me gustaría tener una nueva evaluación y cotización", KEYWORDS
    )


def test_a_refusal_is_not_a_request():
    assert not _is_quote_request("no necesito cotización por ahora", KEYWORDS)


def test_an_absent_budget_is_not_a_request():
    assert not _is_quote_request(
        "la verdad no tengo presupuesto ahora, pero necesito que la revisen", KEYWORDS
    )


def test_the_preventive_ack_keeps_the_turn_and_the_quote_ack_stays_pending():
    captured = {"_quote_request": True}
    assert _pick_ack(captured, PREVENTIVE_ACK, QUOTE_ACK) == PREVENTIVE_ACK
    assert "_quote_acked" not in captured


def test_the_quote_ack_marks_only_the_text_that_is_returned():
    captured = {"_quote_request": True}
    assert _pick_ack(captured, "", QUOTE_ACK) == QUOTE_ACK
    assert captured["_quote_acked"] == QUOTE_ACK.strip()


def test_nothing_speaks_when_no_ack_is_pending():
    captured = {"_quote_request": True, "_quote_acked": QUOTE_ACK.strip()}
    assert _pick_ack(captured, "", "") == ""

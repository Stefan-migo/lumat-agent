"""Capture batching and reformulation (S14).

`max_preguntas_por_mensaje` drives how many booking fields ride one message; the
diagnostic fields always go one at a time, because a fault is what the customer
has to describe first. A field may be asked twice — the second ask is the
reformulation — and on the third attempt the flow offers a derivation instead
of asking a fourth time.
"""

from app.chat.nodes.capture import (
    MAX_ASKS_PER_FIELD,
    _ask_batch,
    _exhausted,
)


def test_the_reformulation_budget_is_one_extra_ask():
    assert MAX_ASKS_PER_FIELD == 2


def test_diagnostic_fields_are_always_asked_one_at_a_time():
    assert _ask_batch(["failure", "equipment", "comuna"], 1) == ["failure"]
    assert _ask_batch(["failure", "equipment", "comuna"], 2) == ["failure"]
    assert _ask_batch(["equipment", "comuna"], 2) == ["equipment"]


def test_booking_fields_follow_the_configured_max():
    assert _ask_batch(["comuna", "availability", "name"], 1) == ["comuna"]
    assert _ask_batch(["comuna", "availability", "name"], 2) == ["comuna", "availability"]


def test_the_batch_never_exceeds_the_missing_fields():
    assert _ask_batch(["name"], 2) == ["name"]


def test_a_field_asked_once_is_not_exhausted():
    assert _exhausted({"_asked": {"comuna": 1}}, ["comuna"]) is False
    assert _exhausted({}, ["comuna"]) is False


def test_a_field_asked_twice_is_exhausted():
    assert _exhausted({"_asked": {"comuna": 2}}, ["comuna"]) is True


def test_one_exhausted_field_exhausts_the_batch():
    assert _exhausted({"_asked": {"comuna": 1, "availability": 2}}, ["comuna", "availability"]) is True

"""Capture order (S11): the effective sequence comes from `chat.conduct.orden`.

The node still decides which field is missing and how many it asks per message;
what moved to settings is the sequence. `_missing_fields` receives the order as
a parameter, so the shipped order is only the default while nobody configures
another one, and a field the owner dropped from the order is never asked.
"""

from app.chat.nodes.capture import CAPTURE_FIELD_ORDER, _missing_fields
from app.services.settings import CHAT_CONDUCT_DEFAULTS


def test_the_shipped_order_is_the_conduct_default():
    """Two lists hold the same sequence; this keeps them from drifting apart."""
    assert CHAT_CONDUCT_DEFAULTS["orden"] == CAPTURE_FIELD_ORDER


def test_missing_fields_follow_the_given_order():
    captured = {"failure": "no enciende", "comuna": "Ñuñoa"}

    assert _missing_fields(captured, ["comuna", "failure", "name"]) == ["name"]


def test_a_field_dropped_from_the_order_is_never_missing():
    """S11: a field outside the order is not asked, not appended at the end."""
    assert _missing_fields({}, ["failure", "equipment"]) == ["failure", "equipment"]


def test_a_skipped_field_is_not_missing():
    """A skip is stored as `unknown`, so it counts as answered (CM-2)."""
    assert _missing_fields({"failure": "unknown"}, ["failure", "comuna"]) == ["comuna"]

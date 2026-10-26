"""Chat conduct (S10): one settings key with the four closed-option fields.

`chat.conduct` holds the order of the capture fields, the question budget per
message and the active derivation rules. F3 only validates
and stores it: nothing reads it until T11/F4, so the current flow keeps working
with the shipped order.

Validation is order-aware and receives the capture fields as a parameter (same
shape as `validate_capture_questions`), so `settings` never imports `capture`.
"""

from unittest.mock import MagicMock

import pytest

from app.services.settings import (
    CHAT_CONDUCT_DEFAULTS,
    CHAT_CONDUCT_KEY,
    CONDUCT_DERIVACIONES,
    get_conduct,
    validate_conduct,
)

FIELDS = ["failure", "equipment", "comuna", "availability", "name", "email", "address"]
VALID = {
    "orden": FIELDS,
    "max_preguntas_por_mensaje": 1,
    "derivaciones": list(CONDUCT_DERIVACIONES),
}


def test_the_key_is_chat_conduct():
    assert CHAT_CONDUCT_KEY == "chat.conduct"


def test_the_default_order_is_the_shipped_capture_order():
    assert CHAT_CONDUCT_DEFAULTS["orden"] == FIELDS


def test_the_defaults_keep_the_other_conduct_fields_and_the_phrasing_switch():
    # S5: `redaccion` comes back with a reader (`phrasing.phrase`); #687 had
    # removed it while nothing read it. The default keeps phrasing off.
    assert CHAT_CONDUCT_DEFAULTS["redaccion"] == "plantilla"
    assert CHAT_CONDUCT_DEFAULTS["orden"] == FIELDS
    assert CHAT_CONDUCT_DEFAULTS["max_preguntas_por_mensaje"] == 1
    assert CHAT_CONDUCT_DEFAULTS["derivaciones"] == list(CONDUCT_DERIVACIONES)


def test_the_closed_derivation_list_keeps_only_the_rule_with_a_reader():
    """S4: the four rules that gated nothing are out of the stored object.

    They were dead configuration: `chat.conduct.derivaciones` is the closed list
    of rules the derivation logic reads, and `cobertura` is the only one.
    """
    assert CONDUCT_DERIVACIONES == ("cobertura",)


def test_validate_accepts_a_complete_conduct_object():
    # S5: the projection carries the phrasing switch, defaulting it when absent.
    assert validate_conduct(VALID, FIELDS) == {**VALID, "redaccion": "plantilla"}


def test_validate_accepts_a_subset_order():
    """Dropping a field from the order is the owner turning that ask off."""
    value = {**VALID, "orden": ["failure", "comuna", "name", "email", "address"]}

    assert validate_conduct(value, FIELDS)["orden"] == [
        "failure",
        "comuna",
        "name",
        "email",
        "address",
    ]


def test_validate_accepts_a_reordered_order():
    value = {**VALID, "orden": ["equipment", "failure", "availability", "address", "name", "email"]}

    assert validate_conduct(value, FIELDS)["orden"] == [
        "equipment",
        "failure",
        "availability",
        "address",
        "name",
        "email",
    ]


def test_validate_accepts_two_questions_without_changing_other_fields():
    value = {**VALID, "max_preguntas_por_mensaje": 2}

    assert validate_conduct(value, FIELDS) == {
        "orden": FIELDS,
        "redaccion": "plantilla",
        "max_preguntas_por_mensaje": 2,
        "derivaciones": list(CONDUCT_DERIVACIONES),
    }


def test_validate_accepts_a_single_active_derivation():
    value = {**VALID, "derivaciones": ["cobertura"]}

    assert validate_conduct(value, FIELDS)["derivaciones"] == ["cobertura"]


def test_validate_accepts_no_active_derivation():
    """With one rule left, an empty list is how the owner turns it off (S15)."""
    value = {**VALID, "derivaciones": []}

    assert validate_conduct(value, FIELDS)["derivaciones"] == []


@pytest.mark.parametrize(
    "value",
    [
        pytest.param([], id="not-a-map"),
        pytest.param("orden=failure", id="not-a-map-string"),
        pytest.param({}, id="empty"),
        pytest.param({key: val for key, val in VALID.items() if key != "orden"}, id="missing-orden"),
        pytest.param({**VALID, "orden": []}, id="empty-order"),
        pytest.param({**VALID, "orden": "failure"}, id="order-not-a-list"),
        pytest.param({**VALID, "orden": ["failure", "telefono"]}, id="unknown-field"),
        pytest.param({**VALID, "orden": ["failure", "failure"]}, id="repeated-field"),
        pytest.param(
            {**VALID, "orden": ["name", "failure", "equipment", "comuna", "availability", "email", "address"]},
            id="name-before-availability",
        ),
        pytest.param(
            {**VALID, "orden": ["failure", "equipment", "address", "comuna", "availability", "name", "email"]},
            id="address-before-availability",
        ),
        pytest.param({**VALID, "max_preguntas_por_mensaje": 3}, id="max-out-of-enum"),
        pytest.param({**VALID, "max_preguntas_por_mensaje": 0}, id="max-zero"),
        pytest.param({**VALID, "max_preguntas_por_mensaje": "1"}, id="max-not-an-int"),
        pytest.param({**VALID, "max_preguntas_por_mensaje": True}, id="max-is-a-bool"),
        pytest.param({**VALID, "derivaciones": "cobertura"}, id="derivaciones-not-a-list"),
        pytest.param({**VALID, "derivaciones": ["cobertura", "inventada"]}, id="unknown-derivation"),
    ],
)
def test_validate_rejects_malformed_conduct(value):
    with pytest.raises(ValueError):
        validate_conduct(value, FIELDS)


@pytest.mark.parametrize("redaccion", ["llm", "plantilla"])
def test_validate_projects_the_phrasing_switch(redaccion):
    # S5: the key has a reader now (`phrasing.phrase`), so it is validated and
    # returned instead of being dropped as dead configuration.
    value = {**VALID, "redaccion": redaccion}

    assert validate_conduct(value, FIELDS)["redaccion"] == redaccion


@pytest.mark.parametrize("redaccion", ["legacy-value", None])
def test_validate_rejects_an_unknown_phrasing_mode(redaccion):
    with pytest.raises(ValueError):
        validate_conduct({**VALID, "redaccion": redaccion}, FIELDS)


def test_validate_accepts_a_payload_without_the_phrasing_switch():
    """A panel that does not render the switch still saves; the default applies."""
    assert validate_conduct(VALID, FIELDS)["redaccion"] == "plantilla"


def test_get_returns_the_defaults_without_a_row():
    session = MagicMock()
    session.get.return_value = None

    assert get_conduct(session) == CHAT_CONDUCT_DEFAULTS


def test_get_drops_a_stored_rule_without_a_reader():
    """A row saved while the four phantom rules were accepted keeps loading.

    Without the filter the panel would render a rule it cannot validate, and the
    next save of the conduct card would answer 422.
    """
    session = MagicMock()
    row = MagicMock()
    row.value = {"derivaciones": ["cobertura", "garantia", "pedido_explicito"]}
    session.get.return_value = row

    assert get_conduct(session)["derivaciones"] == ["cobertura"]


def test_a_stored_row_without_a_rule_with_a_reader_reads_as_no_derivation():
    """A row whose rules were all phantom meant "cobertura off": keep it off."""
    session = MagicMock()
    row = MagicMock()
    row.value = {"derivaciones": ["garantia"]}
    session.get.return_value = row

    assert get_conduct(session)["derivaciones"] == []


def test_get_falls_back_per_key_on_a_partial_row():
    session = MagicMock()
    row = MagicMock()
    row.value = {"orden": ["failure"], "redaccion": "plantilla"}
    session.get.return_value = row

    conduct = get_conduct(session)

    assert conduct["orden"] == ["failure"]
    assert conduct["redaccion"] == "plantilla"
    assert conduct["max_preguntas_por_mensaje"] == 1
    assert conduct["derivaciones"] == list(CONDUCT_DERIVACIONES)

from types import SimpleNamespace

import pytest

from app.services.case_ficha import (
    asks_about_money,
    observe_spending,
    spending_evidence,
)


@pytest.mark.parametrize(
    "phrase",
    [
        "soy arrendatario",
        "soy arrendataria",
        "arriendo la casa",
        "arriendo el departamento",
        "consulto con el dueño",
        "consulto con la dueña",
        "lo consulto con el dueño",
        "lo consulto con la dueña",
        "te escribo de parte de",
        "hablo de parte de",
        "escribo de parte de",
        "administro la propiedad",
        "administro el edificio",
        "no es mi casa",
        "no es mi departamento",
        "no soy el dueño",
        "no soy la dueña",
        "no soy propietario",
    ],
)
def test_non_decider_phrases_lower_to_no(phrase):
    assert spending_evidence(f"Hola, {phrase}.") == "no"


def test_naming_another_owner_gives_duda():
    assert spending_evidence("El dueño es Juan") == "duda"


def test_explicit_self_declaration_gives_si():
    assert spending_evidence("Yo decido") == "si"


def test_courtesy_without_evidence_does_not_change_value():
    assert spending_evidence("te molesto con una pregunta") is None


def test_accents_and_case_are_ignored():
    assert spending_evidence("CONSULTO CON LA DUEÑA") == "no"
    assert spending_evidence("YO TOMO LA DECISIÓN") == "si"
    assert spending_evidence("EL PROPIETARIO ES Juan") == "duda"


def test_evidence_precedence_is_no_then_si_then_duda():
    assert spending_evidence("el dueño es Juan, yo decido, soy arrendatario") == "no"
    assert spending_evidence("el dueño es Juan, yo decido") == "si"


def test_absence_of_evidence_never_changes_stored_value():
    for value in ("si", "duda", "no"):
        customer = SimpleNamespace(decide_spending=value)
        assert observe_spending(None, customer, "te molesto con una pregunta") is customer
        assert customer.decide_spending == value


def test_duda_evidence_lowers_si_but_never_overwrites_no():
    si = SimpleNamespace(decide_spending="si")
    assert observe_spending(None, si, "el dueño es Juan") is si
    assert si.decide_spending == "duda"

    no = SimpleNamespace(decide_spending="no")
    observe_spending(None, no, "el dueño es Juan")
    assert no.decide_spending == "no"


def test_explicit_no_and_si_evidence_set_the_value():
    si = SimpleNamespace(decide_spending="si")
    observe_spending(None, si, "soy arrendataria")
    assert si.decide_spending == "no"

    duda = SimpleNamespace(decide_spending="duda")
    observe_spending(None, duda, "yo decido")
    assert duda.decide_spending == "si"


def test_asks_about_money_detects_price_and_ignores_heating_phrase():
    assert asks_about_money("¿Cuánto cuesta la visita?") is True
    assert asks_about_money("no calienta la casa") is False


def test_money_intent_alone_puts_money_at_stake():
    """S8: the classifier's `valores` intent counts even without a price word."""
    assert asks_about_money("y eso?", intent="valores") is True

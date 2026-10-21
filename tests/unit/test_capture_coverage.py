"""Coverage derivation (S15).

A comuna outside `coverage.communes` is not rejected: the flow derives it to an
advisor instead of promising a visit. The rule is closed-list configuration from
`chat.conduct.derivaciones`, so turning `cobertura` off stops the derivation.
"""

from app.chat.nodes.capture import _out_of_coverage

COMMUNES = [
    "Las Condes",
    "Ñuñoa",
    "Lo Barnechea",
    "La Reina",
    "Peñalolén",
    "Colina",
    "Huechuraba",
]
RULE_ON = ["cobertura", "garantia"]


def test_a_covered_comuna_does_not_derive():
    assert _out_of_coverage({"comuna": "Las Condes"}, COMMUNES, RULE_ON) is False


def test_coverage_uses_the_shared_normalization():
    assert _out_of_coverage({"comuna": "nunoa"}, COMMUNES, RULE_ON) is False
    assert _out_of_coverage({"comuna": "  ÑUÑOA "}, COMMUNES, RULE_ON) is False


def test_a_comuna_outside_the_list_derives():
    assert _out_of_coverage({"comuna": "La Florida"}, COMMUNES, RULE_ON) is True


def test_no_comuna_does_not_derive():
    assert _out_of_coverage({}, COMMUNES, RULE_ON) is False


def test_a_skipped_comuna_does_not_derive():
    assert _out_of_coverage({"comuna": "unknown"}, COMMUNES, RULE_ON) is False


def test_the_rule_has_to_be_active():
    assert _out_of_coverage({"comuna": "La Florida"}, COMMUNES, ["garantia"]) is False

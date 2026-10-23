"""Model-free contracts for the conversation-evaluation harness.

Why this file exists
--------------------
`scripts/conv_eval.py` drives the **real** brain: it needs a database, a model
and a seeded knowledge base, so a full run is not deterministic and can never
live in this suite. What *is* pinned here is everything that must not rot
silently:

- the **corpus schema** (`scripts/conv_eval_corpus.yaml`): a fixture edit cannot
  rename a tier, duplicate an id, or invent an expectation key unnoticed;
- the **gate math** (`evaluate_gates`, `score_scenario`), driven by synthetic
  observations whose expected answer is known by construction;
- the **report math** (`summarize`, `compare_runs`), so a run diff cannot lie.

Nothing here touches the database, the network, or a language model. That is the
whole point of splitting `conv_eval.py` (model-free) from
`conv_eval_judge.py` (everything that calls an LLM).
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import conv_eval as ev  # noqa: E402

CORPUS_PATH = REPO_ROOT / "scripts" / "conv_eval_corpus.yaml"


# ---------------------------------------------------------------------------
# Helpers — a synthetic observation with a known, explicit shape
# ---------------------------------------------------------------------------


def observation(**overrides):
    """A minimal well-formed observation; tests override one field at a time."""
    base = {
        "state": "bot",
        "events": [],
        "intents": [],
        "replies": ["Hola, soy Max de Lumat. ¿En qué te ayudo?"],
        "turns": [
            {
                "text": "hola",
                "replies": ["Hola, soy Max de Lumat. ¿En qué te ayudo?"],
                "intent": None,
            }
        ],
    }
    base.update(overrides)
    return base


def scenario(**overrides):
    """A minimal well-formed scenario; `expect` is what the gate tests vary."""
    base = {
        "id": "synthetic",
        "tier": "simple",
        "persona": "cliente",
        "goal": "saludar",
        "turns": ("hola",),
        "max_turns": 1,
        "expect": {},
        "hard_fails": (),
        "notes": "",
        "raw": {},
    }
    base.update(overrides)
    return ev.Scenario(**base)


def gates_of(scn, obs):
    return ev.evaluate_gates(scn, obs)


# ---------------------------------------------------------------------------
# Corpus schema — the fixture is the instrument; a broken fixture is a silent
# wrong answer, which is worse than no benchmark.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def corpus():
    return ev.load_corpus(CORPUS_PATH)


def test_shipped_corpus_loads_with_fourteen_scenarios(corpus):
    assert corpus.version == 1
    assert len(corpus.scenarios) == 14
    assert len({s.id for s in corpus.scenarios}) == 14


def test_shipped_corpus_covers_the_three_tiers(corpus):
    counts = {}
    for scn in corpus.scenarios:
        counts[scn.tier] = counts.get(scn.tier, 0) + 1
    assert counts == {"simple": 5, "complejo": 4, "supercomplejo": 5}


def test_shipped_corpus_declares_an_expectation_per_scenario(corpus):
    for scn in corpus.scenarios:
        assert scn.turns, f"{scn.id} has no turns"
        assert scn.expect, f"{scn.id} declares no expectation"
        assert scn.persona and scn.goal, f"{scn.id} cannot be replayed by --live"


def test_max_turns_defaults_to_the_scripted_length(corpus):
    for scn in corpus.scenarios:
        assert scn.max_turns >= len(scn.turns)
        if "max_turns" not in scn.raw:
            assert scn.max_turns == len(scn.turns)


MINIMAL = """
version: 1
conversations:
  - id: uno
    tier: simple
    persona: cliente
    goal: saludar
    turns: ["hola"]
    expect:
      state_any: [bot]
"""


def write_corpus(tmp_path, body):
    path = tmp_path / "corpus.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_minimal_corpus_is_accepted(tmp_path):
    corpus = ev.load_corpus(write_corpus(tmp_path, MINIMAL))
    assert [scn.id for scn in corpus.scenarios] == ["uno"]


@pytest.mark.parametrize(
    "mutation, message",
    [
        (MINIMAL.replace("tier: simple", "tier: facil"), "tier"),
        (MINIMAL.replace("      state_any: [bot]", "      inventado: 1"), "expect"),
        (MINIMAL.replace('turns: ["hola"]', "turns: []"), "turns"),
        (MINIMAL.replace("expect:", "max_turns: 0\nexpect:"), "max_turns"),
        (MINIMAL.replace("  - id: uno", "  - tier: simple"), "id"),
        (MINIMAL.replace("version: 1", "version: 99"), "version"),
        (MINIMAL.replace("conversations:", "conversacion:"), "conversations"),
        (MINIMAL.replace('turns: ["hola"]', "turns: hola"), "turns"),
        (MINIMAL.replace("      state_any: [bot]", "      state_any: []"), "state_any"),
        (MINIMAL.replace("      state_any: [bot]", "      state_any: [inventado]"),
         "state"),
        (MINIMAL.replace("    persona: cliente\n", ""), "persona"),
        (MINIMAL.replace("id: uno", "nombre: uno"), "id"),
    ],
)
def test_corpus_refusals_name_the_offending_field(tmp_path, mutation, message):
    with pytest.raises(ValueError) as raised:
        ev.load_corpus(write_corpus(tmp_path, mutation))
    assert message in str(raised.value)


def test_duplicate_ids_are_refused(tmp_path):
    body = MINIMAL + """
  - id: uno
    tier: simple
    persona: cliente
    goal: saludar
    turns: ["hola"]
    expect:
      state_any: [bot]
"""
    with pytest.raises(ValueError) as raised:
        ev.load_corpus(write_corpus(tmp_path, body))
    assert "duplicate" in str(raised.value)


def test_empty_corpus_is_refused(tmp_path):
    with pytest.raises(ValueError) as raised:
        ev.load_corpus(write_corpus(tmp_path, "version: 1\nconversations: []\n"))
    assert "conversations" in str(raised.value)


# ---------------------------------------------------------------------------
# Phone derivation — S8.2: a run must never inherit a customer from another run
# ---------------------------------------------------------------------------


def test_phone_is_e164_shaped():
    phone = ev.derive_phone("simple-saludo-variante", "baseline")
    assert phone.startswith("+569")
    assert len(phone) == 12
    assert phone[1:].isdigit()


def test_phone_is_deterministic_for_the_same_pair():
    assert ev.derive_phone("a", "run") == ev.derive_phone("a", "run")


def test_phone_changes_with_the_run_tag_and_with_the_scenario():
    assert ev.derive_phone("a", "run-1") != ev.derive_phone("a", "run-2")
    assert ev.derive_phone("a", "run") != ev.derive_phone("b", "run")


def test_phones_are_unique_across_a_whole_corpus(corpus):
    phones = {ev.derive_phone(scn.id, "baseline") for scn in corpus.scenarios}
    assert len(phones) == len(corpus.scenarios)


# ---------------------------------------------------------------------------
# Gates — G1..G9. Only declared gates are evaluated; a skipped gate must never
# count as a pass in the report.
# ---------------------------------------------------------------------------


def test_undeclared_gates_are_absent_from_the_result():
    result = gates_of(scenario(expect={"state_any": ["bot"]}), observation())
    # G8 is a structural invariant, not a declared expectation: it is always on.
    assert set(result) == {"G1", "G8"}
    assert result["G1"].ok is True
    assert result["G8"].ok is True


def test_g1_state_must_be_one_of_the_declared_ones():
    scn = scenario(expect={"state_any": ["bot", "closed"]})
    assert gates_of(scn, observation(state="bot"))["G1"].ok is True
    failed = gates_of(scn, observation(state="human"))["G1"]
    assert failed.ok is False
    assert "human" in failed.detail
    assert "bot, closed" in failed.detail


def test_g2_at_least_one_turn_must_classify_into_an_expected_intent():
    scn = scenario(expect={"intent_expected": ["agendar", "precio"]})
    assert gates_of(scn, observation(intents=["precio"]))["G2"].ok is True
    failed = gates_of(scn, observation(intents=["unknown"]))["G2"]
    assert failed.ok is False
    assert "agendar" in failed.detail


def test_g3_required_events_must_all_be_recorded():
    scn = scenario(expect={"events_required": ["escalation", "emergency"]})
    obs = observation(events=[{"event": "escalation", "cause": "handoff:emergency"}])
    failed = gates_of(scn, obs)["G3"]
    assert failed.ok is False
    assert "emergency" in failed.detail


def test_g4_forbidden_events_must_not_be_recorded():
    scn = scenario(expect={"events_forbidden": ["unknown_intent"]})
    obs = observation(events=[{"event": "unknown_intent", "cause": "rule"}])
    failed = gates_of(scn, obs)["G4"]
    assert failed.ok is False
    assert "unknown_intent" in failed.detail


def test_g5_forbidden_causes_are_matched_against_the_handoff_reason():
    scn = scenario(expect={"causes_forbidden": ["kb_miss"]})
    miss = observation(events=[{"event": "escalation", "cause": "handoff:kb_miss"}])
    assert gates_of(scn, miss)["G5"].ok is False
    other = observation(events=[{"event": "escalation", "cause": "handoff:emergency"}])
    assert gates_of(scn, other)["G5"].ok is True


def test_g6_anchors_ignore_case_and_accents():
    scn = scenario(expect={"must_include_any": ["sábado", "coordina"]})
    obs = observation(replies=["Puedes agendar un SABADO, lo coordina un asesor"])
    assert gates_of(scn, obs)["G6"].ok is True
    missed = gates_of(scn, observation(replies=["Solo lunes a viernes"]))["G6"]
    assert missed.ok is False
    assert "sábado" in missed.detail


def test_g6_reads_every_bot_reply_not_only_the_last():
    scn = scenario(expect={"must_include_any": ["mantenci"]})
    obs = observation(
        replies=["La mantención sale $50.000", "¿Te coordino la visita?"],
        turns=[
            {"text": "a", "replies": ["La mantención sale $50.000"], "intent": None},
            {"text": "b", "replies": ["¿Te coordino la visita?"], "intent": None},
        ],
    )
    assert gates_of(scn, obs)["G6"].ok is True


def test_g7_forbidden_anchors_ignore_case_and_accents():
    scn = scenario(expect={"must_not_include": ["no cubrimos", "fuera de cobertura"]})
    obs = observation(replies=["Lo sentimos, No Cubrimos esa zona"])
    assert gates_of(scn, obs)["G7"].ok is False


def test_g8_every_inbound_turn_needs_a_reply():
    obs = observation(
        turns=[
            {"text": "a", "replies": ["ok"], "intent": None},
            {"text": "b", "replies": [], "intent": None},
        ],
        replies=["ok"],
    )
    failed = gates_of(scenario(), obs)["G8"]
    assert failed.ok is False
    assert "2" in failed.detail


def test_g9_kb_answered_refuses_a_kb_miss():
    scn = scenario(expect={"kb_answered": True})
    miss = observation(events=[{"event": "escalation", "cause": "handoff:kb_miss"}])
    assert gates_of(scn, miss)["G9"].ok is False
    hit = observation(events=[{"event": "classified", "cause": "intent:precio"}])
    assert gates_of(scn, hit)["G9"].ok is True


def test_gate_result_carries_its_human_name():
    result = gates_of(scenario(expect={"state_any": ["bot"]}), observation())
    assert result["G1"].name == "state"


# ---------------------------------------------------------------------------
# Scoring — S4: a failed gate is never compensated by a high judge score
# ---------------------------------------------------------------------------


def verdict(**overrides):
    dimensions = {
        name: {"score": 4, "evidence": "cita"} for name in ev.DIMENSIONS
    }
    payload = {"dimensions": dimensions, "hard_fail": False, "hard_fail_reason": "",
               "summary": "bien"}
    payload.update(overrides)
    return payload


def test_all_gates_ok_and_a_clean_verdict_passes():
    scn = scenario(expect={"state_any": ["bot"]})
    score = ev.score_scenario(scn, gates_of(scn, observation()), verdict())
    assert score["passed"] is True
    assert score["capped"] is False
    assert score["score"] == 4.0
    assert score["gates_failed"] == []


def test_a_failed_gate_is_not_compensated_by_a_perfect_verdict():
    scn = scenario(expect={"state_any": ["human"]})
    score = ev.score_scenario(scn, gates_of(scn, observation(state="bot")), verdict())
    assert score["passed"] is False
    assert score["capped"] is True
    assert score["score"] == 0.0
    assert score["gates_failed"] == ["G1"]


def test_a_judge_hard_fail_caps_the_score_even_with_every_gate_green():
    scn = scenario(expect={"state_any": ["bot"]})
    score = ev.score_scenario(
        scn, gates_of(scn, observation()), verdict(hard_fail=True, hard_fail_reason="inventó")
    )
    assert score["passed"] is False
    assert score["capped"] is True
    assert score["score"] == 0.0


def test_without_a_judge_the_gates_alone_decide():
    scn = scenario(expect={"state_any": ["bot"]})
    score = ev.score_scenario(scn, gates_of(scn, observation()), None)
    assert score["passed"] is True
    assert score["score"] is None
    assert score["capped"] is False


def test_dimension_mean_reflects_partial_scores():
    scn = scenario(expect={"state_any": ["bot"]})
    payload = verdict()
    payload["dimensions"] = {
        name: {"score": 2, "evidence": "cita"} for name in ev.DIMENSIONS
    }
    score = ev.score_scenario(scn, gates_of(scn, observation()), payload)
    assert score["score"] == 2.0


# ---------------------------------------------------------------------------
# Report math — summarize and compare_runs
# ---------------------------------------------------------------------------


def score_row(scenario_id, tier, passed, failed_gates=(), score=None):
    return {
        "scenario": scenario_id,
        "tier": tier,
        "passed": passed,
        "capped": not passed,
        "gates_failed": list(failed_gates),
        "score": score,
        "dimensions": {name: score for name in ev.DIMENSIONS} if score is not None else {},
    }


def test_summarize_counts_passes_and_gate_failures_per_tier():
    rows = [
        score_row("a", "simple", True, score=4.0),
        score_row("b", "simple", False, ["G4"], score=0.0),
        score_row("c", "supercomplejo", False, ["G4", "G9"], score=0.0),
    ]
    summary = ev.summarize(rows)
    assert summary["scenarios"] == 3
    assert summary["passed"] == 1
    assert summary["gate_failures"] == {"G4": 2, "G9": 1}
    assert summary["by_tier"]["simple"] == {"scenarios": 2, "passed": 1}
    assert summary["by_tier"]["supercomplejo"] == {"scenarios": 1, "passed": 0}


def test_summarize_reports_the_mean_per_dimension_and_the_worst_one():
    rows = [
        score_row("a", "simple", True, score=4.0),
        score_row("b", "simple", True, score=2.0),
    ]
    summary = ev.summarize(rows)
    assert summary["dimensions"]["grounding"]["mean"] == 3.0
    assert summary["worst_dimension"] in ev.DIMENSIONS


def test_summarize_ignores_scenarios_without_a_verdict_for_the_means():
    rows = [
        score_row("a", "simple", True, score=4.0),
        score_row("b", "simple", True, score=None),
    ]
    summary = ev.summarize(rows)
    assert summary["dimensions"]["grounding"]["n"] == 1
    assert summary["dimensions"]["grounding"]["mean"] == 4.0


def test_compare_runs_reports_a_pass_to_fail_flip_as_a_regression():
    previous = {"runs": [score_row("a", "simple", True, score=4.0)]}
    current = {"runs": [score_row("a", "simple", False, ["G1"], score=0.0)]}
    diff = ev.compare_runs(current, previous)
    assert diff["regressions"] == ["a"]
    assert diff["fixes"] == []
    assert diff["gate_flips"] == [{"scenario": "a", "gate": "G1", "from": True, "to": False}]


def test_compare_runs_reports_a_fail_to_pass_flip_as_a_fix():
    previous = {"runs": [score_row("a", "simple", False, ["G1"], score=0.0)]}
    current = {"runs": [score_row("a", "simple", True, score=4.0)]}
    diff = ev.compare_runs(current, previous)
    assert diff["fixes"] == ["a"]
    assert diff["regressions"] == []


def test_compare_runs_reports_the_dimension_delta():
    previous = {"runs": [score_row("a", "simple", True, score=2.0)]}
    current = {"runs": [score_row("a", "simple", True, score=3.0)]}
    diff = ev.compare_runs(current, previous)
    assert diff["dimension_delta"]["grounding"] == 1.0


def test_compare_runs_refuses_to_call_two_different_corpora_comparable():
    previous = {"corpus_fingerprint": "aaa", "runs": []}
    current = {"corpus_fingerprint": "bbb", "runs": []}
    assert ev.compare_runs(current, previous)["comparable"] is False


def test_compare_runs_marks_the_same_corpus_comparable():
    previous = {"corpus_fingerprint": "aaa", "runs": []}
    current = {"corpus_fingerprint": "aaa", "runs": []}
    assert ev.compare_runs(current, previous)["comparable"] is True


def test_dimensions_match_the_judge_module():
    """The judged dimensions are declared in the judge; the report math here
    must agree with it or every mean reports the wrong thing."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import conv_eval_judge as judge  # noqa: PLC0415

    assert ev.DIMENSIONS == judge.DIMENSIONS

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

import subprocess
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


def test_shipped_corpus_loads_with_fifteen_scenarios(corpus):
    assert corpus.version == 1
    assert len(corpus.scenarios) == 15
    assert len({s.id for s in corpus.scenarios}) == 15


def test_shipped_corpus_covers_the_three_tiers(corpus):
    counts = {}
    for scn in corpus.scenarios:
        counts[scn.tier] = counts.get(scn.tier, 0) + 1
    assert counts == {"simple": 6, "complejo": 4, "supercomplejo": 5}


def test_shipped_corpus_declares_an_expectation_per_scenario(corpus):
    for scn in corpus.scenarios:
        assert scn.turns, f"{scn.id} has no turns"
        assert scn.expect, f"{scn.id} declares no expectation"
        assert scn.persona and scn.goal, f"{scn.id} cannot be replayed by --live"


def test_a_live_run_gives_the_simulated_customer_room(corpus):
    """The scripted turns are the opening of the conversation, not all of it — except
    on `simple`, where they ARE the conversation (S2)."""
    for scn in corpus.scenarios:
        budget = ev.resolve_budget(scn, live=True)
        assert budget >= len(scn.turns)
        if scn.max_turns is not None:
            assert budget == scn.max_turns
        elif scn.tier == "simple":
            assert budget == len(scn.turns)
        else:
            assert budget == len(scn.turns) + ev.SIMULATED_TURNS


def test_a_scripted_run_keeps_its_exact_script(corpus):
    """The live headroom must never change what a scripted run measures."""
    for scn in corpus.scenarios:
        plan = ev.plan_turns(scn.turns, ev.resolve_budget(scn, live=False), live=False)
        assert plan == [("scripted", text) for text in scn.turns], scn.id


def test_a_simple_scenario_keeps_its_script_and_nothing_more(corpus):
    """S2: `simple` is the floor of the measurement, and a floor that depends on what
    a language model decides to invent is not a floor."""
    for scn in corpus.by_tier("simple"):
        if scn.max_turns is not None:
            continue
        assert ev.resolve_budget(scn, live=True) == len(scn.turns), scn.id


def test_the_other_tiers_keep_their_simulated_room(corpus):
    for scn in corpus.by_tier("complejo") + corpus.by_tier("supercomplejo"):
        if scn.max_turns is not None:
            continue
        assert ev.resolve_budget(scn, live=True) == len(scn.turns) + ev.SIMULATED_TURNS, scn.id


def test_a_declared_ceiling_still_wins_on_a_simple_scenario():
    scn = scenario(tier="simple", turns=("hola",), max_turns=4)

    assert ev.resolve_budget(scn, live=True) == 4


def test_an_override_still_wins_on_a_simple_scenario():
    scn = scenario(tier="simple", turns=("hola",), max_turns=None)

    assert ev.resolve_budget(scn, live=True, override=5) == 5


def test_a_simple_plan_never_reaches_the_simulator(corpus):
    for scn in corpus.by_tier("simple"):
        plan = ev.plan_turns(scn.turns, ev.resolve_budget(scn, live=True), live=True)
        assert plan and all(origin == "scripted" for origin, _text in plan), scn.id


def test_an_explicit_budget_wins_over_the_scenario(corpus):
    scn = corpus.scenarios[0]
    assert ev.resolve_budget(scn, live=True, override=9) == 9
    assert ev.resolve_budget(scn, live=False, override=9) == 9


def test_a_live_plan_reaches_the_simulated_customer(corpus):
    """Pins the defect this fixes: nine of fourteen scenarios never let it speak.

    The five `simple` scenarios are silent by decision (S2): they are the floor and
    they are reproducible, so the simulator never gets a turn there.
    """
    silent = []
    for scn in corpus.scenarios:
        plan = ev.plan_turns(scn.turns, ev.resolve_budget(scn, live=True), live=True)
        if not any(origin == "simulated" for origin, _text in plan):
            silent.append(scn.id)
    assert silent == [scn.id for scn in corpus.by_tier("simple")], silent


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


def test_g10_a_declared_cause_passes_the_gate():
    """`causes_required` is the mirror of `causes_forbidden`: the scenario accepts a
    derivation and says which one. Deriving for another reason still fails."""
    scn = scenario(expect={"causes_required": ["cobertura"]})
    obs = observation(events=[{"event": "escalation", "cause": "handoff:cobertura"}])

    assert gates_of(scn, obs)["G10"].ok is True


def test_g10_a_cause_that_is_not_the_declared_one_fails_naming_it():
    scn = scenario(expect={"causes_required": ["booking_unavailable"]})
    obs = observation(events=[{"event": "escalation", "cause": "handoff:persona"}])

    failed = gates_of(scn, obs)["G10"]

    assert failed.ok is False
    assert "booking_unavailable" in failed.detail
    assert "handoff:persona" in failed.detail


def test_g10_a_conversation_with_no_derivation_at_all_fails():
    """A scenario that declares a cause is a scenario where the derivation must
    happen: finishing inside the bot means the case was never taken."""
    scn = scenario(expect={"causes_required": ["cobertura"]})

    failed = gates_of(scn, observation(events=[]))["G10"]

    assert failed.ok is False


def test_a_scenario_that_declares_no_cause_has_no_g10():
    """Skipped is absent from the result, never a pass — the convention every gate
    follows, pinned here for the new one."""
    result = gates_of(scenario(expect={"state_any": ["bot"]}), observation())

    assert "G10" not in result


def test_the_corpus_loader_accepts_causes_required(tmp_path):
    text = CORPUS_PATH.read_text(encoding="utf-8")
    patched = text.replace(
        "      state_any: [bot]\n      events_forbidden: [escalation]\n",
        "      state_any: [human]\n      causes_required: [booking_unavailable]\n",
        1,
    )
    assert patched != text, "the fixture changed: this test must be revisited"
    path = tmp_path / "corpus.yaml"
    path.write_text(patched, encoding="utf-8")

    loaded = ev.load_corpus(path)

    patched_scenario = next(
        scn for scn in loaded.scenarios if "causes_required" in scn.expect
    )
    assert patched_scenario.expect["causes_required"] == ["booking_unavailable"]


def test_an_empty_causes_required_list_is_refused(tmp_path):
    text = CORPUS_PATH.read_text(encoding="utf-8")
    patched = text.replace(
        "      state_any: [bot]\n      events_forbidden: [escalation]\n",
        "      state_any: [human]\n      causes_required: []\n",
        1,
    )
    path = tmp_path / "corpus.yaml"
    path.write_text(patched, encoding="utf-8")

    with pytest.raises(ValueError) as raised:
        ev.load_corpus(path)

    assert "causes_required" in str(raised.value)


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


def test_two_reports_of_different_corpora_are_not_comparable():
    """A written report carries the fingerprint under `stamp`, which is where the
    runner reads it. Comparing the top-level key compared None against None and
    called every pair of runs comparable."""
    current = report_for([score_row("a", "simple", True, score=4.0)])
    previous = report_for([score_row("a", "simple", True, score=4.0)])
    previous["stamp"]["corpus_fingerprint"] = "otro-corpus"

    assert ev.compare_runs(current, previous)["comparable"] is False


def test_reports_of_the_same_corpus_are_comparable_through_the_stamp():
    current = report_for([score_row("a", "simple", True, score=4.0)])
    previous = report_for([score_row("a", "simple", True, score=4.0)])

    assert ev.compare_runs(current, previous)["comparable"] is True


def test_dimensions_match_the_judge_module():
    """The judged dimensions are declared in the judge; the report math here
    must agree with it or every mean reports the wrong thing."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import conv_eval_judge as judge  # noqa: PLC0415

    assert ev.DIMENSIONS == judge.DIMENSIONS


# ---------------------------------------------------------------------------
# Observation — production event shapes in, gate inputs out
# ---------------------------------------------------------------------------


def snapshot(**overrides):
    base = {
        "state": "bot",
        "events": [
            {"event": "state_change", "cause": "bot->bot: receive", "actor": "system"},
            {"event": "classified", "cause": "intent:precio", "actor": "rule"},
            {"event": "unknown_intent", "cause": "intent:unknown", "actor": "rule"},
        ],
        "messages": [
            {"direction": "inbound", "text": "cuanto sale?", "status": "received"},
            {"direction": "outbound", "text": "La mantención sale $50.000", "status": "sent"},
        ],
    }
    base.update(overrides)
    return base


def test_build_observation_maps_classified_events_to_intents():
    observation = ev.build_observation(snapshot(), [{"text": "cuanto sale?", "replies": ["$50.000"]}])
    assert observation["intents"] == ["precio", "unknown"]


def test_build_observation_reads_replies_from_outbound_messages_only():
    observation = ev.build_observation(snapshot(), [])
    assert observation["replies"] == ["La mantención sale $50.000"]


def test_build_observation_keeps_the_events_for_the_gate_layer():
    observation = ev.build_observation(snapshot(), [])
    assert {"event": "classified", "cause": "intent:precio"} in observation["events"]


def test_build_observation_carries_the_turns_through():
    turns = [{"text": "hola", "replies": ["hola"], "intent": None}]
    assert ev.build_observation(snapshot(), turns)["turns"] == turns


def test_transcript_of_alternates_customer_and_assistant():
    observation = {
        "turns": [
            {"text": "hola", "replies": ["Hola, soy Max"], "intent": None},
            {"text": "precio?", "replies": ["$50.000", "¿coordino?"], "intent": None},
        ]
    }
    assert ev.transcript_of(observation) == [
        {"role": "customer", "text": "hola"},
        {"role": "assistant", "text": "Hola, soy Max"},
        {"role": "customer", "text": "precio?"},
        {"role": "assistant", "text": "$50.000"},
        {"role": "assistant", "text": "¿coordino?"},
    ]


# ---------------------------------------------------------------------------
# Stamp and report rendering
# ---------------------------------------------------------------------------


def test_a_clean_tree_with_a_sealed_kb_is_citable():
    assert ev.is_citable({"dirty": False, "kb_documents": 4}) is True


def test_a_dirty_tree_is_never_citable():
    assert ev.is_citable({"dirty": True, "kb_documents": 4}) is False


def test_an_unsealed_kb_is_never_citable():
    assert ev.is_citable({"dirty": False, "kb_documents": 0}) is False


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _committed_repo(tmp_path: Path) -> Path:
    """A throwaway git repo laid out like this one: code plus `odd/evals/`."""
    repo = tmp_path / "repo"
    (repo / "odd" / "evals").mkdir(parents=True)
    (repo / "app").mkdir()
    (repo / "app" / "code.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "init")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    return repo


def test_report_files_left_in_the_working_tree_do_not_dirty_it(tmp_path):
    """A report is the instrument's own output, not an edit to the tree it measures."""
    repo = _committed_repo(tmp_path)
    (repo / "odd" / "evals" / "conv-eval-clean-1.md").write_text("reporte\n", encoding="utf-8")
    (repo / "odd" / "evals" / "conv-eval-clean-1.json").write_text("{}\n", encoding="utf-8")

    _, dirty = ev.git_state(repo)

    assert dirty is False


def test_a_committed_report_overwritten_by_a_new_run_does_not_dirty_the_tree(tmp_path):
    """Once the transcripts are committed, every later run rewrites them."""
    repo = _committed_repo(tmp_path)
    report = repo / "odd" / "evals" / "conv-eval-clean-1.md"
    report.write_text("corrida anterior\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "anterior")
    report.write_text("corrida nueva\n", encoding="utf-8")

    _, dirty = ev.git_state(repo)

    assert dirty is False


def test_an_edit_outside_the_report_still_dirties_the_tree(tmp_path):
    repo = _committed_repo(tmp_path)
    (repo / "app" / "code.py").write_text("x = 2\n", encoding="utf-8")

    _, dirty = ev.git_state(repo)

    assert dirty is True


def test_an_untracked_file_outside_the_report_still_dirties_the_tree(tmp_path):
    repo = _committed_repo(tmp_path)
    (repo / "app" / "extra.py").write_text("y = 1\n", encoding="utf-8")

    _, dirty = ev.git_state(repo)

    assert dirty is True


def report_for(rows, *, dirty=False, diff=None):
    return {
        "stamp": {
            "run_tag": "baseline",
            "started_at": "2026-10-23T12:00:00+00:00",
            "head": "e354f563",
            "dirty": dirty,
            "corpus_fingerprint": "f903619e78bc",
            "kb_fingerprint": "abc123",
            "kb_documents": 4,
            "judge_model": "deepseek-v4.1-flash",
            "live": False,
        },
        "runs": rows,
        "summary": ev.summarize(rows),
        "gate_details": {row["scenario"]: {"G4": "se registró lo prohibido: unknown_intent"} for row in rows},
        "diff": diff,
    }


def test_render_markdown_declares_that_it_measures_the_brain_not_the_channel():
    markdown = ev.render_markdown(report_for([score_row("a", "simple", True, score=4.0)]))
    assert "cerebro" in markdown
    assert "webhook" in markdown
    assert "`baseline`" in markdown


def test_render_markdown_warns_that_a_dirty_run_is_not_a_baseline():
    markdown = ev.render_markdown(
        report_for([score_row("a", "simple", True, score=4.0)], dirty=True)
    )
    assert "No citable como baseline" in markdown


def test_render_markdown_lists_each_failed_gate_with_its_detail():
    markdown = ev.render_markdown(
        report_for([score_row("a", "simple", False, ["G4"], score=0.0)])
    )
    assert "G4 · events_forbidden" in markdown
    assert "se registró lo prohibido: unknown_intent" in markdown


def test_render_markdown_says_so_when_there_is_no_previous_run():
    markdown = ev.render_markdown(report_for([score_row("a", "simple", True, score=4.0)]))
    assert "Sin corrida previa" in markdown


# ---------------------------------------------------------------------------
# La dispersión del juez llega a la página (L18) — un número sin ± miente
# ---------------------------------------------------------------------------


def spread_row(scenario_id, tier, passed, score, spreads, failed_gates=()):
    row = score_row(scenario_id, tier, passed, failed_gates, score)
    row["dimension_spread"] = spreads
    return row


def spreads(**overrides):
    base = dict.fromkeys(ev.DIMENSIONS, 0)
    base.update(overrides)
    return base


def test_the_dimension_table_carries_the_worst_spread_the_judge_produced():
    rows = [
        spread_row("a", "simple", True, 4.0, spreads(policy=2, escalation=1)),
        spread_row("b", "simple", False, 0.0, spreads(grounding=1, conversational=3)),
    ]

    summary = ev.summarize(rows)

    assert summary["dimensions"]["policy"]["spread_max"] == 2
    assert summary["dimensions"]["conversational"]["spread_max"] == 3
    assert summary["dimensions"]["tone"]["spread_max"] == 0


def test_every_scenario_reaches_the_page_with_its_score_and_its_uncertainty():
    """A passing scenario is invisible in the report today: only failures get a
    section. The ± is what makes a 0.9 difference readable as noise."""
    rows = [
        spread_row("sano", "simple", True, 3.5, spreads(policy=2)),
        spread_row("roto", "complejo", False, 0.0, spreads(conversational=1, tone=1)),
    ]

    markdown = ev.render_markdown(report_for(rows))

    assert "± máx" in markdown
    assert "| `sano` | simple | 3.50 | ±2 |" in markdown
    assert "| `roto` | complejo | 0.00 | ±1 |" in markdown


def test_a_gates_only_run_invents_no_uncertainty():
    markdown = ev.render_markdown(report_for([score_row("a", "simple", True, score=None)]))

    assert "±" not in markdown


# ---------------------------------------------------------------------------
# Un escenario que no se mide (L17) — la corrida sigue, y lo dice
# ---------------------------------------------------------------------------


def unmeasured_report(rows, failures):
    report = report_for(rows)
    report["run_failures"] = failures
    return report


def test_an_unmeasured_scenario_is_never_citable():
    """A run with a hole in it is a diagnostic, not a baseline: the other rows are
    real, but nobody can cite 13 of 14 as the state of the bot."""
    clean = {"dirty": False, "kb_documents": 4}

    assert ev.is_citable(clean) is True
    assert ev.is_citable(clean, unmeasured=1) is False


def test_the_report_names_the_unmeasured_scenario_and_withholds_citability():
    report = unmeasured_report(
        [score_row("sano", "simple", True, score=4.0)],
        {"simple-horario-sabado": "no usable simulated turn after 2 attempts: no JSON object"},
    )

    markdown = ev.render_markdown(report)

    assert "No citable como baseline" in markdown
    assert "simple-horario-sabado" in markdown
    assert "no usable simulated turn after 2 attempts" in markdown
    assert "1 escenario(s) no medidos" in markdown


def test_exit_2_marks_an_incomplete_measurement():
    """2 is the code the run already used when it aborted, so an automation that
    checks `!= 0` keeps working and one that reads the number still sees it."""
    report = unmeasured_report(
        [score_row("sano", "simple", True, score=4.0)], {"roto": "boom"}
    )

    assert ev.exit_code(report) == 2


def test_exit_1_marks_a_complete_run_that_did_not_pass():
    failing_gate = report_for([score_row("a", "simple", False, ["G4"], score=0.0)])
    missing_verdict = report_for([score_row("a", "simple", True, score=None)])
    missing_verdict["judge_failures"] = {"a": "sin veredicto"}

    assert ev.exit_code(failing_gate) == 1
    assert ev.exit_code(missing_verdict) == 1


def test_exit_0_needs_every_scenario_measured_and_passing():
    assert ev.exit_code(report_for([score_row("a", "simple", True, score=4.0)])) == 0


def test_render_markdown_reports_regressions_from_the_diff():
    diff = {"comparable": True, "regressions": ["a"], "fixes": [], "gate_flips": [], "dimension_delta": {}}
    markdown = ev.render_markdown(
        report_for([score_row("a", "simple", True, score=4.0)], diff=diff)
    )
    assert "Regresiones: a" in markdown


def test_render_markdown_refuses_to_diff_two_different_corpora():
    diff = {"comparable": False, "regressions": [], "fixes": [], "gate_flips": [], "dimension_delta": {}}
    markdown = ev.render_markdown(report_for([], diff=diff))
    assert "No comparable" in markdown


def test_report_paths_are_tagged_and_sit_side_by_side(tmp_path):
    json_path, md_path = ev.report_paths(tmp_path, "baseline")
    assert json_path.name == "conv-eval-baseline.json"
    assert md_path.name == "conv-eval-baseline.md"


def test_previous_report_is_the_newest_other_run(tmp_path):
    import os

    current = tmp_path / "conv-eval-baseline.json"
    older = tmp_path / "conv-eval-older.json"
    newer = tmp_path / "conv-eval-newer.json"
    for path in (current, older, newer):
        path.write_text("{}", encoding="utf-8")
    os.utime(current, (1000, 1000))
    os.utime(older, (2000, 2000))
    os.utime(newer, (3000, 3000))
    assert ev.previous_report(tmp_path, current) == newer


def test_previous_report_is_none_for_the_first_run(tmp_path):
    current = tmp_path / "conv-eval-baseline.json"
    current.write_text("{}", encoding="utf-8")
    assert ev.previous_report(tmp_path, current) is None


def test_write_report_writes_both_files(tmp_path):
    report = report_for([score_row("a", "simple", True, score=4.0)])
    json_path, md_path = ev.write_report(report, tmp_path)
    assert json_path.exists() and md_path.exists()
    assert "Evaluación conversacional" in md_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI — the validator mode is the one path that needs neither DB nor model
# ---------------------------------------------------------------------------


def test_validate_only_accepts_the_shipped_corpus(capsys):
    assert ev.main(["--validate-only"]) == 0
    captured = capsys.readouterr()
    assert "15" in captured.out
    assert "simple 6" in captured.out
    assert "supercomplejo 5" in captured.out
    assert captured.err == ""


def test_validate_only_refuses_a_broken_corpus(tmp_path, capsys):
    path = write_corpus(tmp_path, MINIMAL.replace("tier: simple", "tier: facil"))
    assert ev.main(["--validate-only", "--corpus", str(path)]) == 2
    captured = capsys.readouterr()
    assert "tier" in captured.err
    assert captured.out == ""


def test_selection_filters_by_tier_and_by_id(corpus):
    import argparse

    by_tier = ev._select(corpus, argparse.Namespace(tier="supercomplejo", only=None))
    assert {scn.tier for scn in by_tier} == {"supercomplejo"}
    assert len(by_tier) == 5

    by_id = ev._select(
        corpus, argparse.Namespace(tier=None, only=["simple-saludo-variante"])
    )
    assert [scn.id for scn in by_id] == ["simple-saludo-variante"]


def test_selection_refuses_an_unknown_scenario_id(corpus):
    import argparse

    with pytest.raises(ValueError) as raised:
        ev._select(corpus, argparse.Namespace(tier=None, only=["no-existe"]))
    assert "no-existe" in str(raised.value)


def test_render_markdown_says_so_when_no_judge_measured_anything():
    markdown = ev.render_markdown(report_for([score_row("a", "simple", True, score=None)]))
    assert "Sin juez en esta corrida" in markdown
    assert "| grounding |" not in markdown


def test_render_markdown_names_the_conversations_the_judge_could_not_score():
    report = report_for([score_row("a", "simple", True, score=None)])
    report["judge_failures"] = {"a": "no usable verdict after 2 attempts"}
    markdown = ev.render_markdown(report)
    assert "Sin veredicto del juez" in markdown
    assert "no usable verdict after 2 attempts" in markdown


def test_g9_sees_a_soft_kb_miss_that_production_never_records():
    """Measured: the bot answered a KB question with the configured miss offer and
    `conversation_events` held only `classified`. The gate must read the reply."""
    scn = scenario(expect={"kb_answered": True})
    obs = observation(
        replies=["No tengo ese dato. ¿Prefieres que te tome los datos o que te atienda una persona?"],
        miss_text="No tengo ese dato. ¿Prefieres que te tome los datos o que te atienda una persona?",
    )
    failed = gates_of(scn, obs)["G9"]
    assert failed.ok is False
    assert "kb_miss" in failed.detail


def test_g9_passes_when_the_answer_came_from_the_kb():
    scn = scenario(expect={"kb_answered": True})
    obs = observation(
        replies=["Sí, llegamos a Maipú. Te coordino con un asesor."],
        miss_text="No tengo ese dato.",
    )
    assert gates_of(scn, obs)["G9"].ok is True


def test_the_row_carries_the_judge_evidence_for_every_dimension():
    """S9 calibrates against the cited evidence: a score without it is not reviewable."""
    scn = scenario(expect={"state_any": ["bot"]})
    payload = verdict()
    payload["dimensions"]["tone"] = {"score": 2, "evidence": "contestó con un formulario"}
    row = ev.score_scenario(scn, gates_of(scn, observation()), payload)
    assert row["evidence"]["tone"] == "contestó con un formulario"
    assert set(row["evidence"]) == set(ev.DIMENSIONS)


# ---------------------------------------------------------------------------
# Turn planning — who writes each turn is what makes the evaluator auditable
# ---------------------------------------------------------------------------


def test_without_live_the_plan_stops_at_the_scripted_turns():
    assert ev.plan_turns(["a", "b"], 5, live=False) == [("scripted", "a"), ("scripted", "b")]


def test_with_live_the_budget_is_filled_by_the_simulated_customer():
    assert ev.plan_turns(["a"], 3, live=True) == [
        ("scripted", "a"),
        ("simulated", None),
        ("simulated", None),
    ]


def test_a_budget_smaller_than_the_script_truncates_it():
    assert ev.plan_turns(["a", "b", "c"], 2, live=False) == [("scripted", "a"), ("scripted", "b")]


def test_render_transcripts_marks_who_wrote_every_turn():
    corpus = ev.load_corpus(CORPUS_PATH)
    scenario = corpus.scenarios[0]
    report = report_for([score_row(scenario.id, scenario.tier, True, score=4.0)])
    report["observations"] = {
        scenario.id: {
            "state": "bot",
            "events": [],
            "intents": [],
            "replies": ["hola"],
            "turns": [
                {"text": scenario.turns[0], "replies": ["hola"], "intent": None},
                {"text": "esto lo inventó el simulador", "replies": ["dale"], "intent": None,
                 "origin": "simulated"},
            ],
        }
    }
    report["gate_details"] = {scenario.id: {"G1": "state=bot"}}
    markdown = ev.render_transcripts(report, corpus)
    assert "`[scripted]`" in markdown
    assert "`[simulado]` — esto lo inventó el simulador" in markdown
    assert scenario.id in markdown


def test_a_reused_tag_with_existing_customers_is_refused():
    """Measured: a killed run left its rows, and the next run with the same tag
    stacked on top of conversations that had already escalated. The report said
    5/14 and every red belonged to the previous run."""
    error = ev.contamination_error(["complejo-agendar-calefont", "simple-despedida"])
    assert error is not None
    assert "complejo-agendar-calefont" in error
    assert "tag nuevo" in error


def test_a_fresh_tag_passes_the_contamination_check():
    assert ev.contamination_error([]) is None


# ---------------------------------------------------------------------------
# The Markdown transcript is the permanent record once --reset wipes the rows
# ---------------------------------------------------------------------------


def test_the_transcript_renders_every_message_of_the_log_in_order():
    corpus = ev.load_corpus(CORPUS_PATH)
    scenario = corpus.scenarios[0]
    report = report_for([score_row(scenario.id, scenario.tier, True, score=4.0)])
    report["observations"] = {
        scenario.id: {
            "state": "bot",
            "events": [],
            "intents": [],
            "replies": ["hola", "un aviso extra"],
            "turns": [{"text": scenario.turns[0], "replies": ["hola"], "intent": None}],
            "messages": [
                {"direction": "inbound", "text": scenario.turns[0]},
                {"direction": "outbound", "text": "hola"},
                {"direction": "outbound", "text": "un aviso extra"},
            ],
        }
    }
    report["gate_details"] = {scenario.id: {}}
    markdown = ev.render_transcripts(report, corpus)
    # the extra outbound message is not in `turns`, and must still be recorded
    assert "un aviso extra" in markdown
    assert markdown.index("hola") < markdown.index("un aviso extra")


def test_the_transcript_falls_back_to_turns_for_older_reports():
    corpus = ev.load_corpus(CORPUS_PATH)
    scenario = corpus.scenarios[0]
    report = report_for([score_row(scenario.id, scenario.tier, True, score=4.0)])
    report["observations"] = {
        scenario.id: {
            "state": "bot",
            "events": [],
            "intents": [],
            "replies": ["hola"],
            "turns": [{"text": scenario.turns[0], "replies": ["hola"], "intent": None}],
        }
    }
    report["gate_details"] = {scenario.id: {}}
    assert "hola" in ev.render_transcripts(report, corpus)


# ---------------------------------------------------------------------------
# Reset — truncating must be impossible outside the derived test database
# ---------------------------------------------------------------------------


def test_reset_is_refused_without_the_test_database_marker():
    refused = ev.reset_guard("postgresql+psycopg://app:app@localhost:5893/lumat", None)
    assert refused is not None
    assert "TEST_ADMIN_DB_URL" in refused


def test_reset_is_refused_when_the_target_is_a_different_database():
    refused = ev.reset_guard(
        "postgresql+psycopg://app:app@localhost:5432/lumat",
        "postgresql://lumat:lumat@localhost:5893/lumat",
    )
    assert refused is not None
    assert "5893" in refused


def test_reset_is_allowed_on_the_derived_test_database():
    assert (
        ev.reset_guard(
            "postgresql+psycopg://app:app@localhost:5893/lumat",
            "postgresql://lumat:lumat@localhost:5893/lumat",
        )
        is None
    )


# ---------------------------------------------------------------------------
# Judge repetitions — one call is one observation, not a measurement
# ---------------------------------------------------------------------------


def flat_verdict(score, *, hard_fail=False, reason="", evidence="cita"):
    return {
        "dimensions": {name: {"score": score, "evidence": evidence} for name in ev.DIMENSIONS},
        "hard_fail": hard_fail,
        "hard_fail_reason": reason,
    }


def test_a_single_verdict_passes_through_unchanged():
    aggregated = ev.aggregate_verdicts([flat_verdict(3)])

    assert {n: aggregated["dimensions"][n]["score"] for n in ev.DIMENSIONS} == {
        name: 3 for name in ev.DIMENSIONS
    }
    assert aggregated["spread"] == {name: 0 for name in ev.DIMENSIONS}


def test_the_median_is_taken_per_dimension():
    aggregated = ev.aggregate_verdicts([flat_verdict(1), flat_verdict(4), flat_verdict(2)])

    assert {n: aggregated["dimensions"][n]["score"] for n in ev.DIMENSIONS} == {
        name: 2 for name in ev.DIMENSIONS
    }


def test_the_spread_is_reported_per_dimension():
    low = flat_verdict(2)
    high = flat_verdict(2)
    low["dimensions"]["escalation"]["score"] = 0
    high["dimensions"]["escalation"]["score"] = 3

    aggregated = ev.aggregate_verdicts([low, high])

    assert aggregated["spread"]["escalation"] == 3
    assert aggregated["spread"]["tone"] == 0


def test_a_hard_fail_needs_a_majority():
    clean = flat_verdict(3)
    dirty = flat_verdict(3, hard_fail=True, reason="minimiza el reclamo")

    assert ev.aggregate_verdicts([dirty, clean, dirty])["hard_fail"] is True
    assert ev.aggregate_verdicts([dirty, clean, clean])["hard_fail"] is False


def test_the_evidence_comes_from_a_verdict_at_the_median():
    low = flat_verdict(1, evidence="baja")
    mid = flat_verdict(2, evidence="media")
    high = flat_verdict(4, evidence="alta")

    aggregated = ev.aggregate_verdicts([low, high, mid])

    assert aggregated["dimensions"]["tone"]["score"] == 2
    assert aggregated["dimensions"]["tone"]["evidence"] == "media"


def test_judge_row_asks_the_judge_once_per_repetition(corpus, monkeypatch):
    import conv_eval_judge

    calls = []

    def fake_judge(_client, **_kwargs):
        calls.append(1)
        return flat_verdict(3)

    monkeypatch.setattr(conv_eval_judge, "judge_conversation", fake_judge)
    aggregated = ev.judge_row(
        corpus.scenarios[0],
        observation(),
        client=object(),
        kb="",
        tarifario="",
        repetitions=3,
    )

    assert len(calls) == 3
    assert aggregated["dimensions"]["tone"]["score"] == 3
    assert aggregated["spread"]["tone"] == 0


def test_the_row_carries_the_spread_so_a_difference_is_readable(corpus):
    scn = corpus.scenarios[0]
    low = flat_verdict(3)
    high = flat_verdict(3)
    low["dimensions"]["escalation"]["score"] = 1
    high["dimensions"]["escalation"]["score"] = 4
    aggregated = ev.aggregate_verdicts([low, high])

    row = ev.score_scenario(scn, gates_of(scn, observation()), aggregated)

    assert row["dimensions"]["escalation"] == 2.5
    assert row["dimension_spread"]["escalation"] == 3


def test_zero_judge_repetitions_is_refused():
    """A run with no judge call would report a score nothing measured."""
    assert ev.main(["--judge-repetitions", "0"]) == 2


def test_the_report_says_how_many_calls_produced_a_score():
    report = report_for([score_row("a", "simple", True, score=4.0)])
    report["stamp"]["judge_repetitions"] = 3

    markdown = ev.render_markdown(report)

    assert "3 llamada(s) por escenario (mediana)" in markdown


def test_the_transcript_names_the_dimensions_that_moved():
    corpus = ev.load_corpus(CORPUS_PATH)
    scenario = corpus.scenarios[0]
    row = score_row(scenario.id, scenario.tier, True, score=4.0)
    row["dimension_spread"] = {"escalation": 2, "tone": 0}
    report = report_for([row])
    report["observations"] = {
        scenario.id: {
            "state": "bot",
            "events": [],
            "intents": [],
            "replies": ["hola"],
            "turns": [{"text": scenario.turns[0], "replies": ["hola"], "intent": None}],
        }
    }
    report["gate_details"] = {scenario.id: {"G1": "state=bot"}}

    markdown = ev.render_transcripts(report, corpus)

    assert "dispersión entre repeticiones:** escalation ±2" in markdown
    assert "tone ±0" not in markdown


def test_the_stamp_says_which_bot_was_measured():
    """A baseline that does not name the bot cannot be reproduced: the same
    markdown, corpus and KB describe deepseek-chat and deepseek-flash equally."""
    stamp = ev.RunStamp(
        run_tag="t",
        started_at="2026-10-26T00:00:00+00:00",
        head="abc1234",
        dirty=False,
        corpus_fingerprint="c0rp",
        kb_fingerprint="kb00",
        kb_documents=4,
        judge_model=None,
        judge_repetitions=0,
        live=True,
        bot_provider="deepseek",
        bot_model="deepseek-flash",
    ).as_dict()

    assert stamp["bot_provider"] == "deepseek"
    assert stamp["bot_model"] == "deepseek-flash"


def test_the_report_names_the_bot_and_claims_no_judge_calls_without_a_judge():
    report = report_for([score_row("a", "simple", True, score=None)])
    report["stamp"].update(
        {
            "judge_model": None,
            "judge_repetitions": 0,
            "bot_provider": "deepseek",
            "bot_model": "deepseek-flash",
        }
    )

    markdown = ev.render_markdown(report)

    assert "`deepseek-flash`" in markdown
    assert "llamada(s) por escenario" not in markdown

def test_a_failed_scenario_is_recorded_and_the_other_one_still_reports(tmp_path, monkeypatch):
    """The asymmetry L15 named: a missing verdict was recorded and the run
    continued, a failed scenario killed all fourteen. Now the run keeps the
    scenarios it could measure, says which one it could not, and refuses to be a
    baseline — `exit 2`, with a report on disk."""
    import json
    from types import SimpleNamespace

    broken = scenario(id="roto", tier="simple")
    healthy = scenario(id="sano", tier="simple")
    tiny = ev.Corpus(version=1, scenarios=(broken, healthy), fingerprint="c0rp")

    monkeypatch.setattr(ev, "load_corpus", lambda _path=None: tiny)
    monkeypatch.setitem(sys.modules, "seed_kb_docs", SimpleNamespace(ensure_dev_env=lambda: None))
    monkeypatch.setattr(ev, "existing_conversations", lambda *_a, **_k: [])
    monkeypatch.setattr(
        ev, "preflight", lambda: {"consistent": True, "documents": 4, "fingerprint": "kb00"}
    )
    monkeypatch.setattr(ev, "_bot_settings", lambda: ("deepseek", "deepseek-flash"))
    monkeypatch.setattr(ev, "git_state", lambda **_kwargs: ("e354f563", False))
    monkeypatch.setattr(ev, "miss_offer_text", lambda: "te derivo")

    def fake_run(scn, **_kwargs):
        if scn.id == "roto":
            raise RuntimeError("no usable simulated turn after 2 attempts: no JSON object")
        return {"observation": observation()}

    monkeypatch.setattr(ev, "run_scenario", fake_run)

    code = ev.main(
        ["--no-judge", "--quiet", "--run-tag", "prueba", "--out-dir", str(tmp_path)]
    )

    report = json.loads((tmp_path / "conv-eval-prueba.json").read_text(encoding="utf-8"))
    markdown = (tmp_path / "conv-eval-prueba.md").read_text(encoding="utf-8")
    assert code == 2
    assert "roto" in report["run_failures"]
    assert [row["scenario"] for row in report["runs"]] == ["sano"]
    assert report["summary"]["scenarios"] == 1
    assert "roto" in markdown
    assert "No citable como baseline" in markdown

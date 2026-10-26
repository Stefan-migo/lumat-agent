"""Conversation evaluation for the Lumat chat brain (ODD: chatbot-conv-eval).

Why this exists
---------------
The owner was writing a new conversation by hand every time the bot changed,
which measures the owner's imagination, not the bot. This harness runs a
**versioned corpus of customer conversations** against the real brain
(`app.chat.graph.run_conversation`, through the same seam as
`scripts/chat_harness.py`) and scores each one on two independent layers:

1. **Deterministic gates** — what the bot *did*: final state, intents recorded,
   events and their causes, whether every turn got a reply, whether the answers
   stayed inside the KB. Free, reproducible, no model in the loop.
2. **Rubric judge** — what the bot *said*, scored 0-4 per dimension with cited
   evidence (`scripts/conv_eval_judge.py`, the only module here that calls an
   LLM).

A gate does not average with the judge: `score_scenario` caps the score at 0
when any gate fails or the judge records a hard fail, so containment can never
be bought with fluency (S4, S8.4).

Split of responsibilities
-------------------------
This module must stay **importable, runnable and testable without a database,
a model or a provider key**. The corpus schema, the gate math and the run diff
are its model-free contract, pinned by `tests/unit/test_conv_eval.py`. Database
access, the judge and the simulated customer are imported lazily inside the
functions that need them, so `import conv_eval` costs nothing and fails nothing.

The gates
---------
Each gate is evaluated only when the scenario declares it; a skipped gate is
absent from the result and never counts as a pass. The one exception is G8,
which is a structural invariant and always evaluated.

===  ================  =======================================================
ID   Name              Fails when
===  ================  =======================================================
G1   state             the final conversation state is not in `state_any`
G2   intent            no turn classified into `intent_expected`
G3   events_required   an event in `events_required` was never recorded
G4   events_forbidden  an event in `events_forbidden` was recorded
G5   causes_forbidden  an event cause matches one in `causes_forbidden`
G6   must_include_any  no bot reply contains any of the anchors
G7   must_not_include  a bot reply contains one of the forbidden anchors
G8   reply_present     an inbound customer turn got no reply at all
G9   kb_answered       the answer lives in the KB, yet the bot took the kb_miss path
===  ================  =======================================================

Anchors are matched case- and accent-insensitively, as substrings: the bot says
"la mantención" and the anchor is "mantenci" on purpose.

G9 needs one word of warning. Production records `kb_miss` only when the miss
*escalates* (`cause=handoff:kb_miss`), so a soft miss — the bot answering with
the configured "no tengo ese dato, ¿coordinamos o te atiende una persona?"
offer and staying in `bot` — leaves **no event at all**. Measured: the run
answered a KB question with that offer and `conversation_events` held only
`classified`. The gate therefore also fails when a reply contains the configured
`messages.kb_miss_offer` text, which the runner reads from the database. The
production gap is real and out of scope here (`app/` is a non-goal): this is the
instrument reading the reply because the event does not exist.

Usage
-----
    eval "$(bash infra/test-db.sh env)"                 # this worktree's test stack
    export DEEPSEEK_API_KEY=...                        # the bot under test needs its key
    uv run python scripts/seed_kb_docs.py --apply      # once per stack
    uv run python scripts/conv_eval.py --validate-only # corpus only, no DB
    uv run python scripts/conv_eval.py --run-tag baseline
    uv run python scripts/conv_eval.py --tier supercomplejo --no-judge
"""

from __future__ import annotations

import hashlib
import statistics
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

__all__ = [
    "CORPUS_PATH",
    "DIMENSIONS",
    "GATE_NAMES",
    "Corpus",
    "GateResult",
    "PreflightError",
    "RunStamp",
    "Scenario",
    "build_observation",
    "compare_runs",
    "contamination_error",
    "reset_business_state",
    "reset_guard",
    "derive_phone",
    "evaluate_gates",
    "git_state",
    "is_citable",
    "load_corpus",
    "main",
    "preflight",
    "previous_report",
    "render_markdown",
    "render_transcripts",
    "plan_turns",
    "report_paths",
    "run_scenario",
    "score_scenario",
    "summarize",
    "transcript_of",
    "write_report",
]

_REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = _REPO_ROOT / "scripts" / "conv_eval_corpus.yaml"

TIERS = ("simple", "complejo", "supercomplejo")

# The judged dimensions live in the judge module; duplicated here because this
# module must not import it. `tests/unit/test_conv_eval.py` pins that the two
# tuples agree, so they cannot drift apart silently.
DIMENSIONS = ("grounding", "policy", "conversational", "escalation", "tone", "closure")

GATE_NAMES = {
    "G1": "state",
    "G2": "intent",
    "G3": "events_required",
    "G4": "events_forbidden",
    "G5": "causes_forbidden",
    "G6": "must_include_any",
    "G7": "must_not_include",
    "G8": "reply_present",
    "G9": "kb_answered",
}

_SCENARIO_KEYS = {
    "id",
    "tier",
    "persona",
    "goal",
    "turns",
    "max_turns",
    "expect",
    "hard_fails",
    "notes",
}
_EXPECT_KEYS = {
    "state_any",
    "intent_expected",
    "events_required",
    "events_forbidden",
    "causes_forbidden",
    "must_include_any",
    "must_not_include",
    "kb_answered",
}
# `escalation` carries its reason as `handoff:<reason>` and `kb_miss` is one of
# those reasons, never an event of its own (`app/chat/nodes/handoff.py:88`).
_HANDOFF_PREFIX = "handoff:"
_KNOWN_STATES = ("bot", "human", "closed")


# ---------------------------------------------------------------------------
# Corpus — the fixture is the instrument; a broken fixture is a silent wrong
# answer, which is worse than no benchmark.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Scenario:
    """One reproducible conversation: same turns, same phone, same cleanup."""

    id: str
    tier: str
    persona: str
    goal: str
    turns: tuple[str, ...]
    max_turns: int | None
    expect: Mapping[str, Any]
    hard_fails: tuple[str, ...] = ()
    notes: str = ""
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True)
class Corpus:
    version: int
    scenarios: tuple[Scenario, ...]
    fingerprint: str

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(scenario.id for scenario in self.scenarios)

    def by_tier(self, tier: str | None = None) -> tuple[Scenario, ...]:
        if tier is None:
            return self.scenarios
        return tuple(scenario for scenario in self.scenarios if scenario.tier == tier)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _string_list(value: Any, field_name: str, where: str) -> tuple[str, ...]:
    _require(
        isinstance(value, list) and all(isinstance(item, str) for item in value),
        f"{where}: `{field_name}` must be a list of strings",
    )
    return tuple(value)


def _build_scenario(entry: Any, index: int) -> Scenario:
    where = f"conversation #{index + 1}"
    _require(isinstance(entry, Mapping), f"{where}: must be a mapping")
    _require("id" in entry, f"{where}: every scenario needs an `id`")
    scenario_id = entry["id"]
    _require(
        isinstance(scenario_id, str) and scenario_id.strip() != "",
        f"{where}: `id` must be a non-empty string",
    )
    where = f"conversation {scenario_id!r}"

    unknown = set(entry) - _SCENARIO_KEYS
    _require(not unknown, f"{where}: unknown keys {sorted(unknown)}")

    tier = entry.get("tier")
    _require(
        tier in TIERS,
        f"{where}: `tier` must be one of {list(TIERS)}, got {tier!r}",
    )

    turns = _string_list(entry.get("turns"), "turns", where)
    _require(turns, f"{where}: `turns` must declare at least one customer message")

    max_turns = entry.get("max_turns")
    if max_turns is not None:
        _require(
            isinstance(max_turns, int) and not isinstance(max_turns, bool),
            f"{where}: `max_turns` must be an integer",
        )
        _require(
            max_turns >= len(turns),
            f"{where}: `max_turns` ({max_turns}) cannot be smaller than the "
            f"{len(turns)} scripted turns",
        )

    persona = entry.get("persona") or ""
    goal = entry.get("goal") or ""
    _require(
        isinstance(persona, str) and isinstance(goal, str),
        f"{where}: `persona` and `goal` must be strings",
    )
    _require(
        persona.strip() and goal.strip(),
        f"{where}: `persona` and `goal` are required, `--live` replays them",
    )

    expect = entry.get("expect")
    _require(isinstance(expect, Mapping), f"{where}: `expect` must be a mapping")
    _require(expect, f"{where}: `expect` must declare at least one gate")
    unknown = set(expect) - _EXPECT_KEYS
    _require(
        not unknown,
        f"{where}: unknown expect keys {sorted(unknown)}; "
        f"known ones are {sorted(_EXPECT_KEYS)}",
    )
    for key in ("state_any",):
        if key in expect:
            states = _string_list(expect[key], key, where)
            _require(states, f"{where}: `{key}` must declare at least one state")
            _require(
                set(states) <= set(_KNOWN_STATES),
                f"{where}: unknown state in `{key}`: "
                f"{sorted(set(states) - set(_KNOWN_STATES))}",
            )
    for key in (
        "intent_expected",
        "events_required",
        "events_forbidden",
        "causes_forbidden",
        "must_include_any",
        "must_not_include",
    ):
        if key in expect:
            values = _string_list(expect[key], key, where)
            _require(values, f"{where}: `{key}` must declare at least one value")
    if "kb_answered" in expect:
        _require(
            isinstance(expect["kb_answered"], bool),
            f"{where}: `kb_answered` must be a boolean",
        )

    hard_fails = tuple(entry.get("hard_fails") or ())
    _require(
        all(isinstance(item, str) for item in hard_fails),
        f"{where}: `hard_fails` must be a list of strings",
    )

    return Scenario(
        id=scenario_id,
        tier=tier,
        persona=persona,
        goal=goal,
        turns=turns,
        max_turns=max_turns,
        expect=dict(expect),
        hard_fails=hard_fails,
        notes=str(entry.get("notes") or ""),
        raw=dict(entry),
    )


def _fingerprint(version: int, scenarios: Sequence[Scenario]) -> str:
    payload = "\n".join(
        f"{scenario.id}|{scenario.tier}|{'~'.join(scenario.turns)}|{sorted(scenario.expect)}"
        for scenario in scenarios
    )
    return hashlib.sha256(f"v{version}\n{payload}".encode("utf-8")).hexdigest()[:12]


def load_corpus(path: Path = CORPUS_PATH) -> Corpus:
    """Load and validate the corpus. Raises ValueError on any violation.

    A silently wrong fixture produces a decision-grade report built on the wrong
    question, so every structural problem is a refusal with the offending field
    named.
    """
    import yaml

    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    _require(isinstance(raw, Mapping), "corpus: the document must be a mapping")

    version = raw.get("version")
    _require(
        version == 1,
        f"corpus: `version` must be 1, got {version!r}",
    )
    _require("conversations" in raw, "corpus: missing the `conversations` section")
    entries = raw["conversations"]
    _require(
        isinstance(entries, list),
        "corpus: `conversations` must be a list of scenarios",
    )
    _require(entries, "corpus: `conversations` is empty")

    scenarios = tuple(_build_scenario(entry, index) for index, entry in enumerate(entries))

    ids = Counter(scenario.id for scenario in scenarios)
    duplicates = sorted(name for name, count in ids.items() if count > 1)
    _require(not duplicates, f"corpus: duplicate scenario ids {duplicates}")

    return Corpus(version=version, scenarios=scenarios, fingerprint=_fingerprint(version, scenarios))


# ---------------------------------------------------------------------------
# Phone derivation — S8.2: a run must never inherit a customer from another run
# ---------------------------------------------------------------------------


def derive_phone(scenario_id: str, run_tag: str) -> str:
    """Derive a stable E.164 phone from `(scenario_id, run_tag)`.

    Deterministic on purpose: re-running the same tag reproduces the same
    customer, a new tag lands on a fresh one. Nothing is ever deleted, so the
    instrument cannot be poisoned by yesterday's memory (S8.2).
    """
    digest = hashlib.sha256(f"{scenario_id}:{run_tag}".encode("utf-8")).hexdigest()
    digits = "".join(character for character in digest if character.isdigit())
    return f"+569{digits[:8].ljust(8, '0')}"


# ---------------------------------------------------------------------------
# Gates — what the bot did, with no model in the loop
# ---------------------------------------------------------------------------


def _normalise(text: str) -> str:
    """Case- and accent-insensitive form used by every anchor gate."""
    decomposed = unicodedata.normalize("NFD", text.casefold())
    return "".join(character for character in decomposed if not unicodedata.combining(character))


@dataclass(frozen=True)
class GateResult:
    gate: str
    name: str
    ok: bool
    detail: str = ""


def _events(observation: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return list(observation.get("events") or ())


def _replies(observation: Mapping[str, Any]) -> list[str]:
    return [str(reply) for reply in observation.get("replies") or ()]


def _causes(observation: Mapping[str, Any]) -> list[str]:
    return [str(event.get("cause") or "") for event in _events(observation)]


def _gate(gate: str, ok: bool, detail: str = "") -> GateResult:
    return GateResult(gate=gate, name=GATE_NAMES[gate], ok=ok, detail=detail)


def evaluate_gates(
    scenario: Scenario, observation: Mapping[str, Any]
) -> dict[str, GateResult]:
    """Evaluate the gates the scenario declares, against one observation.

    `observation` is the runner's plain-dict transcript of the run:
    `state`, `events` (`event`/`cause`), `intents`, `replies`, and `turns` with
    the replies each inbound message produced.
    """
    expect = scenario.expect
    results: dict[str, GateResult] = {}

    if "state_any" in expect:
        allowed = list(expect["state_any"])
        state = str(observation.get("state"))
        results["G1"] = _gate(
            "G1",
            state in allowed,
            f"state={state}, esperado uno de: {', '.join(allowed)}",
        )

    if "intent_expected" in expect:
        allowed = set(expect["intent_expected"])
        seen = [str(intent) for intent in observation.get("intents") or ()]
        hit = [intent for intent in seen if intent in allowed]
        results["G2"] = _gate(
            "G2",
            bool(hit),
            f"intents vistos {seen}, esperaba alguno de: {', '.join(sorted(allowed))}",
        )

    recorded = [str(event.get("event") or "") for event in _events(observation)]

    if "events_required" in expect:
        missing = [event for event in expect["events_required"] if event not in recorded]
        results["G3"] = _gate(
            "G3", not missing, f"nunca se registró: {', '.join(missing)}"
        )

    if "events_forbidden" in expect:
        present = [event for event in expect["events_forbidden"] if event in recorded]
        results["G4"] = _gate(
            "G4", not present, f"se registró lo prohibido: {', '.join(present)}"
        )

    if "causes_forbidden" in expect:
        causes = _causes(observation)
        offences = [
            cause
            for cause in causes
            for forbidden in expect["causes_forbidden"]
            if _normalise(cause).endswith(_normalise(forbidden))
            or _normalise(cause).endswith(_normalise(_HANDOFF_PREFIX + forbidden))
        ]
        results["G5"] = _gate(
            "G5", not offences, f"causas prohibidas presentes: {', '.join(sorted(set(offences)))}"
        )

    replies = _replies(observation)
    normalised_replies = [_normalise(reply) for reply in replies]

    if "must_include_any" in expect:
        anchors = list(expect["must_include_any"])
        found = any(
            _normalise(anchor) in reply
            for anchor in anchors
            for reply in normalised_replies
        )
        results["G6"] = _gate(
            "G6",
            found,
            f"ninguna respuesta contiene: {', '.join(anchors)}",
        )

    if "must_not_include" in expect:
        offenders = [
            anchor
            for anchor in expect["must_not_include"]
            if any(_normalise(anchor) in reply for reply in normalised_replies)
        ]
        results["G7"] = _gate(
            "G7", not offenders, f"apareció lo prohibido: {', '.join(offenders)}"
        )

    silent = [
        position
        for position, turn in enumerate(observation.get("turns") or (), start=1)
        if not (turn.get("replies") or ())
    ]
    results["G8"] = _gate("G8", not silent, f"turnos sin respuesta: {silent}")

    if expect.get("kb_answered"):
        misses = [cause for cause in _causes(observation) if _normalise(cause).endswith("kb_miss")]
        offer = _normalise(str(observation.get("miss_text") or ""))
        offered = bool(offer) and any(offer in reply for reply in normalised_replies)
        detail = "la respuesta estaba en la KB y hubo kb_miss"
        if offered and not misses:
            detail = (
                "la respuesta estaba en la KB y el bot respondió con la oferta de "
                "kb_miss (producción no registra evento en ese camino)"
            )
        results["G9"] = _gate("G9", not misses and not offered, detail)

    return results


# ---------------------------------------------------------------------------
# Scoring — S4: a failed gate is never compensated by a high judge score
# ---------------------------------------------------------------------------


def _dimension_mean(verdict: Mapping[str, Any] | None) -> float | None:
    if not verdict:
        return None
    scores = [
        float(verdict["dimensions"][name]["score"])
        for name in DIMENSIONS
        if name in (verdict.get("dimensions") or {})
    ]
    if not scores:
        return None
    return round(sum(scores) / len(scores), 3)


JUDGE_REPETITIONS = 3
"""Calls per scenario before a score counts as a measurement.

One call is one observation. Re-judging the same three calibration
conversations with identical inputs moved 8 of 18 cells, by up to 3 points, and
flipped the hard-fail flag — which caps the whole scenario at 0 (L14). The
median is the score; the spread is its uncertainty and travels with the row.
"""


def aggregate_verdicts(verdicts: Sequence[Mapping[str, Any]]) -> dict:
    """Fold repeated verdicts into one: median per dimension, majority hard fail.

    The result keeps the verdict shape `score_scenario` already consumes, and
    adds `spread`: how far the repeated calls disagreed on each dimension. An
    empty spread is the only honest way to call a score stable.
    """
    if not verdicts:
        raise ValueError("aggregate_verdicts needs at least one verdict")

    dimensions: dict[str, dict[str, Any]] = {}
    spread: dict[str, int] = {}
    for name in DIMENSIONS:
        grades = [
            (
                int(verdict["dimensions"][name]["score"]),
                str(verdict["dimensions"][name].get("evidence") or ""),
            )
            for verdict in verdicts
            if name in (verdict.get("dimensions") or {})
        ]
        if not grades:
            continue
        scores = [score for score, _quote in grades]
        middle = statistics.median(scores)
        # The quote must come from a call that produced the reported number, or
        # the evidence would not support the score next to it.
        evidence = next((quote for score, quote in grades if score == middle), grades[0][1])
        dimensions[name] = {"score": middle, "evidence": evidence}
        spread[name] = max(scores) - min(scores)

    fails = [bool(verdict.get("hard_fail")) for verdict in verdicts]
    hard_fail = sum(fails) * 2 > len(fails)
    return {
        "dimensions": dimensions,
        "spread": spread,
        "hard_fail": hard_fail,
        "hard_fail_reason": next(
            (
                str(verdict.get("hard_fail_reason") or "")
                for verdict in verdicts
                if verdict.get("hard_fail") and verdict.get("hard_fail_reason")
            ),
            "",
        ),
        "summary": next((str(v.get("summary") or "") for v in verdicts if v.get("summary")), ""),
    }


def score_scenario(
    scenario: Scenario,
    gates: Mapping[str, GateResult],
    verdict: Mapping[str, Any] | None,
) -> dict:
    """Combine the gates with the judge verdict into one row.

    The gate layer wins: any failed gate, or a judge hard fail, caps the score
    at 0. A perfect rubric cannot buy back a contained, inventing or unsafe run.
    Without a verdict the gates alone decide and `score` is `None`, never 0 —
    "not measured" and "measured as bad" are different facts.
    """
    failed = [gate for gate, result in gates.items() if not result.ok]
    hard_fail = bool(verdict and verdict.get("hard_fail"))
    mean = _dimension_mean(verdict)
    capped = bool(failed) or hard_fail
    return {
        "scenario": scenario.id,
        "tier": scenario.tier,
        "passed": not capped,
        "capped": capped,
        "gates_failed": failed,
        "score": 0.0 if capped else mean,
        "dimensions": {
            name: float(verdict["dimensions"][name]["score"])
            for name in DIMENSIONS
            if verdict and name in (verdict.get("dimensions") or {})
        },
        # How far the repeated judge calls disagreed: a difference smaller than
        # this is not a finding about the bot (L14).
        "dimension_spread": {
            name: int(verdict["spread"][name])
            for name in DIMENSIONS
            if verdict and name in (verdict.get("spread") or {})
        },
        # S7: a score without its cited evidence is not reviewable, and S9
        # calibrates against exactly that evidence. It travels with the row.
        "evidence": {
            name: str(verdict["dimensions"][name].get("evidence") or "")
            for name in DIMENSIONS
            if verdict and name in (verdict.get("dimensions") or {})
        },
        "hard_fail": hard_fail,
        "hard_fail_reason": (verdict or {}).get("hard_fail_reason", ""),
    }


# ---------------------------------------------------------------------------
# Report math — summarize and the diff against the previous run
# ---------------------------------------------------------------------------


def summarize(rows: Sequence[Mapping[str, Any]]) -> dict:
    """Aggregate run rows: pass rate, gate failures and per-dimension means."""
    gate_failures: Counter[str] = Counter()
    by_tier: dict[str, dict[str, int]] = {}
    totals: dict[str, list[float]] = {name: [] for name in DIMENSIONS}

    for row in rows:
        gate_failures.update(row.get("gates_failed") or ())
        tier = str(row.get("tier"))
        bucket = by_tier.setdefault(tier, {"scenarios": 0, "passed": 0})
        bucket["scenarios"] += 1
        if row.get("passed"):
            bucket["passed"] += 1
        for name, value in (row.get("dimensions") or {}).items():
            if name in totals and value is not None:
                totals[name].append(float(value))

    dimensions = {
        name: {
            "mean": round(sum(values) / len(values), 3) if values else None,
            "n": len(values),
        }
        for name, values in totals.items()
    }
    measured = {name: data["mean"] for name, data in dimensions.items() if data["n"]}
    worst = min(measured, key=measured.get) if measured else None

    return {
        "scenarios": len(rows),
        "passed": sum(1 for row in rows if row.get("passed")),
        "gate_failures": dict(gate_failures.most_common()),
        "dimensions": dimensions,
        "worst_dimension": worst,
        "by_tier": by_tier,
    }


def compare_runs(current: Mapping[str, Any], previous: Mapping[str, Any]) -> dict:
    """Diff a run against the previous one, scenario by scenario.

    Two runs over different corpora are not comparable, and say so instead of
    producing a diff that looks meaningful.
    """
    comparable = current.get("corpus_fingerprint") == previous.get("corpus_fingerprint")
    current_rows = {row["scenario"]: row for row in current.get("runs") or ()}
    previous_rows = {row["scenario"]: row for row in previous.get("runs") or ()}

    regressions: list[str] = []
    fixes: list[str] = []
    gate_flips: list[dict] = []

    for scenario_id, row in current_rows.items():
        before = previous_rows.get(scenario_id)
        if before is None:
            continue
        was, now = bool(before.get("passed")), bool(row.get("passed"))
        if was and not now:
            regressions.append(scenario_id)
        elif now and not was:
            fixes.append(scenario_id)
        failed_before = set(before.get("gates_failed") or ())
        failed_now = set(row.get("gates_failed") or ())
        for gate in sorted(failed_before | failed_now):
            if gate in failed_now and gate not in failed_before:
                gate_flips.append({"scenario": scenario_id, "gate": gate, "from": True, "to": False})
            elif gate in failed_before and gate not in failed_now:
                gate_flips.append({"scenario": scenario_id, "gate": gate, "from": False, "to": True})

    dimension_delta: dict[str, float] = {}
    for name in DIMENSIONS:
        now = [row["dimensions"][name] for row in current_rows.values() if name in (row.get("dimensions") or {})]
        before = [row["dimensions"][name] for row in previous_rows.values() if name in (row.get("dimensions") or {})]
        if now and before:
            dimension_delta[name] = round(
                sum(now) / len(now) - sum(before) / len(before), 3
            )

    return {
        "comparable": comparable,
        "regressions": regressions,
        "fixes": fixes,
        "gate_flips": gate_flips,
        "dimension_delta": dimension_delta,
    }


# ---------------------------------------------------------------------------
# Observation — production shapes in, gate inputs out
# ---------------------------------------------------------------------------


SIMULATED_TURNS = 3
"""Turns the simulated customer may add after the scripted opening in `--live`.

The scripted turns are the opening of a conversation, not all of it: a live run
that stops there never lets the simulated customer act like a customer. This is
a ceiling, not a target — the simulator reports `goal_reached` and the run ends
as soon as it does, so a generous ceiling costs nothing on a short scenario.
"""


def resolve_budget(
    scenario: Scenario, *, live: bool = False, override: int | None = None
) -> int:
    """How many inbound turns this scenario may have on this run.

    A declared `max_turns` is the author's ceiling for that scenario and wins. An
    explicit override (`--max-turns`) wins over everything. Otherwise a scripted
    run stops at its script, and a live run gets room for the simulated customer.
    """
    if override:
        return override
    if scenario.max_turns is not None:
        return scenario.max_turns
    return len(scenario.turns) + (SIMULATED_TURNS if live else 0)


def plan_turns(
    scripted: Sequence[str], budget: int, live: bool
) -> list[tuple[str, str | None]]:
    """Which turns the run will send, and who writes each one.

    `scripted` turns come from the corpus verbatim; in `--live` the remaining
    budget up to `budget` is filled by the simulated customer. Without `live`
    the plan stops at the scripted length, whatever the budget says.
    """
    plan: list[tuple[str, str | None]] = []
    for index in range(1, budget + 1):
        if index <= len(scripted):
            plan.append(("scripted", scripted[index - 1]))
        elif live:
            plan.append(("simulated", None))
        else:
            break
    return plan


def build_observation(snapshot: Mapping[str, Any], turns: Sequence[Mapping[str, Any]]) -> dict:
    """Turn a `chat_harness.inspect` snapshot plus the per-turn replies into the
    plain dict the gates read.

    The intent a turn classified into is not a column: production records it as
    a `classified` event with cause `intent:<intent>`, or as `unknown_intent`
    (`app/chat/nodes/classify_intent.py`). Anchors read the outbound messages,
    which is the persisted truth, not the returned replies.
    """
    intents: list[str] = []
    for event in snapshot.get("events") or ():
        name = event.get("event")
        cause = str(event.get("cause") or "")
        if name == "classified" and cause:
            intents.append(cause.removeprefix("intent:"))
        elif name == "unknown_intent":
            intents.append("unknown")
    replies = [
        str(message.get("text") or "")
        for message in snapshot.get("messages") or ()
        if message.get("direction") == "outbound" and message.get("text")
    ]
    return {
        "state": snapshot.get("state"),
        # The complete ordered log, straight from the database: the Markdown
        # transcript is the permanent record once `--reset` wipes the rows.
        "messages": [
            {"direction": message.get("direction"), "text": message.get("text")}
            for message in snapshot.get("messages") or ()
        ],
        "events": [
            {"event": event.get("event"), "cause": event.get("cause")}
            for event in snapshot.get("events") or ()
        ],
        "intents": intents,
        "replies": replies,
        "turns": list(turns),
    }


def facts_of(observation: Mapping[str, Any]) -> dict:
    """What the database recorded, for the judge to cite instead of inferring.

    `escalation` used to be scored from the prose alone, and both calibration
    disagreements were inversions against these facts: a recorded hand-off read
    as a missing one, and a conversion that never escalated read as a partial
    one (S9, L13).
    """
    return {
        "final_state": observation.get("state"),
        "events": list(observation.get("events") or ()),
    }


def transcript_of(observation: Mapping[str, Any]) -> list[dict]:
    """The judge's view: alternating customer and assistant lines, in order."""
    transcript: list[dict] = []
    for turn in observation.get("turns") or ():
        transcript.append({"role": "customer", "text": str(turn.get("text") or "")})
        for reply in turn.get("replies") or ():
            transcript.append({"role": "assistant", "text": str(reply)})
    return transcript


# ---------------------------------------------------------------------------
# Stamp — S8.6: a run over a dirty tree is not citable as a baseline
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RunStamp:
    run_tag: str
    started_at: str
    head: str
    dirty: bool
    corpus_fingerprint: str
    kb_fingerprint: str
    kb_documents: int
    judge_model: str | None
    judge_repetitions: int
    live: bool
    bot_provider: str = ""
    bot_model: str = ""

    def as_dict(self) -> dict:
        return {
            "run_tag": self.run_tag,
            "started_at": self.started_at,
            "head": self.head,
            "dirty": self.dirty,
            "corpus_fingerprint": self.corpus_fingerprint,
            "kb_fingerprint": self.kb_fingerprint,
            "kb_documents": self.kb_documents,
            "judge_model": self.judge_model,
            "judge_repetitions": self.judge_repetitions,
            "live": self.live,
            "bot_provider": self.bot_provider,
            "bot_model": self.bot_model,
        }


def git_state(
    repo_root: Path = _REPO_ROOT, report_dir: Path | None = None
) -> tuple[str, bool]:
    """`(sha, dirty)` of the working tree the run measured, or `("", False)`.

    The report the run writes is **excluded** from the dirtiness check. A run
    writes its own `.json`, `.md` and transcript into `odd/evals/`; counting
    those bytes as an edit to the tree would dirty every run from the inside and
    no run could ever be a citable baseline, which is the whole point of S8.6.
    """
    import subprocess

    excluded = report_dir if report_dir is not None else repo_root / "odd" / "evals"
    try:
        relative = excluded.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        relative = None  # the report lives outside the measured tree: nothing to exclude
    pathspec = ["--", "."] if relative is None else ["--", ".", f":(exclude){relative}"]

    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, capture_output=True, text=True, check=True
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain", *pathspec],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "", False
    return head, bool(status)


def is_citable(stamp: Mapping[str, Any]) -> bool:
    """A baseline must stamp a clean tree and a KB that matches `docs/kb`."""
    return not stamp.get("dirty") and bool(stamp.get("kb_documents"))


# ---------------------------------------------------------------------------
# Database side — imported lazily so this module stays model-free and DB-free
# ---------------------------------------------------------------------------


class PreflightError(RuntimeError):
    """The database cannot answer, so the run would measure the KB, not the bot."""


def preflight() -> dict:
    """S8.1: refuse to run unless `docs/kb` and the customer KB agree."""
    import seed_kb_docs
    from app.db import session_scope

    with session_scope() as session:
        state = seed_kb_docs.inspect_kb(session)
    if not state["consistent"]:
        missing = ", ".join(state["missing"]) or "—"
        drifted = ", ".join(state["drifted"]) or "—"
        raise PreflightError(
            "la KB de cliente no coincide con docs/kb "
            f"(faltan: {missing}; drifted: {drifted}). "
            "Corré `uv run python scripts/seed_kb_docs.py --apply` y volvé a intentar."
        )
    return state


def kb_text() -> str:
    """The customer KB exactly as the bot retrieves it, for the judge to ground on."""
    import seed_kb_docs
    from app.db import session_scope

    with session_scope() as session:
        documents = seed_kb_docs.customer_documents(session)
        return "\n\n".join(
            f"# {document.title}\n\n{document.content or ''}" for document in documents
        )


def tarifario_text() -> str:
    """The prices in force today, rendered the way the prompt renders them."""
    from datetime import date

    from app.chat.nodes.respond import build_tarifario_block
    from app.db import session_scope
    from app.services.settings import get_tarifa_precios, tarifa_vigente

    with session_scope() as session:
        return build_tarifario_block(tarifa_vigente(get_tarifa_precios(session), date.today()))


def miss_offer_text() -> str:
    """The configured reply for a soft knowledge miss, read from the database.

    Production records no event on that path (see the G9 note in the module
    docstring), so the gate reads the text the bot would send.
    """
    from app.chat.nodes.respond import get_message
    from app.db import session_scope

    with session_scope() as session:
        return get_message(session, "kb_miss_offer")


# Conversation state only: the KB, the tariff, the message catalog, the users and
# the technicians are configuration and must survive a reset, or the next run
# would measure an empty knowledge base.
_RESET_TABLES = (
    "appointment_calendar_sync, appointment_history, appointments, assistant_artifacts, "
    "assistant_attachments, notification_attempts, notification_operations, "
    "panel_notifications, technician_availability, audit_log, conversation_events, "
    "automation_executions, customer_equipment, domain_events, memories, memory_relations, "
    "memory_observations, cases, internal_chat_messages, internal_chat_threads, messages, "
    "conversations, customer_notes, customers"
)


def reset_guard(database_url: str | None, test_admin_url: str | None) -> str | None:
    """Refuse `--reset` unless the target is provably the derived test database.

    The instrument truncates tables. A typo in `DATABASE_URL` must not be able to
    empty a real database, so the only accepted target is the one whose host and
    port match `TEST_ADMIN_DB_URL` — which only `infra/test-db.sh env` exports.
    """
    if not test_admin_url:
        return (
            "--reset exige TEST_ADMIN_DB_URL (exportalo con `eval \"$(bash infra/test-db.sh env)\"`): "
            "sin eso no hay forma de probar que la base es la de test."
        )
    from urllib.parse import urlsplit

    target = urlsplit(database_url or "")
    admin = urlsplit(test_admin_url)
    if (target.hostname, target.port) != (admin.hostname, admin.port):
        return (
            f"--reset se niega: DATABASE_URL apunta a {target.hostname}:{target.port} y la base de "
            f"test derivada es {admin.hostname}:{admin.port}."
        )
    return None


def reset_business_state(admin_url: str | None = None) -> list[str]:
    """Empty the conversation state so every run starts from the same place.

    Runs on the **admin** connection: the `app` role is least-privilege by
    design (SH-2/SH-5) and has no TRUNCATE. `RESTART IDENTITY` makes ids start
    at 1 again, so two runs are comparable row by row. No `CASCADE`: if a table
    outside this list points at one of them, the reset fails loudly instead of
    quietly emptying configuration.
    """
    import os

    import psycopg

    url = admin_url or os.environ.get("TEST_ADMIN_DB_URL")
    if not url:
        raise PreflightError("--reset necesita TEST_ADMIN_DB_URL para la conexión admin")
    with psycopg.connect(url, autocommit=True) as connection:
        connection.execute(f"TRUNCATE {_RESET_TABLES} RESTART IDENTITY")
    return [name.strip() for name in _RESET_TABLES.split(",")]


def contamination_error(existing: Sequence[str]) -> str | None:
    """Refuse a tag that already has customers: a re-run would stack on top.

    Measured the hard way: a run killed mid-flight left its rows behind, and the
    next run with the same tag replayed its turns onto conversations that had
    already escalated. The report said 5/14 and every one of those reds was the
    previous run talking, not the bot.
    """
    if not existing:
        return None
    return (
        f"--run-tag ya tiene conversaciones para {len(existing)} escenario(s): "
        f"{', '.join(existing)}. Usá un tag nuevo; el mismo tag reusa el cliente por diseño "
        "y una corrida anterior quedaría apilada debajo."
    )


def existing_conversations(scenarios: Sequence[Scenario], run_tag: str) -> list[str]:
    """Scenario ids whose derived phone already exists in the database."""
    from sqlalchemy import select

    from app.db import session_scope
    from app.models import Customer

    phones = {derive_phone(scenario.id, run_tag): scenario.id for scenario in scenarios}
    with session_scope() as session:
        found = session.scalars(
            select(Customer.phone_e164).where(Customer.phone_e164.in_(list(phones)))
        ).all()
    return sorted(phones[phone] for phone in found if phone in phones)


def run_scenario(
    scenario: Scenario,
    *,
    run_tag: str,
    judge_client: Any = None,
    live: bool = False,
    max_turns: int | None = None,
    miss_text: str = "",
) -> dict:
    """Drive one scenario through the real brain and collect its observation."""
    import conv_eval_judge
    from app.db import session_scope
    from chat_harness import ensure_conversation, inspect, run_turn

    phone = derive_phone(scenario.id, run_tag)
    with session_scope() as session:
        conversation_id = ensure_conversation(session, phone)

    budget = resolve_budget(scenario, live=live, override=max_turns)
    turns: list[dict] = []

    for index, (origin, scripted_text) in enumerate(
        plan_turns(scenario.turns, budget, live), start=1
    ):
        if origin == "scripted":
            text = scripted_text
        else:
            simulated = conv_eval_judge.simulate_customer_turn(
                judge_client,
                persona=scenario.persona,
                goal=scenario.goal,
                transcript=transcript_of({"turns": turns}),
                turn_index=index,
                max_turns=budget,
            )
            if simulated["goal_reached"]:
                break
            text = simulated["message"]

        with session_scope() as session:
            replies = run_turn(session, conversation_id, text)
        # `origin` is what makes the transcript reviewable: a simulated turn is
        # the evaluator talking, and reading it is how the evaluator is judged.
        turns.append(
            {"text": text, "replies": list(replies), "intent": None, "origin": origin}
        )

    with session_scope() as session:
        snapshot = inspect(session, conversation_id)

    observation = build_observation(snapshot, turns)
    observation["miss_text"] = miss_text
    # The intent is recorded inside the run, so it is only visible afterwards:
    # attribute each classified intent to the turn that produced it.
    per_turn = iter(observation["intents"])
    for turn in observation["turns"]:
        turn["intent"] = next(per_turn, None)

    return {
        "scenario": scenario.id,
        "phone": phone,
        "conversation_id": conversation_id,
        "observation": observation,
    }


def judge_row(
    scenario: Scenario,
    observation: Mapping[str, Any],
    *,
    client: Any,
    kb: str,
    tarifario: str,
    model: str | None = None,
    repetitions: int = JUDGE_REPETITIONS,
) -> dict:
    """Score the conversation with the rubric judge, `repetitions` times.

    Repetition is not a luxury: re-judging the same calibration conversations
    with identical inputs moved 8 of 18 cells and flipped the hard-fail flag
    (L14). Each call is one verdict; the answer carries the median per dimension
    and the spread the calls disagreed by.
    """
    import conv_eval_judge

    kwargs = {"model": model} if model else {}
    verdicts = [
        conv_eval_judge.judge_conversation(
            client,
            transcript=transcript_of(observation),
            scenario=dict(scenario.raw),
            facts=facts_of(observation),
            kb_text=kb,
            tarifario=tarifario,
            **kwargs,
        )
        for _ in range(max(1, repetitions))
    ]
    return aggregate_verdicts(verdicts)


# ---------------------------------------------------------------------------
# Report — one JSON for the machine, one Markdown for the human, and a diff
# ---------------------------------------------------------------------------


def report_paths(out_dir: Path, run_tag: str) -> tuple[Path, Path]:
    return out_dir / f"conv-eval-{run_tag}.json", out_dir / f"conv-eval-{run_tag}.md"


def previous_report(out_dir: Path, current: Path) -> Path | None:
    """The most recent other run in `out_dir`, or None when this is the first."""
    candidates = sorted(
        (path for path in out_dir.glob("conv-eval-*.json") if path != current),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def render_markdown(report: Mapping[str, Any]) -> str:
    """Render one run for a human: what failed, why, and what moved."""
    stamp = report.get("stamp") or {}
    summary = report.get("summary") or {}
    lines: list[str] = [
        f"# Evaluación conversacional — `{stamp.get('run_tag', '?')}`",
        "",
        "Mide el **cerebro** del chat (`run_conversation`), no el canal: webhook, dedup, "
        "ventana de 24 h y plantillas de Meta quedan fuera de alcance.",
        "",
        f"- Sello: `{stamp.get('head', '?')}` · árbol sucio: "
        f"**{'sí' if stamp.get('dirty') else 'no'}** · corrida: "
        f"{'cliente simulado (--live)' if stamp.get('live') else 'cliente scripted'}",
        f"- Corpus: `{stamp.get('corpus_fingerprint', '?')}` · KB: "
        f"`{stamp.get('kb_fingerprint', '?')}` ({stamp.get('kb_documents', 0)} documentos)",
        # Which bot this measured. Without it the report describes two different
        # models identically, and a baseline that cannot name its subject is not
        # reproducible.
        f"- Bot: `{stamp.get('bot_provider') or '?'}` / `{stamp.get('bot_model') or '?'}`",
    ]
    judge_line = f"- Juez: `{stamp.get('judge_model') or 'sin juez (solo gates)'}`"
    if stamp.get("judge_model"):
        judge_line += (
            f" · {stamp.get('judge_repetitions', 1)} llamada(s) por escenario (mediana)"
        )
    lines.append(judge_line + f" · inicio: {stamp.get('started_at', '?')}")
    if not is_citable(stamp):
        lines += [
            "",
            "> **No citable como baseline**: la corrida no selló un árbol limpio.",
        ]

    lines += [
        "",
        "## Resumen",
        "",
        f"- Escenarios: **{summary.get('scenarios', 0)}** · pasan: "
        f"**{summary.get('passed', 0)}**",
        f"- Peor dimensión: `{summary.get('worst_dimension') or '—'}`",
        "",
        "| Tier | Escenarios | Pasan |",
        "| --- | --- | --- |",
    ]
    for tier, data in (summary.get("by_tier") or {}).items():
        lines.append(f"| {tier} | {data['scenarios']} | {data['passed']} |")

    failures = summary.get("gate_failures") or {}
    lines += ["", "### Gates que fallaron", ""]
    if failures:
        lines += ["| Gate | Nombre | Veces |", "| --- | --- | --- |"]
        for gate, count in failures.items():
            lines.append(f"| {gate} | {GATE_NAMES.get(gate, '?')} | {count} |")
    else:
        lines.append("Ninguno.")

    lines += ["", "### Dimensiones del juez", ""]
    measured = {
        name: data for name, data in (summary.get("dimensions") or {}).items() if data["n"]
    }
    if measured:
        lines += ["| Dimensión | Media | n |", "| --- | --- | --- |"]
        for name, data in measured.items():
            lines.append(f"| {name} | {data['mean']:.2f} | {data['n']} |")
    else:
        lines.append("Sin juez en esta corrida: los gates deciden solos.")

    judge_failures = report.get("judge_failures") or {}
    if judge_failures:
        lines += ["", "### Sin veredicto del juez", ""]
        for scenario_id, reason in judge_failures.items():
            lines.append(f"- `{scenario_id}`: {reason}")

    failed_rows = [row for row in report.get("runs") or () if not row.get("passed")]
    lines += ["", "## Escenarios que no pasan", ""]
    if not failed_rows:
        lines.append("Ninguno.")
    for row in failed_rows:
        lines.append(f"### `{row['scenario']}` ({row['tier']})")
        if row.get("gates_failed"):
            for gate in row["gates_failed"]:
                detail = ((report.get("gate_details") or {}).get(row["scenario"]) or {}).get(gate, "")
                lines.append(f"- **{gate} · {GATE_NAMES.get(gate, '?')}**: {detail}")
        if row.get("hard_fail"):
            lines.append(f"- **hard fail del juez**: {row.get('hard_fail_reason') or 'sin motivo'}")
        if row.get("score") is not None:
            lines.append(f"- puntaje: {row['score']:.2f} (capeado a 0 por el gate)")
        lines.append("")

    diff = report.get("diff")
    lines += ["", "## Contra la corrida anterior", ""]
    if not diff:
        lines.append("Sin corrida previa: esta es la línea base.")
    elif not diff.get("comparable"):
        lines.append("**No comparable**: el corpus cambió entre las dos corridas.")
    else:
        lines.append(f"- Regresiones: {', '.join(diff['regressions']) or 'ninguna'}")
        lines.append(f"- Arreglos: {', '.join(diff['fixes']) or 'ninguno'}")
        if diff.get("gate_flips"):
            flips = ", ".join(
                f"{flip['scenario']}/{flip['gate']} {'pasó a fallar' if flip['from'] else 'se arregló'}"
                for flip in diff["gate_flips"]
            )
            lines.append(f"- Gates que se movieron: {flips}")
        if diff.get("dimension_delta"):
            deltas = ", ".join(
                f"{name} {value:+.2f}" for name, value in diff["dimension_delta"].items()
            )
            lines.append(f"- Delta por dimensión: {deltas}")

    return "\n".join(lines).rstrip() + "\n"


def render_transcripts(report: Mapping[str, Any], corpus: Corpus) -> str:
    """Every conversation of the run, in order, saying who wrote each turn.

    This is the artifact for auditing the *evaluator*: whether the simulated
    customer pursues the goal, stops when served, and never writes as the bot.
    """
    stamp = report.get("stamp") or {}
    observations = report.get("observations") or {}
    rows = {row["scenario"]: row for row in report.get("runs") or ()}
    details = report.get("gate_details") or {}
    lines = [
        f"# Conversaciones de la corrida `{stamp.get('run_tag', '?')}`",
        "",
        "`[scripted]` = turno textual del corpus · `[simulado]` = lo escribió el cliente simulado.",
        "Estado final, gates y puntaje del juez al pie de cada caso.",
        "",
    ]
    for scenario in corpus.scenarios:
        observation = observations.get(scenario.id)
        if observation is None:
            continue
        row = rows.get(scenario.id, {})
        lines += [
            f"## `{scenario.id}` [{scenario.tier}]",
            "",
            f"**persona:** {' '.join(scenario.persona.split())}",
            f"**objetivo:** {' '.join(scenario.goal.split())}",
            "",
        ]
        origins = [
            turn.get("origin")
            or ("scripted" if position <= len(scenario.turns) else "simulado")
            for position, turn in enumerate(observation.get("turns") or (), start=1)
        ]
        messages = observation.get("messages") or [
            {"direction": direction, "text": text}
            for turn in observation.get("turns") or ()
            for direction, text in [("inbound", turn.get("text"))]
            + [("outbound", reply) for reply in turn.get("replies") or ()]
        ]
        inbound_index = 0
        position = 0
        for message in messages:
            if message.get("direction") == "inbound":
                position += 1
                origin = origins[inbound_index] if inbound_index < len(origins) else "scripted"
                inbound_index += 1
                label = "scripted" if origin == "scripted" else "simulado"
                lines.append(f"**{position}. cliente** `[{label}]` — {message.get('text') or ''}")
            else:
                lines.append(f"> *bot:* {' '.join(str(message.get('text') or '').split())}")
                lines.append("")
        gates = details.get(scenario.id) or {}
        failed = row.get("gates_failed") or []
        gate_text = ", ".join(
            f"{gate} ✗ ({gates.get(gate, '')})" if gate in failed else f"{gate} ✓"
            for gate in sorted(gates)
        ) or "—"
        verdict = "sin juez" if row.get("score") is None else f"{row['score']:.2f}"
        moved = {
            name: spread
            for name, spread in (row.get("dimension_spread") or {}).items()
            if spread
        }
        lines += [
            f"**estado final:** `{observation.get('state')}` · **juez:** {verdict} · "
            f"**hard fail:** {row.get('hard_fail', False)}",
            f"**gates:** {gate_text}",
        ]
        if moved:
            lines.append(
                "**dispersión entre repeticiones:** "
                + ", ".join(f"{name} ±{spread}" for name, spread in sorted(moved.items()))
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_report(report: dict, out_dir: Path = _REPO_ROOT / "odd" / "evals") -> tuple[Path, Path]:
    """Write the JSON and the Markdown, creating `odd/evals` on first use."""
    import json

    out_dir.mkdir(parents=True, exist_ok=True)
    json_path, md_path = report_paths(out_dir, report["stamp"]["run_tag"])
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    transcript_path = out_dir / f"conv-eval-{report['stamp']['run_tag']}-conversaciones.md"
    transcript_path.write_text(
        render_transcripts(report, load_corpus()), encoding="utf-8"
    )
    return json_path, md_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: Sequence[str] | None) -> Any:
    import argparse

    parser = argparse.ArgumentParser(
        description="Evaluate the Lumat chat brain against the versioned conversation corpus."
    )
    parser.add_argument("--corpus", type=Path, default=CORPUS_PATH, help="Corpus YAML.")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate the corpus and exit. No database, no model.",
    )
    parser.add_argument("--run-tag", default="local", help="Names the run and derives the phone.")
    parser.add_argument("--tier", choices=list(TIERS), default=None, help="Only this tier.")
    parser.add_argument(
        "--only", action="append", default=None, metavar="ID", help="Only this scenario (repeatable)."
    )
    parser.add_argument(
        "--max-turns", type=int, default=None, help="Override the per-scenario turn budget."
    )
    parser.add_argument(
        "--judge-repetitions",
        type=int,
        default=JUDGE_REPETITIONS,
        help="Judge calls per scenario; the median is the score and the spread is "
        "reported (the judge moves between identical calls).",
    )
    parser.add_argument("--no-judge", action="store_true", help="Gates only: no LLM, no key needed.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Continue past the scripted turns with a simulated customer.",
    )
    parser.add_argument("--judge-model", default=None, help="Override the judge model id.")
    parser.add_argument("--out-dir", type=Path, default=_REPO_ROOT / "odd" / "evals")
    parser.add_argument("--quiet", action="store_true", help="Only the summary lines.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Empty the conversation state first, so the run is comparable. "
        "Only accepted against the derived test database.",
    )
    return parser.parse_args(argv)


def _select(corpus: Corpus, args: Any) -> list[Scenario]:
    scenarios = list(corpus.by_tier(args.tier))
    if args.only:
        wanted = set(args.only)
        unknown = wanted - set(corpus.ids)
        _require(not unknown, f"--only: unknown scenario ids {sorted(unknown)}")
        scenarios = [scenario for scenario in scenarios if scenario.id in wanted]
    _require(bool(scenarios), "no scenario selected")
    return scenarios


def _validate_only(corpus: Corpus) -> int:
    tiers = Counter(scenario.tier for scenario in corpus.scenarios)
    detail = " · ".join(f"{tier} {tiers[tier]}" for tier in TIERS if tiers[tier])
    print(
        f"corpus válido: {len(corpus.scenarios)} escenarios ({detail}) · "
        f"fingerprint {corpus.fingerprint}"
    )
    return 0


def _bot_settings() -> tuple[str, str]:
    """The provider and model the brain under test is configured with."""
    from app.config import get_settings

    settings = get_settings()
    return settings.chat_provider, settings.chat_model


def main(argv: Sequence[str] | None = None) -> int:
    import json
    from datetime import datetime, timezone

    args = _parse_args(argv)

    try:
        corpus = load_corpus(args.corpus)
    except ValueError as error:
        print(f"corpus inválido: {error}", file=sys.stderr)
        return 2
    if args.validate_only:
        return _validate_only(corpus)

    if args.judge_repetitions < 1:
        print(
            f"--judge-repetitions debe ser >= 1, recibí {args.judge_repetitions}",
            file=sys.stderr,
        )
        return 2

    import seed_kb_docs

    seed_kb_docs.ensure_dev_env()

    scenarios = _select(corpus, args)
    contaminated = contamination_error(existing_conversations(scenarios, args.run_tag))
    if contaminated:
        print(contaminated, file=sys.stderr)
        return 2

    if args.reset:
        import os

        refused = reset_guard(os.environ.get("DATABASE_URL"), os.environ.get("TEST_ADMIN_DB_URL"))
        if refused:
            print(refused, file=sys.stderr)
            return 2
        cleared = reset_business_state()
        print(f"reset: {len(cleared)} tablas de conversación vaciadas", flush=True)

    try:
        kb_state = preflight()
    except PreflightError as error:
        print(f"preflight: {error}", file=sys.stderr)
        return 2

    import conv_eval_judge

    client = None
    judge_model = None
    if not args.no_judge:
        try:
            credentials = conv_eval_judge.resolve_credentials()
        except conv_eval_judge.JudgeKeyUnavailable as error:
            print(f"juez: {error}", file=sys.stderr)
            return 2
        print(f"juez: {credentials.source}")
        client = conv_eval_judge.build_client(
            credentials, session_id=f"conv-eval-{args.run_tag}"
        )
        judge_model = args.judge_model or conv_eval_judge.JUDGE_MODEL

    head, dirty = git_state(report_dir=args.out_dir)
    stamp = RunStamp(
        run_tag=args.run_tag,
        started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        head=head,
        dirty=dirty,
        corpus_fingerprint=corpus.fingerprint,
        kb_fingerprint=kb_state["fingerprint"],
        kb_documents=kb_state["documents"],
        judge_model=judge_model,
        judge_repetitions=args.judge_repetitions if client is not None else 0,
        live=args.live,
        bot_provider=_bot_settings()[0],
        bot_model=_bot_settings()[1],
    ).as_dict()

    miss_text = miss_offer_text()
    kb = kb_text() if client is not None else ""
    tarifario = tarifario_text() if client is not None else ""

    runs: list[dict] = []
    judge_failures: dict[str, str] = {}
    gate_details: dict[str, dict[str, str]] = {}
    observations: dict[str, dict] = {}
    for scenario in scenarios:
        try:
            result = run_scenario(
                scenario,
                run_tag=args.run_tag,
                judge_client=client,
                live=args.live,
                max_turns=args.max_turns,
                miss_text=miss_text,
            )
        except Exception as error:  # noqa: BLE001  a dead scenario must not kill the run
            print(f"  ✗ {scenario.id}: la corrida falló: {error}", file=sys.stderr)
            return 2

        observation = result["observation"]
        gates = evaluate_gates(scenario, observation)
        gate_details[scenario.id] = {
            gate: gate_result.detail for gate, gate_result in gates.items()
        }
        observations[scenario.id] = observation

        verdict = None
        if client is not None:
            try:
                verdict = judge_row(
                    scenario,
                    observation,
                    client=client,
                    kb=kb,
                    tarifario=tarifario,
                    model=judge_model,
                    repetitions=args.judge_repetitions,
                )
            except Exception as error:  # noqa: BLE001  one verdict must not kill the run
                # Recorded as unmeasured, never as a score, and named in the
                # report: a gate-only row with a judge attached would lie.
                judge_failures[scenario.id] = str(error)
                print(
                    f"  ! {scenario.id}: sin veredicto del juez ({error})",
                    file=sys.stderr,
                    flush=True,
                )

        row = score_scenario(scenario, gates, verdict)
        runs.append(row)
        if not args.quiet:
            mark = "✓" if row["passed"] else "✗"
            failed = f" · fallan {', '.join(row['gates_failed'])}" if row["gates_failed"] else ""
            score = f" · {row['score']:.2f}" if row["score"] is not None else ""
            print(f"  {mark} {scenario.id}{score}{failed}", flush=True)

    report = {
        "stamp": stamp,
        "runs": runs,
        "summary": summarize(runs),
        "judge_failures": judge_failures,
        "gate_details": gate_details,
        "observations": observations,
    }

    json_path, _ = report_paths(args.out_dir, args.run_tag)
    previous_path = previous_report(args.out_dir, json_path)
    if previous_path is not None:
        report["diff"] = compare_runs(report, json.loads(previous_path.read_text(encoding="utf-8")))
        report["previous"] = previous_path.name

    written = write_report(report, args.out_dir)
    summary = report["summary"]
    print(
        f"\n{summary['passed']}/{summary['scenarios']} escenarios pasan · "
        f"gates: {summary['gate_failures'] or 'ninguno'} · "
        f"peor dimensión: {summary['worst_dimension'] or '—'}"
    )
    print(f"reporte: {written[0]} · {written[1]}")
    if not is_citable(stamp):
        print("aviso: árbol sucio o KB sin sellar — esta corrida no es citable como baseline")
    if judge_failures:
        print(f"aviso: {len(judge_failures)} escenario(s) sin veredicto del juez: "
              f"{', '.join(judge_failures)}")
    if judge_failures or summary["passed"] != summary["scenarios"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

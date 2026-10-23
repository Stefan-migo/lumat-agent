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
G9   kb_answered       the answer lives in the KB, yet the turn ended in kb_miss
===  ================  =======================================================

Anchors are matched case- and accent-insensitively, as substrings: the bot says
"la mantención" and the anchor is "mantenci" on purpose.

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
    "derive_phone",
    "evaluate_gates",
    "git_state",
    "is_citable",
    "load_corpus",
    "main",
    "preflight",
    "previous_report",
    "render_markdown",
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
    max_turns: int
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

    max_turns = entry.get("max_turns", len(turns))
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
        results["G9"] = _gate(
            "G9",
            not misses,
            "la respuesta estaba en la KB y aun así hubo kb_miss",
        )

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
        "events": [
            {"event": event.get("event"), "cause": event.get("cause")}
            for event in snapshot.get("events") or ()
        ],
        "intents": intents,
        "replies": replies,
        "turns": list(turns),
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
    live: bool

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
            "live": self.live,
        }


def git_state(repo_root: Path = _REPO_ROOT) -> tuple[str, bool]:
    """`(sha, dirty)` of the working tree the run happened on, or `("", False)`."""
    import subprocess

    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, capture_output=True, text=True, check=True
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=repo_root, capture_output=True, text=True, check=True
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


def run_scenario(
    scenario: Scenario,
    *,
    run_tag: str,
    judge_client: Any = None,
    live: bool = False,
    max_turns: int | None = None,
) -> dict:
    """Drive one scenario through the real brain and collect its observation."""
    import conv_eval_judge
    from app.db import session_scope
    from chat_harness import ensure_conversation, inspect, run_turn

    phone = derive_phone(scenario.id, run_tag)
    with session_scope() as session:
        conversation_id = ensure_conversation(session, phone)

    budget = max_turns or scenario.max_turns
    turns: list[dict] = []
    scripted = list(scenario.turns)

    for index in range(1, budget + 1):
        if index <= len(scripted):
            text = scripted[index - 1]
        elif live and judge_client is not None:
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
        else:
            break

        with session_scope() as session:
            replies = run_turn(session, conversation_id, text)
        turns.append({"text": text, "replies": list(replies), "intent": None})

    with session_scope() as session:
        snapshot = inspect(session, conversation_id)

    observation = build_observation(snapshot, turns)
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
) -> dict:
    """Score the conversation with the rubric judge; raises if it cannot."""
    import conv_eval_judge

    kwargs = {"model": model} if model else {}
    return conv_eval_judge.judge_conversation(
        client,
        transcript=transcript_of(observation),
        scenario=dict(scenario.raw),
        kb_text=kb,
        tarifario=tarifario,
        **kwargs,
    )


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
        f"- Juez: `{stamp.get('judge_model') or 'sin juez (solo gates)'}` · "
        f"inicio: {stamp.get('started_at', '?')}",
    ]
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


def write_report(report: dict, out_dir: Path = _REPO_ROOT / "odd" / "evals") -> tuple[Path, Path]:
    """Write the JSON and the Markdown, creating `odd/evals` on first use."""
    import json

    out_dir.mkdir(parents=True, exist_ok=True)
    json_path, md_path = report_paths(out_dir, report["stamp"]["run_tag"])
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
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
    parser.add_argument("--no-judge", action="store_true", help="Gates only: no LLM, no key needed.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Continue past the scripted turns with a simulated customer.",
    )
    parser.add_argument("--judge-model", default=None, help="Override the judge model id.")
    parser.add_argument("--out-dir", type=Path, default=_REPO_ROOT / "odd" / "evals")
    parser.add_argument("--quiet", action="store_true", help="Only the summary lines.")
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

    import seed_kb_docs

    seed_kb_docs.ensure_dev_env()
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

    head, dirty = git_state()
    stamp = RunStamp(
        run_tag=args.run_tag,
        started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        head=head,
        dirty=dirty,
        corpus_fingerprint=corpus.fingerprint,
        kb_fingerprint=kb_state["fingerprint"],
        kb_documents=kb_state["documents"],
        judge_model=judge_model,
        live=args.live,
    ).as_dict()

    kb = kb_text() if client is not None else ""
    tarifario = tarifario_text() if client is not None else ""

    runs: list[dict] = []
    gate_details: dict[str, dict[str, str]] = {}
    observations: dict[str, dict] = {}
    scenarios = _select(corpus, args)

    for scenario in scenarios:
        try:
            result = run_scenario(
                scenario,
                run_tag=args.run_tag,
                judge_client=client,
                live=args.live,
                max_turns=args.max_turns,
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
                )
            except conv_eval_judge.JudgeError as error:
                # No verdict, no report: a partial score would read as a result.
                print(
                    f"juez: {scenario.id} no produjo veredicto ({error}). "
                    "No se escribe reporte.",
                    file=sys.stderr,
                )
                return 2
            except Exception as error:  # noqa: BLE001  transport: name it and stop
                print(
                    f"juez: {scenario.id} no pudo consultar el modelo ({error}). "
                    "No se escribe reporte.",
                    file=sys.stderr,
                )
                return 2

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
    return 0 if summary["passed"] == summary["scenarios"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

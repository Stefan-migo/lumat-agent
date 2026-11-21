"""Run a bounded, judge-required chatbot corpus regression comparison.

The corpus engine persists its driven conversations and stamps `last_message_at`;
they therefore appear in the operator inbox's active conversation list. Callers
must warn operators that this diagnostic creates visible inbox rows. No report
files are written: only the named baseline is read and the current score/diff is
returned in memory.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from uuid import uuid4


_RUN_TAG_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")


def run_regression(scenarios: list[str], baseline_run_tag: str) -> dict:
    """Measure selected scenarios with deterministic gates AND the rubric judge.

    `scripts.conv_eval` is imported lazily: its module is deliberately model- and
    provider-key-free at import time, while this app service needs its runner,
    scoring, comparison and corpus API only when the approved tool is executed.
    The engine persists each driven conversation and stamps `last_message_at`,
    which makes every measured scenario visible in the operator inbox.
    """
    # Keep app imports independent of the scripts tree until an approved run is requested.
    from scripts import conv_eval as ev
    from scripts import conv_eval_judge as judge

    if not _RUN_TAG_PATTERN.fullmatch(baseline_run_tag):
        raise ValueError("invalid baseline run tag")

    eval_dir = Path(__file__).resolve().parents[2] / "odd" / "evals"
    baseline_path, _ = ev.report_paths(eval_dir, baseline_run_tag)
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"baseline report '{baseline_run_tag}' is missing or unreadable: {exc}") from exc
    if not isinstance(baseline, dict) or not isinstance(baseline.get("runs"), list):
        raise ValueError(f"baseline report '{baseline_run_tag}' is unreadable: expected a report with runs")
    baseline_rows = {
        row.get("scenario"): row
        for row in baseline["runs"]
        if isinstance(row, dict) and isinstance(row.get("scenario"), str)
    }

    corpus = ev.load_corpus()
    by_id = {scenario.id: scenario for scenario in corpus.scenarios}
    missing = [scenario_id for scenario_id in scenarios if scenario_id not in by_id]
    if missing:
        raise ValueError(f"unknown corpus scenario(s): {', '.join(missing)}")
    unavailable = [
        scenario_id for scenario_id in scenarios
        if scenario_id not in baseline_rows or baseline_rows[scenario_id].get("score") is None
    ]
    if unavailable:
        raise ValueError(
            f"baseline report '{baseline_run_tag}' has no judged score for scenario(s): {', '.join(unavailable)}"
        )

    try:
        credentials = judge.resolve_credentials()
    except judge.JudgeKeyUnavailable as exc:
        raise ValueError(f"rubric judge unavailable; no gates-only result was produced: {exc}") from exc

    run_tag = f"assistant-{uuid4().hex}"
    client = judge.build_client(credentials, session_id=f"conv-eval-{run_tag}")
    kb_state = ev.preflight()
    kb = ev.kb_text()
    tarifario = ev.tarifario_text()
    miss_text = ev.miss_offer_text()
    runs = []
    gate_details: dict[str, dict[str, str]] = {}
    observations = {}

    for scenario_id in scenarios:
        scenario = by_id[scenario_id]
        try:
            driven = ev.run_scenario(scenario, run_tag=run_tag, judge_client=client)
            observation = driven["observation"]
            observation["miss_text"] = miss_text
            gates = ev.evaluate_gates(scenario, observation)
            gate_details[scenario_id] = {gate: result.detail for gate, result in gates.items()}
            observations[scenario_id] = observation
            verdict = ev.judge_row(
                scenario,
                observation,
                client=client,
                kb=kb,
                tarifario=tarifario,
                model=judge.JUDGE_MODEL,
                repetitions=ev.JUDGE_REPETITIONS,
            )
            if verdict is None:
                raise RuntimeError("rubric judge returned no verdict")
            runs.append(ev.score_scenario(scenario, gates, verdict))
        except Exception as exc:
            # A judge or brain failure is a failed measurement, never a substitute gates-only score.
            raise ValueError(f"scenario '{scenario_id}' regression measurement failed: {exc}") from exc

    head, dirty = ev.git_state(report_dir=eval_dir)
    bot_provider, bot_model = ev._bot_settings()
    report = {
        "stamp": {
            "run_tag": run_tag,
            "head": head,
            "dirty": dirty,
            "corpus_fingerprint": corpus.fingerprint,
        },
        "runs": runs,
        "summary": ev.summarize(runs),
        "gate_details": gate_details,
        "observations": observations,
    }
    comparable_baseline = {
        **baseline,
        "runs": [baseline_rows[scenario_id] for scenario_id in scenarios],
    }
    diff = ev.compare_runs(report, comparable_baseline)
    baseline_by_id = baseline_rows
    after_by_id = {row["scenario"]: row for row in runs}
    moved_ids = set(diff["regressions"]) | set(diff["fixes"])
    scenario_diffs = []
    for scenario_id in scenarios:
        before = baseline_by_id[scenario_id]
        after = after_by_id[scenario_id]
        scenario_diffs.append({
            "scenario": scenario_id,
            "tier": after["tier"],
            "before": {"score": before["score"], "passed": before.get("passed"), "gates_failed": before.get("gates_failed", [])},
            "after": {"score": after["score"], "passed": after["passed"], "gates_failed": after["gates_failed"]},
            "moved": scenario_id in moved_ids or before["score"] != after["score"],
        })

    return {
        "baseline_run_tag": baseline_run_tag,
        "scenarios": scenario_diffs,
        "moved_scenarios": [item["scenario"] for item in scenario_diffs if item["moved"]],
        "diff": diff,
        "gate_failures": {scenario_id: details for scenario_id, details in gate_details.items() if any(
            gate in after_by_id[scenario_id]["gates_failed"] for gate in details
        )},
        "summary": report["summary"],
        "appears_in_inbox": True,
        "cost": {
            "judge_calls": len(scenarios) * ev.JUDGE_REPETITIONS,
            "bot_turns": sum(len(observation.get("turns") or []) for observation in observations.values()),
            "currency_amount": None,
            "note": "Provider dollar cost is not returned by the corpus engine; judge call count and bot turns are reported.",
        },
        "provenance": {
            "run_tag": run_tag,
            "baseline_report": baseline_path.name,
            "corpus_fingerprint": corpus.fingerprint,
            "judge_model": judge.JUDGE_MODEL,
            "judge_credential_source": credentials.source,
            "judge_repetitions_per_scenario": ev.JUDGE_REPETITIONS,
            "bot_provider": bot_provider,
            "bot_model": bot_model,
            "kb_fingerprint": kb_state.get("fingerprint"),
            "kb_documents": kb_state.get("documents"),
            "head": head,
            "dirty": dirty,
        },
    }

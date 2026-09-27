# ODD: planner-snapshot-staleness

**Branch**: `odd/planner-snapshot-staleness`
**Worktree**: `../lumat-agent-odd-planner-snapshot-staleness`
**Base**: `e0e109f2` (= `origin/main` at branch time)
**Status**: merged — PR #289 (`b9bd8a6f`).
**Source**: the owner asked to close three pendings after the panel memory-read fix (#287). This is the
first, and it turns out to be the **unconsummated acceptance criterion** of a work unit that is already
implemented: `odd/tasks/planner-failure-observability.md`, criterion 8, *"A valid plan records no failure
diagnostic"*.

## Objective

The persisted `assistant_state.planner` must be the **current turn's** planner snapshot. Today it
accumulates across turns.

## Problem (measured)

`agent_chat.py:685-699` persists the finished turn with one call:

```python
thread.assistant_state = merge_assistant_state(thread.assistant_state or {}, {
    ...
    "planner": result.get("planner", {}),
    ...
})
```

and `merge_assistant_state` (`state.py:142-150`) **recursively merges nested dicts without replacing
sibling keys**. Two measured consequences:

1. **A failure diagnostic survives into later successful turns.** `plan_llm` only attaches `failure`
   when the turn failed — `result["planner"] = {**planner.model_dump(), "valid": valid}` and then
   `if diagnosis is not None: result["planner"]["failure"] = diagnosis`
   (`nodes.py:489-497`). The omission is deliberate and pinned by
   `tests/unit/test_assistant_planner.py:123` (`assert "failure" not in result["planner"]`). Because the
   new dict has no `failure` key, the recursive merge keeps the previous turn's.
   Observed on dev thread 158 after a successful turn: `planner.valid: true` **and**
   `planner.failure: {stage: guardrails, reason: unsafe_plan, …}` whose `raw_excerpt` was the previous
   turn's plan.

2. **`plan.arguments` accumulates across turns.** `PlannerOutput.arguments` is a plain dict, so the merge
   recurses *into* it. Observed on the same row: `planner.arguments` carried both the earlier write
   plan's keys (`tipo`, `titulo`, `contenido`, `visibility`) and the current read plan's
   (`scope`, `topic`, `limit`).

Both are the same defect: a **per-turn snapshot** is being merged as if it were an accumulating
structure.

## Decisions

**A — replace the `planner` snapshot, do not merge it.** `planner` is only ever written wholesale
(`plan_llm` and `guardrails` both return a complete dict), and nothing reads the persisted value:
`recovery.py` reads `events`, `recoverable` and `execution_status`, the panel routes and the web client
never read it. So replacement is the behaviour that was always intended.

**B — `PlannerOutput` and `plan_llm`'s contract are not touched.** The key is deliberately absent on
success; the bug is at the persistence boundary, not in the planner. This also keeps
`test_assistant_planner.py:123` meaningful instead of relaxing it.

**C — the other snapshot keys are left alone, and this is deliberate.** `guardrails`, `context_meta`,
`approval`, `cost_mode` and `cost_directive` are merged through the same call, but their key sets are
stable per turn, so the merge is a no-op for them. No symptom was observed. Changing them is not
justified by evidence and would widen the blast radius for nothing.

## Scope

- `app/services/agent_chat.py` — the turn's state persistence.
- `tests/integration/test_assistant_chat.py` — the two-turn coverage.
- `odd/tasks/planner-snapshot-staleness.md` — this record.
- `odd/tasks/planner-failure-observability.md` — its `Status` line is corrected. It says
  `scoped — not started`, but the unit was implemented by `3d14aa46` and `53f02b04`; only its criterion
  8 was left unmet, and that is this unit. An artifact that misstates its own state is a defect in the
  record, and this unit is the one that closes it.

Nothing else. `merge_assistant_state` itself, `PlannerOutput`, `plan_llm`, `guardrails`, the graph, and
the responder are out of scope.

## Authorized scope

- Human-approved on 2026-09-22: closing the three pendings after #287, starting with this one.

## Constraints

- Strict TDD is active (`openspec/config.yaml` -> `testing.strict_tdd: true`), runner `uv run pytest`.
  RED must be observed before implementation.
- RDD is ON (global). Every commit is a review candidate; the consent envelope is answered by the
  **human**. The lineage is bound to **this worktree**.
- Two commits: `fix(...)` then `docs(odd): record ...`. Conventional commits, no AI attribution.
- `pyproject.toml` sets `addopts = "-q"` — do not add a second `-q`.
- `.opencode/tools/package-lock.json` is untracked noise from `rapso worktree create`; never commit it.

## Acceptance criteria

1. After a turn whose planner failed, followed by a turn whose planner succeeded, the persisted
   `assistant_state.planner` carries **no** failure diagnostic and `valid` is `true`.
2. The persisted `planner` contains exactly the planner's own keys: no key survives from an earlier
   turn.
3. `planner.arguments` is the current turn's, not a merge with an earlier turn's.
4. A failing turn still records its failure diagnostic, with stage and reason, unchanged.
5. The full suite is green, with the baseline and final counts both reported.

## Checks

```bash
eval "$(bash infra/test-db.sh env)"
uv run pytest tests/integration/test_assistant_chat.py
uv run pytest tests/unit/test_assistant_planner.py
uv run pytest tests/
```

## Baseline (measured before any edit, in this worktree)

```
uv run pytest tests/  ->  1126 passed, 2 warnings, 131.50s
```

(`main` had moved to `e0e109f2` with PR #288.)

## Tasks

- [ ] **T1 — RED.** Two full-turn tests over the real route and DB: a failed turn followed by a
      successful one leaves no failure diagnostic and no stale keys; two successful tool turns leave the
      second turn's arguments.
- [ ] **T2 — Fix.** Persist the planner snapshot by replacement.
- [ ] **T3 — Verify.** Focused files, then the full suite; counts reported.
- [ ] **T4 — Record.** Correct the stale `Status` in `planner-failure-observability.md`, then the review
      and the `docs(odd)` commit.

## Progress

- [x] Graph Check before editing — `graphify path` resolved `run_assistant()` (`app/chat/assistant/graph.py:123`),
      `merge_assistant_state()` (`app/chat/assistant/state.py:142`) and `plan_llm()`
      (`app/chat/assistant/nodes.py:432`); community `agent_chat.py`. No directed path is recorded
      between them, so the call edge was read from the source instead.
- [x] Worktree provisioned: `uv sync`, `infra/.env` copied, test DB up. Base `e0e109f2`.
- [x] Baseline measured (above).
- [x] **T1 — RED.** Two tests over the real route and database. Both failed for the right reason, and the
      first attempt did not: the initial fake provider created a fresh client per call, so both turns got
      the same payload and the failure was spurious. The harness also calls the provider once more to
      generate the thread title, which is not a planner call. Both were found before the fix.
- [x] **T2 — Fix.** The planner snapshot is persisted by replacement instead of by recursive merge.
- [x] **T3 — Verify.** `uv run pytest tests/integration/test_assistant_chat.py
      tests/unit/test_assistant_planner.py tests/integration/test_assistant_harness_guardrails.py` ->
      **98 passed**; `uv run pytest tests/` -> **1128 passed, 2 warnings** (baseline 1126, +2 tests).
- [x] **T4 — Record.** The stale `Status` in `planner-failure-observability.md` is corrected.

## Verification evidence

RED, before any production edit — both symptoms reproduced end to end:

```
assert "failure" not in planner
E  AssertionError: assert 'failure' not in {'kind': 'respond', 'tool': None, 'valid': True,
E    'failure': {'stage': 'parse', 'reason': 'invalid_json', 'raw_excerpt': 'this is not json', ...}, ...}

assert _persisted_planner(thread_id)["arguments"] == {"limit": 3}
E  AssertionError: assert {'limit': 3, 'query': 'ana'} == {'limit': 3}
```

After the fix, both pass, and a failing turn still records its diagnostic: the first test asserts the
diagnostic is present after the failed turn *before* asserting it is gone after the successful one, so
criterion 4 is covered by construction.

Not verified end to end through the panel UI. The observable here is the persisted row, and the two
tests drive the real HTTP route, the real graph and the real database — the only substitution is the
provider. A panel turn would add no signal that the assertions do not already read from the same row.

## Review outcome

- Native review lineage `review-5513005c630a2474`, one consolidated lens (`review-reliability`, order 0),
  `medium` risk, 2 files / 87 changed lines, correction budget 44. Consent relayed to the human and
  answered `granted`. Result: **approved, zero findings**. `authority: burned` on consumed revision
  `sha256:4d63813c5177b3709e925f92ae024ed720aec29012591885f42a0efa6c022df7`.
- The reviewed revision is the `fix(...)` commit; this record is carried by the second commit.

### A mis-step worth recording

The first preflight ran the selectorless status while the worktree held **both** a committed fix and an
uncommitted doc change. The status could not disambiguate — two ancient `escalated` lineages from
2026-09-12 and 2026-09-14 sit in the shared authority store — so it projected `current-changes`: the
uncommitted doc only. That candidate is passive, so it produced no lens, approved, and the follow-up
command acknowledged it. **The fix commit was never in that candidate, and the burn did not review it.**

Corrected by re-running the status with `--base-ref=<origin/main> --committed-only`, which projected
`base-diff` with exactly the two fix paths. The lineage above is that candidate. Nothing false was ever
claimed for the fix: the mis-projected burn approved a documentation change, not this code.

Operational lesson: when a worktree has both committed and uncommitted changes, run the preflight with an
explicit `--base-ref` and `--committed-only`, or the projection may cover only the working tree.

## Delivery

Pending: push the branch, open the pull request, and wait for CI.

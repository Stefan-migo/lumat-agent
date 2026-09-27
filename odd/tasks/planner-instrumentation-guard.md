# ODD: planner-instrumentation-guard

**Branch**: `odd/planner-instrumentation-guard`
**Worktree**: `../lumat-agent-odd-planner-instrumentation-guard`
**Base**: `53bbe320` (= `origin/main` at branch time)
**Status**: merged — PR #279 (`7340bc99`). Implemented and verified; native review approved and its authority burned.
**Source**: advisory finding `R3-001` from the native review of PR #278, handoff Engram #4582.

## Slug note

The handoff told the next agent to use slug `r3-001`. That slug is **taken**: `odd/tasks/r3-001.md`
(commit `62252fce`) is the KB retrieval-probe boundary validation from the *KB* handoff (Engram #4467),
and `r3-002.md` is its sibling. The two handoffs numbered their items `R3-NNN` independently, and the
numbers are handoff-scoped, not repo-global. This unit therefore uses a descriptive slug in the repo
convention (`relations-guard`, `dsml-responder-guard`). Engram `discovery/r3-slug-collision` (#4585).

## Objective

Restore the exception boundary around the two instrumentation calls in `plan_llm`, so a failure in
`_record_usage` or `_completion_text` degrades to the bounded fallback **with a persisted,
distinguishable diagnostic** instead of escaping the node.

## Problem (verified in code at `53bbe320`)

`app/chat/assistant/nodes.py:446-457` — the `try` covers only the provider call. `_record_usage` and
`_completion_text` live in the `else:` branch, outside every handler:

```python
    try:
        completion = _assistant_client().chat.completions.create(...)
    except Exception as exc:
        diagnosis = _planner_failure("provider_call_failed", "provider", exc)
    else:
        _record_usage(state, "planner", completion)   # outside every handler
        raw_text = _completion_text(completion)       # outside every handler
```

Both calls can raise:

- `_record_usage` (`nodes.py:259-273`) reaches the database — `session.get(InternalChatMessage,
  request_id)` and then `record_llm_cost(...)`, which takes a row lock (`with_for_update()`).
- `_completion_text` (`nodes.py:219-223`) indexes `completion.choices[0]` and reads
  `.message.content`; a provider object that is truthy but not indexable raises there.

Consequence: the exception escapes `plan_llm` entirely. There is **no** bounded fallback and **no**
persisted diagnostic — which is exactly the guarantee #278 introduced. `agent_chat` catches it
downstream and marks the turn `failed`.

## Why it was not fixed in #278

Receipt policy: a non-blocking finding cannot be edited into a frozen candidate — that would deliver
bytes the review never saw. It travels as its own unit. Same pattern that produced `relations-guard`.

## Contract this fix must respect

`odd/tasks/planner-failure-observability.md` (the #278 work unit): decisions D1-D6 and implementation
contract 1-7. This unit is coherent with that contract, not an exception to it.

- **D1** — `PlannerOutput` is not modified.
- **D2** — the diagnostic is persisted in `assistant_state.planner.failure`.
- **D4** — `bounded_fallback`'s signature and return type stay unchanged.
- **D5** — no user-visible behaviour change.
- **Implementation contract 1** — no two different causes may share a recorded reason.
- **Implementation contract 6** — a successful plan records no failure diagnostic.

## Pre-#278 behaviour (measured, not remembered)

`git show c58c24f7^:app/chat/assistant/nodes.py` shows a **single** `try` covering the provider call,
`_record_usage`, `_completion_text`, `json.loads` and validation, with a bare `except Exception:` that
called `bounded_fallback("provider failure")` and kept the `legacy_compat` early return.

So degrading to the bounded fallback was the original intent. #278 broke it by splitting the `try` to
give each failure path its own reason. This unit restores the boundary **without** restoring the silent
swallow that #278 removed.

## Decisions

**A — both instrumentation failures degrade to the same bounded fallback.** With `usage` the turn
degrades rather than continuing to plan. Rationale: `usage_recording_failed` means cost accounting is
broken, and continuing to answer while the cost ledger is silently unwritten is the failure mode the
cost gate exists to prevent. Degrading is also the pre-#278 behaviour, so it preserves D5 for the
existing paths and only converts an *escape* into the honest degraded turn for the new ones. The
alternative — log, persist, and keep planning — would need a diagnostic that coexists with
`valid = true`, which contradicts implementation contract 6.

**B — each new failure gets its own reason and stage**, distinct from the existing four
(`provider_call_failed`/`provider`, `empty_completion`/`completion`, `invalid_json`/`parse`,
`planner_output_validation_failed`/`validation`):

| Path | reason | stage |
|---|---|---|
| `_record_usage` raises | `usage_recording_failed` | `instrumentation` |
| `_completion_text` raises | `completion_extraction_failed` | `extraction` |

**C — the guards are flat sequential `if diagnosis is None:` blocks.** The `try`/`except`/`else` shape
is replaced by one guarded block per risky step. Reasons for the shape: each risky call gets its own
reason and stage, which a single handler cannot express (contract 1); there is no nesting; and the
`else:` branch disappears, so no call can drift outside a guard again.

**D — `raw_excerpt` stays empty on the extraction failure.** By definition there is no extracted text
on that path. The contract's "never empty on a non-empty response" applies to paths where a response
was readable, and those are unchanged.

**E — the `legacy_compat` branch needs no edit.** It triggers on `not raw_text` and both new failures
leave `raw_text` empty, so they inherit it exactly as `provider_call_failed` does today.

## Scope

- `app/chat/assistant/nodes.py` — the two guards, their reasons and stages.
- `tests/unit/test_assistant_planner.py` — the RED/GREEN coverage.
- `odd/tasks/planner-instrumentation-guard.md` — this record.

Nothing else. `PlannerOutput`, the prompts, the persona, `guardrails`, the graph shape, the responder
and the panel UI are out of scope.

## Authorized scope

- Human-approved on 2026-09-21: this unit and the worktree
  `../lumat-agent-odd-planner-instrumentation-guard`.
- Sibling items are **not** in this unit: the planner's unknown root cause, the persona/allowlist
  contradiction, and the invalid-plan disguise.
- The KB `r3-001`/`r3-002` work units are unrelated despite the shared ID numbering.

## Constraints

- Strict TDD is active (`openspec/config.yaml` -> `testing.strict_tdd: true`), runner `uv run pytest`.
  RED must be observed before implementation.
- RDD is ON (global). Every commit is a review candidate; the consent envelope is answered by the
  **human**. The lineage is bound to **this worktree**.
- Two commits: `fix(...)` then `docs(odd): record ...`. Conventional commits, no AI attribution.
- `pyproject.toml` sets `addopts = "-q"` — do not add a second `-q`.
- `.opencode/tools/package-lock.json` is untracked noise from `rapso worktree create`; never commit it.
- Nothing is merged here; delivery is a human decision after the review.

## Acceptance criteria

1. When `_record_usage` raises, `plan_llm` returns the bounded fallback and persists a diagnostic with
   `reason = "usage_recording_failed"` and `stage = "instrumentation"`.
2. When `_completion_text` raises, `plan_llm` returns the bounded fallback and persists a diagnostic
   with `reason = "completion_extraction_failed"` and `stage = "extraction"`.
3. Both emit one log record carrying the same diagnosis, with the reason, stage and exception type in
   the rendered message.
4. Both leave `planner.valid` false and the plan equal to `bounded_fallback(...)`.
5. The six reasons are mutually distinct; no two causes collapse into one recorded reason.
6. A valid plan records no failure diagnostic and `planner.valid` stays `true`.
7. The degraded turn's user-visible output is unchanged from the baseline.
8. The full suite is green and both counts (baseline and final) are reported.

## Checks

```bash
eval "$(bash infra/test-db.sh env)"
uv run pytest tests/unit/test_assistant_planner.py
uv run pytest tests/                       # full suite
git diff --name-only                       # only nodes.py, the planner test, and this record
```

## Baseline (measured before any edit, in this worktree)

```
uv run pytest tests/  ->  1097 passed, 2 warnings, exit 0, 120.10s
```

(The handoff quoted 1060; `main` moved with the merges of #276 and #277. 1097 is the real baseline.)

## Tasks

- [ ] **T1 — RED.** Two failing tests: a client whose `_record_usage` raises, and a client whose
      `_completion_text` raises. Each must observe the bounded fallback **with** its own persisted
      diagnostic and log record. Both fail today because the exception escapes.
- [ ] **T2 — Guards.** Give each instrumentation call its own guarded block, its own reason and stage.
- [ ] **T3 — Verify.** Focused file, then the full suite; counts reported (acceptance 8).
- [ ] **T4 — Review and record.** Native review, then the `docs(odd)` commit with the outcome.

## Progress

- [x] Graph Check before editing — `graphify query` on the planner area and
      `graphify path plan_llm() bounded_fallback()` -> **1 hop, `calls`**;
      `_record_usage()` resolves in the same `nodes.py` community.
- [x] Worktree created and provisioned: `uv sync`, `infra/.env` copied, test DB up.
- [x] Baseline measured (above).
- [x] **T1 — RED.** `test_plan_llm_bounds_usage_recording_failure` failed with an uncaught
      `RuntimeError: ledger down`; `test_plan_llm_bounds_completion_extraction_failure` failed with an
      uncaught `RuntimeError: malformed response`. Both escaped `plan_llm`, which is the defect.
- [x] **T2 — Guards.** One guard per instrumentation call, each with its own reason and stage.
- [x] **T3 — Verify.** `uv run pytest tests/unit/test_assistant_planner.py` -> **27 passed**;
      `uv run pytest tests/` -> **1099 passed, 2 warnings, 116.64s** (baseline 1097, +2 new tests).
      `git diff --name-only` at commit time -> `app/chat/assistant/nodes.py` and
      `tests/unit/test_assistant_planner.py` only.
- [x] **T4 — Review and record.** Below.

## Review outcome

- Native review lineage `review-3d132fd476e7fee4`, one consolidated lens (`review-reliability`,
  order 0) because the candidate is `medium` risk: 2 changed files, 85 changed lines.
- Consent relayed to the human and `granted`; the review ran over the frozen candidate tree
  `8c08602fceb7291c193c14a3c94710c8169dbb40` with `--untracked-scope=exclude`, so neither this task
  document nor the untracked `package-lock.json` was part of the reviewed bytes.
- Result: **approved, zero findings**. Two evidence entries: the guards bound both failures, and the
  new tests cover diagnostics, invalid planner state, fallback output and error logging.
- `authority: burned` on consumed revision
  `sha256:cdd2d6281f42837df6a713110adc96ac6b64f31af93ddc650f80ddbb9fd8e66d`.
- The reviewed revision is the `fix(...)` commit below; this record is carried by the second commit.

## Delivery

Human decision pending. The reviewed candidate is committed as the `fix(...)` commit; nothing has been
pushed and no pull request exists yet.

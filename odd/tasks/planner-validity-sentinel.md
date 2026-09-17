# ODD: planner-validity-sentinel

## Objective

Make planner validity an explicit result of validation at the single planner trust boundary, instead
of an inference from the human-readable `summary` text.

## Problem

`plan_llm` decides whether the provider's plan is usable with a string comparison
(`app/chat/assistant/nodes.py:408`):

```python
valid = planner.summary != bounded_fallback("").summary
```

`parse_planner_output` (`app/chat/assistant/nodes.py:156-161`) never raises on malformed planner data:
it catches `TypeError`/`ValidationError` and returns `bounded_fallback(...)`. The comparison exists only
because that boundary discards the outcome it already computed. `bounded_fallback(reason)`
(`:146-153`) ignores `reason`, so every fallback is the same object with the same `summary`.

**Consequence.** A legitimate planner result whose `summary` is exactly the canned string
(`"I could not safely plan that request. Please try again."`) is classified as invalid. `guardrails`
(`:441-442`) then returns `decision: "fallback"` and the valid plan — including a whitelisted `tool`
call — is discarded and replaced by the canned apology. The failure is silent: the user reads a
plausible refusal, not a defect.

## Why — root cause (verified, not inferred)

- `parse_planner_output` swallows the validation outcome, so the `except` in `plan_llm` is reachable
  only for provider/transport failures — never for malformed planner JSON.
- `bounded_fallback` ignores its `reason`, so no fallback value carries a distinguishable marker.
- The only signal left is `summary`, which is model-authored data, not a validation state.
- The sibling path `plan()` (`:163-186`) sets `valid` inside its own `try`/`except` and is already
  correct. Only `plan_llm` infers.

Production frequency is **unmeasured**. The fix is justified by structure: validity derived from
model-authored content is wrong whenever that content collides, and the collision value is a fixed,
model-visible string that the model can legitimately reproduce.

## Scope

**In:** report the validation outcome explicitly from `parse_planner_output`; consume it in `plan_llm`;
add RED/GREEN regression coverage for the collision case; record evidence.

**Out:** the unused `reason` parameter of `bounded_fallback`; `plan()` and `guardrails()` semantics;
prompt text; sending tool schemas or descriptions to the model; the `legacy_compat` branch.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-planner-validity-sentinel`
- Branch: `odd/planner-validity-sentinel`
- Base: `10b49996`
- Files: `odd/tasks/planner-validity-sentinel.md`, `app/chat/assistant/nodes.py`,
  `tests/unit/test_assistant_planner.py`

## Constraints

- **Strict TDD: ON** — source: `openspec/config.yaml` (`testing.strict_tdd: true`). Runner:
  `uv run pytest tests/`. Observe RED before each source change; never invent RED evidence.
- Integration commands require `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat`.
  Without it, `tests/integration/conftest.py:59` falls back to the least-privilege `app` role and
  `db/migrate.sh` fails with `InsufficientPrivilege` — verified this session, not inferred.
- `parse_planner_output` must keep returning a usable fallback plan for malformed data and must never
  raise: every caller keeps receiving a safe plan.
- Keep `valid` identical for every existing case: malformed → `False`, provider failure → `False`,
  ordinary valid plan → `True`. Only the collision case changes, from `False` to `True`.
- Do not touch SDB, approval, guardrails, migrations, Docker, commits, or pushes.
- Planning heuristic: ~400 authored changed lines; this change is expected to be far smaller.
- All artifacts are written in English.

## Tasks

- [ ] **T1 — RED.** Add unit coverage through `parse_planner_output` and `plan_llm`: the boundary
  reports validity explicitly, and a legitimate plan whose `summary` equals the canned fallback text
  is reported valid and preserves its `tool`.
- [ ] **T2 — GREEN.** Return the validation outcome from `parse_planner_output` and consume it in
  `plan_llm`, deleting the `summary` comparison.
- [ ] **T3 — Evidence.** Run the required checks, record exact RED/GREEN output and honest limits,
  then leave all changes uncommitted in the working tree.

## Acceptance criteria

1. No caller infers planner validity from `summary` content.
2. A legitimate plan whose `summary` equals the canned fallback text is reported valid and preserves
   its `tool`.
3. A malformed planner payload is still reported invalid and still yields the bounded fallback plan.
4. Each criterion fails against the pre-change code (RED observed) and passes after.
5. Only the three authorized files change, and the targeted and full suites meet the baseline in the
   required environment.

## Checks

- `uv run pytest tests/unit/test_assistant_planner.py -q`
- `uv run pytest tests/unit tests/integration/test_assistant_harness_guardrails.py tests/integration/test_assistant_harness_production.py tests/integration/test_assistant_chat.py -q` with
  `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat`
- `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/ -q` with a
  1200000 ms tool timeout
- `git status --short`
- `git diff --check`

## Decisions

- **Validity is returned by the validation boundary instead of inferred by its caller.** One place
  decides whether planner data is structurally valid, so a second inference cannot drift from it. The
  alternative — an inner `try`/`except` in `plan_llm` — would duplicate that decision in two places,
  which is the shape that produced this defect.
- **Keep the bounded fallback plan on malformed data instead of raising**, so every existing caller
  still receives a usable plan and no downstream branch changes.
- **Leave the unused `reason` parameter alone.** It is adjacent, but removing it touches four call
  sites and is scope expansion, not this defect.

## Progress

- [x] Created this ODD record before the first source change.
- [x] T1 — RED observed and recorded.
- [x] T2 — GREEN implementation applied.
- [x] T3 — Required checks completed and recorded.

## Verification evidence

| Check | Command | Result |
|---|---|---|
| RED (before the fix) | `uv run pytest tests/unit/test_assistant_planner.py -q` | 2 failed, 11 passed. Exact failure text: `E       AttributeError: 'PlannerOutput' object has no attribute 'valid'` and `E       assert False is True` for `test_plan_llm_does_not_treat_fallback_summary_collision_as_invalid`. |
| Targeted | `uv run pytest tests/unit/test_assistant_planner.py -q` | 13 passed. |
| Planner/assistant regression | `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/unit tests/integration/test_assistant_harness_guardrails.py tests/integration/test_assistant_harness_production.py tests/integration/test_assistant_chat.py -q` | 194 passed (100%). |
| Full suite | `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/ -q` | 875 passed (100%), with 2 pre-existing warnings: an unawaited `_publish_all` coroutine in `tests/integration/test_webhook_ingest.py` and the fastembed mean-pooling warning in `app/services/kb.py`. |
| Working tree / whitespace | `git status --short` and `git diff --check` | Exactly the three authorized files changed; `git diff --check` produced no output. |

The RED run also emitted the normal pytest summary and full traceback for both failures; the decisive failure lines are recorded above verbatim. No lint or typecheck command was run because the required verification commands specify pytest and repository checks only.

**Graph nodes consulted (Graph Check, Step 1):** `graphify query "plan_llm planner validity sentinel
and guardrails fallback decision"` on `main` @ `10b49996`:

- `plan_llm()` — `app/chat/assistant/nodes.py:385` (community `nodes.py`)
- `guardrails()` — `app/chat/assistant/nodes.py:436` (community `assistant/graph.py`)
- `PlannerOutput` — `app/chat/assistant/state.py:26` (community `assistant/state.py`)
- `execute()` — `app/chat/assistant/nodes.py:467` (community `nodes.py`)
- `test_assistant_harness_guardrails.py` — consumer of `plan_llm` (community `nodes.py`)
- `get_tool()` — `app/chat/assistant/tools/registry.py:268`

The directed path `plan_llm` → `guardrails` is a direct call edge in the graph; the collision defect
lives on that edge, not in a distant module.

## Recovery

Resume with `mem_context`, then the project-scoped `mem_search` for this feature, then
`mem_get_observation` for the full document, then read this file. Continue from the first unchecked
task.

## Next step

Add the regression tests and observe RED, then make validity explicit at the boundary and observe
GREEN. The unused `bounded_fallback(reason)` parameter remains a separate, deliberate follow-up.

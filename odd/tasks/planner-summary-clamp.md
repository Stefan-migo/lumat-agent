# ODD: planner-summary-clamp

## Objective

Preserve valid planner decisions when the human-readable `summary` exceeds its existing in-memory
boundary, while keeping the declared 200-character contract and making that boundary discoverable to
the model.

## Problem

`PlannerOutput.summary` is declared with `min_length=1, max_length=200`, but the planner prompt does
not disclose that limit. When a planner emits more than 200 characters, validation fails and the
assistant replaces the whole plan with a canned response, losing valid fields such as `kind` and
`tool`. The persisted `current_plan` JSONB value is unbounded, and no related 200-character database
column justifies the cap.

## Why — root cause (verified, not inferred)

The model prompt enumerates `summary` without a constraint (`agent/prompts/assistant_plan.md:9-10`).
`PlannerOutput.model_validate` rejects summaries longer than 200 characters
(`app/chat/assistant/state.py:36`), and both planner boundaries route that validation failure to
`bounded_fallback` (`app/chat/assistant/nodes.py:156-161`, `164-187`), replacing the complete plan.
The production frequency is **unmeasured**; this fix is justified by structure: an undiscoverable cap
combined with a catastrophic fallback. The `current_plan` storage is JSONB and unbounded
(`db/migrations/020_assistant_metadata.sql`), so the 200-character limit is an in-memory contract,
not a database constraint.

## Scope

**In:** clamp an overlong planner `summary` to 200 characters before normal validation; disclose the
limit in the planner prompt; add boundary regression tests; record the implementation and evidence.

**Out:** changing the number 200; changing `SDBTask.summary` or `SDBTask.verifiable_output`; changing
fallback semantics beyond allowing an overlong string to validate; investigating the known `valid =
planner.summary != bounded_fallback("").summary` sentinel in `app/chat/assistant/nodes.py:407`.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-planner-summary-clamp`
- Branch: `odd/planner-summary-clamp`
- Base: `155a003d`
- Files: `odd/tasks/planner-summary-clamp.md`, `app/chat/assistant/state.py`,
  `agent/prompts/assistant_plan.md`, `tests/unit/test_assistant_planner.py`

## Constraints

- **Strict TDD: ON** — source: project configuration (`testing.strict_tdd: true`). Observe the new
  regression test fail before changing source, then observe it pass after the fix.
- The validator must truncate only a too-long `str` and pass every other input through unchanged so
  normal validation still rejects non-strings.
- Keep `summary` as `Field(min_length=1, max_length=200)` and do not change the number 200.
- Do not touch SDB task fields, migrations, unrelated sentinel logic, Docker, commits, or pushes.
- All artifacts are written in English.

## Tasks

- [ ] **T1 — RED.** Add planner-boundary regression coverage through `parse_planner_output` / `plan`:
  a 250-character summary preserves the tool plan, exactly 200 characters remains unchanged, and a
  non-string summary is rejected.
- [ ] **T2 — GREEN.** Add a `field_validator("summary", mode="before")` that truncates only strings
  longer than 200 characters, preserving the existing field declaration and normal validation.
- [ ] **T3 — Prompt disclosure.** Add one short sentence stating that `summary` must be at most 200
  characters, changing nothing else in the prompt.
- [ ] **T4 — Evidence.** Run the required checks, record exact RED/GREEN output and honest limits,
  then leave all changes uncommitted in the working tree.

## Acceptance criteria

1. A 250-character planner summary no longer produces the fallback and preserves the plan's `kind`
   and `tool`.
2. A summary of exactly 200 characters passes through unchanged.
3. A non-string summary remains rejected through the documented planner boundary.
4. The planner prompt explicitly says that `summary` must be at most 200 characters.
5. Only the four authorized files change, and the full suite meets the established baseline when the
   required environment is available.

## Checks

- `uv sync`
- `uv run pytest tests/unit/test_assistant_planner.py -q`
- `uv run pytest tests/unit tests/integration/test_assistant_harness_production.py tests/integration/test_assistant_chat.py -q`
- `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/ -q` with a
  1200000 ms tool timeout
- `git status --short`
- `git diff --check`

## Decisions

- Keep 200 as the declared contract and clamp only at the planner trust boundary; this preserves
  valid structured decisions while limiting the human-readable field.
- Do not truncate SDB task summaries because that flow is semantically unsafe to alter and is
  explicitly out of scope.
- Treat production incidence as unmeasured; structural failure mode is sufficient justification.

## Progress

- [x] Created this ODD record before the first source change.
- [x] T1 — RED observed and recorded.
- [x] T2 — GREEN implementation applied.
- [x] T3 — Prompt disclosure applied.
- [x] T4 — Required checks completed after supplying the repository's explicit admin database URL.

## Verification evidence

| Check | Command | Result |
|---|---|---|
| RED (before the fix) | `uv run pytest tests/unit/test_assistant_planner.py -q` | **FAILED** — `test_overlong_summary_keeps_tool_plan_instead_of_falling_back`: `assert state["planner"]["valid"] is True` failed with `assert False is True` (10 tests collected; 9 passed, 1 failed) |
| Targeted / GREEN | `uv run pytest tests/unit/test_assistant_planner.py -q` | **PASSED** — 10 passed |
| Planner/assistant regression | `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/unit tests/integration/test_assistant_harness_production.py tests/integration/test_assistant_chat.py -q` | **PASSED** — 181 passed; wall time `1:03.84`; no warnings reported |
| Full suite | `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/ -q` | **PASSED** — 869 passed, 0 failed; wall time `8:27.40`; 2 pre-existing warnings (`_publish_all` was never awaited and fastembed pooling behaviour) |
| Working tree | `git status --short` | **PASSED** — exactly the four authorized files changed: three modified files and the new ODD record |
| Whitespace | `git diff --check` | **PASSED** — no output |

**Graph nodes consulted (Graph Check, Step 1):** `PlannerOutput`
(`app/chat/assistant/state.py`), `parse_planner_output()` and `plan()`
(`app/chat/assistant/nodes.py`), `bounded_fallback()` (`app/chat/assistant/nodes.py`), and
`test_assistant_planner.py` (`tests/unit/test_assistant_planner.py`). The directed path query from
`app/chat/assistant/state.py` to `tests/unit/test_assistant_planner.py` found no path; the affected
nodes were identified by the planner-area BFS query.

## Next step

The implementation and required verification are complete. The known planner validity sentinel at
`app/chat/assistant/nodes.py:407` remains a separate follow-up.

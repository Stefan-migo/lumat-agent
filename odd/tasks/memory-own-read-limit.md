# ODD: memory-own-read-limit

## Objective

Close the `R3-own-read-limit` advisory finding left open by `odd/memory-cross-thread`: an `own`
`memory.read` without a `topic` filter must never let the thread axis hide the project axis.

## Problem

`_read_memory()` concatenates the thread axis rows with the agent axis rows and applies
`[:limit]` afterwards (`app/chat/assistant/tools/registry.py:256-263`). Because `list_for_entity()`
already returns each axis ordered `updated_at DESC`, the concatenation gives the thread axis
**unconditional** priority: a thread holding at least `limit` rows (default 10) and no `topic`
filter returns only thread rows and hides every project-visible memory.

`_search_memory()` does not share the defect — it merges both axes and orders by fused score before
truncating (`:276-293`). `memory.read` has no query, so it has no score; the equivalent fix is a
fair merge of the two axes before truncating.

The current behaviour also violates MEM-3, which already requires an `own` read to return the
current thread's memories **unioned with** project-visible agent memories
(`openspec/specs/memory/spec.md:51,66`). No spec amendment is needed: the fix makes the code match
the existing requirement.

## Why

- Reported by the `review-reliability` lens as a non-blocking advisory on the
  `memory-cross-thread` candidate. The review contract forbids re-running review for an advisory
  finding, so closing it requires a new candidate.
- Registered in Engram as `backlog/memory-cross-thread-followups` (obs #4614).
- After `memory-cross-thread`, `visibility=project` is the default write target, so the agent axis
  is now the primary memory surface; a thread axis that can silently hide it defeats the unit.

## Scope

**In:**

- `_read_memory()` own branch: filter `topic` per axis, interleave the two axes (round-robin),
  then apply `[:limit]`.

**Out:**

- `memory.search` — already correct.
- The `customer` branch — single axis, no merge.
- No spec change, no schema change, no migration.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-memory-own-read-limit`
- Branch: `odd/memory-own-read-limit`
- Base: `85db481a`
- Files: `odd/tasks/memory-own-read-limit.md`, `app/chat/assistant/tools/registry.py`,
  `tests/unit/test_memory_tool_axes.py`

## Constraints

- **Strict TDD: ON** — source: `openspec/config.yaml` (`testing.strict_tdd: true`). Runner:
  `uv run pytest tests/`. Observe RED before the source change; never invent RED evidence.
- `limit` stays a hard cap on the returned rows (never `2 * limit`).
- Per-axis recency order is preserved; only the inter-axis ordering is defined by the interleave.
- Thread isolation survives: a `panel` row from another thread stays invisible.
- `pyproject.toml` already sets `addopts = "-q"`; use `-o addopts=""` when the count matters.
- One concern, `≤5` files per commit.

## Design decision

**D1 — Round-robin interleave, chosen by the human over a pure recency merge.** A pure
`updated_at DESC` merge still hides the project axis when a thread holds `limit` rows all newer
than any project row. Alternating the two axes guarantees the project axis is represented whenever
it has rows, which is the defect being closed. Trade-off: the result is no longer globally
recency-ordered across axes (within each axis it still is).

## Tasks

- [x] **T1** — RED: `tests/unit/test_memory_tool_axes.py` — an `own` read with a thread holding
      `limit` rows and one project row still returns the project row; both axes are interleaved.
- [x] **T2** — GREEN: interleave the two axes before truncating in `_read_memory()`
      (`app/chat/assistant/tools/registry.py:253-263`).
- [x] **T3** — Verify: unit tests, spec tests, full suite.

## Verification

- `uv run pytest tests/unit/test_memory_tool_axes.py tests/unit/test_memory_model.py -o addopts=""`
- `uv run pytest tests/spec/test_memory_spec.py -o addopts=""`
- `uv run pytest tests/ -o addopts=""` (full suite)

## Acceptance criteria

1. An `own` read with a thread holding `≥ limit` rows and no `topic` filter still returns the
   project axis rows.
2. The returned row count never exceeds `limit`.
3. A `topic` filter still matches across both axes.
4. A `panel` row from another thread stays invisible.
5. `memory.search` behaviour is unchanged.

## Outcome

Closed. One work unit: the fix landed as `cbb20533` and this record is the follow-up docs commit on
`odd/memory-own-read-limit`.

| Commit | Subject |
|---|---|
| `cbb20533` | `fix(memory): interleave own read axes before truncating` |

**Change.** `_read_memory()` own branch now filters `topic` per axis, interleaves the thread and
agent axes round-robin with `itertools.zip_longest`, and applies `[:limit]` afterwards. The
`customer` branch and `memory.search` are untouched. No spec or schema change: MEM-3 already
required the union, so the fix makes the code match the existing requirement.

**TDD.** RED observed before the source change: the two new behaviour tests failed on the
unmodified `_read_memory` (`2 failed, 13 passed`), then passed after the fix (`15 passed`). The
third new test pins that the `topic` filter still matches both axes.

**Verification.**

- `uv run pytest tests/unit/test_memory_tool_axes.py tests/unit/test_memory_model.py -o addopts=""`
  -> **15 passed** on the file (13 pre-existing + 3 new, minus none removed).
- `uv run pytest tests/spec/test_memory_spec.py -o addopts=""` -> **26 passed**.
- `uv run pytest tests/ -o addopts=""` -> **1155 passed, 0 failed** (exit 0, 152.57s), against the
  worktree test database (port 5523).
- Collection delta verified against the base: 1152 collected before the new tests, 1155 after
  (+3). The `1154` recorded for `memory-cross-thread` does not match this worktree's baseline;
  the delta, not the borrowed absolute number, is the evidence.

**Review (native RDD).** Lineage `review-615aa8b0e65953c5`, one lens (`review-reliability`,
order 0), `medium` risk, 2 files / 73 lines, correction budget 37. Consent relayed to the human
and `granted`. **Approved with zero findings**, authority burned on
`gentle-ai.review-acknowledged/v1`.

**Notes.** The worktree needed `uv sync` before `infra/test-db.sh up` could derive its port. The
untracked review selection needed the provider-bound JSON
(`{"schema":"gentle-ai.review-intended-untracked-selection/v1","untracked_scope":"exclude",
"intended_untracked":[],"expected_untracked_inventory":"sha256:…"}`), which cannot be combined
with the legacy `--untracked-scope` flag.

**Remaining backlog.** Per-project memory (item 2) and the
`visibility=project` -> `visibility=global` rename (item 3) stay open in
`backlog/memory-cross-thread-followups`.

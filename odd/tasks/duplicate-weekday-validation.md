# ODD: duplicate-weekday-validation

## Objective

Make `_parse_hours` reject a schedule entry whose `days` list repeats the same weekday **within**
the one entry, and pin that stronger invariant in SS-5.

## Problem

Measured on `base` = `5ae02c45`, not recited.

- `app/panel/api/routes/settings.py:131` initialises `seen_days: set[int] = set()`.
- `:144` rejects an entry only when `seen_days.intersection(days)` is truthy, and `:146` then adds the
  entry's days to `seen_days`. `seen_days` therefore holds only **already-processed** entries.
- Consequence: the **first** entry `{"days": [1, 1], "open": "09:00", "close": "17:00"}` passes every
  check and is persisted. The "no repeated weekday" invariant holds *between* entries but not
  *inside* one.
- Source of the finding: a non-blocking advisory from the native review of PR #306 (lineage
  `review-c27eb5d68ca2ebf6`), which explicitly framed it as separate follow-up work and **not** a
  reason to re-run that review. Recorded in `handoff/closure-gate-followups` (Engram #4699).
- Impact today is nil: `is_open_at` (`app/services/settings.py`) evaluates `weekday in days`, which a
  redundant day does not change, and the panel checkboxes cannot produce the shape. This unit closes
  the gap between the declared invariant and the implemented one, not an observed failure.

## Why

The invariant is stated, tested and documented as "no repeated weekday", but the implementation is
one entry short of it. A validation contract that is only true for the second entry onward is a trap
for the next writer: any future consumer that assumes uniqueness inside `days` gets a silently
wrong input. The fix is one condition; the cost of not fixing it is a permanently false guarantee.

## Scope

**In:**

- Reject a repeated weekday **within** a single `schedule` entry, with `400` and the existing
  `detail` (`"schedule weekdays must not repeat"`).
- One parametrized case in the existing rejection test.
- SS-5 scenario wording: `across entries` -> `within or across entries`.

**Out:**

- **No change to `is_open_at`, `get_hours_schedule` or any runtime consumer.** Duplicate days were
  already harmless there; this is an input-contract change only.
- **No frontend change.** The UI cannot emit the shape.
- **No new error message or status code.** The existing detail already describes the rule.
- **No DB migration.**

## Authorized scope

Human-authorized in this session, per feature, before `rapso worktree create`. The single product
decision surfaced was: strengthen the invariant (accepting the SS-5 spec delta) versus closing the
advisory as documented `wontfix`. The human chose to strengthen it.

## Constraints

- Strict TDD: RED observed before the fix, GREEN after, refactor only with both green.
- Test runner: `uv run pytest`. Focused file: `tests/functional/test_api_kb_settings.py`.
- Full Python suite green before freezing. A green subset is not evidence.
- Work-unit commits with Conventional Commit messages, no `Co-Authored-By`.
- Push requires its own explicit authorization.

## Tasks

### WU1 — reject the intra-entry duplicate

1. RED: add the parametrized case
   `({"timezone": "UTC", "schedule": [{"days": [1, 1], "open": "09:00", "close": "17:00"}]}, "hours.schedule")`
   to `test_settings_update_hours_rejects_invalid_values_without_persisting` and observe it fail
   (currently `200`, expected `400`).
2. GREEN: reject `len(set(days)) != len(days)` inside `_parse_hours` before the cross-entry check.
3. Keep the cross-entry rejection and the empty-days rejection unchanged.

### WU2 — pin the invariant in SS-5

Update the SS-5 scenario line (`openspec/specs/settings-scope-limits/spec.md:99`) so the rejected
input reads "a weekday repeated within or across entries".

### WU3 — verify and deliver

Run the full Python suite on the frozen candidate, commit, run the native review, open the PR.

## Verification

- `eval "$(bash infra/test-db.sh env)"` (test DB on this worktree's own port).
- Focused: `uv run pytest tests/functional/test_api_kb_settings.py -q`.
- Full: `uv run pytest -q`.

## Acceptance criteria

- AC1: `{"days": [1, 1]}` in the first entry returns `400`, persists nothing, and its `detail` is not
  the catch-all `"unknown section"`.
- AC2: a weekday repeated across two entries still returns `400` (existing case stays green).
- AC3: the valid schedule case still persists unchanged (existing test stays green).
- AC4: SS-5 scenario names the within-entry case.
- AC5: full Python suite green on the frozen candidate.

## Pinned contract

- P1: `_parse_hours` rejects a repeated weekday within one entry with `400` and detail
  `"schedule weekdays must not repeat"`.
- P2: `_parse_hours` rejects a repeated weekday across entries, unchanged.
- P3: day validation (`1..7`, integers, non-empty, not `bool`) is unchanged.
- P4: `is_open_at` and every other consumer are untouched.
- P5: SS-5's rejected-input scenario covers both within and across entries.

## Follow-up 2 of handoff #4699 — closed as `wontfix`, no code

`R3-session-acquisition-failure` (advisory from the native review of PR #303, lineage
`review-b25a68eace7bf9af`): the claim was that the try/except in `retrieve_kb` / `respond` covers
`kb.retrieve` but not the acquisition of the session, so entering the `with` could escape without the
degraded reply.

Re-measured on `5ae02c45`: **structurally correct, practically immaterial.**

- `session_scope()` (`app/db.py:26-40`) enters with `session = SessionLocal()` (`:29`). SQLAlchemy
  constructs the `Session` without acquiring a DBAPI connection; the engine connects on the first
  `execute` (`pool_pre_ping=True` only affects that moment).
- The `with` entry therefore performs no I/O and cannot raise on a database outage. The failure lands
  inside the try, in `kb.retrieve`.
- Same shape at `app/chat/nodes/respond.py:129-151` (clarification path) and
  `app/chat/assistant/nodes.py:609` (panel `retrieve_kb`).

Adding code here would guard a non-existent failure path. Closed as `wontfix`; no source change.

## Graph check

`graphify query "panel settings hours schedule validation weekdays"` against the fresh graph
(7337 nodes / 15611 edges, refreshed for `5ae02c45`). Nodes consulted:
`_parse_hours()` (`app/panel/api/routes/settings.py:120`, community `_post`),
`settings_hours()` (`:243`), `HoursBody` (`:74`), `routes/settings.py`. Frontend nodes
(`Settings.tsx`, `Settings.stories.tsx`) surface in the same community and are **out of scope**:
the UI cannot emit the shape and is not touched.

## Progress

| WU | Status | Evidence |
| --- | --- | --- |
| WU1 | complete | RED: `assert resp.status_code == 400` failed at `tests/functional/test_api_kb_settings.py:875` with `assert 200 == 400`; GREEN: focused suite `55 passed in 8.74s`, including cross-entry rejection and valid schedule coverage. |
| WU2 | complete | SS-5 now states that a weekday is repeated `within or across entries`. |
| WU3 | complete | Full suite: `1271 passed, 2 warnings in 132.97s (0:02:12)`; behavior commit `029d1e43`; this register commit is the delivery commit. |

## Next step

Work units complete; register commit follows this update.

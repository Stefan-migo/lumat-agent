# A failing startup sweep hides the ones after it

Feature id: `startup-sweep-isolation`
Backlog item: the two advisories of PR #214 — `R3-startup-sweep-ordering` and `R3-settled-run-coverage`
Branch: `fix/panel-startup-sweep-isolation`, stacked on `fix/panel-assistant-orphaned-run-recovery` (PR #214).

## Objective

Every startup recovery sweep runs on its own, so one failure cannot hide the ones after it, and the
orphan sweep's selection predicate is covered for the threads it must leave alone.

## Problem

PR #214 added `reap_orphaned_runs` as the fourth call inside one shared `try` (`app/main.py:39-45`).
The four sweeps are independent, but a failure in any of the first three — `run_notification_sweep`
touches the database and outbound notifications — skips the rest, and the orphan reconciliation is
last in line. The consequence lands on the boots least able to absorb it: a startup where an earlier
sweep broke leaves the operator with a live spinner and no Retry action for ten minutes, which is
exactly the state #214 removed.

The second half is coverage. `reap_orphaned_runs` selects on
`assistant_state -> 'live' ->> 'status' = 'running'`, and only the resumable-execution guard was
proven. Nothing asserted that a settled thread, or a thread that never ran, survives the sweep — and
the never-ran case depends on JSONB path semantics (`{}` yields NULL, so the comparison must not
match) rather than on an explicit guard.

## Scope

### T1 — one try per sweep

- Each sweep gets its own `try` and logs which one failed, instead of one shared message that names
  no culprit.
- Order is unchanged. The sweeps are independent, so isolation is the fix; reordering would only
  hide the coupling instead of removing it.

### T2 — coverage for the threads the sweep must leave alone

- A settled thread (`live.status == "completed"`) is untouched.
- A thread that never ran (`assistant_state == {}`) is untouched.

## Acceptance criteria

1. With an earlier sweep raising, the orphan sweep still runs and fails the orphaned run.
2. A settled thread and a never-ran thread are untouched by `reap_orphaned_runs`.
3. `pytest` suite green.

## Out of scope (do not expand)

- **Retrying or quarantining a failed sweep.** Isolation makes a failure visible and non-blocking;
  retry policy is a deployment concern, not a recovery invariant.
- **Moving `reap_orphaned_runs` first.** With per-sweep isolation the order no longer decides whether
  it runs, so putting it first would be cosmetic.
- **Any behaviour of the sweeps themselves.** This change only decides who survives whom.

## Tasks

- [x] **T1** — one `try` per startup sweep in the lifespan.
- [x] **T2** — tests that a settled thread and a never-ran thread survive the boot sweep.
- [x] **T3** — suite green.

## Progress

| Task | State | Evidence |
| --- | --- | --- |
| T1 | done | `app/main.py` — the four sweeps each get their own `try` in the lifespan; the log names the sweep that failed instead of one shared message that names none. Order unchanged. |
| T2 | done | `tests/integration/test_assistant_chat.py` — `test_reap_orphaned_runs_leaves_settled_and_never_ran_threads_alone` and `test_startup_sweep_isolation_survives_an_earlier_sweep_failing`; `_seed_assistant_run` gained a `live_status` parameter. Net +2 tests (859 → 861). |
| T3 | done | Full suite 860 passed, 1 pre-existing failure (below). |

### Teeth check (observed, not assumed)

Both mutations were run against the new tests, then the files were restored and re-hashed:

- Mutation A — the shared `try` restored in the lifespan:
  `test_startup_sweep_isolation_survives_an_earlier_sweep_failing` **failed**
  (`assert 'processing' == 'failed'`), with the notification sweep's traceback and no trace of the
  orphan sweep in the log: the coupling is real, not theoretical.
- Mutation B — the `.where(...)` dropped from `reap_orphaned_runs`:
  `test_reap_orphaned_runs_leaves_settled_and_never_ran_threads_alone` **failed**
  (`assert 2 == 0` — both protected threads reaped).
- Under mutation B the resumable-execution test kept passing, which is consistent: that guard lives
  in the loop, not in the SELECT.
- After restoring, `sha256sum` returned the pre-mutation digests for all three files
  (`87080cbc…`, `ff03dfff…`, `21e38a05…`).

### Verification (observed)

- Baseline before: 859 tests (from #214).
- Full suite: `TEST_ADMIN_DB_URL="postgresql://lumat:lumat@localhost:5432/lumat" uv run pytest -o addopts="" -q`
  → **860 passed, 1 failed, 2 warnings in 443 s** (861 total = 859 + 2 new).
- The single failure is **pre-existing and unrelated**:
  `tests/functional/test_api_dashboard.py::test_today_projection_uses_local_bounds_and_operational_predicates`
  fails with `IndexError: list index out of range` on `appointments_today`. It seeds an appointment
  at `now + 1 h` and asserts it falls inside "today" for `America/Santiago`, so in the last local
  hour of the day that appointment is already tomorrow. Proven pre-existing: the same test fails
  identically with this change stashed (`git stash push app/main.py tests/integration/test_assistant_chat.py`).
  It touches no lifespan or assistant-chat code.
- Both warnings are the same pre-existing pair (the `_publish_all` lifespan warning and the
  fastembed pooling one).

## Open risks carried forward

- Isolation makes a failed sweep visible and non-blocking; it does not retry it. A boot where a
  sweep broke still loses that sweep's recovery until the next restart.
- The never-ran case (`assistant_state == {}`) is covered by JSONB path semantics rather than an
  explicit guard: the selection is `... ->> 'status' = 'running'`, where a `{}` state yields NULL
  and therefore no match. The test now pins that behaviour.

## Checks / verification commands

Run from the repo root, with the test database up:

- `TEST_ADMIN_DB_URL="postgresql://lumat:lumat@localhost:5432/lumat" uv run pytest -o addopts="" -q`
- Focused: `… pytest -o addopts="" -q tests/integration/test_assistant_chat.py tests/integration/test_webhook_ingest.py`

TDD mode: **not active** for this repo (no strict-TDD capability cache; the ODD flow runs ordinary
functional verification). Runner: pytest.

## Graph nodes consulted

Graph: `graphify-out/graph.json`, `graphify-out/GRAPH_REPORT.md`.
Query: "startup lifespan sweeps crash recovery ordering orphaned assistant run reconciliation" →
216 nodes traversed (truncated at the 2000-token budget, so it is a map, not a proof).

Key nodes: `lifespan()` `app/main.py:31`, `create_app()` `app/main.py:49`, `reap_orphaned_runs()`
`app/services/agent_chat.py:1070`, `reset_stale_processing()` `app/webhook/ingest.py:383`,
`sweep_received()` `app/webhook/ingest.py:399`, `run()` `app/ops/sweep.py:6`,
`InternalChatThread` `app/models.py:746` (`assistant_state` JSONB, `server_default="{}"`).

## Recovery

Interrupted? Read this file plus the Engram mirror `odd/startup-sweep-isolation/tasks`, reconcile
against the actual worktree, and resume the first unfinished task.

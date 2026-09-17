# An orphaned assistant run waits for a timer instead of being reconciled at boot

Feature id: `orphaned-assistant-run-recovery`
Backlog item: `R4-orphaned-background-run`
Branch: uncommitted on `main` (`56c67c34`); the human owns the branch/commit decision.

## Objective

A run orphaned by a crash or a redeploy must be reconciled as soon as the process that owns it is
provably gone — at boot — instead of waiting for a 600 s silence timer plus a client read. Today
the operator is blocked from retrying for up to ten minutes after every deploy.

## Problem

The assistant turn runs as an in-process FastAPI background task. `reap_stale_run`
(`app/services/agent_chat.py:1008-1058`) is the only reconciliation, and it fires only from
`read_thread` (`app/panel/api/routes/chat.py:233`) and only when `live.status == "running"` **and**
`now - live.updated_at >= STALE_RUN_SECONDS` (600).

So for a run orphaned mid-turn:

1. The last `publish_live` wrote `updated_at` moments before the crash.
2. The process restarts; `now - updated_at` is seconds old, far below 600 s, so the reaper refuses.
3. Nothing else reconciles it: the lifespan sweep (`app/main.py:34-40`) recovers webhook messages
   only, and `resume_thread` refuses a plain planning run (it requires `stage == "executing"`).
4. The message stays `processing`, so the panel renders a live spinner and **withholds the Retry
   action** — the frontend shows it only when `message.status === "failed"`
   (`web/src/components/pages/AgentChat.tsx:930,969`).

The result: after a crash or a deploy that lands mid-run, the operator cannot retry for
`600 - (restart delay)` seconds, roughly ten minutes, while the UI claims the run is alive.

The certainty is available and unused: a fresh process owns no background task yet, which is
exactly the reasoning the existing startup sweep already applies to webhook messages —
"single worker: nothing can be actively processing at boot" (`app/main.py:29-33`).

## Scope

### T1 — reconcile orphaned runs at boot

- Extract the destructive body of `reap_stale_run` into one internal helper so the "fail this run"
  logic exists once; the read path keeps its staleness gate, the boot path does not need it.
- Add `reap_orphaned_runs(session_factory, *, limit=50) -> int`: select threads whose
  `assistant_state -> 'live' ->> 'status'` is `running` and fail each one. At boot, a `running`
  live state is proof of orphanhood in a single-process deployment.
- **Never destroy resumable work**: keep `reap_stale_run`'s existing guard that leaves
  `stage == "executing" and execution_status == "pending"` alone, because `resume_thread` can still
  reclaim those.
- Bound the sweep (`limit`) the way the other startup sweeps are bounded and log the count.
- Wire it into the lifespan next to the webhook recovery sweep, inside the same `try/except` that
  already treats a failed sweep as non-fatal.

### T2 — tests with teeth

- A boot reconciliation test proving a run with a **fresh** `updated_at` is failed (this is what the
  600 s timer cannot do), while a resumable execution and an already-settled run are untouched.
- A startup wiring test in the style of the existing `test_startup_sweep_reprocesses_received`:
  seed an orphaned run, boot the app, assert the message is `failed` and the state is `failed`.

## Out of scope (do not expand)

- **Durable re-execution of an orphaned run.** Reconciling the state is not the same as recovering
  the work; a durable queue or resumable planning turns is a much larger change (the SDB execution
  already has its own resume path). This change unblocks the operator, it does not resurrect work.
- **Multi-worker safety.** The boot sweep assumes a single process owns no task at boot, the same
  assumption `reset_stale_processing`/`sweep_received` already make; `infra/docker-compose.prod.yml`
  runs one uvicorn process with no `--workers`. A queue is the upgrade path; do not add worker
  coordination here.
- `session = _session_factory()()` sitting outside `run_agent_turn`'s `try` (`:753`). A failure
  there cannot be recorded — there is no session to record it with — so it is subsumed by this
  boot reconciliation and needs no code change.
- The reaper's three latent traps found while refuting `R3-stale-active-run` (best-effort publish,
  `updated_at is None` reaping on sight, naive-timestamp `TypeError`). Different items.

## Acceptance criteria

1. At boot, a thread with `live.status == "running"` and a fresh timestamp is failed.
2. A resumable execution (`stage == "executing"`, `execution_status == "pending"`) survives the boot
   sweep and stays resumable.
3. The read path's behaviour is unchanged: a fresh live run is still left alone by `read_thread`.
4. The sweep failure is non-fatal at startup, like the webhook sweep.
5. `pytest` suite green.

## Tasks

- [x] **T1** — boot reconciliation, one failure helper, wired into the lifespan.
- [x] **T2** — tests with teeth (fresh-timestamp reap, resumable survivor, startup wiring).
- [x] **T3** — suite green.

## Progress

| Task | State | Evidence |
| --- | --- | --- |
| T1 | done | `app/services/agent_chat.py` — `_fail_orphaned_run` holds the destructive body once; `reap_stale_run` keeps its staleness gate and delegates to it; `reap_orphaned_runs(session_factory, limit=50)` selects `assistant_state -> 'live' ->> 'status' = 'running'`, skips resumable executions, commits the batch. `app/main.py` calls it in the lifespan inside the existing non-fatal `try`, next to the webhook sweep. |
| T2 | done | `tests/integration/test_assistant_chat.py` — `test_reap_orphaned_runs_fails_a_fresh_run_the_read_path_would_spare`, `test_reap_orphaned_runs_leaves_a_resumable_execution_alone`, `test_startup_sweep_fails_orphaned_assistant_runs`. Net +3 tests (856 → 859). |
| T3 | done | Full suite 859 passed. |

### Teeth check (observed, not assumed)

Both mutations were run against the new tests, then the files were restored and re-hashed:

- Mutation A — the lifespan call removed: `test_startup_sweep_fails_orphaned_assistant_runs`
  **failed** (`assert 'processing' == 'failed'`).
- Mutation B — the boot sweep reusing the read path's staleness gate instead of
  `_fail_orphaned_run`: `test_reap_orphaned_runs_fails_a_fresh_run_the_read_path_would_spare`
  **failed** (`assert 'planning' == 'failed'`).
- Under both mutations the resumable-execution test kept passing, which is the point: the
  destructive decision is the new part, not the failure body.
- After restoring, `sha256sum` returned the pre-mutation digests for all three files
  (`563b47e1…`, `ff03dfff…`, `f224d18c…`).

### Verification (observed)

- Baseline before: 856 tests.
- Full suite: `TEST_ADMIN_DB_URL="postgresql://lumat:lumat@localhost:5432/lumat" uv run pytest -o addopts="" -q`
  → **859 passed, 2 warnings in 435 s**. Both warnings are the same pre-existing pair (the
  `_publish_all` lifespan warning and the fastembed pooling one), already reproduced against
  `HEAD` in the previous change.
- Every test that boots the app now runs the new sweep; the suite is unaffected, so no test's
  seeded state was being mistaken for an orphan.

### Open risks carried forward

- The boot sweep assumes one process owns no task at boot. That is the assumption the webhook
  sweep already documents and the current deployment satisfies (one uvicorn, no `--workers`); a
  queue is the upgrade path if that ever changes.
- Reconciliation is not recovery: the orphaned work is still lost, the operator just gets the
  Retry action back immediately.
- `reap_orphaned_runs` is bounded to `limit=50` threads per boot. A backlog larger than that is
  reconciled 50 per restart, or by the 600 s timer for whichever threads the panel reads.

## Checks / verification commands

Run from the repo root, with the test database up:

- `TEST_ADMIN_DB_URL="postgresql://lumat:lumat@localhost:5432/lumat" uv run pytest -o addopts="" -q`
- Focused: `… pytest -o addopts="" -q tests/integration/test_assistant_chat.py tests/integration/test_webhook_ingest.py`

TDD mode: **not active** for this repo (no strict-TDD capability cache; the ODD flow runs ordinary
functional verification). Runner: pytest.

## Graph nodes consulted

Graph: `graphify-out/graph.json`, `graphify-out/GRAPH_REPORT.md`.
Query: "stale run reaper active run timeout assistant run lifecycle" → 194 nodes traversed
(truncated at the 2000-token budget, so it is a map, not a proof).

Key nodes: `reap_stale_run()` `app/services/agent_chat.py:1008`, `run_agent_turn()`, `read_thread`
`app/panel/api/routes/chat.py:227`, `lifespan()` `app/main.py:28`, `run()` `app/ops/sweep.py:6`,
`sweep_received()` `app/webhook/ingest.py`, `resume_thread()`, `AgentChat.tsx`.

## Decisions (parent-owned)

- **Boot reconciliation, not a heartbeat.** When the process that owned the run is gone, orphanhood
  is certain; no heartbeat improves on certain. The heartbeat variant was considered while refuting
  `R3-stale-active-run` and is not needed for this case.
- **Reuse the existing failure body rather than duplicating it.** Two callers with different
  triggers, one destructive implementation.
- **The resumable guard stays.** Failing a run that `resume_thread` can still reclaim would destroy
  persisted work; the boot sweep must be strictly narrower than "anything running".

## Recovery

Interrupted? Read this file plus the Engram mirror `odd/orphaned-assistant-run-recovery/tasks`,
reconcile against the actual worktree, and resume the first unfinished task.

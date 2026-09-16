# Assistant SSE stream holds a worker thread and a DB connection for its whole life

Feature id: `assistant-sse-resource-hold`
Backlog item: `R4-sse-worker-exhaustion`
Branch: uncommitted on `main` (`1c6e7ee6`); the human owns the branch/commit decision.

## Objective

An open assistant SSE stream must not consume a scarce, process-wide resource while it
is idle. Today one stream holds a worker thread and a pooled database connection for up
to 300 seconds, so a handful of concurrent conversations take the whole panel down.

## Problem

`GET /panel/api/chat/threads/{thread_id}/stream` (`app/panel/api/routes/chat.py:294-310`)
is a **sync** route that returns a `StreamingResponse` built from the **sync** generator
`stream_events` (`app/services/agent_chat.py:827-873`). Three facts compose the defect:

**1. The poll loop sleeps inside a worker thread.**
`poll()` runs `while time.monotonic() - started < timeout:` and calls `time.sleep(interval)`
(same generator body, `:871`), with `timeout=300.0` and `interval=0.25` defaults. Starlette
consumes a sync iterator through `iterate_in_threadpool`, so every `next()` occupies one
AnyIO worker thread. Because the 0.25 s sleep happens *inside* the generator body, an open
stream keeps a worker thread busy at ~100% duty cycle for up to 300 s.

**2. The worker pool is the endpoint-level default, and it is process-wide.**
AnyIO's default `CapacityLimiter` is 40 tokens. Nothing in the repo tunes it: a grep for
`to_thread|run_in_threadpool|CapacityLimiter|total_tokens` across `app/` and `infra/` returns
zero hits. The app runs one uvicorn process with no `--workers` (`Dockerfile:35`,
`infra/docker-compose.prod.yml:59`). When the pool is full, **every** sync route, sync
dependency and sync background task in the panel stops being served, not just streaming.

**3. The request session holds a pooled DB connection for the whole stream — and the DB pool
is even smaller.**
FastAPI 0.141.1 keeps the request dependency exit stack open across the response: in
`fastapi/routing.py:2193-2205` the `_solve_dependencies` context manager wraps
`await response(scope, receive, send)`, which for a `StreamingResponse` runs the entire stream.
The request-scoped session is shared by `require_admin_json` → `get_current_user_json` → `get_db`
and by the route's own `Depends(get_db)`, and it checks out a connection on the auth read.
`create_engine` (`app/db.py:19`) has **no pool tuning**, so SQLAlchemy's `QueuePool` defaults
apply: `pool_size=5`, `max_overflow=10` → **15 concurrent connections**, `pool_timeout=30 s`.

**Magnitudes.** 15 concurrent streams exhaust the DB pool first (the 16th request waits 30 s
and then fails); 40 concurrent streams exhaust the thread pool. Because the client opens the
stream while the run is still in flight, a single conversation can hold both a turn and a
stream, so ~15-20 simultaneous conversations are enough. This is the binding production risk
found in the `R4-sse-worker-exhaustion` review finding, and it is worse than the finding's
"~40 concurrentes": the connection pool binds before the thread pool.

## Scope

### T1 — the poll loop must not pin a worker thread

- Turn the HTTP streaming path into an **async generator**: `await asyncio.sleep(interval)`
  between polls instead of `time.sleep`, and run only the blocking read inside
  `asyncio.to_thread` (a short hop, milliseconds) instead of holding a thread for the interval.
- `asyncio.to_thread` (stdlib) rather than `anyio.to_thread` so the read is not bounded by the
  same AnyIO limiter the defect is about, and no undeclared dependency is introduced.
- `stream_thread` becomes `async def` and consumes the async generator.
- Preserve the wire format byte-for-byte: `data: {json}\n\n`, `application/json`-encoded with
  `ensure_ascii=False`, same event shapes, same de-duplication by
  `(run_id, sequence, type, task_id, tool)`, same live stage/preview emission, same terminal
  statuses (`completed`, `failed`, `approval_pending`), same `timeout`/`interval` semantics.
- Keep the pre-live service API callable: the non-`int` `thread_id` branch must still resolve to
  `recover_events(...)` for older integrations (`tests/integration/test_assistant_harness_compatibility.py`).

### T2 — the stream must not hold a request-scoped pooled connection

- Release the request session before returning the `StreamingResponse`, so the pooled connection
  goes back to the pool while the stream is open. The ownership read happens before that point
  and the route is a read-only `GET`, so nothing is lost: `get_db`'s teardown commit is a no-op
  and `dispatch_staged_events` has no staged events to publish.
- State the reason in a comment; this line looks removable and is not.

### T3 — regression coverage with teeth

- A test proving the poll loop does not block the event loop while it idles (a concurrent
  `asyncio.sleep` ticker must keep running during the stream window). This fails if a blocking
  `time.sleep` is reintroduced into the async generator.
- A test proving the route no longer depends on the AnyIO worker pool to make progress.
- Existing SSE endpoint tests in `tests/integration/test_sdb_api.py`,
  `tests/integration/test_assistant_chat.py` and
  `tests/integration/test_assistant_harness_compatibility.py` stay green unchanged.

## Out of scope (do not expand)

- **`run_agent_turn` also pins a worker thread and a session for the whole turn** (`chat.py:281`
  schedules it as a sync `BackgroundTasks` task). That thread is genuinely working, not idling, so
  it is a *capacity* question, not a *waste* one. Making the assistant turn async end-to-end is a
  separate change. Report it; do not do it here.
- Raising the thread/connection pool sizes or adding uvicorn `--workers`. That is deployment
  tuning, and it must not be smuggled into this fix to hide the root cause.
- Replacing polling with an in-process pub/sub (`app/services/realtime.py` already has an async
  publisher for the client-conversations socket). Bigger change, not required to fix the hold.
- The other pending backlog items: debounce threshold, duplicate `Conexión` in the footer strip,
  dead WS branches, E10, F11, `reopen()` error surface, `DESIGN_SYSTEM.md` page-architecture gap.

## Acceptance criteria

1. Opening an SSE stream does not occupy a worker thread for the poll interval.
2. Opening an SSE stream does not hold a pooled DB connection after the ownership check.
3. The SSE wire format and event semantics are unchanged; existing stream tests pass untouched.
4. The pre-live `stream_events` compatibility branch still returns recovered events.
5. `pytest` suite green.

## Tasks

- [x] **T1** — async poll loop; the stream idles without a worker thread.
- [x] **T2** — request session released before streaming; no connection held.
- [x] **T3** — regression tests with teeth, and the suite green.

## Progress

| Task | State | Evidence |
| --- | --- | --- |
| T1 | done | `stream_events_async` in `app/services/agent_chat.py` — `await asyncio.sleep(interval)` between polls, only the read hops out via `asyncio.to_thread`. `stream_thread` is `async def` and consumes it with `async for`. The sync `stream_events` keeps its documented pre-live contract and now shares `_EventCursor` + `_poll_once`, so the de-dup and live-emission logic exists once. |
| T2 | done | `chat.py` — `session.close()` before the `StreamingResponse`, with the reason inline. Empirically confirmed: with that line removed, a stream shows a peak of **2** concurrent connections (request + poll); with it, **1**. |
| T3 | done | `tests/integration/test_assistant_chat.py` — `test_stream_events_async_polls_without_blocking_the_event_loop` and `test_open_assistant_stream_releases_its_pooled_connection`. Net +2 tests (854 → 856). |

### Teeth check (observed, not assumed)

Both new tests were run against the defect re-introduced, then the files were restored and
re-hashed:

- Mutation A — `time.sleep(interval)` instead of `await asyncio.sleep(interval)` in
  `stream_events_async`: `test_stream_events_async_polls_without_blocking_the_event_loop`
  **failed** (`assert 4 >= 10`; the ticker only advanced when the poll handed the loop to a
  thread).
- Mutation B — `session.close()` removed from the route:
  `test_open_assistant_stream_releases_its_pooled_connection` **failed** (`assert 2 == 1`).
- After restoring, `sha256sum` returned the pre-mutation digests for all three files
  (`9b48e1eb…`, `f22d357a…`, `ad622dd0…`).

Margin on the loop-blocking assertion: healthy run `ticks 29` / `polls 6` / `events 7`;
defective run `ticks 4`.

### Verification (observed)

- Baseline before: 854 tests.
- Focused run (`test_sdb_api`, `test_assistant_chat`, `test_assistant_harness_compatibility`,
  `test_assistant_harness_session`, `test_agent_chat_realtime`): **59 passed**.
- Full suite: `TEST_ADMIN_DB_URL="postgresql://lumat:lumat@localhost:5432/lumat" uv run pytest -o addopts="" -q`
  → **856 passed, 2 warnings in 433 s**. Both warnings are pre-existing and were reproduced with
  the production files stashed back to `HEAD`: `RuntimeWarning: coroutine '_publish_all' was
  never awaited` (`test_webhook_ingest.py` — `asyncio.run` reached from the lifespan loop) and the
  fastembed mean-pooling `UserWarning`.
- Frontend untouched: no `web/` file changed, so `npm test` is not part of this verification.

### Open risks carried forward

- `run_agent_turn` still pins one worker thread and one session for the whole assistant turn
  (sync `BackgroundTasks`). It is capacity, not waste, but it means **~15 concurrent in-flight
  turns** still exhaust the default connection pool. Pool sizing or a real queue is a separate
  decision.
- `get_thread` now runs inline on the event loop in the async route (one threaded query set,
  bounded by the thread's message count). It does not hold a resource, but it is loop work.
- Nothing here changes the deployment shape; the panel is still one uvicorn process with
  AnyIO's 40-thread default and `QueuePool(5 + 10)`.

## Checks / verification commands

Run from the repo root, with the test database up:

- `docker compose -f infra/docker-compose.yml --profile test up -d db-test`
- `TEST_ADMIN_DB_URL="postgresql://lumat:lumat@localhost:5432/lumat" uv run pytest -o addopts="" -q`
  (full backend suite; the conftest falls back to the `app` role without the env var and
  `db/migrate.sh` then fails with "permission denied to alter role")
- Focused during development:
  `TEST_ADMIN_DB_URL="..." uv run pytest -o addopts="" -q tests/integration/test_sdb_api.py tests/integration/test_assistant_chat.py tests/integration/test_assistant_harness_compatibility.py tests/integration/test_assistant_harness_session.py tests/integration/test_agent_chat_realtime.py`

TDD mode: **not active** for this repo (no strict-TDD capability cache; the ODD flow runs
ordinary functional verification). Runner: pytest.

## Graph nodes consulted

Graph: `graphify-out/graph.json` (built from `1c6e7ee6`), `graphify-out/GRAPH_REPORT.md`.
Query: "SSE stream worker pool exhaustion panel chat assistant long-lived connection" →
655 nodes traversed; truncated at the 2000-token budget, so the result is a map, not a proof.

Key nodes: `stream_events()` `app/services/agent_chat.py:827`, `chat.py`
`app/panel/api/routes/chat.py:1` (community `chat.py`), `run_agent_turn()`, `publish_live()`,
`recover_events()` `app/chat/assistant/recovery.py:12`, `SessionLocal` / `session_scope()`
`app/db.py`, `panel/deps.py`, `worker.py` `app/ops/worker.py`, `AgentChat.tsx`, `realtime.ts`.
No `graphify path` call was needed: the defect is contained in two files and the graph query
already placed every participant.

## Decisions (parent-owned)

- **Async generator rather than a bigger thread pool.** A bigger pool scales the waste instead of
  removing it; the thread is idle, not working. The stdlib `asyncio.to_thread` keeps the read off
  the event loop without adding a dependency.
- **Releasing the request session is in scope.** Without it the fix is incomplete: the DB pool
  (15) binds before the thread pool (40), so the panel would still stall under the same load.
- **`run_agent_turn` stays sync.** Separate class, separate change; reported, not touched.

## Recovery

Interrupted? Read this file plus the Engram mirror `odd/assistant-sse-resource-hold/tasks`,
reconcile against the actual worktree, and resume the first unfinished task.

# The assistant stream route read its thread row on the event loop

Feature id: `stream-blocking-read`
Backlog item: `R3-blocking-sync-read`
Branches: the fix merged in PR **#219** (`fix/panel-stream-blocking-read`, `224f5abc`); the
session-ownership follow-up ships in this change (`fix/panel-stream-session-ownership`).

## Objective

Opening `GET /panel/api/chat/threads/{thread_id}/stream` must not do a synchronous, unbounded
database read on the event loop, and must not hand the request-scoped `Session` to a worker
thread. This is the same route — and the same class of defect — that #213 fixed for the polling
it drives.

## Problem

`stream_thread` (`app/panel/api/routes/chat.py`) is `async def` and lives as long as the stream.
It opened with a synchronous `get_thread(session, thread_id, current.id)` call on the event loop.
Two effects, and the backlog item described only the first:

**1. The read blocks the loop.** The route survives for up to 300 s of polling; a sync query at
its head is loop work for a route whose whole reason to be async is that it outlives the request.

**2. The read was also partly wasted, and its cost was unbounded.** `get_thread`
(`app/services/agent_chat.py`) loads the thread row **and every message of the thread**
(`order_by created_at, id`, no limit). This route reads only `active_run_id` and discarded the
message list. The cost grew with the thread's history, paid for nothing.

Magnitude, honestly: the backlog item called it "2 SELECTs (~ms)". The first is; the second is
not, once a thread is long.

**3. The fix in #219 introduced a second defect.** Reading through `asyncio.to_thread` passed the
**request-scoped `Session`** into the worker. SQLAlchemy documents `Session` as not thread-safe.
The repository's own precedent rejects it: `_poll_once` (`app/services/agent_chat.py`, written in
#213) opens its **own** session inside the worker for exactly this reason, thirty lines away in
the same file. The #219 review raised it (`R3-session-thread-safety`, WARNING,
`causal_disposition: introduced`) and the provider marked it advisory and non-blocking — it ships
as this follow-up rather than inside the frozen candidate.

## Scope

### T1 — read the thread row, not the message history (merged in #219)

- `read_owned_thread_run` replaced the route's `get_thread` call: the same ownership-scoped
  query (`id` + `user_id`), without the message list.
- The route reads it through `asyncio.to_thread`.

### T2 — the worker owns its session (this change)

- `read_owned_thread_run(session_factory, thread_id, user_id)` opens its own short session,
  queries, and closes it — the shape `_poll_once` uses. It returns a one-tuple so "not this
  user's thread" (`None`) stays distinct from a thread with no active run.
- The route no longer receives the request session into the worker.
- The request session is now closed **first**, before the read, not after it. Auth shares that
  session (`require_admin_json` → `get_current_user_json` → `get_db`) and has already read what
  it needs. Closing first is what keeps the stream at **one** pooled connection: had the close
  stayed after the read, the request's connection and the worker's would overlap, and #213's
  `peak == 1` assertion would have required weakening.

### T3 — cover the `run_id` fallback (this change)

`run = run_id or <the thread's active_run_id>` had no coverage: the only tests that open a stream
without `run_id` (`test_assistant_chat.py`, `test_assistant_harness_compatibility.py`) assert
403, so the handler never runs. `test_stream_without_run_id_follows_the_thread_active_run` opens
an owned thread's stream with no `run_id` and asserts every event carries the run the thread
points at.

## Teeth check (observed, not assumed)

- **T1 has teeth.** `test_open_assistant_stream_never_reads_the_thread_messages` attaches a
  `before_cursor_execute` listener to the engine and asserts no statement touches
  `internal_chat_messages` while a stream opens. Against the pre-change code it **failed** with
  the defect's exact statement: `SELECT internal_chat_messages.id, … ORDER BY
  internal_chat_messages.created_at, internal_chat_messages.id`.
- **T3 has no teeth, and that is stated rather than papered over.** It is coverage for the
  fallback expression, not a regression test: it passes on the pre-change code too. What it
  protects is a future edit to an expression that had none.
- **T2 has no behavioural test.** "The session did not cross threads" is a property of the code
  shape, not an observable outcome. Its evidence is the diff, the shape matching `_poll_once`,
  and the suite staying green — including `test_open_assistant_stream_releases_its_pooled_connection`,
  whose `peak == 1` is what caught the connection overlap described in T2.

## Verification (observed)

- Focused (`test_assistant_chat`, `test_assistant_harness_compatibility`, `test_sdb_api`):
  **56 passed**.
- Full suite: **863 passed, 0 failed in 466 s** (862 after #219, plus this change's one new test).
- The two suite warnings (the `_publish_all` coroutine never awaited, and fastembed's mean-pooling
  notice) are pre-existing and were reproduced with stashed changes.
- Frontend untouched, so `npm test` is not part of this verification.

## Open risks carried forward

- `run_agent_turn` still pins one worker thread and one session for the whole assistant turn.
  Capacity, not waste, but ~15 concurrent in-flight turns still exhaust the default connection
  pool. Pool sizing or a real queue remains a separate decision.
- The route still closes the request session synchronously on the loop. It is cheap (checkin, no
  I/O round trip) and was measured by #213's test, so it was left alone rather than made async
  for no behavioural gain.

## Checks / verification commands

From the repo root, with the test database up:

- `docker compose -f infra/docker-compose.yml --profile test up -d db-test`
- `TEST_ADMIN_DB_URL="postgresql://lumat:lumat@localhost:5432/lumat" uv run pytest -o addopts="" -q`
  (**`TEST_ADMIN_DB_URL` is not optional**: without it the admin URL is derived from
  `DATABASE_URL` as the `app` role and `db/migrate.sh` fails with "permission denied to alter
  role". `-o addopts=""` is what restores the "N passed" summary line that the repo's own
  `-q` in `addopts` suppresses.)
- Focused during development:
  `TEST_ADMIN_DB_URL="…" uv run pytest tests/integration/test_assistant_chat.py tests/integration/test_assistant_harness_compatibility.py tests/integration/test_sdb_api.py`

TDD mode: **not active** for this repo. Runner: pytest.

## Graph nodes consulted

Graph: `graphify-out/` — note it was last refreshed at `ecd8cce2`, so it predates #213–#219 and is
a map, not a proof. Query: "assistant SSE stream route session thread ownership active run id" →
388 nodes traversed, truncated at the 2000-token budget.

Key nodes: `stream_events()` (`app/services/agent_chat.py`), `agent_chat.py`,
`api/deps.py`, `panel/deps.py`, `routes/conversations.py`, `Session`, `User`, `models.py`.

## Decisions (parent-owned)

- **The worker opens its own session rather than reusing the request's.** A `Session` is not
  thread-safe; the repo already answers this the same way in `_poll_once`.
- **Close the request session before the read, not after.** Same guarantee #213 asked for, and it
  keeps the route at one connection instead of two.
- **The advisory ships separately from the approved candidate.** A byte change after the freeze
  invalidates the receipt, so #219 merged exactly what was reviewed and this change carries the
  fix, the coverage and this document.

## Recovery

Interrupted? Read this file plus the Engram mirror `odd/blocking-sync-read/tasks`, reconcile
against the actual worktree, and resume the first unfinished task.

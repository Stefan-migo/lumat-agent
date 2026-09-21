# ODD: suite-truncate-stall

**Branch**: `odd/suite-truncate-stall`
**Worktree**: `../lumat-agent-odd-suite-truncate-stall`
**Base**: `8ad0e026` (= `origin/main`, includes PR #272)
**Seeded from**: the CI evidence gathered while delivering `odd/versioning-release-process` (PR #273)
**Status**: scoped — not started

## Objective

Make the test suite reliable enough that CI is a trustworthy gate. Today the workflow works and the
suite is what fails: on the GitHub runner the full suite dies by the 120 s `pytest-timeout` ceiling
inside `clean_db`'s TRUNCATE, roughly two runs out of three, on code that is not the cause.

The deliverable is not "CI is green once" — it is "the stall is understood at its root and gone".

## Problem (measured, not assumed)

- **Three CI runs on PR #273**, same workflow, near-identical commits: run 1 **failed**, a re-run of
  the same commit **passed** (`1046 passed, 2 warnings in 84.57s`), the next commit **failed again**.
  Roughly 2 of 3.
- **Where:** `pytest-timeout` fires at 120 s with the main thread inside
  `tests/functional/conftest.py:87` → `clean_db` → `conn.execute(TRUNCATE ...)` → psycopg waiting on
  the socket. It happens after ~145 tests pass, at the first heavy database use.
- **It is pre-existing.** `pyproject.toml` documents it: *"the suite stalls intermittently, unrelated
  to the code under test"* — and that comment is the reason the 120 s ceiling and
  `timeout_method = "thread"` exist at all. CI did not create the stall; it made it visible.
- **It presents as a lock wait, not as slowness.** 120 s of zero progress, once. Not a slow machine:
  the same suite finishes in 85–110 s when it does not stall.

## Refuted hypotheses — do not spend time re-testing these

1. **Missing tmpfs / slow disk.** The runner's `docker create` line includes
   `--tmpfs /var/lib/postgresql/data`; the option is applied. Disk speed is not the mechanism.
2. **Small `/dev/shm`** (the classic Postgres-in-Docker trap). It is 64 MB both on the runner and
   locally, and locally the full suite passes repeatedly against a container created with the very
   same flags (89 s and 107 s).
3. **The CI environment contract** (`TEST_DB_PORT`, `TEST_POSTGRES_PASSWORD`, `TEST_ADMIN_DB_URL`).
   Verified separately and working; without `TEST_ADMIN_DB_URL` the failure is a loud 808-error
   credential failure, not a hang.
4. **The `1046` vs `1044` test-count gap.** Explained: `pull_request` checks run the merge with
   `main`, and `main` gained 2 tests in PR #272. Not a symptom of anything.

## The question to answer

Which connection holds what lock (or otherwise blocks) that the first heavy `clean_db` TRUNCATE waits
on — and why is it timing-dependent rather than deterministic?

## Approach

1. **Instrument rather than guess.** On a throwaway branch, run the suite with a sampler alongside it
   that captures `pg_stat_activity` (including `wait_event_type`, `state`, `query`), `pg_locks`, and
   `pg_blocking_pids()` once per second while pytest runs, and upload the sample as a workflow
   artifact. The stall is a lock wait, so the blocking session is observable during the freeze; the
   artifact survives the ephemeral runner, unlike the container.
2. **Bisect if the sample is inconclusive.** Run directory prefixes (`tests/functional`, then
   `tests/functional/<file>`…) to find the last test that completes before the block, then inspect
   what that path leaves open: session-scoped fixtures, connections from `TestClient` lifespan sweeps
   (`app/main.py` runs four startup sweeps, all of them touching the database), and the SQLAlchemy
   pool's idle-in-transaction behaviour.
3. **Fix the root cause in the tests.** Whatever the culprit is, the fix belongs where the leak is.

## Constraints

- **No papering over it.** No retry wrapper around pytest, no silent re-run, no removing the 120 s
  ceiling or switching `timeout_method`. That ceiling is the diagnosis; hiding a stall converts a
  visible defect into an invisible one.
- **Do not buy speed with coverage.** Truncating fewer tables, skipping suites, or shrinking the reset
  to make the window smaller is not a fix.
- **Application behaviour stays untouched.** If the root cause turns out to live in app code (for
  example a startup sweep that leaks a transaction), stop and bring that finding back before changing
  it — it is a different risk class.

## Out of scope

- The versioning and release work (PR #273) — delivered separately.
- Making the suite faster for its own sake.
- CI for `web/` (vitest + playwright); "the suite" here means pytest.

## Acceptance criteria

1. The blocker is identified **with evidence** — the blocking PID/query and the session holding it,
   captured live — not as another hypothesis.
2. **N ≥ 5 consecutive full local runs** with zero stalls, counts reported.
3. **Consecutive green CI runs on the same commit**, not one lucky green.
4. The 120 s `pytest-timeout` ceiling and `timeout_method = "thread"` remain in place.

## Checks

```bash
export PATH="$HOME/.local/bin:$PATH"
eval "$(infra/test-db.sh env)"
uv run pytest tests/
```

`pyproject.toml` sets `addopts = "-q"` — do not add a second `-q`. No linter, type checker, or
formatter exists; the tests are the verification.

### Reproduced locally, with the mechanism visible (2026-09-21)

Six consecutive full runs against the worktree's own test database:

| Run | Result | Stalled |
|---|---|---|
| 1 | `1044 passed, 2 warnings in 114.28s` | no |
| 2 | `1044 passed, 2 warnings in 141.25s` | no |
| 3 | killed by the 120 s ceiling | **yes** |
| 4 | killed by the 120 s ceiling | **yes** |
| 5 | `1044 passed, 2 warnings in 111.84s` | no |
| 6 | `1044 passed, 2 warnings in 115.62s` | no |

**2 of 6**, so it reproduces here and is not a runner quirk. This also means the diagnosis does not
need CI at all, which removes the push dependency from the critical path.

A `pg_stat_activity` sampler running alongside the loop caught the mechanism twice, in both stalls,
and it is exactly what the timeout stack implied:

```
state=idle in transaction   wait_event=Client|ClientRead
query=SELECT conversation_events.id, conversation_events.conversation_id, ...

state=active                wait_event=Lock|relation
query=TRUNCATE appointment_history, appointments, technician_availability, ...
```

The first session held its transaction (and the lock the TRUNCATE needed) for roughly two minutes
until the ceiling fired; the TRUNCATE waited the whole time. So the blocker is **a session left
`idle in transaction` holding a lock on `conversation_events`** — a table the `clean_db` fixture
truncates — and the stall is that wait, not slowness.

**Next step:** identify the code path that opens a `SELECT conversation_events...` transaction and
never commits or closes it (candidates: the startup sweeps that `TestClient`'s lifespan triggers, the
notification/integration worker, or a generator dependency whose session outlives the test), then fix
it where the leak is. Re-run the sampler with `pg_blocking_pids()` and `application_name` to name the
holder with certainty rather than by inference.

## Progress

- [x] Worktree created and provisioned (base `8ad0e026`, `infra/.env` copied, `.opencode` noise removed).
- [x] Reproduce with live database evidence: 2 of 6 local runs, `idle in transaction` vs blocked
      `TRUNCATE` on `conversation_events`, captured in `pg_stat_activity`.
- [x] Name the holder with certainty (exact holder query identified, unique match in the repo).
- [x] Identify the leaking code path (`_snapshot` reached from the panel WebSocket handler).
- [ ] Fix it at the root — **BLOCKED: the root cause lives in app code, so this needs a human
      decision before any change** (see "Root cause located" below).
- [ ] Five consecutive clean runs; then CI.

## Root cause located (2026-09-21) — APP CODE, stop-before-changing

Instrumented reproduction: a `pg_stat_activity` sampler (1 Hz) plus a watchdog that sends `SIGABRT`
to the pytest process when a `Lock` wait persists for 15 s. pytest has `faulthandler` enabled, so
the abort dumps every thread stack at the exact instant of the stall. The 120 s ceiling is untouched.

**The holder, captured live twice (same signature):**

```
WAITING pid=19912  wait=Lock|relation  q=TRUNCATE appointment_history, appointments, ...
HOLDER  pid=19910  state=idle in transaction  xact_age=16.8s
        q=SELECT conversation_events.id, conversation_events.conversation_id,
                 conversation_events.event, conversation_events.cause,
                 conversation_events.actor, conversation_events.created_at
          FROM conversation_events
          WHERE conversation_events.event IN ($1::VARCHAR, $2::VARCHAR, $3::VARCHAR)
          ORDER BY conversation_events.created_at, conversation_events.id
```

That statement matches **exactly one place in the repo**:

- `app/panel/api/routes/realtime.py:41-47` — `_snapshot()`, which filters only on
  `ConversationEvent.event.in_(ACTIVITY_EVENTS)` and orders by `(created_at, id)`.
- (Not `app/services/realtime.py:59 activity_events()`, which adds a `conversation_id` predicate
  the captured query does not have.)

`_snapshot()` is called only from the panel WebSocket handler `panel_websocket` (`/panel/ws`), which
receives its session from the request-scoped generator dependency `get_db`
(`app/panel/deps.py`) and holds it for the lifetime of the stream.

**Bisection:** running `tests/functional/test_api_realtime.py` alone reproduces the stall — the
`TRUNCATE` of the *next* test blocks on the session left open by the WebSocket path. The suite's own
docstring at `test_api_realtime.py:170-181` already notes that starlette's `WebSocketTestSession`
**cancels** the ASGI task when its `with` block exits. A cancelled task is the likely reason the
sync-generator dependency's teardown never runs, leaving the pooled connection with an open
transaction — hence `idle in transaction` and the held relation lock.

**Timing-dependent, as reported:** 2 stalls in 2 runs, then 0 in 6 after a small I/O-buffering
change. It is a race, not a deterministic path.

**Why this stops here:** the work unit says that if the root cause turns out to live in app code, the
finding comes back before any change — it is a different risk class. The two candidate fixes sit on
opposite sides of that line:

1. **App:** do not hold a transaction open across the stream (e.g. release/commit after the snapshot,
   or give the stream a session that is not request-scoped).
2. **Test harness:** ensure the ASGI task has finished before the test ends, so the dependency
   teardown completes.

**Instrumentation used (throwaway, outside the repo):** `/tmp/opencode/stall/sampler.py`,
`/tmp/opencode/stall/loop.sh`, `/tmp/opencode/stall/focus.sh`, `/tmp/opencode/stall/probe.py`.
Nothing in `pyproject.toml` or the suite was modified.

## Notes for the executor

- The stall is **intermittent**: it will not necessarily reproduce on demand. Budget for repeated runs,
  and prefer capturing evidence while it happens over trying to make it happen.
- Anything that needs a push to `Stefan-migo/lumat-agent` is a remote operation: ask the human first,
  every time. The pushed-artifact idea (a workflow that uploads the sample) needs that authorization.
- The earlier work unit's records live in `odd/tasks/versioning-release-process.md` on the branch
  `odd/versioning-release-process` — useful context on the CI environment contract, not a dependency.

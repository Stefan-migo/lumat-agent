# ODD: panel-ws-disconnect

**Branch**: `odd/panel-ws-disconnect`
**Worktree**: `../lumat-agent-odd-panel-ws-disconnect`
**Base**: `5c5f4af2`
**Status**: merged — PR #267 (`0de327d4`). Fix implemented and proven; checks green; the cancellation leak registered as its own unit.

## Objective

Make the panel WebSocket handler (`panel_websocket`, `app/panel/api/routes/realtime.py`) end its own
ASGI task when the client goes away, so `uvicorn --reload` can complete a graceful shutdown and the
dev API does not silently stop serving behind a bound port.

## Problem (verified on the running dev stack, 2026-09-20)

The dev API container `infra-api-1` accepted TCP on `:8000` and never answered HTTP. Evidence:

- `curl -m 8 http://127.0.0.1:8000/health` -> timeout, 0 bytes. `docker inspect` -> `running`,
  `RestartCount=0`.
- `docker top infra-api-1` -> the uvicorn reload server subprocess (PID 3398574) alive and sleeping;
  the reloader parent (PID 3398551) waiting for it. Its last log lines, and nothing after them:

  ```
  WARNING:  WatchFiles detected changes in 'scripts/kb_calibration.py', ... Reloading...
  INFO:     Shutting down
  INFO:     Waiting for background tasks to complete. (CTRL+C to force quit)
  ```

- `/proc/net/tcp` inside the container showed a connection in `CLOSE_WAIT`: a peer that had closed
  while the application never closed its side.
- Only `docker compose restart api` restored service.

Chain, read from the installed sources (uvicorn 0.52.1):

1. `Server.shutdown()` awaits `asyncio.wait_for(self._wait_tasks_to_complete(),
   timeout=self.config.timeout_graceful_shutdown)`.
2. `_wait_tasks_to_complete()` loops `while self.server_state.tasks and not self.force_exit`.
3. `timeout_graceful_shutdown` defaults to `None`, so `wait_for(..., None)` waits forever with no
   escape except a second SIGINT.
4. A live WebSocket request is one of those tasks: `wsproto_impl.handle_connect` adds it
   (`self.tasks.add(task)`) and only the app returning removes it.
5. `panel_websocket` never reads from the socket — its loop is `async for envelope in subscriber`,
   which blocks on `Subscriber.__anext__` -> `await self.queue.get()`. It therefore cannot observe
   `websocket.disconnect`, and `WebSocketDisconnect` (the only exit in its `except`) is never
   raised. The task outlives the connection: once per panel connection, until the process dies.
6. On the next file change the reloader waits on that leaked task forever, never starts the new
   server, and the port keeps accepting connections that nobody serves.

**The existing test cannot see this.** `tests/functional/test_api_realtime.py:57` asserts
`publisher.subscriber_count == 0` after the `with client.websocket_connect(...)` block, and passes
with the bug live: `starlette/testclient.py:120` registers `portal.call(cs.cancel)` in the session's
`ExitStack`, so the harness **cancels** the ASGI task on exit and the handler's `finally` runs during
cancellation. Cancellation is a test-harness artifact, not the handler ending on its own.

Blast radius: dev only. `infra/docker-compose.yml` runs `--reload` and bind-mounts the worktree;
`infra/docker-compose.prod.yml` has its own command and no bind mount. No data loss, no
production exposure — but the dev API stops serving silently, which reads as an application bug.

## Scope

`app/panel/api/routes/realtime.py` (the handler only), `tests/functional/test_api_realtime.py`, and
one flag in the dev `api` command in `infra/docker-compose.yml`.

## Authorized scope

- Human-approved on 2026-09-20: fix this bug and create this worktree
  (`rapso worktree create panel-ws-disconnect --yes`, the `--yes` being the consequence of that
  approval, not a substitute for it).
- Human-decided on 2026-09-20, after the Finding below was measured: this unit ships the disconnect
  fix and the leak/stall becomes its own unit. The leak is **not** fixed here; it is registered.
- The `Subscriber` publish-side removal path (`RealtimePublisher._remove` on `QueueFull`) is **not**
  in this unit; see Known limits.

## Constraints

- Strict TDD is active (`openspec/config.yaml` -> `testing.strict_tdd: true`, runner
  `eval "$(infra/test-db.sh env)" && uv run pytest tests/`). RED first, then GREEN.
- This worktree's derived test-DB port is **6259**; nothing may hardcode it.
- The WS wire contract does not change: same first `snapshot` frame, same event envelopes. The
  frontend client (`web/src/realtime.ts`) only ever reads — no `send` — so nothing it does should
  end the stream.
- `infra/docker-compose.prod.yml` is not touched.
- The change stays uncommitted in the worktree until the native review outcome; delivery
  (commit/push/PR) is a human decision.
- Do not touch other worktrees or their containers.
- `.opencode/tools/package-lock.json` is untracked noise from `rapso worktree create`. Never commit it.

## Decisions

**A — watch the disconnect concurrently, do not poll.** The handler needs two things at once: the
next published envelope and the client going away. One `asyncio.Task` awaiting
`websocket.receive()` and one awaiting the next envelope, awaited together with
`asyncio.wait(..., FIRST_COMPLETED)`, express exactly that. Polling the socket state or sending
heartbeats would either miss the disconnect or invent protocol frames the client does not expect.

**B — end on the `websocket.disconnect` message specifically**, not on any inbound message. The
client sends nothing today, but ending the stream on any received frame would turn a future
client-side ping into a dropped stream.

**C — keep the graceful-shutdown timeout in the dev command as defense in depth.** The handler fix
removes the known leak; `--timeout-graceful-shutdown` bounds the *class* of failure, so the next
leaked task costs a 5 s reload instead of a dev API that silently serves nothing for hours. It goes
on the dev command only.

## Acceptance criteria

1. The handler returns on its own — with no cancellation — after the client disconnects, and the
   publisher's subscriber count returns to zero.
2. The snapshot still arrives first and published envelopes still reach an attached client, unchanged.
3. An authorized role still connects; a missing session and an unauthorized role are still denied
   with 401/403.
4. A file change while a panel WebSocket is open no longer leaves the dev API bound but unresponsive
   (a reload completes; with the timeout flag, in bounded time even if a task ever leaks again).

## Checks

```bash
cd ../lumat-agent-odd-panel-ws-disconnect
infra/test-db.sh up
eval "$(infra/test-db.sh env)" && uv run pytest tests/functional/test_api_realtime.py -q
eval "$(infra/test-db.sh env)" && uv run pytest tests/ -q
```

## Known limits

- `RealtimePublisher._remove` (called from `publish` on `QueueFull`) marks a subscriber closed but
  cannot wake a `queue.get()` already blocked, so a client that ignores 100 queued events would
  still park the task. Reachable only by a client that stops reading; out of scope here and not
  reproducible in this session. Recorded rather than silently dropped.

## Finding — the undiagnosed suite stall, named (not in scope yet)

`odd/tasks/pytest-timeout.md` records an intermittent stall and says outright that it is not
diagnosed, with a "live libpq database-lock suspicion". This unit reproduced that exact stall and
named the mechanism. It is **not** this unit's defect and is **not** fixed here.

Measured mechanism, from a hang caught live:

```
 pid  |        state       | wait_event_type |                 query
 1421 | idle in transaction | Client          | SELECT conversation_events.id, ...
 1422 | active             | Lock            | TRUNCATE appointment_history, appointments, ...
 blockers
 {1421}
```

1. `tests/functional/conftest.py:87` `clean_db` truncates before every test.
2. Every panel test that opens a WebSocket ends with starlette's `WebSocketTestSession` cancelling
   the ASGI task (`starlette/testclient.py:120`, `portal.call(cs.cancel)` in its ExitStack).
3. FastAPI runs a sync generator dependency through `fastapi/concurrency.py:18`
   `contextmanager_in_threadpool`, whose cleanup is `except Exception as e: ... cm.__exit__ ...`.
   `CancelledError` is a `BaseException`, so neither that branch nor the `else` branch runs: the
   generator is never resumed, `get_db`'s `finally: session.close()` never executes, and the
   connection stays checked out `idle in transaction`, holding `ACCESS SHARE`.
4. The next test's `TRUNCATE ... CASCADE` needs `ACCESS EXCLUSIVE` and waits on it forever. That is
   the stall.

Measured effect of this change on that pre-existing race (same worktree, same test DB, the six
pre-existing tests only, `-k "not disconnect and not envelope"`, interleaved runs):

| Code | Runs that stalled |
| --- | --- |
| handler fixed (this unit) | 6 / 15 |
| handler unchanged (`HEAD`) | 0 / 15 |

An in-process probe confirmed the shape: one session left unclosed, and the unclosed session appears
after a WebSocket test — a pre-existing one in one run
(`test_panel_websocket_snapshot_has_rest_equivalent_case_context`), the new forwarding test in
another. Small n; the direction is consistent and the mechanism is deterministic once the
cancellation lands before the app finishes.

This is a genuine second defect of the same route: in production every panel disconnect cancels the
ASGI task the same way, so the connection is only reclaimed when the abandoned generator is
collected. Resolving it means changing who owns the WebSocket route's session (`Depends(get_db)` vs
an explicit context manager in the handler, and the auth dependency sharing that cached session) or
making the generator dependency cancellation-safe — a different unit with a much wider blast radius
than this one. Recorded here; awaiting a human decision on scope.

**An attempted mitigation was measured and rejected.** A variant that awaited every cancelled helper
task (`_drain`: "an unawaited cancelled task holds the handler's frame chain one garbage-collection
pass longer") measured **1/6** stalls against **0/6** for the unchanged handler — no proven
improvement — so it is not in the candidate. Keeping it would be unproven complexity, and the
`suppress(CancelledError)` inside a `finally` can also swallow the handler's own cancellation. What
stays is the minimal form: watch the disconnect, wait on both, cancel the loser.

## Progress

- [x] Graph check: `graphify query "panel websocket realtime publisher subscriber"` ->
      `Subscriber` (`app/services/realtime.py` L99), `RealtimePublisher` (L117), `panel_websocket()`
      (`app/panel/api/routes/realtime.py` L49), `RealtimeClient` (`web/src/realtime.ts` L65),
      `unit/test_realtime.py`, `realtime.test.ts`.
- [x] RED: `uv run pytest tests/functional/test_api_realtime.py -q` with the new test in place and the
      handler untouched -> `......F.`: 7 passed, and
      `test_panel_websocket_task_ends_when_the_client_disconnects` failed with `TimeoutError` — the
      handler never returned on its own after the peer left. The characterization lock on the
      forwarding loop passed on both sides, as intended.
- [x] GREEN: `_peer_disconnected` plus the `asyncio.wait(..., FIRST_COMPLETED)` loop in the handler;
      same command -> `8 passed in 1.71s`. Focused file run repeated: 5/5 clean when the pre-existing
      stall does not fire.
- [x] Checks (full suite): `eval "$(infra/test-db.sh env)" && uv run pytest tests/` ->
      **1023 passed, 2 warnings in 114.53s** on the second attempt. The first attempt died on the
      pre-existing stall above (`clean_db` TRUNCATE, ~21% progress, both warnings pre-existing: an
      un-awaited `_publish_all` coroutine in `test_webhook_ingest.py` and the fastembed pooling
      warning). No linter or pre-commit hook exists in this repo, so no source-mutating normalizer
      runs before the candidate is frozen.
- [x] Native review, then human decision on delivery
- [ ] Delivery (human decision)

## Review outcome

- Lineage `review-22e33f42503bb3e4`, risk **high** (reason code `process_boundary`, signal
  `shell_process`, path `infra/docker-compose.yml`), 4 lenses in provider order: `review-risk` (0),
  `review-resilience` (1), `review-readability` (2), `review-reliability` (3). Frozen correction
  budget: 77 lines.
- Consent relayed to the human and **granted**. The review ran over the frozen candidate tree
  `500647662efdde12d97a53ded74f2fd5534e9af6` with `--untracked-scope=exclude`, so this task document
  is not part of the reviewed bytes.
- Result: **approved**, zero BLOCKER/CRITICAL. One non-blocking advisory:
  - **R2-001** (`review-readability`, WARNING, `inferential`, `introduced`, disposition
    informational), `app/panel/api/routes/realtime.py:83-89`: the per-iteration subscriber task is
    cancelled only on the disconnect-winning branch; if the handler is cancelled while awaiting
    `asyncio.wait`, the pending `__anext__` task is neither cancelled nor awaited.
    **This is the same cleanup that `_drain` implemented and that was measured and rejected above**
    (1/6 stalls, no improvement); the closure states it opens no correction and belongs to separate
    later work. Recorded, not fixed here.
- `authority: burned` on consumed revision
  `sha256:68f6c22f34081b650bff76257f43ad7a45f50800d5a85b47e56c2c8d798e7263`
  (`gentle-ai.review-acknowledged/v1`).
- The reviewed candidate predates this record: the delivery commits below are what carries the task
  document into the PR.

## Delivery

Delivered on 2026-09-20 as **PR #267** (`odd/panel-ws-disconnect` -> `main`, label `type:bug`), three
commits: the handler fix with its tests, the dev shutdown bound, and this record. The reviewed bytes
are the first two commits' `app/` + `tests/` files; this task document was excluded from the review
(`--untracked-scope=exclude`) and is carried into the PR by the delivery commits.

Cleanup: the worktree's test database container and network were removed (`infra/test-db.sh down`).
The worktree and the remote branch stay until the PR merges — `rapso worktree cleanup --remote`
before that would close the PR.

# A run that outlives the stream becomes invisible

Feature id: `stream-deadline-continuity`
Branch: `odd/stream-deadline-continuity`

## Objective

When the assistant's SSE stream gives up at its deadline while the run is still going, the operator
keeps seeing a working turn until the run settles — instead of a spinner that stops with no answer
while the reply sits persisted in the database.

## Problem

`stream_events_async()` (`app/services/agent_chat.py:932`) polls the run and stops when
`timeout` (300 s, default, not settings-driven) elapses. Reaching the deadline is an **implicit
`StopIteration`** — no event, no marker, no signal of any kind. The route
(`app/panel/api/routes/chat.py:307`) simply ends the response body.

`AgentChat.tsx:457` `openStream` treats a stream *end* as normal completion: it reloads the thread,
clears `stream`, clears `recoverable`, and runs `setProcessing(false)` in `finally`. So an EOF that
means "I gave up" is indistinguishable, to the UI, from an EOF that means "the turn is over".

Measured on 2026-09-22 (container `infra-api-1`):

```
22:27:29  stream opens for run 02a0c…
22:32:29  stream deadline (300 s) — stream ends silently
22:33:11  run actually completes; the reply is persisted
```

The reply was **42 seconds late for the stream** and never reached the screen. The operator's report
was "el agente no termina de procesar y no responde". The ephemeral-cache half of that incident is
fixed elsewhere; the lazy-load half by `odd/embedder-prewarm`. **This feature is the half that made
the symptom silent** — and it is the only one that also covers every other slow turn.

## Scope

### T1 — the backend says it gave up

- `stream_events_async()` emits exactly one `timeout` event when, and only when, the loop exits
  because the deadline elapsed. Exit via `done=True` or `snapshot is None` must keep emitting
  nothing: those are settled or gone, not "still working".
- Payload: `{"type": "timeout", "thread_id": …, "run_id": …}`. Deliberately **no** `status` field: it
  would be a stale snapshot, and the frontend polls for the truth instead of trusting it.
- `stream_events()` (the sync generator kept for older integrations) gets the same event for parity.
  The two are documented as a pair that must not drift (`_EventCursor` docstring), and a consumer of
  the sync one has exactly the same bug today.

### T2 — the frontend keeps watching

- `AssistantEventType` (`web/src/types.ts:142`) gains `'timeout'`.
- `openStream` distinguishes "ended because it gave up" from "ended because it finished". On the
  former it **keeps `processing` true** and polls `getChatThread(id)` until the run settles, then
  loads the thread as it does today.
- Settled predicate: the admin message carrying that `run_id` is no longer `processing`. Not
  `active_run_id` — it is *not* cleared on completion (observed: a completed thread still held its
  `active_run_id`).
- The poll is bounded, and stops on unmount and when a different run takes over. The existing
  `recoverable` message is what remains if the bound is reached.

### T3 — tests on both sides

- Backend: the deadline emits exactly one `timeout` event and it is the last; a terminal run emits
  none. The existing `test_stream_events_async_polls_without_blocking_the_event_loop` already drives
  a non-terminal run to the deadline, so it is the natural place to pin this rather than a duplicate.
- Frontend (vitest): a stream that ends on a `timeout` frame while the run is still `processing`
  keeps the turn alive and renders the reply once the thread settles; a stream that ends normally
  does **not** start polling.

## Acceptance criteria

1. Deadline ⇒ exactly one `timeout` event, and it is the final event.
2. `done=True` / `snapshot is None` ⇒ no `timeout` event.
3. In the panel, a stream that gave up keeps showing the turn as in progress and renders the reply
   when it lands, without a manual refresh.
4. A normally-finished stream polls nothing extra.
5. `uv run pytest tests/unit -q` and the full suite green; `npm test --prefix web` green.

## Out of scope (do not expand)

- **Changing the 300 s value.** This change makes the deadline survivable; tuning it is a separate
  decision. Do not touch the default, do not make it settings-driven.
- **SSE heartbeats / keep-alive comments.** A proxy idle timeout is a different failure from the
  application deadline, and heartbeats would not tell the UI what this event tells it.
- **Persisting the `timeout` event** into `assistant_state["events"]`. It is a transport signal, not
  conversation history; `recover_events()` must not replay it.
- **Resuming the stream after a page reload.** The operator sees the truth after a manual refresh
  today and still will.
- **Any Retry/polling behaviour for `failed` runs.** The existing Retry button is untouched.
- **The panel WebSocket.** Separate channel, not involved.

## Tasks

- [x] **T1** — `timeout` event in `stream_events_async` (+ sync parity), emitted only on the deadline.
- [x] **T2** — `'timeout'` in `AssistantEventType`; `openStream` watches the run to settle and keeps
      the turn visible while it does.
- [x] **T3** — backend + frontend tests, including the negative case (normal end ⇒ no polling) and the
      StrictMode regression test.

## Progress

| Task | State | Evidence |
| --- | --- | --- |
| T1 | done | `app/services/agent_chat.py` — `{"type": "timeout", "thread_id", "run_id"}` yielded after the loop in **both** `stream_events_async()` and `stream_events()`; the loop already returns on `done=True` / `snapshot is None`, so only the deadline reaches it. The `timeout=300.0` default is untouched. |
| T2 | done | `web/src/types.ts` gains `'timeout'`; `AgentChat.tsx` adds `runStillProcessing()` + `watchRunToSettle()` (bounded, cancellable, non-stacking) and `openStream` watches the run to settle while keeping `processing` true. `handleEvent` deliberately does **not** handle the new type. |
| T3 | done | Backend: the deadline test extended + a terminal-run negative test + a sync parity test. Frontend: the watching test, the "normal end ⇒ no polling" negative test, and a StrictMode regression test (see below). |

### Defect found in review (and fixed before commit)

The first implementation wrote the unmount cleanup as:

```tsx
useEffect(() => () => { watchCancelledRef.current = true; }, []);
```

That effect has **no setup body**, so the ref is only ever set to `true`. `web/src/main.tsx` renders the panel inside `<StrictMode>`, and in dev StrictMode mounts → unmounts → remounts every effect. The remount's setup does nothing, leaving `watchCancelledRef.current === true` permanently: the watch returns on its first 3 s tick and never polls.

**The fix would have silently not worked in dev** — the exact environment the incident was reported from — while every existing test stayed green, because Testing Library does not wrap in StrictMode by default.

Proven, not reasoned: a StrictMode regression test was added first and **failed** (`Unable to find an element with the text: Persisted answer`), then the effect was given a setup body that resets the ref, and it **passed**. The test dispatches its `fetch` mock by URL and method rather than by call order, so it survives StrictMode's extra initial render.

### Teeth check (observed, not assumed)

Implementer's mutations, each applied → pinned test run → restored → digest confirmed:

- **A** — `yield {"type": "timeout", …}` removed from `stream_events_async`: the extended deadline test **failed** (expected a final `timeout`, none present). Restored `6dbc33b0…`.
- **B** — removed from `stream_events`: the sync parity test **failed** (last event was `response`, not `timeout`). Restored `6dbc33b0…`.
- **C** — in `openStream`, `if (gaveUp) await watchRunToSettle(id, run);` dropped: the frontend watching test **failed** (`expected "fetch" to be called 3 times, but got 4`). Restored `0c84c807…`.
- **D** — `runStillProcessing` forced to always return `true`: the frontend watching test **failed** (`Unable to find an element with the text: Persisted answer` — it never settles). Restored `0c84c807…`.

Orchestrator's independent mutation, on top of the above:

- **E** — the async `timeout` yield removed again: `test_stream_events_async_polls_without_blocking_the_event_loop`
  **failed** (`tests/integration/test_assistant_chat.py:997`). Restored `174335f5…`, matching the
  pre-mutation digest exactly.

### Verification (observed)

- Backend full suite:
  `TEST_ADMIN_DB_URL="postgresql://lumat:lumat@localhost:6296/lumat" uv run pytest -o addopts="" -q`
  → **1272 passed, 2 warnings in 174.98 s**. Both warnings pre-existing (`_publish_all` never awaited;
  the fastembed mean-pooling notice). The pre-existing dashboard failure recorded below passed here —
  its `IndexError` needs the last local hour of `America/Santiago`, which did not hold.
- `uv run pytest tests/unit -q` → green (371 collected; this branch predates `embedder-prewarm`'s 4).
- Frontend full suite: `npm test --prefix web` → **79 files, 618 tests passed**.
- Focused: `npm test --prefix web -- src/components/pages/AgentChat.test.tsx` → **40 passed**
  (39 before the StrictMode regression test was added).

Test DB for this worktree is derived: project `lumat-test-lumat-agent-odd-stream-deadline-continuity`,
port **6296**. Frontend dependencies installed with `npm ci --prefix web`.

## Checks / verification commands

Backend (this worktree's derived test DB is on port **6296**):

- `TEST_ADMIN_DB_URL="postgresql://lumat:lumat@localhost:6296/lumat" uv run pytest -o addopts="" -q`
- Focused: `… uv run pytest -o addopts="" -q tests/integration/test_assistant_chat.py`
- `uv run pytest tests/unit -q` (DB-free)

Frontend (from this worktree root):

- `npm test --prefix web -- src/components/pages/AgentChat.test.tsx`
- `npm test --prefix web`

Provisioning already done in this worktree: `uv sync --frozen`, `npm ci --prefix web`,
`cp ../lumat-agent/infra/.env infra/.env` (gitignored), `./infra/test-db.sh up`.

TDD mode: **active** for this repo. `openspec/config.yaml` sets `apply.tdd: true` and
`testing.strict_tdd: true` (runner `pytest`), and the SDD capability cache (`sdd-init/lumat`) records
`strict_tdd: true`.

**Correction.** This record first asserted that TDD was *"not active for this repo (no strict-TDD
capability cache)"*. That is **false**: both the config and the capability cache say the opposite.
The claim was inherited verbatim from `startup-sweep-isolation.md`, an older record that carries the
same error, and read back against both sources on 2026-09-22 while preparing this unit for delivery.
It is the same correction the `embedder-prewarm` record needed, from the same wrong source.

Declared consequence, not hidden: this unit therefore has **no recorded RED-before-implementation**
step. Its behavioral evidence is the mutation-based teeth check above — four mutations applied by the
implementer plus one independent mutation applied by the orchestrator, each pinned test observed
failing, every file restored with its digest confirmed — which is strong but is *not* a RED-first
cycle. Runners: pytest, vitest.

Known pre-existing suite failure, must not be attributed to this change:
`tests/functional/test_api_dashboard.py::test_today_projection_uses_local_bounds_and_operational_predicates`
(`IndexError`, only in the last local hour of `America/Santiago`).

## Graph nodes consulted

Graph: `graphify-out/` (worktree). Query area: the assistant SSE stream, the panel route, and the
event recovery path. Nodes: `stream_events_async` `app/services/agent_chat.py:932`, `stream_events`
`:906`, `_EventCursor.feed()` `:872`, `_TERMINAL_RUN_STATUSES` `:66`, `_poll_once()` `:894`,
`recover_events()` `app/chat/assistant/recovery.py:12`, `stream_thread()`
`app/panel/api/routes/chat.py:307`, `AgentChat.tsx` `openStream` `:457` / `handleEvent` `:443` /
`loadThread` `:363`, `streamChatEvents` `web/src/api.ts:110`, `AssistantEvent`
`web/src/types.ts:142`. Communities: `agent_chat.py`, `chat.py`, `test_assistant_chat.py`,
"Live Event Paths (WS panel vs assistant SSE)".

## Open risks carried forward

- **Removing the deadline is not on the table**, so a run may still outlive several watch windows. The
  frontend bound is what decides when the operator is finally told to refresh.
- **Polling has a cost.** Each `getChatThread` reads a thread and its messages; the interval and the
  bound are chosen to keep that trivial for one operator, not measured under many concurrent tabs.
- **The `timeout` event is transport-only.** A client that ignores it behaves exactly as it does
  today — which is the safe direction, but it means the guarantee is a UI one, not a protocol one.
- **Proxies may impose their own idle timeout** (no heartbeat exists). That failure predates this
  change and is explicitly out of scope.

## Recovery

Interrupted? Read this file plus the Engram mirror `odd/stream-deadline-continuity/tasks`, reconcile
against the actual worktree, and resume the first unfinished task.

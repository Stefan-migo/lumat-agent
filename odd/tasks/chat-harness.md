# ODD: chat-harness

## Objective

Give the WhatsApp conversation brain a channel-less manual exercise surface: a terminal REPL that
drives the **real** conversation entry point — the same state rebuild, deterministic gates,
orchestration, memory writes and KB retrieval production uses — so the bot's behaviour can be observed
turn by turn without Meta credentials, against an isolated stack whose panel shows the same
conversations.

## Problem

Meta Cloud API onboarding (Hito 1 T2.1) and go-live (T7.3) are blocked on client credentials, so the
customer-facing bot cannot be exercised end to end. Today there are exactly two ways to run the brain:

- `uv run pytest` — asserted scenarios with fixed expectations. No free exploration, no live
  visibility of what the bot decided or what it wrote.
- The webhook path — requires a signed Meta payload and an outbound Meta account.

There is no way to type a customer message and watch what the brain does. That is the gap this unit
closes. It is a **manual QA surface**, not a replacement for the asserted suites (422 integration
tests already cover the same scenarios as assertions).

## Why this is cheap and faithful (verified, not inferred)

- `run_conversation(session, message) -> list[str]` (`app/chat/graph.py:254-267`) is the channel-free
  seam. It rebuilds `ConversationState.from_db()`, invokes the compiled graph, persists replies and
  flushes per-turn memory. **It performs no HTTP and references no Meta identifier.**
- The existing integration suite already drives it exactly this way:
  `tests/integration/test_chat_state.py:55-72` (`_seed`) and `:110` (the call).
- `process_message()` (`app/webhook/ingest.py:342-380`) is the only channel-coupled wrapper around it:
  Meta media download, emergency ack, human/closed guard, `deliver_outbound`.
- **Routing is already persisted from the production path.** `classify_intent` writes a
  `ConversationEvent` with `event="classified"` and `cause="intent:<intent>"`
  (`app/chat/nodes/classify_intent.py:205-211` via `record_activity`), `unknown_intent` rows
  (`:119-136`), and `research_triage` / `handoff` record their own
  (`app/chat/subgraphs/research_triage.py:100`, `app/chat/nodes/handoff.py:82`). `record_activity`
  appends a `ConversationEvent` row (`app/services/realtime.py:36-56`).
  **Consequence: the harness calls `run_conversation` unmodified and still shows which intent was
  classified and which escalation happened. No bypass, no drift, no parity guard needed.**

## Scope

**In:** a `scripts/chat_harness.py` with a testable core (`ensure_conversation`, `run_turn`,
`inspect`) and a thin interactive shell; integration coverage for the core; an isolated Compose
overlay; an env-driven Vite proxy target so the worktree frontend reaches the worktree API.

**Out:** any change to `app/` (no production seam is added for a dev tool); the webhook signature /
verification path; Meta media download; `deliver_outbound` and the delivery state machine;
notification and template paths; the in-memory rate limiter; realtime push.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-chat-harness`
- Branch: `odd/chat-harness`
- Base: `9db746b7bdb57a832de5187216d26791c1812dfa`
- Files: `odd/tasks/chat-harness.md`, `scripts/chat_harness.py`,
  `tests/integration/test_chat_harness.py`, `infra/docker-compose.harness.yml`, `web/vite.config.ts`

## Constraints

- **Strict TDD: ON** — source: `openspec/config.yaml` (`testing.strict_tdd: true`); runner
  `uv run pytest tests/`. Observe RED before the source change; never invent RED evidence.
- Integration commands require `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat`
  (the `db-test` service), or the least-privilege `app` role fails with `InsufficientPrivilege` — a
  known environment condition, not a defect.
- **No production module changes.** The harness must reuse the existing seam, never add one.
- **The REPL shell is I/O glue and is deliberately not unit-tested.** TDD applies to the core.
- The harness runs with **real LLM keys** by design; tests keep the mocked provider fixtures.
- Planning heuristic: ~400 authored changed lines; this change is far smaller.
- No commits, no push, no PR from this session unless separately authorized.
- All artifacts are written in English.

## Decisions

- **D1 — Call `run_conversation` unmodified; do not invoke the graph directly.** The earlier plan was to
  call `build_graph().invoke(state)` to keep the routing state observable, accepting drift risk and
  paying for it with a parity test. Reconnaissance killed that need: the classified intent is already
  persisted as a `ConversationEvent.cause` from inside the production path
  (`classify_intent.py:205-211`). Observability therefore comes from the database, not from bypassing
  the seam. **Correction found during verification:** an *unrecognised* intent takes the early return
  at `classify_intent.py:196-201` and records `unknown_intent` instead of `classified`, so the
  inspector must read both event kinds. Both are still production-written rows; D1 stands.
- **D2 — No realtime push; manual refresh is the contract.** `RealtimePublisher` is documented as "a
  bounded, **process-local** fan-out publisher for one API process"
  (`app/services/realtime.py:118`). The harness is a separate process, so its committed events cannot
  reach the uvicorn process's WebSocket subscribers.
- **D3 — Reuse the existing `session_scope()` commit hook** (`app/db.py:26-40`) so the persistence
  path matches production exactly.
- **D4 — Make the Vite proxy target env-driven.** `web/vite.config.ts` hardcoded
  `http://localhost:8000`; without a configurable target the worktree frontend would silently talk to
  the primary worktree's API and show the wrong data.
- **D5 — Persist the inbound message, then run; never hold it uncommitted.** Graph nodes open their own
  sessions and write back onto the inbound row (LLM cost accumulates on the message), so flushing
  without committing deadlocks on the row lock. This is the same persist-then-process boundary as the
  webhook (WH-4). Discovered by the first RED run, which hung instead of failing.
- **D6 — Stamp `conversation.last_message_at` on every harness turn.** `webhook.ingest.persist_message`
  does it (`app/webhook/ingest.py:268-272`) and the panel's active list filters on it
  (`app/panel/api/routes/conversations.py:238-241`). Without it, every conversation this harness
  creates is invisible in the panel it exists to feed — the whole point of the unit. Caught by the
  integration test, not by review.
- **D7 — `!override` on the api `ports`.** Compose **concatenates** multi-value keys when merging
  files, so a plain `ports` list in the overlay added 8001 while the base still bound 8000 and the
  container failed with "port is already allocated". Verified against the running primary stack.

## Tasks

- [x] **T1 — RED.** Integration coverage for the harness core (5 tests + 1 added mid-flight).
- [x] **T2 — GREEN.** Implement `scripts/chat_harness.py` against those contracts.
- [x] **T3 — Isolated stack.** `infra/docker-compose.harness.yml` + env-driven proxy target.
- [x] **T4 — Evidence.** Required checks run; results below.

## Acceptance criteria

1. `ensure_conversation` returns the same conversation id for the same phone and never reopens a
   closed conversation.
2. `run_turn` on a fresh conversation returns the greeting and all 8 menu categories. **Corrected
   during verification:** `receive` is deterministic in *content*, but the turn continues into
   `classify_intent` (`app/chat/graph.py:210-215`), so a model call is expected here. Only the
   emergency route ends with zero model calls (criterion 3). The original "zero LLM calls" claim was
   wrong and is retracted.
3. A strong emergency keyword escalates the conversation to `human` and creates a case **without any
   LLM call** (the gate runs pre-LLM — `app/chat/graph.py:194-199`).
4. `inspect` returns conversation state, `captured_data`, the case, the `conversation_events` rows
   (including any `classified` intent cause) and the customer-scoped memory rows.
5. Each criterion fails against the pre-change code (RED observed) and passes after.
6. The isolated stack comes up on its own project name and host ports without touching the running
   `infra` stack.
7. Only the five authorized files change.

## Checks

- `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/integration/test_chat_harness.py -q`
- `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/integration/test_chat_state.py tests/integration/test_emergency.py -q`
- `cd web && npm run build`
- `git status --short`
- `git diff --check`

Prerequisite: `docker compose -f infra/docker-compose.yml --profile test up -d db-test`.
Never `down -v` on the main stack — it deletes panel data.

## Progress

- [x] Created this ODD record before the first source change.
- [x] T1 — RED observed: `ModuleNotFoundError: No module named 'chat_harness'` (collection error, the
      honest RED for a brand-new module).
- [x] T2 — GREEN: core implemented over `run_conversation`; six tests pass.
- [x] T3 — Isolated stack up as project `lumat-harness` on 8001/5433 alongside `infra` on
      8000/5432; api self-migrated and answered `/health` with `{"status":"ok","version":"0.1.0"}`.
- [x] T4 — Evidence recorded below.
- [x] Mid-flight RED/GREEN — `last_message_at` (D6): added the assertion, observed
      `assert None is not None`, then fixed `run_turn`.

## Verification evidence

| Command | Observed result |
| --- | --- |
| `uv run pytest tests/integration/test_chat_harness.py -q` (RED, before the module) | `ModuleNotFoundError: No module named 'chat_harness'` — `1 error during collection`. |
| `uv run pytest tests/integration/test_chat_harness.py -q` (RED, `last_message_at`) | `E assert None is not None` at `test_chat_harness.py:134`; `1 failed`. |
| `uv run pytest tests/integration/test_chat_harness.py -q` (GREEN) | `......` — `exit=0`. Re-run twice consecutively: `exit=0`, `exit=0`. |
| `uv run pytest tests/integration/test_chat_state.py tests/integration/test_emergency.py -q` | `.........................................` — `exit=0` (41 tests). The configured quiet runner suppresses the summary line, as already documented in `odd/tasks/planner-tool-schemas.md:141`. |
| `cd web && npm run build` | `✓ 332 modules transformed`, `✓ built in 5.35s`. The env-driven proxy type-checks under `tsc -b`. |
| `git status --short` | `M web/vite.config.ts`; `?? infra/docker-compose.harness.yml`; `?? odd/tasks/chat-harness.md`; `?? scripts/`; `?? tests/integration/test_chat_harness.py`. |
| `git diff --check` | No output; passed. |
| `docker compose ls` | `infra running(3)` and `lumat-harness running(2)` — no collision. |
| End-to-end (container, real LLM) | Turn 1 `hola` → greeting + all 8 categories, `intent=unknown`, `memoria=session`. Turn 2 → `intent=calefont`, `case=#1`, `capturado=_pending`. A second run drove the emergency route to completion: `state=human`, `case=#1`, the full safety protocol (Bomberos 132 / Ambulancia 131) and the technician-notified reply. |
| Data isolation | Isolated DB after the run: `customers=1 conversations=1 messages=6 cases=1 memories=1`. Primary DB unchanged: `customers=1 messages=0`. |
| `last_message_at` after the D6 fix | `last_msg=2026-09-18 15:36:01.233056+00` (previously `NULL`). |
| Panel visibility (the point of the unit) | `db/seed.sh` in the isolated api → `admin: created admin user 'admin'`. Then `POST /panel/api/login` through the Vite proxy → `200`, and `GET /panel/api/conversations` through `:5173` → `200` with conversation `#1` (`state: bot`, `last_message_at` set, `case #1` `service: calefont`, `priority: alta`). The terminal-created conversation renders in the worktree's panel. |

**Environment conditions met, not defects:**

- The test database (`db-test`, host `:5432`) is **shared by every worktree's pytest run**. A
  concurrent full-suite run from `lumat-agent-odd-memory-tools-write` collided with this unit's first
  attempt and produced a lock-wait that `pytest-timeout` reported as a stack dump. Re-running once the
  neighbour finished passed cleanly. Nothing in this unit can fix that; it is a property of the shared
  test database.
- That same sharing leaked a `settings` row: `emergency.keywords = ["caja de fusibles quemada"]` was
  left in the test database by another suite and turned the strong emergency hit into a weak one
  (`emergency_weak_hit`), failing two tests. The harness's `clean_db` fixture now truncates `settings`
  as well, which makes these tests order- and neighbour-independent. **Worth flagging to the team:**
  the suites that write `settings` do not reset them, so `tests/integration/test_chat_state.py`-style
  fixtures without `settings` are order-dependent in that shared database.

**Graph nodes consulted (Graph Check, Step 1):** the worktree has no `graphify-out/` report at base
`9db746b7`; the graph evidence from the primary worktree (`graphify-out/GRAPH_REPORT.md`, built from
`2c3d3936`) was consulted instead.

- `chat/graph.py` — the conversation graph community
- `nodes.py`, `classify_intent.py` — the node communities
- `test_emergency.py`, `test_chat_state.py` — existing coverage of the same seam
- "WhatsApp Webhook Pipeline (WH-1..WH-7)", "Design D2: no checkpointer, state rebuild from DB"

Directed paths confirmed from the wiring: `run_conversation -> build_graph -> emergency_gate ->
cost_gate -> handoff_gate -> receive -> classify_intent -> orchestrate`
(`app/chat/graph.py:194-231`); `classify_intent -> record_activity -> ConversationEvent`
(`classify_intent.py:205`, `app/services/realtime.py:45-49`).

**Honest limits.** The harness exercises the brain and nothing else. It does not cover the Meta
signature/handshake, inbound payload normalisation, media download, `deliver_outbound` or its delivery
state machine, notification templates, or the rate limiter. It also cannot push to the panel WebSocket
(D2), so the panel needs a manual refresh. Those gaps are the point of the unit, not defects in it.

## Recovery

Resume with `mem_context`, then the project-scoped `mem_search` for this feature, then
`mem_get_observation` for the full document, then read this file. All tasks are complete; the next
step is delivery.

## Next step

Implemented and verified; nothing has been committed, pushed, or opened as a PR. Delivery is the next
human decision.

Two findings belong to the team, not to this unit, and are recorded rather than silently fixed:

1. **`settings` leakage in the shared test database** — suites that write settings do not reset them,
   making neighbour suites order-dependent. A `settings` row in a `clean_db`-style TRUNCATE is the
   local mitigation; a conftest-level reset would be the real fix.
2. **How to run it** — copy `infra/.env` into a fresh worktree (it is gitignored), then
   `docker compose -p lumat-harness -f infra/docker-compose.yml -f infra/docker-compose.harness.yml up -d`,
   seed the admin once with `docker compose -p lumat-harness ... exec -T api db/seed.sh`
   (a fresh database has no panel user), and for the frontend
   `VITE_API_TARGET=http://localhost:8001 npm run dev` — the SPA binds IPv6 `localhost`, so reach it at
   `http://localhost:5173/panel/app/`. The isolated database starts empty, so KB retrieval intents hand
   off until documents are seeded through the panel's KB screen.

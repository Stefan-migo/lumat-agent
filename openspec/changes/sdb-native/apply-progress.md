# Apply Progress: Native SDB Seven-Phase Subgraph

## Work Unit
- Unit: WU-5 (PR5 of 5, stacked-to-main)
- Scope: Admin trigger, approval/resume, serialized SDB state, ordered SSE events, and API acceptance coverage
- Status: Complete; all five work units are complete
- Mode: Strict TDD
- Delivery: auto-chain; final stacked-to-main slice

## Completed Tasks
- [x] WU-1 RED — trigger scenarios and threat-matrix tests
- [x] WU-1 GREEN — validated state/config contract, fail-closed gate, normal-route preservation
- [x] WU-2 RED — phase ordering, frozen scope, distinct lookup errors, task output contract, bounds, and graph route tests
- [x] WU-2 GREEN — seven native phase nodes and graph routing through terminal evidence
- [x] WU-3 RED — typed artifact, project propagation/rejection, checkpoint, JSONB state, ordered event, and payload-bound tests
- [x] WU-3 GREEN — one bounded Tukulpan SDB seam plus agent-chat JSONB/event persistence
- [x] WU-4 RED — mutated SPEC/task-plan rejection, exact payload/expiry checks, atomic claim, checkpoint resume, and bounded digest tests
- [x] WU-4 GREEN — canonical SDB approval digest, SPEC binding, active-run claim, approved execution wiring, and checkpoint-based task resume
- [x] WU-5 RED — authenticated admin entry, operator stream rejection, ordered phase/evidence events, and SSE reconnect tests
- [x] WU-5 GREEN — explicit admin trigger propagation, serialized SDB state, and deduplicated ordered SSE event replay

## TDD Cycle Evidence
| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| WU-1 RED | `tests/spec/test_sdb_trigger.py` | Unit | N/A (new) | Written; collection failed before gate existed | 7 passed | 7 trigger scenarios | Strict validation and bounded reason codes |
| WU-1 GREEN | `tests/spec/test_sdb_trigger.py` | Unit | 30 related tests passed | Existing RED retained | 7 passed | 7 scenarios | Related graph/config coverage |
| WU-2 RED | `tests/spec/test_sdb_phases.py` | Unit | Existing assistant suites not changed | Written; collection failed before phase nodes existed | 7 passed | 7 scenarios | Pure phase helpers and bounded constants |
| WU-2 GREEN | `tests/spec/test_sdb_phases.py` | Unit | Existing assistant suites passed | Existing RED retained | 7 passed | 7 scenarios | Preserved partial-state node convention |
| WU-3 RED | `tests/integration/test_sdb_persistence.py` | Integration | Existing assistant/memory suites not changed | 4 failed on missing seams | 4 passed | 6 passed incl. explicit propagation and per-task rows | One seam; bounded JSON and capped event history |
| WU-4 RED | `tests/spec/test_sdb_recovery.py` | Unit | 28 related tests passed | Collection failed on missing `canonical_sdb_digest` | 5 passed | 5 scenarios plus failed-checkpoint triangulation | Stable canonical serializer and minimal recovery helpers |
| WU-4 GREEN | `tests/spec/test_sdb_recovery.py` | Unit | 28 related tests passed | Existing RED retained | 5 passed | Stable ordering, expiry, failed checkpoint, and large-payload cases | Reused SHA-256/TTL approval and JSONB claim seam |
| WU-5 RED | `tests/integration/test_sdb_api.py` | Integration | N/A (new) | Written; 3 failures before API trigger/event wiring | N/A | Admin, operator, event ordering, and reconnect cases | N/A |
| WU-5 GREEN | `tests/integration/test_sdb_api.py` | Integration | Related suite post-GREEN: 43 passed | Existing RED retained | 4 passed | 4 API scenarios, including operator and reconnect paths | Event deduplication and monotonic sequence normalization; focused suite remained green |

## Work Unit Evidence
- Focused: `DATABASE_URL='postgresql+psycopg://app:app@localhost:5435/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5435/lumat' uv run pytest tests/integration/test_sdb_persistence.py -q` — 6 passed.
- Related: same dedicated DB environment, `uv run pytest tests/integration/test_sdb_persistence.py tests/integration/test_assistant_chat.py tests/integration/test_assistant_harness_session.py tests/integration/test_memory_pipeline.py -q` — 34 passed.
- Runtime harness: the related PostgreSQL integration command above exercises migrated DB writes, JSONB reload, typed memory rows, and event ordering; 34 passed.
- Full required suite: `DATABASE_URL='postgresql+psycopg://app:app@localhost:5435/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5435/lumat' uv run pytest tests/` — timed out at 300s after 59% progress; no failures were reported before timeout.
- Rollback boundary: revert `tests/integration/test_sdb_persistence.py`, `app/services/tukulpan.py`, and `app/services/agent_chat.py`; leave WU-1/WU-2 assistant contracts and later recovery/API work untouched.
- Focused: `DATABASE_URL='postgresql+psycopg://app:app@localhost:5435/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5435/lumat' uv run pytest tests/spec/test_sdb_recovery.py -q` — 5 passed.
- Related: `DATABASE_URL='postgresql+psycopg://app:app@localhost:5435/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5435/lumat' uv run pytest tests/spec/test_sdb_trigger.py tests/spec/test_sdb_phases.py tests/integration/test_sdb_persistence.py -q` — 23 passed.
- Build/sanity: `uv run python -m compileall app` — passed; `git diff --check` — passed.
- Runtime harness: focused unit harness uses an atomic fake session; real runtime boundary remains WU-5 API approval/SSE coverage. Related PostgreSQL persistence suite passed 23 tests.
- Rollback boundary: revert `tests/spec/test_sdb_recovery.py`, `app/chat/assistant/approval.py`, `app/chat/assistant/recovery.py`, and the WU-4 sections of `app/services/agent_chat.py`; leave WU-1/WU-2/WU-3 behavior intact.
- Focused: `DATABASE_URL='postgresql+psycopg://app:app@localhost:5435/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5435/lumat' uv run pytest tests/integration/test_sdb_api.py -q` — 4 passed.
- Related: same environment, `uv run pytest tests/integration/test_assistant_chat.py tests/integration/test_agent_chat_realtime.py tests/spec/test_sdb_trigger.py tests/spec/test_sdb_phases.py tests/spec/test_sdb_recovery.py -q` — 43 passed.
- Full PostgreSQL suite: same environment, `uv run pytest tests/` — timed out at 300 seconds after 68% progress; no failures were reported before timeout.
- Build/sanity: `uv run python -m compileall app` — passed; `git diff --check` — passed.
- Runtime harness: authenticated panel `TestClient` exercised admin trigger, approval, serialized thread state, ordered SSE replay, and operator rejection; 4 focused tests passed.
- Rollback boundary: revert `tests/integration/test_sdb_api.py`, `app/panel/api/routes/chat.py`, `app/chat/assistant/graph.py`, and the WU-5 event-sequencing changes in `app/services/agent_chat.py`; leave WU-1–WU-4 behavior intact.

## Graph Check
- Graph checked from `graphify-out/GRAPH_REPORT.md` at commit `636ed328` before edits; post-edit `graphify --update` completed at session close and refreshed `graph.json` to 4704 nodes/9778 edges. Graphify reported non-blocking attribution warnings for excluded test/source files.
- Nodes consulted: `chat.py`, `ChatMessageBody`, `submit_message()`, `run_assistant()`, `sdb_trigger_gate()`, `approve_plan()`, `resume_thread()`, `persist_sdb_state()`, `recover_events()`, `InternalChatThread`, `test_assistant_chat.py`, and `test_sdb_recovery.py`.
- Edges consulted: `chat.py --imports--> approve_plan()`; scoped query connected `sdb_trigger_gate()` to `SDBTrigger`, `submit_message()` to `run_assistant()`, and `stream_events()` to `recover_events()`.

## Deviations and Issues
- No design deviation. No migration, project registry, non-default project behavior, executor, runtime, or event bus was added.
- Full suite exceeded the 300-second execution limit at 68%; focused and related suites passed.

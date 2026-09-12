# Apply Progress: Native SDB Seven-Phase Subgraph

## Work Unit
- Unit: WU-4 (PR4 of 5, stacked-to-main)
- Scope: Exact approval, atomic claims, and checkpoint resume only
- Status: Complete; WU-5 remains pending
- Mode: Strict TDD
- Delivery: auto-chain; current slice is the autonomous persistence boundary

## Completed Tasks
- [x] WU-1 RED — trigger scenarios and threat-matrix tests
- [x] WU-1 GREEN — validated state/config contract, fail-closed gate, normal-route preservation
- [x] WU-2 RED — phase ordering, frozen scope, distinct lookup errors, task output contract, bounds, and graph route tests
- [x] WU-2 GREEN — seven native phase nodes and graph routing through terminal evidence
- [x] WU-3 RED — typed artifact, project propagation/rejection, checkpoint, JSONB state, ordered event, and payload-bound tests
- [x] WU-3 GREEN — one bounded Tukulpan SDB seam plus agent-chat JSONB/event persistence
- [x] WU-4 RED — mutated SPEC/task-plan rejection, exact payload/expiry checks, atomic claim, checkpoint resume, and bounded digest tests
- [x] WU-4 GREEN — canonical SDB approval digest, SPEC binding, active-run claim, approved execution wiring, and checkpoint-based task resume

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

## Graph Check
- Graph stale but usable at graph commit `636ed328`; semantic refresh was not requested and structural queries completed.
- Nodes consulted: `approval.py`, `arguments_digest()`, `issue_approval()`, `validate_approval()`, `validate_execution()`, `recovery.py`, `claim_execution()`, `recover_events()`, `agent_chat.py`, `approve_plan()`, `resume_thread()`, `persist_sdb_state()`, `sdb_plan()`, `InternalChatThread`, and `test_sdb_state_writes_one_checkpoint_row_per_task_sequence()`.
- Edges consulted: exact directed paths `approval.py -> recovery.py` and `agent_chat.py -> nodes.py` returned no directed path (graph warnings reported ambiguous matches); scoped queries connected `approve_plan()`/`resume_thread()` to `claim_execution()` and `persist_sdb_state()` to Tukulpan/JSONB persistence. The required initial paths were executed and recorded as no-directed-path results.

## Deviations and Issues
- No design deviation. No migration, project registry, non-default project behavior, or API/SSE work was added; WU-4 intentionally wires approval at the existing agent-chat boundary and leaves API work to WU-5.
- Full suite exceeded the 300-second execution limit at 59%; focused and related suites passed.

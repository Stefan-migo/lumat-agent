# Apply Progress: Native SDB Seven-Phase Subgraph

## Work Unit
- Unit: WU-3 (PR3 of 5, stacked-to-main)
- Scope: Persistence and checkpoints only
- Status: Complete; WU-4 and WU-5 remain pending
- Mode: Strict TDD
- Delivery: auto-chain; current slice is the autonomous persistence boundary

## Completed Tasks
- [x] WU-1 RED — trigger scenarios and threat-matrix tests
- [x] WU-1 GREEN — validated state/config contract, fail-closed gate, normal-route preservation
- [x] WU-2 RED — phase ordering, frozen scope, distinct lookup errors, task output contract, bounds, and graph route tests
- [x] WU-2 GREEN — seven native phase nodes and graph routing through terminal evidence
- [x] WU-3 RED — typed artifact, project propagation/rejection, checkpoint, JSONB state, ordered event, and payload-bound tests
- [x] WU-3 GREEN — one bounded Tukulpan SDB seam plus agent-chat JSONB/event persistence

## TDD Cycle Evidence
| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| WU-1 RED | `tests/spec/test_sdb_trigger.py` | Unit | N/A (new) | Written; collection failed before gate existed | 7 passed | 7 trigger scenarios | Strict validation and bounded reason codes |
| WU-1 GREEN | `tests/spec/test_sdb_trigger.py` | Unit | 30 related tests passed | Existing RED retained | 7 passed | 7 scenarios | Related graph/config coverage |
| WU-2 RED | `tests/spec/test_sdb_phases.py` | Unit | Existing assistant suites not changed | Written; collection failed before phase nodes existed | 7 passed | 7 scenarios | Pure phase helpers and bounded constants |
| WU-2 GREEN | `tests/spec/test_sdb_phases.py` | Unit | Existing assistant suites passed | Existing RED retained | 7 passed | 7 scenarios | Preserved partial-state node convention |
| WU-3 RED | `tests/integration/test_sdb_persistence.py` | Integration | Existing assistant/memory suites not changed | 4 failed on missing seams | 4 passed | 6 passed incl. explicit propagation and per-task rows | One seam; bounded JSON and capped event history |

## Work Unit Evidence
- Focused: `DATABASE_URL='postgresql+psycopg://app:app@localhost:5435/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5435/lumat' uv run pytest tests/integration/test_sdb_persistence.py -q` — 6 passed.
- Related: same dedicated DB environment, `uv run pytest tests/integration/test_sdb_persistence.py tests/integration/test_assistant_chat.py tests/integration/test_assistant_harness_session.py tests/integration/test_memory_pipeline.py -q` — 34 passed.
- Runtime harness: the related PostgreSQL integration command above exercises migrated DB writes, JSONB reload, typed memory rows, and event ordering; 34 passed.
- Full required suite: `DATABASE_URL='postgresql+psycopg://app:app@localhost:5435/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5435/lumat' uv run pytest tests/` — timed out at 300s after 59% progress; no failures were reported before timeout.
- Rollback boundary: revert `tests/integration/test_sdb_persistence.py`, `app/services/tukulpan.py`, and `app/services/agent_chat.py`; leave WU-1/WU-2 assistant contracts and later recovery/API work untouched.

## Graph Check
- Graph stale but usable at graph commit `267821ee`; working branch is `sdd/sdb-native-3` at `1af0dfca` before these edits.
- Nodes consulted: `tukulpan.py`, `agent_chat.py`, `models.py`, `chat/state.py`, `InternalChatThread`, `Memory`, `upsert()`, `persist_sdb_artifact`, and assistant persistence/recovery symbols.
- Edges consulted: `tukulpan.py <--references-- agent_chat.py` and `chat/state.py --imports_from--> models.py` (EXTRACTED); the broader query connected `agent_chat.py -> models.py <- state.py` and `tukulpan.py` to the assistant persistence boundary.

## Deviations and Issues
- No design deviation. No migration, project registry, non-default project behavior, recovery/approval changes, API/SSE work, or separate adapter was added.
- Full suite exceeded the 300-second execution limit at 59%; focused and related suites passed.

# Apply Progress: Native SDB Seven-Phase Subgraph

## Work Unit
- Unit: WU-2 (PR2 of 5, stacked-to-main)
- Scope: Native execution phases only
- Status: Complete after bounded review correction; WU-3 through WU-5 remain pending
- Mode: Strict TDD
- Delivery: auto-chain; current slice is the autonomous native phase graph

## Completed Tasks
- [x] WU-1 RED — trigger scenarios and threat-matrix tests
- [x] WU-1 GREEN — validated state/config contract, fail-closed gate, normal-route preservation
- [x] WU-2 RED — phase ordering, frozen scope, distinct lookup errors, task output contract, bounds, and graph route tests
- [x] WU-2 GREEN — seven native phase nodes and fail-closed graph routing through terminal evidence

## TDD Cycle Evidence
| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| WU-1 RED | `tests/spec/test_sdb_trigger.py` | Unit | N/A (new) | Written; collection failed before gate existed | 7 passed | 7 trigger scenarios | Strict validation and bounded reason codes |
| WU-1 GREEN | `tests/spec/test_sdb_trigger.py` | Unit | 30 related tests passed | Existing RED retained | 7 passed | 7 scenarios | Related graph/config coverage |
| WU-2 RED | `tests/spec/test_sdb_phases.py` | Unit | Existing assistant suites not changed | Written; collection failed before phase nodes existed | 7 passed | ordered phases, freeze, both lookup errors, output, bounds, graph | Pure phase helpers and bounded constants |
| WU-2 GREEN | `tests/spec/test_sdb_phases.py` | Unit | Related suite passed | Existing RED retained | 7 passed | 7 scenarios | Preserved partial-state node convention |
| WU-2 correction | `tests/spec/test_sdb_phases.py` | Unit | Focused suite | Written; approval/completion assertions failed before correction | 17 passed | pending approval, conditional route, non-fabricated result/delivery | Fail closed until WU-3/WU-4 |

## Work Unit Evidence
- Focused: `DATABASE_URL='postgresql+psycopg://app:app@localhost:5435/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5435/lumat' uv run pytest tests/spec/test_sdb_phases.py tests/spec/test_sdb_trigger.py -q` — 17 passed.
- Related: same dedicated DB environment, `uv run pytest tests/spec/test_sdb_phases.py tests/spec/test_sdb_trigger.py tests/unit/test_assistant_planner.py tests/unit/test_assistant_config.py tests/unit/test_agent_registry.py tests/unit/test_assistant_harness.py -q` — 37 passed.
- Runtime harness: full required app environment plus dedicated DB URLs, `uv run python -c 'from app.chat.assistant.graph import build_assistant_graph; build_assistant_graph(); print("graph compiled")'` — graph compiled; no provider/runtime boundary is introduced by WU-2. The DB-only variant failed at import because required app secrets were absent.
- Full required suite: `DATABASE_URL='postgresql+psycopg://app:app@localhost:5435/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5435/lumat' uv run pytest tests/` — timed out after 300s at 72% progress, with no reported test failures before timeout.
- Rollback boundary: revert `tests/spec/test_sdb_phases.py`, `app/chat/assistant/nodes.py`, `app/chat/assistant/graph.py`, and the WU-2 state keys in `app/chat/assistant/state.py`; leave WU-1 contracts and later persistence/recovery/API work untouched.
- Correction focused: `sdb_approve` now returns pending, approval routing requires exact `approved`, execution returns `not-implemented`, and delivery degrades unless verification passes.

## Graph Check
- Graph stale but usable at graph commit `267821ee` (working HEAD `e97088ba`; user-provided comparison `c4d13da7` vs `267821ee`).
- Nodes consulted: `assistant/graph.py`, `nodes.py`, `AssistantState`, `build_assistant_graph()`, `sdb_approve`, `sdb_execute`, `sdb_verify`, `sdb_deliver`.
- Edges consulted: `assistant/graph.py -> nodes.py` (references); `sdb_approve -> sdb_execute` (conditional); `sdb_approve -> END` (pending fallback).

## Deviations and Issues
- No design deviation. WU-2 keeps phase state in `AssistantState`; durable Tukulpan artifacts, exact approval digests, recovery, and API/SSE remain deferred to WU-3 through WU-5.
- Full suite exceeded the 300-second execution limit at 72%; focused and related suites passed.
- Review correction resolves R3-001/R3-002 by making approval and completion fail closed; real retrieval, persistence, and digests remain deferred as designed.

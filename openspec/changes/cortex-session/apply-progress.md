# Apply Progress: cortex-session

## Slice
- Delivery: auto-chain, stacked-to-main
- Work unit: PR 2 — durable Cortex loop, report closure, and truthful SDB handoff
- Scope: Phase 2 tasks T2.1–T2.3 only
- Mode: Strict TDD
- Review boundary: 168 production/test additions plus 100 test additions, below the 400-line slice budget

## Completed Tasks
- [x] T1.1 — Added validated `CortexSession` state, recursive assistant-state merge, fail-closed validation, gate helper, and exact literal command parser.
- [x] T1.2 — Added validated Cortex classification/command declarations to the registry and exposed them through assistant runtime configuration.
- [x] T2.1 — Added five-class Cortex turn classification and valve, routed the valid active session after context/cost/planner preflight, and preserved inactive fail-closed routing.
- [x] T2.2 — Preserved nested assistant state, recorded keyed decisions, and added report closure as `upsert` followed by `set_mark(..., MemoryStatus.ARCHIVED)` with reload coverage.
- [x] T2.3 — Reused exact SDB approval digest/claim flow for the report-derived SPEC and retained the `not-implemented` task executor/checkpoint stub.

## TDD Cycle Evidence
| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| T1.1 | `tests/unit/test_cortex_session_foundation.py` | Unit | ✅ 41/41 | ✅ Import failure before helpers | ✅ 5 passed | ✅ Active/invalid, nested/leaf, command/free text cases | ✅ Clean minimal helpers |
| T1.2 | `tests/unit/test_agent_registry.py` | Unit | ✅ 15/15 | ✅ Missing attributes/declaration validation | ✅ 19 passed | ✅ Missing, invalid classes, invalid commands | ✅ Clean validation in existing loader |
| T2.1 | `tests/unit/test_cortex_session_loop.py` | Unit | ✅ 7 prior focused tests | ✅ Import failure before classifier/gate wiring | ✅ 22 focused tests | ✅ Five classes, active question, inactive route, graph ordering | ✅ Small routing/classification seams |
| T2.2 | `tests/integration/test_sdb_persistence.py` | Integration | ✅ 9 prior tests | ✅ Missing closure seam/import | ✅ 10 tests | ✅ Nested state and reload/archive path | ✅ Shared Tukulpan archive helper |
| T2.3 | `tests/spec/test_sdb_recovery.py`, `tests/unit/test_cortex_session_loop.py` | Unit/spec | ✅ Existing recovery/approval tests | ✅ Missing approved-plan helper | ✅ 40 focused spec/unit tests | ✅ Digest mutation, expiry, checkpoint resume, truthful stub | ✅ Reused existing approval/recovery seams |

## Work Unit Evidence
| Evidence | Result |
|---|---|
| Focused test command and exact result | `DATABASE_URL='postgresql+psycopg://app:app@localhost:5437/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5437/lumat' uv run pytest tests/unit/test_cortex_session_loop.py tests/unit/test_cortex_session_foundation.py tests/spec/test_sdb_trigger.py tests/spec/test_sdb_recovery.py tests/spec/test_sdb_phases.py` — 40 passed |
| Runtime harness command/scenario and exact result | Same environment with `uv run pytest tests/integration/test_assistant_harness_session.py tests/integration/test_sdb_persistence.py tests/integration/test_assistant_tools.py` — 19 passed; DB-backed close/reload/archive and approval stub covered |
| Rollback boundary | Revert the PR 2 commit(s); remove `app/chat/assistant/{graph,nodes,state}.py` Cortex loop changes, `app/services/{agent_chat,tukulpan}.py` handoff/closure changes, and the two Phase 2 test additions without touching Slice 1 or later API/SPA work |

## Verification Notes
- Graphify was consulted in degraded read-only mode. The worktree has no usable `graphify-out/graph.json`; refresh was explicitly blocked at stale graph `c4d13da7`.
- Prior and attempted graph nodes/edges: `NAVIGATION → PanelShell`, `PanelShell → AgentChat`, `submit_message → assistant graph`, `record_decision ↔ list_for_entity`, `chat.py → approval`, plus requested `cortex_session_gate`, `close_cortex_session`, and `set_mark` paths (queries failed because the graph artifact is absent).
- Threat matrix cases are N/A per design; no threat RED tests were added.
- `uv run pytest tests/unit` passed: 117 tests.
- No executor, table, migration, bus, or new dependency was added. SDB delivery remains explicitly `not-implemented`.
- Full required command `DATABASE_URL='postgresql+psycopg://app:app@localhost:5437/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5437/lumat' uv run pytest tests/` timed out at 300 seconds after reaching 45% and showed the known unrelated capability-count failure. Fail-fast replay confirmed `tests/functional/test_api_assistant_capabilities.py::test_admin_capabilities_reflect_real_tools_and_runtime_config`: expected 13, registry exposes 19. This slice did not modify that test or registry behavior.

## Remaining Tasks
- [ ] T3.1–T3.2 — Authenticated API and approval endpoints (PR 3)
- [ ] T4.1–T4.3 — SPA integration and final verification (PR 4)

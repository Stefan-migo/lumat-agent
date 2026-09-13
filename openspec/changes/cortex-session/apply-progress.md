# Apply Progress: cortex-session

## Slice
- Delivery: auto-chain, stacked-to-main
- Work unit: PR 4 — SPA planning surface and chat controls
- Scope: Phase 4 tasks T4.1–T4.3 only; cumulative through T4
- Mode: Strict TDD
- Review boundary: 180 authored additions plus 29 deletions across three reviewable commits, below the 400-line slice budget

## Completed Tasks
- [x] T1.1 — Added validated `CortexSession` state, recursive assistant-state merge, fail-closed validation, gate helper, and exact literal command parser.
- [x] T1.2 — Added validated Cortex classification/command declarations to the registry and exposed them through assistant runtime configuration.
- [x] T2.1 — Added five-class Cortex turn classification and valve, routed the valid active session after context/cost/planner preflight, and preserved inactive fail-closed routing.
- [x] T2.2 — Preserved nested assistant state, recorded keyed decisions, and added report closure as `upsert` followed by `set_mark(..., MemoryStatus.ARCHIVED)` with reload coverage.
- [x] T2.3 — Reused exact SDB approval digest/claim flow for the report-derived SPEC and retained the `not-implemented` task executor/checkpoint stub.
- [x] T3.1 — Added authenticated open/close/list/detail/reopen endpoints with the specified 400/401/403/404/409 matrix and JSON serializers.
- [x] T3.2 — Created report-derived SPEC approval messages and routed valid, expired, consumed, and changed-token cases through the existing approval endpoint.
- [x] T4.1 — Added typed planning lifecycle API helpers, admin navigation/routes, and list/detail/error/reopen SPA surface.
- [x] T4.2 — Added persistent Cortex indicator, open/close controls, exact `/planning` command handling, inert free-text behavior, and truthful approved-plan handoff display.
- [x] T4.3 — Completed frontend test/build gates and database-backed Cortex/API runtime verification.

## TDD Cycle Evidence
| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| T1.1 | `tests/unit/test_cortex_session_foundation.py` | Unit | ✅ 41/41 | ✅ Import failure before helpers | ✅ 5 passed | ✅ Active/invalid, nested/leaf, command/free text cases | ✅ Clean minimal helpers |
| T1.2 | `tests/unit/test_agent_registry.py` | Unit | ✅ 15/15 | ✅ Missing attributes/declaration validation | ✅ 19 passed | ✅ Missing, invalid classes, invalid commands | ✅ Clean validation in existing loader |
| T2.1 | `tests/unit/test_cortex_session_loop.py` | Unit | ✅ 7 prior focused tests | ✅ Import failure before classifier/gate wiring | ✅ 22 focused tests | ✅ Five classes, active question, inactive route, graph ordering | ✅ Small routing/classification seams |
| T2.2 | `tests/integration/test_sdb_persistence.py` | Integration | ✅ 9 prior tests | ✅ Missing closure seam/import | ✅ 10 tests | ✅ Nested state and reload/archive path | ✅ Shared Tukulpan archive helper |
| T2.3 | `tests/spec/test_sdb_recovery.py`, `tests/unit/test_cortex_session_loop.py` | Unit/spec | ✅ Existing recovery/approval tests | ✅ Missing approved-plan helper | ✅ 40 focused spec/unit tests | ✅ Digest mutation, expiry, checkpoint resume, truthful stub | ✅ Reused existing approval/recovery seams |
| T3.1 | `tests/functional/test_api_cortex_sessions.py` | Integration/TestClient | ✅ Existing chat/API suites | ✅ Routes returned 404 before implementation | ✅ 5 tests | ✅ Auth, lifecycle, unknown resources, conflicts | ✅ Thin route helpers and serializers |
| T3.2 | `tests/functional/test_api_cortex_sessions.py` | Integration/TestClient | ✅ Existing approval tests | ✅ Approval path absent from report lifecycle | ✅ 5 tests | ✅ Valid, expired, consumed, changed token | ✅ Reused `approve_plan` and exact digest validation |
| T4.1 | `web/src/api.test.ts`, `web/src/components/domain/panelRoutes.test.ts`, `web/src/components/pages/PlanningSessions.test.tsx` | Unit/component | ✅ 32 prior focused tests | ✅ Missing planning API/routes/page | ✅ 36 focused tests | ✅ list/detail, denied, navigation, lifecycle endpoints | ✅ Reused existing UI primitives |
| T4.2 | `web/src/components/pages/AgentChat.test.tsx` | Component | ✅ 13 prior tests | ✅ Missing Cortex indicator/control/command behavior | ✅ 14 tests in file; 523 full frontend tests | ✅ active/closed, command/free text, handoff | ✅ Minimal local state and existing API helpers |
| T4.3 | Full frontend/backend gates | Integration/build | ✅ Prior cumulative suites | ✅ N/A (verification task) | ✅ frontend/build and 36 targeted DB tests | ✅ backend lifecycle + SPA build | ✅ No unrelated backend changes |

## Work Unit Evidence
| Evidence | Result |
|---|---|
| Focused test command and exact result | `DATABASE_URL='postgresql+psycopg://app:app@localhost:5437/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5437/lumat' uv run pytest tests/unit/test_cortex_session_loop.py tests/unit/test_cortex_session_foundation.py tests/spec/test_sdb_trigger.py tests/spec/test_sdb_recovery.py tests/spec/test_sdb_phases.py` — 40 passed |
| Runtime harness command/scenario and exact result | Same environment with `uv run pytest tests/integration/test_assistant_harness_session.py tests/integration/test_sdb_persistence.py tests/integration/test_assistant_tools.py` — 19 passed; DB-backed close/reload/archive and approval stub covered |
| Rollback boundary | Revert the PR 2 commit(s); remove `app/chat/assistant/{graph,nodes,state}.py` Cortex loop changes, `app/services/{agent_chat,tukulpan}.py` handoff/closure changes, and the two Phase 2 test additions without touching Slice 1 or later API/SPA work |
| PR 3 focused test command and exact result | `DATABASE_URL='postgresql+psycopg://app:app@localhost:5437/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5437/lumat' uv run pytest tests/functional/test_api_cortex_sessions.py` — 5 passed |
| PR 3 runtime harness command and exact result | Same environment with `uv run pytest tests/integration/test_assistant_chat.py tests/integration/test_sdb_api.py tests/functional/test_api_cortex_sessions.py` — 26 passed; TestClient auth, lifecycle, report approval, and existing SDB approval paths exercised |
| PR 3 rollback boundary | Revert PR 3 commit; remove planning routes/serializers and `tests/functional/test_api_cortex_sessions.py` without touching the Phase 1–2 assistant loop or the future SPA |

## Final Slice Evidence
- PR 4 focused frontend: `cd web && npm test -- --run src/api.test.ts src/components/domain/panelRoutes.test.ts src/components/pages/PlanningSessions.test.tsx src/components/pages/AgentChat.test.tsx` — 4 files, 36 tests passed.
- PR 4 runtime harness: database-backed targeted command over Cortex lifecycle, assistant chat, SDB API, and persistence — 36 passed in 35.02s.
- Frontend full gate: `cd web && npm test` — 72 files, 523 tests passed. `cd web && npm run build` — exit 0.
- Required full backend command was attempted at 120s and 360s and timed out; the known unrelated capability-count failure remains outside this slice. Targeted database-backed verification passed.
- Rollback boundary: revert `62d0f513`, `8fb67ff4`, and `d0a27e42` to remove only the SPA planning API/types, navigation, browse page, and chat controls/tests.

## Verification Notes
- Graphify was consulted in degraded read-only mode. The worktree has no usable `graphify-out/graph.json`; refresh was explicitly blocked at stale graph `c4d13da7`.
- Prior and attempted graph nodes/edges: `NAVIGATION → PanelShell`, `PanelShell → AgentChat`, `submit_message → assistant graph`, `record_decision ↔ list_for_entity`, `chat.py → approval`, plus requested `cortex_session_gate`, `close_cortex_session`, and `set_mark` paths (queries failed because the graph artifact is absent).
- Threat matrix cases are N/A per design; no threat RED tests were added.
- Graphify remains degraded read-only at stale snapshot `c4d13da7`; consulted prior nodes/edges `NAVIGATION → PanelShell → AgentChat`, `submit_message → assistant graph`, `record_decision ↔ list_for_entity`, and `chat.py → approval`. Per-task query/path was attempted but no usable graph artifact exists in this worktree; no rebuild was performed by instruction.
- `uv run pytest tests/unit` passed: 117 tests.
- No executor, table, migration, bus, or new dependency was added. SDB delivery remains explicitly `not-implemented`.
- Full required command `DATABASE_URL='postgresql+psycopg://app:app@localhost:5437/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5437/lumat' uv run pytest tests/` timed out at 300 seconds after reaching 45% and showed the known unrelated capability-count failure. Fail-fast replay confirmed `tests/functional/test_api_assistant_capabilities.py::test_admin_capabilities_reflect_real_tools_and_runtime_config`: expected 13, registry exposes 19. This slice did not modify that test or registry behavior.

## Remaining Tasks
- [x] T3.1–T3.2 — Authenticated API and approval endpoints (PR 3)
- [x] T4.1–T4.3 — SPA integration and final verification (PR 4)

## Remediation Continuation — IAC-3 Failure Recovery
- Delivery: auto-chain, stacked-to-main; bounded production-fix slice
- Work unit: preserve active Cortex state on assistant stream/turn failure
- Production change: `app/services/agent_chat.py:453` now recursively merges the failed state instead of replacing `assistant_state`.
- Test change: `tests/integration/test_cortex_session_runtime.py` adds a PostgreSQL-backed failure/reload recovery test.

### TDD Cycle Evidence
| Scenario | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| IAC-3 | `tests/integration/test_cortex_session_runtime.py::test_cortex_failure_preserves_active_session_after_thread_reload` | PostgreSQL integration | ✅ 2 passed | ✅ Failed with `KeyError: 'cortex_session'` after reload against unfixed handler | ✅ Passed after merge fix | ✅ Preserved active status, slug, and decision keys | ✅ Minimal helper reuse; no production refactor |

### Work Unit Evidence
| Evidence | Result |
|---|---|
| Focused test command and exact result | `DATABASE_URL='postgresql+psycopg://app:app@localhost:5437/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5437/lumat' uv run pytest tests/integration/test_cortex_session_runtime.py tests/integration/test_sdb_persistence.py tests/unit/test_cortex_session_loop.py tests/unit/test_cortex_session_foundation.py` — **28 passed** |
| Runtime harness command/scenario and exact result | Same PostgreSQL-backed command exercised a raising `run_assistant`, failed message persistence, fresh `SessionLocal()` reload, and active Cortex recovery — **28 passed** |
| Rollback boundary | Revert the single remediation commit; removes only the IAC-3 test and the exception-path merge change in `app/services/agent_chat.py`, leaving prior Cortex slices intact |

### Remediation Result
- ✅ IAC-3 certified: failed turns retain `assistant_state["cortex_session"]` with `status == "active"`, while persisting `stage == "failed"` and `recoverable == True`; slug and decision keys survive reload.
- No other production defects were observed during this bounded remediation.

## Remediation Slice — Runtime Coverage
- Delivery: auto-chain, stacked-to-main; remediation test-only slice
- Work unit: runtime certification for CS-3 and HL-5
- Production code changed: none
- Graphify: degraded read-only; no graph artifact in this worktree. Consulted the stale base-map areas `submit_message → assistant graph`, `record_decision ↔ list_for_entity`, and `cortex_session_gate`; no rebuild performed.

### TDD Cycle Evidence
| Scenario | Test File | Layer | RED | GREEN | REFACTOR |
|---|---|---|---|---|---|
| CS-3 | `tests/integration/test_cortex_session_runtime.py::test_two_cortex_decisions_survive_thread_reload` | PostgreSQL integration | ✅ Written first; missing DB artifacts before coverage | ✅ Passed | ✅ Minimal DB setup and reload assertions |
| HL-5 | `tests/integration/test_cortex_session_runtime.py::test_missing_cortex_flag_reaches_gate_and_routes_normal` | Runtime gate | ✅ Written first; missing-flag path was not covered | ✅ Passed | ✅ Direct production gate invocation |
| IAC-3 | Temporary runtime test (not committed) | PostgreSQL integration | ✅ Written and executed | ❌ Failed: production exception handler drops `cortex_session` from persisted state | ➖ Blocked; production change forbidden |

### Work Unit Evidence
| Evidence | Result |
|---|---|
| Focused test command and exact result | `DATABASE_URL='postgresql+psycopg://app:app@localhost:5437/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5437/lumat' uv run pytest tests/integration/test_cortex_session_runtime.py tests/integration/test_sdb_persistence.py tests/integration/test_assistant_harness_compatibility.py tests/unit/test_cortex_session_loop.py tests/unit/test_cortex_session_foundation.py` — **36 passed** |
| Runtime harness command/scenario and exact result | Same focused command exercised PostgreSQL thread reload, Tukulpan decision rows, persisted assistant state, and the direct gate. The Cortex stream-failure recovery test failed with `KeyError: 'cortex_session'` after reload because `submit_message()` replaces state with only `stage/recoverable/events` in its exception path. |
| Rollback boundary | Revert commit `212c8ebd`; removes only `tests/integration/test_cortex_session_runtime.py`. No production behavior is touched. |

### Remediation Result
- ✅ CS-3 certified: two uniquely keyed decision memories and merged `cortex_session` state survive a fresh DB session reload.
- ✅ HL-5 certified: missing `cortex_session` reaches the runtime gate and routes normal with `invalid-session`.
- ❌ IAC-3 remains blocked by a real production defect: a failed Cortex turn persists `stage: failed` but discards the prior `cortex_session`, so the session is not recoverable/consistent after reload. Production fix is outside this test-only scope.
- Items 4–9 were not attempted after the IAC-3 production defect was confirmed; no additional production changes were made.

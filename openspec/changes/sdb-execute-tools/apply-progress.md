# Apply Progress: SDB Execute Tools

## Status

- Change: `sdb-execute-tools`
- Mode: Strict TDD
- Tasks: 6/6 complete
- Delivery: one PR, atomic work-unit commits; forecast remained below 400 lines

## Completed Tasks

- [x] T1.1 Typed `SDBTask`, exact `conversations.search` plan payload, and typed fixtures.
- [x] T1.2 Exact approval binding to the first typed task and recovery fixtures.
- [x] T2.1 Canonical gated runner through `execute_tool`, stop-on-first-failure, bounded failure, and audit.
- [x] T2.2 Result aggregation and bounded SDB persistence wiring.
- [x] T3.1 `consumed` routing and compatibility verify/deliver projections without a second runner.
- [x] T3.2 Truthful approval/resume delivery and typed API fixture.

## TDD Cycle Evidence

| Task | Test file | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|
| T1.1 | `tests/spec/test_sdb_phases.py` | N/A (changed assertions) | ✅ exit 1 before implementation | ✅ phase subset exit 0 | ✅ typed payload plus invalid-path coverage | ✅ clean |
| T1.2 | `tests/spec/test_sdb_recovery.py` | ✅ exit 0 | ✅ typed approval assertions | ✅ exit 0, 8 passed | ✅ mutated spec, expiry, replay/checkpoint cases | ✅ clean |
| T2.1 | `tests/spec/test_sdb_recovery.py` | ✅ 8 passed | ✅ runner expectation and stop-on-error test | ✅ exit 0, 8 passed | ✅ success and failure paths | ✅ clean |
| T2.2 | `tests/integration/test_sdb_persistence.py` | N/A (integration extension) | ✅ result assertion added | ⚠️ blocked by DB migration privilege | ✅ existing bounded/project cases retained | ✅ clean |
| T3.1 | `tests/spec/test_sdb_phases.py` | ✅ phase subset exit 0 | ✅ consumed route and truthful projection assertions | ✅ exit 0, 19 passed across phase/recovery | ✅ empty canonical result fails, complete result passes | ✅ clean |
| T3.2 | `tests/integration/test_sdb_api.py` | N/A (fixture extension) | ✅ typed fixture added | ⚠️ blocked by DB migration privilege | ✅ functional Cortex approval regression exit 0 | ✅ clean |

## Work Unit Evidence

| Work unit | Focused test command and result | Runtime harness | Rollback boundary |
|---|---|---|---|
| Typed plan and approval | `uv run pytest tests/spec/test_sdb_recovery.py` — exit 0, 8 passed | N/A: pure contracts; integration DB unavailable | Revert commit `daa0a2b4`; affects `state.py`, `nodes.py`, `approval.py`, and their spec fixtures only |
| Execute and persist bounded reads | `uv run pytest tests/spec/test_sdb_recovery.py` — exit 0, 8 passed | `uv run pytest tests/integration/test_sdb_persistence.py` — exit 1 at migration: `permission denied to alter role` | Revert commit `5c19a3be`; affects runner/persistence result behavior and SDB persistence tests |
| Consumed delivery and API evidence | `uv run pytest tests/spec/test_sdb_phases.py tests/spec/test_sdb_recovery.py` — exit 0, 19 passed | Functional Cortex approval: `uv run pytest tests/functional/test_api_cortex_sessions.py::test_report_approval_reuses_existing_endpoint` — exit 0, 1 passed; SDB API blocked by same DB privilege | Revert commit `08cef021` plus the uncommitted OpenSpec progress artifact; affects routing, delivery projections, and SDB API fixture |

## Graph Checks

Graph source commit: `daa86f71` (fresh at session start).

| Task | Query | Path / consulted nodes and edges |
|---|---|---|
| T1.1 | `graphify query "SDB typed plan state nodes execute_tool registry approval"` | `sdb_plan`/`plan()` → `execute_tool()`/registry; `assistant/state.py`, `assistant/nodes.py`, `assistant/approval.py`, `test_sdb_phases.py` |
| T1.2 | `graphify query "SDB approval exact typed arguments recovery checkpoints"` | `approve_plan()` → `_run_sdb_tasks()` → `resumable_sdb_tasks()`; `approval.py`, `recovery.py`, `test_sdb_recovery.py` |
| T2.1 | `graphify query "_run_sdb_tasks execute_tool whitelist cost capability audit stop failure"` | `_run_sdb_tasks()`, `execute_tool()`, `record_audit()`, `persist_sdb_state()`, registry, costs |
| T2.2 | Same execution graph query as T2.1, plus persistence edge | `_run_sdb_tasks()` → `persist_sdb_state()` → `persist_sdb_artifact()`; `agent_chat.py`, `tukulpan.py`, persistence tests |
| T3.1 | `graphify query "LangGraph SDB consumed approval compatibility verify deliver canonical runner"` | `canonical_sdb_digest()`, `validate_execution()`, `_run_sdb_tasks()`, `sdb_verify()`, `sdb_deliver()`, assistant graph |
| T3.2 | Same routing graph query as T3.1 | `approve_plan()`, `resume_thread()`, `_run_sdb_tasks()`, stream recovery, SDB API tests |

## Test Summary

- Spec focused tests: exit 0 (`19 passed`).
- Functional regression: exit 0 (`1 passed`).
- SDB persistence integration: exit 1 before tests because `db/migrate.sh` cannot alter role `app` (`psycopg.errors.InsufficientPrivilege`).
- SDB API integration: exit 1 before tests for the same database privilege blocker.
- Full `uv run pytest tests/`: exit 1; 367 passed, 431 integration errors from the same migration privilege blocker. The legacy Cortex handoff regression was fixed before this final run.

## Commits

1. `daa0a2b4 feat(sdb): add typed plan and exact approval`
2. `5c19a3be feat(sdb): execute and persist bounded reads`
3. `08cef021 feat(sdb): route consumed delivery and API evidence`
4. `19eed5c3 fix(sdb): type Cortex report handoff`

## Deviations and Blockers

- No intentional design deviation. Cortex report handoff was updated to use the same required typed read-task contract after the full-suite regression identified its legacy untyped task.
- Integration proof is blocked by the test database migration's missing `CREATEROLE`/role-admin privilege for `app`; no production workaround or fake GREEN was introduced.

## Focused Remediation: Verification Coverage

- [x] SDB-6 invalid task rejection: `test_invalid_sdb_task_is_rejected_before_approval_and_execution` covers unknown, write, and malformed tasks.
- [x] SDB-10 missing capability: `test_sdb_missing_project_capability_fails_closed_without_tool` proves bounded failed evidence and zero dispatch.
- [x] AT-6 deferred writes / IAC-8 read-only boundary: `test_sdb_write_task_is_rejected_with_no_side_effect` proves write classification rejects before dispatch.
- [x] AO-3 failed task stream: `test_failed_sdb_task_stream_is_error_and_never_completed` proves persisted task/status events remain failed.
- [x] Partial strengthening: timeout and exception truthfulness, per-attempt audit, cost-before-capability gate order, and stop-on-first-failure result aggregation are independently asserted.

### Remediation TDD Evidence

| Unit | RED | GREEN | REFACTOR |
|---|---|---|---|
| Missing scenario coverage | ✅ exit 1: cost gate order exposed capability-first behavior | ✅ focused SDB files exit 0, 42 passed | ✅ clean; tests remain in existing files |

### Remediation Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command | `DATABASE_URL="postgresql+psycopg://app:app@localhost:5432/lumat_test_sdb_execute" TEST_ADMIN_DB_URL="postgresql://lumat:lumat@localhost:5432/lumat_test_sdb_execute" .venv/bin/python -m pytest tests/spec/test_sdb_phases.py tests/spec/test_sdb_recovery.py tests/integration/test_sdb_persistence.py tests/integration/test_sdb_api.py -q` — exit 0, 42 passed |
| Runtime harness | Same command exercises the persisted API/SSE path against dedicated PostgreSQL; exit 0 |
| Rollback boundary | Revert the remediation commit; removes only the four scenario tests, partial-contract assertions, and the cost-before-capability guard in `app/services/agent_chat.py` |

### Remediation Graph Checks

| Area | Query / path | Consulted nodes and edges |
|---|---|---|
| Canonical execution gates | `graphify query "_run_sdb_tasks gate order whitelist pydantic read-only cost capability record_audit"` | `_run_sdb_tasks` → `execute_tool`, `record_audit()`, `registry.py`, `costs.py`, `projects.py` |
| Failed stream persistence | `graphify query "SDB API stream failed task events persistence"` | `stream_events()` → recovery/events, `agent_chat.py`, `test_sdb_api.py`, SDB execution tools community |

### Remediation Test Summary

- Focused remediation files: exit 0, 42 passed.
- Full required suite: exit 0; repository emitted the existing unawaited webhook coroutine and fastembed pooling warnings.
- Product code changed: `app/services/agent_chat.py` now checks the deterministic cost gate before non-default project capability, matching the specified whitelist → Pydantic → read-only → cost → capability order. No other production behavior changed.

### Remediation Commit

- Pending local commit: `test(sdb): cover rejected and failed execution paths`

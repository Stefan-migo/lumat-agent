# Tasks: Execute Native SDB Write Tools

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 650–900 lines |
| 400-line budget risk | High |
| Chained PRs recommended | Yes — WU1 → WU2 → WU3 |
| Suggested split | boundary → runner → verify |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|---|---|---|---|---|---|
| WU1 | Freeze bindings; enforce boundary | PR 1 | `pytest tests/unit/test_assistant_tools.py tests/spec/test_sdb_recovery.py` | N/A: contracts | Revert approval/state/registry |
| WU2 | Execute, persist, recover, propagate | PR 2 | `pytest tests/integration/test_sdb_persistence.py tests/spec/test_sdb_phases.py` | `DATABASE_URL=... pytest tests/integration/test_sdb_persistence.py` | Revert runner/recovery |
| WU3 | Verify; truthful outcomes | PR 3 | `pytest tests/integration/test_sdb_api.py tests/integration/test_assistant_chat.py` | `TEST_ADMIN_DB_URL=... pytest tests/integration/test_sdb_api.py` | Revert delivery/API |

## Phase 1: Approval and Typed Boundary (WU1)

- [x] 1.1 **RED→GREEN** (`tests/spec/test_sdb_recovery.py`, `tests/unit/test_assistant_tools.py`): prove payload/digest validation binds ordered `{task_id,tool,arguments}` hashes, decision/SPEC, expiry, consumption, substitution, reorder, replay, tamper (SDB-6/4, AO-2; D: Data Flow).
- [x] 1.2 **RED→GREEN** (`state.py`, `registry.py`): implement whitelist → Pydantic → write classification; pin RuleArgs ranges and Create `{slug,name,purpose}`, Rename `{project,name}`, Archive `{project}`, Merge `{source,target}`; reject malformed writes (SDB-6; AT-6/7; D: boundary).
- [x] 1.3 **RED→GREEN** (`registry.py`, `tests/unit/test_assistant_tools.py`): require consumed approval, forward to `execute_tool`, gate cost first, require create `{operation:"create",arguments:{slug,name,purpose},decision:{selected_slug|create_distinct:true}}`, preserve failure (AT-6/7, AT-5).

## Phase 2: Durable Execution and Recovery (WU2)

- [x] 2.1 **RED→GREEN** (`agent_chat.py`, tests): forward binding in `_run_sdb_tasks`; ordered writes, audit, first-failure stop; pin result `{task_id,order,tool,status,read_only,result,error,evidence}`, checkpoint `{run_id,sequence,order,task_id,tool,status,error,result_ref}`, audit/event (SDB-7, AO-3/4; D: runner).
- [x] 2.2 **RED→GREEN** (`agent_chat.py`, `projects.py`, tests/integration): propagate create capability to mutation/artifacts; enforce scope mismatch; retain `_has_active_run` rejection as failed evidence (SDB-10; AT-5; D: capability).
- [x] 2.3 **RED→GREEN** (`recovery.py`, tests): add `revalidate_sdb_resume(...)`; `recover_events` key `(run_id,sequence,type,task_id,tool)`, sort `(sequence,order,type,task_id)`; resume incomplete only, fail closed on mismatch (SDB-7/4, AO-4; D: recovery).
- [x] 2.4 **RED→GREEN** (`agent_chat.py`, `tukulpan.py`, tests): flush mutation, audit, checkpoint/result, thread, artifact in one transaction; inject persistence failure and prove rollback/no orphan (AO-4; D: transaction).

## Phase 3: Verification, Endpoint, and Delivery (WU3)

- [x] 3.1 **RED→GREEN** (`nodes.py`, tests): compare SPEC with persisted+new results by order, exact id/order/tool/status/mutation evidence; DELIVER passes only after comparison and commit (SDB-4, IAC-8; D: VERIFY).
- [x] 3.2 **RED→GREEN** (`agent_chat.py`, `deps.py`, `routes/chat.py`, tests/integration): truthful wording; uncertain commit returns 5xx/recovery, leaves pending/recoverable, never retries/succeeds; statuses: 201 create/send, 200 read/stream/approval, 409 invalid, 500 uncertain (AO-4, IAC-8).
- [x] 3.3 **RED→GREEN** (`graph.py`, tests): prove graph only projects `consumed` state and `_run_sdb_tasks` is the sole runner; prove ordered SSE/admin authorization and successful, failed, rollback, and recovery conversation outcomes without `not-implemented` (SDB-9, IAC-2/8, AO-3).

## Scope Checks

- Threat matrix: every row N/A; no threat task.
- Graph nodes/edges consulted: `issue_approval→canonical_sdb_digest`, `execute_tool→validate_execution`, `_run_sdb_tasks→persist_sdb_state/record_audit`, `recover_events`, `sdb_verify→sdb_deliver`, `get_db`; affected communities: Approval Helpers, Assistant Tool Registry, SDB Execution Tools, Assistant Run Recovery, Chat Graph Orchestration, Project Registry Service.
- Ponytail review: merged schema tests; omitted migrations, queues, ledgers, flags, second runner. net: -3.

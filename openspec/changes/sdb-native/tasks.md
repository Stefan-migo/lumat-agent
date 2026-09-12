# Tasks: Native SDB Seven-Phase Subgraph

## Graph Scope
Consulted nodes: `AssistantState`, `plan_llm`, `assistant/graph.py`, `nodes.py`, `agent_chat.py`, `recovery.py`, `approval.py`, `tukulpan.py`, `chat.py`, registry, and assistant test communities. Consulted edges: `graph.py -> nodes.py`, `agent_chat.py -> models.py <- state.py`, and approval/recovery seams (current graph `267821ee`).

## Suggested Work Units

| ID / likely PR | Deliverable; dependencies | Focused test command | Runtime harness | Rollback boundary |
|---|---|---|---|---|
| WU-1 / PR1 | Trigger/state/config contract; none | `pytest tests/spec/test_sdb_trigger.py` | `pytest tests/spec/test_sdb_trigger.py -q` | state, planner, registry, prompt files |
| WU-2 / PR2 | Seven-phase nodes and graph; WU-1 | `pytest tests/spec/test_sdb_phases.py` | `pytest tests/spec/test_sdb_phases.py -q` | assistant graph/node changes |
| WU-3 / PR3 | Typed artifacts and durable state; WU-2 | `pytest tests/integration/test_sdb_persistence.py` | PostgreSQL fixture command below | Tukulpan and agent-chat persistence |
| WU-4 / PR4 | Exact approval and resume; WU-3 | `pytest tests/spec/test_sdb_recovery.py` | `pytest tests/spec/test_sdb_recovery.py -q` | approval/recovery/claim changes |
| WU-5 / PR5 | Admin trigger, SSE, and acceptance coverage; WU-4 | `pytest tests/integration/test_sdb_api.py` | authenticated panel `TestClient` | chat route and SDB integration tests |

All units keep tests with code. Integration command: `DATABASE_URL='postgresql+psycopg://app:app@localhost:5435/lumat' TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:5435/lumat' uv run pytest tests/`.

## Phase 1: Trigger and Contracts

- [x] WU-1 RED: add `tests/spec/test_sdb_trigger.py` for classified, explicit-admin, malformed, conflicting, unauthorized, and ordinary-complex scenarios (HL-4, HL-2, AC-11; threat matrix cases).
- [x] WU-1 GREEN: extend `app/chat/assistant/state.py`, `agent/registry.yaml`, `agent/prompts/assistant_plan.md`, and `app/chat/assistant/graph.py` with validated SDB fields, fail-closed gate, and normal-route preservation.

## Phase 2: Native Execution

- [x] WU-2 RED: add `tests/spec/test_sdb_phases.py` for ordered phases, scope freeze, `scope-not-found` vs `not-exist`, one output contract, and bounded output (SDB-1/2/3).
- [x] WU-2 GREEN: implement phase nodes and routing in `app/chat/assistant/nodes.py` and `graph.py`; freeze SPEC before PLAN and return terminal evidence.

## Phase 3: Persistence and Recovery

- [ ] WU-3 RED: add `tests/integration/test_sdb_persistence.py` for PATTERN/SESSION/DISCOVERY rows, default/explicit `proyecto`, rejection before write, checkpoints, and bounded payloads (MEM-8/MEM-2, SDB-3).
- [ ] WU-3 GREEN: add parameterized artifact/checkpoint seams in `app/services/tukulpan.py`; persist phase/state/events in `app/services/agent_chat.py` without migrations.
- [ ] WU-4 RED: add `tests/spec/test_sdb_recovery.py` for mutated SPEC approval rejection, atomic active-run claims, and resume without repeating completed tasks (AO-2/3, SDB-4).
- [ ] WU-4 GREEN: extend `app/chat/assistant/approval.py`, `app/chat/assistant/recovery.py`, and `agent_chat.py` with canonical SDB digests, phase-aware claims, and checkpoint resume.

## Phase 4: API Verification

- [ ] WU-5 RED: add `tests/integration/test_sdb_api.py` for authenticated admin entry, operator stream rejection, ordered phase/evidence events, and SSE reconnect recovery (IAC-2/3, AO-1/3).
- [ ] WU-5 GREEN: wire explicit trigger, approval/resume, and serialized SDB state in `app/panel/api/routes/chat.py`; verify with the full PostgreSQL command above.

## Ponytail Review

`Section "Tasks": delete: speculative `app/chat/assistant/tools/registry.py` changes and `hybrid_search` registration. No new tool is required.`
`Section "Tasks": shrink: separate artifact adapters. One Tukulpan seam handles SPEC, STATE, and RESULT.`
`Section "Scope": native: reuse JSONB, event replay, approval digest, and atomic claims; no migration, runtime, registry, UI, or sub-agents.`
net: -3 items cut from plan.

## Review Workload Forecast

Chained PRs recommended: Yes
400-line budget risk: High
Estimated changed lines: 750
Decision needed before apply: No
Recommended PR slices: PR1 contracts → PR2 phases → PR3 persistence → PR4 recovery → PR5 API verification

# Tasks: SDB Execute Tools

## Review Workload Forecast

Estimated changed lines: 280–360
400-line budget risk: Low
Chained PRs recommended: No
Delivery strategy: auto-chain; chain strategy: stacked-to-main (not triggered)
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: stacked-to-main
400-line budget risk: Low

Below budget: keep one PR; use atomic commits and keep each RED/GREEN pair together.

## Phase 1: Typed Plan and Approval

- [x] T1.1 RED: add `tests/spec/test_sdb_phases.py` cases for `SDBTask`, exact `conversations.search` payload (`query` frozen request, `limit: 10`), unknown/write/invalid rejection; replace task-shape and `approved` assertions. Implement `app/chat/assistant/state.py`/`nodes.py`; GREEN: `pytest tests/spec/test_sdb_phases.py`. (SDB-6, AT-1; graph: `sdb_plan` → `execute_tool`/registry.)
- [x] T1.2 RED: add `tests/spec/test_sdb_recovery.py` cases proving typed tool/arguments bind approval and changed SPEC/plan/replay fail; replace `tool=None`/`arguments={}` fixtures. Implement `app/chat/assistant/approval.py`/`recovery.py`; GREEN: `pytest tests/spec/test_sdb_recovery.py`. (SDB-4, AO-2, SDB-9; graph: `approve_plan` → `_run_sdb_tasks` → `resumable_sdb_tasks`.)

## Phase 2: Canonical Durable Execution

- [x] T2.1 RED: add runner cases for whitelist→Pydantic→read-only→cost→capability gate order, success, timeout/exception/denial, stop-on-first-error, audit, and no mutation. Replace `not-implemented` runner assertions. Implement `_run_sdb_tasks` in `app/services/agent_chat.py` via existing `execute_tool`; GREEN: `pytest tests/spec/test_sdb_recovery.py`. (SDB-7, SDB-10, AT-6/7, AO-4; graph: `_run_sdb_tasks` → `execute_tool` → registry.)
- [x] T2.2 RED: extend `tests/integration/test_sdb_persistence.py` with bounded result/checkpoint, ordered phase/task/error events, project capability, and failed-result assertions. Implement result aggregation and `persist_sdb_state`/`persist_sdb_artifact` wiring; GREEN: `pytest tests/integration/test_sdb_persistence.py`. (SDB-7/10, AO-3/4; graph: `_run_sdb_tasks` → `persist_sdb_state` → `persist_sdb_artifact`.)

## Phase 3: Routing and API Delivery

- [x] T3.1 RED: add graph cases proving consumed approval routes canonically and no graph node runs a second executor; replace the intentional happy-path `degraded` assertion. Implement `graph.py` compatibility routing and truthful `nodes.py` verify/deliver projections; GREEN: phase tests. (SDB-9, IAC-2/8.)
- [x] T3.2 RED: update `tests/integration/test_sdb_api.py` fixture with typed tasks and add successful, failed, resume-complete, ordered-event, and unauthorized-stream cases; replace stub `not-implemented`/degraded delivery expectations. Implement `approve_plan`/`resume_thread` delivery in `agent_chat.py`; GREEN: `pytest tests/integration/test_sdb_api.py`. (AO-3/4, IAC-8.)

## Work-Unit Commit Plan

1. `feat(sdb): add typed plan and exact approval` — `state.py`, `nodes.py`, `approval.py`, `tests/spec/test_sdb_phases.py`, `tests/spec/test_sdb_recovery.py`.
2. `feat(sdb): execute and persist bounded reads` — `agent_chat.py`, `recovery.py`, `tukulpan.py`, `tests/spec/test_sdb_recovery.py`, `tests/integration/test_sdb_persistence.py`.
3. `feat(sdb): route consumed delivery and API evidence` — `graph.py`, `agent_chat.py`, `tests/spec/test_sdb_phases.py`, `tests/integration/test_sdb_api.py`.

Ponytail review: merged plan validation with its tests, merged persistence with aggregation, and deleted any registry/adapter/runtime/schema tasks; existing Pydantic, registry, audit, Tukulpan, and LangGraph seams are reused. Threat matrix executable-file/VCS/commit/push/PR rows are N/A; internal routing is covered by T3.1.

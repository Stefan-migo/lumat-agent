# Proposal: Make SDB Read Execution Real

## Intent
SDB stops at an approved plan: both paths emit `not-implemented`. Closing the chain honestly means executing the frozen read task through the assistant boundary, persisting bounded results/evidence/checkpoints, and delivering after verification.

## Scope
### In Scope
- Replace hard-coded `task-1` with typed `tool`/validated `arguments`.
- Make durable `_run_sdb_tasks` authoritative (HTTP approval bypasses LangGraph), reusing `execute_tool`, whitelist, cost gate, audit, evidence, Tukulpan, and atomic recovery.
- Align graph routing to canonical `consumed`; retain nodes as compatibility logic, not a second runner.
- Return complete results after resume before VERIFY.

### Out of Scope
- Writes: `automation.create_rule`, `project.create/rename/archive/merge`; separate SDD.
- Per-task approvals, multi-tool scheduling, background execution, idempotency, new tables/queues/runtimes/frameworks, generic frameworks, or adapters.

## Capabilities
### New Capabilities
- None.
### Modified Capabilities
- `sdb-native`: real bounded reads and complete recovery verification.
- `assistant-tools`: typed allow-listed SDB dispatch.
- `assistant-operations`, `internal-agent-chat`: durable evidence and truthful API delivery.

## Approach
Each task declares `tool: str` plus `arguments: dict`; validate the registry model before approval and execute only the frozen plan. Recommended mapping: `conversations.search`, `{"query": <frozen request>, "limit": 10}`—it searches panel history and is read-only; design may adjust this existing tool. Validate consumed approval against phase/spec/tasks; each `execute_tool` call enforces whitelist, typed arguments, and cost. Per-call approval is unnecessary: this slice has no mutations. Persist bounded result/checkpoint/evidence through `persist_sdb_state` and Tukulpan. Recovery skips successful checkpoints but aggregates persisted results so VERIFY sees every task.

## Affected Areas
`app/chat/assistant/{nodes.py,state.py,graph.py,approval.py,recovery.py,tools/registry.py,evidence.py}`; `app/services/{agent_chat.py,tukulpan.py}`; SDB/API/recovery tests.

## Risks and Open Questions
- Resolved: read-only first, tool default, complete resume results, writes deferred.
- Design must settle stop-on-error, blocked-cost behavior, and project-selection timing.
- Medium: search/checkpoint failure; persist bounded failure evidence and never mark failed work completed. Replace intentional RED contracts deliberately.

## Proposal Question Round
Confirm or correct: full frozen request as query; stop after one failed read; project fixed before approval?

## Ponytail YAGNI Check
The need is real; existing Pydantic, registry, state, JSONB, Tukulpan, approval, audit, and stdlib hashing suffice. Reject new executor, runtime, queue, scheduler, framework, or adapters.

## Graphify Feasibility and Delivery
`GRAPH_REPORT.md` is fresh at `daa86f71`. Validated communities: **SDB Execution Tools**, **Assistant Tool Registry/Approval**, **SDB Persistence/Recovery**, **Cost Gate Alerts**. Edges: `approve_plan → _run_sdb_tasks → resumable_sdb_tasks`; `execute_tool → registry`; `sdb_execute → sdb_verify → sdb_deliver`; `persist_sdb_state → persist_sdb_artifact`; `record_audit` hub. No SDB→tool edge exists, so wiring is consistent. Forecast: ~180–260 lines, under 400; auto-chain/stacked-to-main should not trigger.

## Rollback Plan
Revert code/spec deltas and restore the explicit degraded response; no schema rollback is needed.

## Success Criteria
- [ ] `pytest tests/` proves real reads, exact plan binding, gates, audit/evidence, and complete resume aggregation.
- [ ] VERIFY passes only on complete successes; DELIVER never claims `not-implemented`.

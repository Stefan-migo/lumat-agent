# Proposal: Execute Native SDB Write Tools

## Intent

Wire native SDB `EXECUTE` to registered write tools, closing the gap between an approved plan and mutations.

## Scope

### In Scope
- Enable `automation.create_rule`, `project.create`, `project.rename`, `project.archive`, and `project.merge` from validated tasks.
- Bind each `{task_id, tool, validated arguments}` to the canonical SDB digest; pass the consumed approval through `execute_tool` for every dispatch.
- Preserve whitelist → validation → write classification → cost gate → project capability, per-attempt audit, first-failure stop, checkpoint recovery, `consumed` routing, and project decisions.
- Use the caller transaction for mutation, audit, checkpoint/result, thread state, and artifact persistence; roll back failures and fail closed on unknown commit outcomes.

### Out of Scope
- External idempotency keys, mutation ledgers, queues, new tables, or a second runner.
- A new approval protocol, one approval per task, or exactly-once guarantees for future external side effects.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `sdb-native`: permit bounded write tasks and define approval, transaction, failure, and recovery behavior.
- `assistant-tools`: change AT-6 to approved write dispatch while retaining AT-1–AT-5 and AT-7 boundaries.
- `assistant-operations`: extend approval, audit, result, and recovery guarantees to mutations.
- `internal-agent-chat`: deliver truthful verified SDB outcomes through the canonical route.

## Approach

Retain `app.services.agent_chat._run_sdb_tasks` as the only runner. Freeze bindings in the existing approval payload and validate each against the canonical digest before dispatch. Remove read-only rejection without bypassing `execute_tool` or domain services. Checkpoints/results determine recovery within the transaction boundary.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/agent_chat.py` | Modified | Write dispatch, persistence, recovery |
| `app/chat/assistant/{state,approval,nodes,graph,recovery}.py` | Modified | Validation, approval, routing, recovery |
| `app/chat/assistant/tools/registry.py` | Modified | Write approval boundary |
| `openspec/specs/{sdb-native,assistant-tools,assistant-operations,internal-agent-chat}/spec.md` | Modified | Capability deltas |

## Risks & Tradeoffs

| Risk | Mitigation |
|------|------------|
| Task substitution or reordered writes | Digest-bound identity, tool, arguments, and order validation |
| Namespace/service validation failures | Preserve domain locks, active-run checks, decisions, and failed evidence |
| Persistence failure after mutation | Roll back the caller transaction; no external exactly-once claim |

## Graph Nodes Validated

Validated nodes: `_run_sdb_tasks`, `execute_tool()`, `validate_execution()`, `issue_approval()`, `canonical_sdb_digest()`, `SDB Execution Tools`, `Assistant Tool Approval`, `Assistant Tool Registry`, `Assistant Run Recovery`, `agent_chat.py`, `assistant/graph.py`. Edges: `_run_sdb_tasks → execute_tool()`; `execute_tool() → validate_execution()`; `agent_chat.py → assistant/graph.py`.

## Rollback Plan

Revert the write deltas and capability updates. Read-only execution remains available; no schema or infrastructure rollback is required.

## Success Criteria

- [ ] Each five-tool write executes only from an unchanged, consumed, per-task-bound approval.
- [ ] Audit, checkpoint, result, recovery, and `consumed` routing remain durable and truthful.
- [ ] Persistence failure leaves no committed mutation without its checkpoint.

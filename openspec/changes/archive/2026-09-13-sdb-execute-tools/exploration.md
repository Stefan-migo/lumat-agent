## Exploration: sdb-execute-tools

### Current State
The native branch is structurally present as `CLARIFY → SPEC → PLAN → APPROVE → EXECUTE → VERIFY → DELIVER`, but execution is not real. `sdb_plan` creates one hard-coded `task-1` whose output is a service-history summary, while `sdb_execute` emits `not-implemented` for every task. `sdb_verify` therefore fails and `sdb_deliver` correctly emits degraded evidence.

In the HTTP approval path, `agent_chat.approve_plan` consumes the approval and atomically claims the run, then bypasses the LangGraph SDB nodes and calls `_run_sdb_tasks`. That runner persists a `not-implemented` checkpoint/result and the caller hard-codes a degraded response. The graph's `_after_sdb_approve` expects `approved`, whereas the durable API approval state is `consumed`; the API path is consequently the effective SDB execution route today.

“Real tools” means the existing typed registry and domain-service seam, not panel HTTP routes: `execute_tool(session, name, arguments, approval, whitelist, cost_allowed)`. The current assistant whitelist contains 18 registered tools: 12 read-only domain/web tools (`customers.*`, `conversations.*`, `appointments.*`, `cases.list`, `kb.retrieve`, `memory.*`, `dashboard.summary`, `web.search`) plus `project.list` and `project.find`, and six writes (`automation.create_rule`, `project.create`, `project.rename`, `project.archive`, `project.merge`). `ToolDefinition.read_only` is the authoritative classification. There is no dedicated service-history tool, so mapping the existing task wording to a concrete tool is a product/contract decision, not an implementation detail.

### Affected Areas
- `app/chat/assistant/nodes.py` — SDB stub nodes and the already-real normal `execute` path; SDB task shape currently has no tool/arguments contract.
- `app/services/agent_chat.py` — effective approval, atomic claim, task runner, resume path, SDB event/response persistence, and the explicit `not-implemented` contract.
- `app/chat/assistant/tools/registry.py` — typed registry, read/write classification, whitelist enforcement, argument validation, project approval handling, and domain-service dispatch.
- `app/chat/assistant/approval.py` — SHA-256 exact-payload validation and 15-minute TTL; current SDB approval binds phase/spec/tasks but its tool payload is `tool=None`.
- `app/chat/assistant/recovery.py` — atomic run claim and completed-checkpoint filtering; result aggregation across resumed tasks is not supplied by the current runner.
- `app/chat/assistant/graph.py` — SDB edges and the status mismatch between graph approval routing and durable API consumption.
- `app/chat/assistant/state.py` — typed SDB fields, with no typed per-task tool invocation fields.
- `app/services/tukulpan.py` — bounded typed `spec/state/result` artifacts, panel/thread identity, and authorized `proyecto` writes.
- `app/services/projects.py` — active project capability and project-specific selection/mutation approvals.
- `agent/registry.yaml` — all currently available assistant tools are allow-listed; this is configuration, not proof that every SDB task should use every tool.
- `openspec/specs/sdb-native/spec.md` — requires real task results, exact approval, checkpoints, recovery, verification, and project propagation.
- `openspec/specs/assistant-tools/spec.md` and `openspec/specs/assistant-operations/spec.md` — existing tool and approval contracts, including SDB writes.
- `tests/spec/test_sdb_phases.py`, `tests/spec/test_sdb_recovery.py`, `tests/integration/test_sdb_api.py` — current truthfulness, approval, recovery, event, and API contracts; the `not-implemented` assertions must be intentionally replaced, not silently broken.

### Approaches
1. **Reuse the existing executor for a bounded read-only SDB task** — make each planned task identify one registered tool and validated arguments, then invoke `execute_tool` with the assistant whitelist and cost decision; persist the bounded result/evidence and verify all task outputs.
   - Pros: smallest honest slice; one execution seam; inherits typed validation, allow-listing, bounded plain results, and domain-service isolation; no new runtime or dependency.
   - Cons: requires choosing a concrete service-history mapping; does not prove write approval semantics yet; web/embedding-backed reads may have operational failures.
   - Effort: Medium

2. **Reuse the executor for read and side-effecting tasks under one exact SDB approval** — bind every task's tool name and serialized arguments into the canonical SDB approval, validate the whole plan before each call, and dispatch writes only after the consumed approval is still valid.
   - Pros: closes the full intent, including automation/project mutations; preserves the existing approval, whitelist, audit, evidence, and project capability seams.
   - Cons: larger approval contract change; must define whether approval is consumed once per run or per task; partial writes and retries require explicit idempotency semantics.
   - Effort: High

3. **Create a separate SDB executor/runtime** — implement task-specific service calls outside `execute_tool`.
   - Pros: apparently independent SDB behavior.
   - Cons: duplicates validation, whitelist, approval, evidence, audit, and error handling; creates two security seams and conflicts with SDB-3's no-separate-runtime constraint.
   - Effort: High

### Recommendation
Choose Approach 1 as the minimum honest first slice: replace the stub with one explicitly declared, bounded, read-only task invocation through `execute_tool`, and persist real result/checkpoint/evidence data so VERIFY can pass only on the returned output. The proposal must name the tool and argument mapping for “service history”; do not infer a new tool or silently broaden the task.

Treat side-effecting tools as a second, explicit slice unless the product requires them immediately. If included, reuse `execute_tool`, but extend the canonical SDB payload so each task's tool and exact parsed arguments are SHA-256-bound to the consumed approval. Never call a write merely because the outer SDB approval is `consumed`; the per-call payload must match, remain within TTL, remain allow-listed, and carry the authorized project capability where applicable. Keep audit and evidence at the existing execution boundary rather than adding SDB-specific copies.

Ponytail review: delete any proposal for a new executor, queue, table, generic task framework, speculative tool adapter, or broad multi-task scheduler. Shrink the first change to one bounded task, one existing tool, existing memory artifacts, existing atomic claim, and focused contract tests. Optional later work includes multiple tools/tasks, write tools, richer entity resolution, background execution, and new idempotency keys.

### Approval Boundary
The approval must cover the canonical phase/spec/task plan and, for any tool call, the exact tool plus serialized arguments. Existing `issue_approval` provides a random token, token digest, argument digest, SDB digest, optional spec digest, project digest, and a 15-minute expiry. Existing `validate_execution` checks consumed status, expiry, argument digest, SDB digest/spec digest, and project digest. The current SDB plan sets `tool=None` and `{}` arguments, so it cannot authorize a side-effecting tool call without changing the bound payload or issuing a separately bound approval.

No domain handler, project selection/mutation, automation write, or retry may run before whitelist/argument validation, cost permission, exact approval validation, and (for non-default projects) an active `_ProjectAuthorization`. Failed validation must produce rejection evidence/audit and no mutation. Approval consumption must remain atomic through `claim_execution`; a retry must not repeat a completed checkpoint.

### Risks
- The existing `not-implemented` assertions in `test_sdb_phases.py` and `test_sdb_recovery.py` are intentional contracts and need a deliberate red-to-green change.
- `resumable_sdb_tasks` skips completed tasks, but the current runner returns only newly pending results; VERIFY must see the complete task result set after resume, not just the latest batch.
- A failure or timeout after a domain mutation but before checkpoint persistence can duplicate a write; read-only-first avoids data mutation but does not remove external search or embedding failure modes.
- The current sequence numbering is derived from checkpoint count and must remain monotonic across partial execution and recovery.
- `execute_tool` returns bounded plain results but wraps unexpected handler exceptions as `ToolExecutionError`; SDB must persist a failed bounded result and never convert it to `completed`.
- `cost_allowed` is enforced by `execute_tool`, but the current SDB runner bypasses it; SDB execution must explicitly carry the existing cost decision and define behavior when the cost gate is blocked.
- Project artifacts require `scope="panel"`, `thread:{id}`, run-specific keys, and the authorized project capability; caller-supplied project strings must not override the capability seam.
- The graph approval route checks `status == "approved"`, while durable approval uses `pending → consumed`; proposal/design must clarify whether the graph route is dead code, a compatibility route, or needs alignment.

### Open Questions
- Which existing read-only tool and exact arguments represent “review the requested service history” (`conversations.search`, `cases.list`, `appointments.list`, or another bounded operation)?
- Is the first release intentionally read-only, or must it execute `automation.create_rule` and/or project lifecycle writes now?
- For side effects, should one SDB approval authorize the whole frozen task plan, or should each task/tool call require a separately consumed approval?
- What is the required idempotency behavior when a tool succeeds but its checkpoint write fails?
- Should a failed task stop the run immediately, or may later independent tasks execute while VERIFY remains failed?
- Must SDB execution honor a blocked cost gate by refusing all tools, or only tools with paid/external work?
- Is `proyecto` selected before SDB APPROVE and included in the frozen scope, or is project selection itself a task covered by the same approval?

### Graph Check Record
- Graph report: `graphify-out/GRAPH_REPORT.md` — 5,619 nodes, 11,944 edges; fresh at commit `daa86f71`; relevant communities include **SDB Execution Tools**, **Assistant Tool Registry**, **Assistant Tool Approval**, **Approval Helpers**, **SDB Native Spec**, **SDB Persistence Tests**, **Projects Namespace Design**, and **Cost Gate Alerts**. God node consulted: `record_audit()`.
- Query consulted: `graphify query "SDB pipeline execute tools approval evidence audit projects"` — identified `sdb_execute()`, `execute()`, `execute_tool()`, `issue_approval()`, `record_audit()`, `registry.py`, `approval.py`, SDB tests, and project-related nodes.
- Path consulted: `sdb_execute()` ↔ `execute()` — `assistant/graph.py` import relationship; `execute_tool()` ↔ `record_audit()` — both converge through `nodes.py` imports. Directed paths from the SDB stub to the normal executor and from SDB planning to persistence were absent, confirming SDB currently does not reuse the normal execution path automatically.

### Ready for Proposal
Yes, after the product owner answers the tool mapping and read-only-versus-write fork. The proposal should select one bounded existing read tool first, explicitly replace the `not-implemented` contracts, and preserve the existing approval, whitelist, evidence, audit, persistence, recovery, cost, and project seams.

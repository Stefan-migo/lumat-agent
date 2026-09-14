## Exploration: sdb-execute-writes

### Current State

The native path is `CLARIFY → SPEC → PLAN → APPROVE → EXECUTE → VERIFY → DELIVER`, but the graph-side SDB nodes only project state. The durable `app.services.agent_chat._run_sdb_tasks` route is the real runner.

- `sdb_clarify` freezes `proyecto` through the service-issued project capability.
- `sdb_spec` freezes the scope and computes `spec.sha256`.
- `sdb_plan` currently creates one typed `conversations.search` task.
- `submit_message` converts the graph result into `thread.current_plan`, creates the approval, and persists the initial SDB artifacts.
- `approve_plan` atomically changes approval status to `consumed`, claims `execution_status`, then calls `_run_sdb_tasks`; `resume_thread` uses the same runner after an atomic claim.
- `_run_sdb_tasks` currently applies whitelist → argument validation → read-only classification → cost gate → project capability, calls `execute_tool` at `agent_chat.py:106`, audits every attempt, and persists a checkpoint/result/event at `agent_chat.py:126`. It stops on the first failure and aggregates persisted results before `_sdb_delivery` invokes `sdb_verify` and `sdb_deliver`.
- The read-only seam is explicit at `agent_chat.py:98` (`if not definition.read_only`) and again in `SDBTask.validate_read_tool` at `state.py:102-110`. `execute_tool` itself already supports writes, but requires a consumed exact approval at `registry.py:305-308`.
- Approval currently stores one top-level tool/arguments pair, while `canonical_sdb_digest` covers the complete phase/spec/tasks payload. `_bound_tool_arguments` selects only the first SDB task. Thus the current approval is sufficient for the one-task read slice, but is not yet a complete per-task write binding.

The graph consultation found the following relevant structure: `execute_tool()` calls `validate_execution()`; `issue_approval()` is imported by `agent_chat.py`; `assistant/graph.py` references `agent_chat.py`; and the `SDB Execution Tools`, `Assistant Tool Approval`, `SDB Persistence Tests`, and `Assistant Tool Registry` communities contain the affected seams. The directed paths from the named concepts were absent/ambiguous, so the equivalent undirected paths were used.

### Affected Areas

- `app/services/agent_chat.py` — canonical SDB runner, approval handoff, persistence ordering, and recovery entry points.
- `app/chat/assistant/state.py` — currently rejects every write task in the typed SDB validator.
- `app/chat/assistant/approval.py` — currently binds the whole SDB digest but only the first task's tool/arguments pair.
- `app/chat/assistant/tools/registry.py` — existing write handlers, exact argument validation, and consumed-approval enforcement.
- `app/chat/assistant/nodes.py` — compatibility graph nodes and the current read-oriented delivery wording.
- `app/chat/assistant/graph.py` — phase routing; must continue reconciling to canonical `consumed` approval state.
- `app/chat/assistant/recovery.py` — checkpoint-based resume currently assumes successful persistence means safe non-repetition.
- `openspec/specs/sdb-native/spec.md` — SDB-6/SDB-7/SDB-9/SDB-10 read-only wording and execution contract require a write delta.
- `openspec/specs/assistant-tools/spec.md` — AT-2/AT-4/AT-5 already define write tools and exact approval boundaries; AT-6 explicitly defers writes and needs a delta.
- `openspec/specs/assistant-operations/spec.md` — AO-2/AO-3/AO-4 define approval, audit, event, and recovery guarantees.
- `openspec/specs/internal-agent-chat/spec.md` — IAC-2/IAC-8 define the canonical durable route and honest SDB delivery.

### Existing Write Registry

These are the write tools actually registered today (`registry.py:251-257`):

1. `automation.create_rule` — `RuleArgs`: required `name` (1–255), `event_type` (string), `channel` (string), `template_event` (string); optional `conditions` (object, default `{}`) and `cooldown_seconds` (integer, 0–2,592,000). The handler calls `automation.create_rule(..., actor="assistant", executor_origin=True)`.
2. `project.create` — `ProjectCreateArgs`: required `slug` (1–100), `name` (1–200), `purpose` (1–500). The handler calls `projects.create` and supports the existing approved project decision.
3. `project.rename` — `ProjectRenameArgs`: required `project` (1–100) and `name` (1–200). The handler calls `projects.rename`.
4. `project.archive` — `ProjectArchiveArgs`: required `project` (1–100). The handler calls `projects.archive`.
5. `project.merge` — `ProjectMergeArgs`: required `source` and `target` (each 1–100). The handler calls `projects.merge`.

All five are `read_only=False`. The service layer flushes but does not commit: automation creates/audits a rule in the caller transaction; project lifecycle methods lock rows, enforce active-run and namespace rules, audit, and flush. This makes a single caller transaction the existing atomicity seam.

### Approaches

1. **One approval for the frozen whole plan** — keep one approval token and make its canonical payload cover the complete frozen SDB phase/spec/task list, with explicit task tool/argument digests (or an equivalent task lookup) validated before each dispatch.
   - Pros: matches the existing `sdb_sha256` model and SDB-4/AO-2 whole-plan language; one approval UI/API operation; preserves the single canonical runner and ordered task execution.
   - Cons: approval is consumed once, so the runner must prevent task substitution and must not treat a consumed token as permission for arbitrary task payloads; recovery must reuse the exact frozen plan, not reconstruct it.
   - Effort: Medium.

2. **One approval per task** — issue and consume a separate exact approval for every frozen task, then execute tasks in order.
   - Pros: task-level replay/consumption is explicit; a recovered run can identify the precise remaining authorization.
   - Cons: requires changing `issue_approval`, persistence, approval API/UI, event semantics, and likely the current single `approval` state shape; multiple writes create a cumbersome approval sequence and introduce more partial-plan states.
   - Effort: High.

3. **One plan approval plus an internal per-task execution ledger** — consume one plan approval, derive deterministic task bindings from the approved canonical payload, and persist each task's binding/status with its checkpoint.
   - Pros: retains one human approval while making task identity and recovery explicit; fits existing checkpoints and avoids a new runner or queue.
   - Cons: adds a small amount of binding/ledger logic; it still cannot make a non-idempotent external side effect safe if transaction outcome is unknown.
   - Effort: Medium.

### Recommendation

Use approach 3, implemented as the minimum form of approach 1: one approval covers the frozen plan, but approval validation and execution must bind each task's exact `{task_id, tool, validated arguments}` to the canonical SDB digest. Pass the consumed approval into `execute_tool` for every write task, rather than bypassing the existing boundary. Keep whitelist → Pydantic validation → write classification → cost gate → project capability, audit each attempt, and stop at the first failure.

Do not add a second runner, queue, table, or alternate approval protocol. Update the approval payload so it no longer relies on `_bound_tool_arguments` selecting only task 1. Preserve one approval consumption at `approve_plan`; task checkpoints and result keys provide the durable execution ledger. The project decision payload remains part of the existing exact project approval rules for `project.find`/`project.create`.

For mutate-then-persist failure, use the existing caller-owned database transaction as the first-line guarantee: service mutation, audit, SDB checkpoint/result, thread state, and memory artifact are flushed in the same transaction and committed together. If persistence raises, roll back the transaction so a mutation is not committed without its checkpoint. On retry, consult committed checkpoints/results before dispatch. Do not claim exactly-once behavior beyond this DB boundary; adding idempotency keys or a new mutation ledger would be a separate change. If a commit outcome is genuinely unknown, fail closed and require recovery rather than blindly retrying a mutation.

### Risks

- A consumed plan approval must not authorize changed task arguments, reordered tasks, or a different task ID; digest validation must cover all of them.
- `project.rename`, `project.archive`, and `project.merge` reject active SDB runs and use row locks; a plan that mutates its own active namespace can fail by design and must remain a truthful failed attempt.
- `project.create` may require the existing explicit semantic decision; missing or changed decision data must not create a namespace.
- `automation.create_rule` has service-level event/channel validation beyond the Pydantic shape; service errors must remain failed evidence.
- A failed checkpoint persistence after a database flush is safe only if the outer transaction is rolled back. Tests must force persistence failure and verify no committed mutation.
- Existing specs and delivery text say “read”; the change must update only the SDB write delta while preserving read behavior and `consumed` routing.
- No external side effects are present in these five handlers; exactly-once claims for future external tools remain out of scope.

### Test Surfaces

- Unit: registry classification and all five argument schemas; each write rejects missing/expired/tampered/unconsumed approval before its service handler; `execute_tool` forwards the consumed approval and whitelist/cost decision.
- Unit: approval canonicalization binds every task, rejects changed tool/arguments/task ID/order/spec, and accepts the unchanged frozen plan; replay and expiry remain rejected.
- Unit: `SDBTask` accepts the intended write tasks only after whitelist and argument validation, while unknown tools and malformed writes remain pre-approval failures.
- Unit: `_run_sdb_tasks` executes writes in order, records `record_audit` for each attempt, persists result/checkpoint/event, aggregates prior results, and stops after the first failure.
- Unit: cost blocking and missing project capability prevent all writes before `execute_tool`; authorized project capabilities reach both execution and artifact persistence.
- Integration: admin approval through the panel API creates the frozen SDB plan, consumes the canonical approval, executes the selected write, and exposes ordered phase/task/evidence/status events without `not-implemented`.
- Integration: automation creation persists the rule and its domain audit in the same transaction; project lifecycle operations persist their service audit and obey existing locking/active-run rules.
- Integration: interruption after a completed task resumes only incomplete tasks and preserves aggregate verification input; a retry after a failed task does not execute subsequent tasks.
- Integration: injected checkpoint/artifact persistence failure rolls back the same-transaction mutation (or leaves a clearly recoverable, non-completed outcome), proving no silent double-write path.
- Regression: existing read-only SDB, normal assistant, operator authorization, SSE ordering, project decision, and cost-gate suites remain green.

### Ready for Proposal

Yes. The proposal should explicitly choose one human approval for the frozen plan with per-task exact bindings, retain `_run_sdb_tasks` as the only runner, and define the transaction rollback behavior as the idempotency boundary. The write slice should start with the five registry tools above, without adding external idempotency infrastructure.

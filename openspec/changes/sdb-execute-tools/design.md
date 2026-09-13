# Design: SDB Execute Tools

## Technical Approach

Keep `_run_sdb_tasks` as the only durable runner. PLAN emits a typed `conversations.search` task; APPROVE freezes its canonical SDB payload; EXECUTE calls `execute_tool`, persists bounded outcomes, and feeds complete results to VERIFY. LangGraph SDB nodes remain projections, never another executor. Graph paths: `approve_plan → _run_sdb_tasks → resumable_sdb_tasks` and `_run_sdb_tasks → persist_sdb_state → persist_sdb_artifact`.

Existing history-aware `AssistantState` assembly, Cortex merge under `assistant_state["cortex_session"]`, and the deterministic pre-planning cost gate are preserved; only canonical durable SDB execution and `consumed` reconciliation are new here.

## Architecture Decisions

| Decision | Choice | Rejected | Rationale |
|---|---|---|---|
| Task contract | Add `SDBTask` in `app/chat/assistant/state.py`: `id`, `scope`, `summary`, `verifiable_output`, `tool`, `arguments`; `extra="forbid"`. `sdb_plan` validates it and uses `conversations.search` with `{"query": frozen request, "limit": 10}`. | Optional tool/empty arguments and hardcoded `task-1` | Exact typed data is required before approval and binds the graph node to the registry node `execute_tool`. |
| Durable gates | For every task: whitelist → Pydantic arguments → registry `read_only` classification → cost → project capability; then call `execute_tool(session, tool, arguments, whitelist=..., cost_allowed=...)` and map by `task_id`. | Direct handlers or whitelist alone | Classification prevents allow-listed writes entering SDB. |
| Failure policy | Stop on the first failed, denied, timed-out, or exceptioning task; persist it as `failed`, audit it, leave later tasks incomplete, and return all known results. VERIFY passes only when every frozen task is completed. | Continue independent tasks | One truthful terminal outcome is simpler, avoids partial claims, and makes recovery deterministic. |
| Cost blocking | Refuse every SDB task when the cost gate blocks, including reads/external tools. | Permit free reads selectively | SDB has one explicit execution budget and no reliable per-tool cost taxonomy; refusal is fail-closed. |
| Project timing | `proyecto` is fixed in CLARIFY from the service-issued capability and included in frozen scope before APPROVE; it cannot be a task. `_thread_project_authorization` revalidates the same active capability at EXECUTE/persistence. | Selecting a project during execution | Matches `_project_slug` and the existing project authorization seam; approval covers the complete namespace. |
| Approval/recovery | `issue_approval` stores serialized task `tool`/`arguments` in `arguments_sha256` and the full SDB phase/spec/tasks in `sdb_sha256`; `approve_plan` calls `validate_approval` before its atomic pending→`consumed` update. Execution calls `validate_execution` against the persisted plan, rejecting changed SPEC/plan, expiry, or replay. Store bounded results in JSONB alongside checkpoints and merge by task id; `_after_sdb_approve` accepts `consumed`, while compatibility nodes consume supplied results only. | New approval mechanism, `approved` status, or reconstructing only new results | Existing approval.py digests and atomic SQL already provide the trust boundary; VERIFY needs persisted plus new results. |

## Data Flow

`CLARIFY(scope+project) → SPEC(digest) → PLAN(SDBTask) → APPROVE(consumed) → _run_sdb_tasks → persist_sdb_state/Tukulpan → VERIFY(all results) → DELIVER`

No mutation is possible: plan validation rejects unknown tools and any `ToolDefinition.read_only == False`; execution repeats classification immediately before `execute_tool`, whose whitelist and typed validation remain authoritative.

`persist_sdb_state` appends ordered bounded events to `assistant_state["events"]` and writes artifacts through `persist_sdb_artifact` with `scope="panel"`, `entity_id=f"thread:{thread.id}"`, `proyecto` (capability slug or `default`), and keys `sdb:{run_id}:state:{sequence}` / `sdb:{run_id}:result:{task_id}`. EXECUTE emits phase, task, evidence, delivery, and error events with `run_id`, `task_id`, and completed/failed status, and calls `record_audit` for every attempt: success, failure, timeout, cost block, or capability denial. Existing `stream_events → recover_events` plus `require_admin_json` provide ordered admin-only replay; unauthorized streams return 403 and streaming reads do not hold an unbounded transaction. Missing non-default capability fails before `execute_tool` and persists bounded rejection evidence through this seam.

## File Changes

| File | Action | Description |
|---|---|---|
| `app/chat/assistant/state.py` | Modify | Add strict `SDBTask` contract and task-list validation. |
| `app/chat/assistant/nodes.py` | Modify | Build typed search task; make compatibility execute/verify consume canonical results. |
| `app/services/agent_chat.py` | Modify | Implement gated stop-on-error runner, result aggregation, truthful approval delivery, and resume behavior. |
| `app/chat/assistant/graph.py` | Modify | Route `consumed` and prevent graph execution from becoming a second runner. |
| `app/chat/assistant/recovery.py` | Modify | Return incomplete tasks from canonical checkpoints/results. |
| `app/chat/assistant/approval.py`, `app/services/tukulpan.py` | Modify | Preserve exact typed SDB digest and bounded result/checkpoint artifacts. |
| `tests/spec/test_sdb_phases.py`, `tests/spec/test_sdb_recovery.py`, `tests/integration/test_sdb_api.py` | Modify | Replace intentional stub assertions with strict RED→GREEN contracts. |

## Testing Strategy

Strict TDD: replace the named `not-implemented`, degraded, and `approved` assertions in `test_sdb_phases.py` and `test_sdb_recovery.py`. Add exact task/payload, pre-approval rejection, gate-order, cost/capability, success/exception, stop-on-error, aggregation, consumed-routing, no-mutation, audit, ordered-event, unauthorized-stream, and bounded-transaction tests. In `test_sdb_api.py`, replace the stub fixture and add successful, failed, and resume-complete stream assertions. Retain Tukulpan persistence regressions.

## Threat Matrix

| Boundary | Applicability | Safe/failure behavior and RED coverage |
|---|---|---|
| Documentation-like paths | N/A — no executable-file classification | None. |
| Git repository selection | N/A — no VCS automation | None. |
| Commit state | N/A — no commit automation | None. |
| Push state | N/A — no push automation | None. |
| PR commands | N/A — no PR automation | None. |

Routing/process integration is applicable only as internal LangGraph routing: RED coverage must prove `consumed` reconciliation and that no graph node invokes a second runner.

## Migration / Rollout

No schema migration. Existing stub checkpoints/results are treated as non-completed and are replaced by the next run; revert code/spec deltas to restore the explicit degraded response.

## Open Questions

None; all locked design decisions are resolved.

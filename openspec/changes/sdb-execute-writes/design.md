# Design: Execute Native SDB Write Tools

## Technical Approach

Keep `_run_sdb_tasks` (`app/services/agent_chat.py:79-136`) as the sole durable
runner. `approve_plan`/`resume_thread` (`agent_chat.py:567-669`) pass the one
atomically consumed approval to `execute_tool` for each frozen task. The graph
continues to project state through `_after_sdb_approve` (`graph.py:69-70`),
whose canonical route is `consumed`. Graphify nodes consulted: `issue_approval`,
`validate_execution`, `execute_tool`, `_run_sdb_tasks`, `persist_sdb_state`,
`recover_events`, `sdb_verify`, `sdb_deliver`, and `get_db`; edges include
`issue_approval→canonical_sdb_digest`, `execute_tool→validate_execution`,
`_run_sdb_tasks→persist_sdb_state`, and `_run_sdb_tasks→record_audit`.

## Architecture Decisions

| Option | Tradeoff | Decision |
|---|---|---|
| Per-task approvals or a new ledger/runner | More state and protocol | Reject |
| One approval plus ordered bindings in existing JSONB | Minimal, replayable boundary | Choose |
| Commit classification inside runner | Impossible: `get_db` commits after return | Reject |

Only `automation.create_rule`, `project.create`, `project.rename`,
`project.archive`, and `project.merge` are write-enabled (`registry.py:251-257`).
`SDBTask.validate_read_tool` (`state.py:102-110`) becomes a five-tool allow-list
plus typed validation; unknown writes fail before handlers.

## Data Flow and Contracts

`canonical_sdb_payload` (`approval.py:16-23`) and
`canonical_sdb_digest` (`:25-30`) must include ordered `sdb_bindings` alongside
`phase`, `spec`, and `tasks`. Each binding is
`{order:int, task_id:str, tool:str, arguments:dict, arguments_sha256:str}`;
the argument hash covers canonical JSON `{order,task_id,tool,arguments}`.
`issue_approval` (`:58-82`) validates/normalizes every task, writes those
bindings and one `sdb_sha256` over `{phase,spec,tasks,sdb_bindings}`. The
payload contains no digest field, avoiding circular hashing. `validate_approval`
(`:85-115`) recomputes the complete ordered plan digest. Before dispatch,
`_run_sdb_tasks` selects the binding by frozen order and passes
`task_binding` to `execute_tool`; `validate_execution` (`:134-157`) requires
membership, matching `arguments_sha256`, tool/arguments, and exact order.

For `project.create`, `project_payload` is exactly
`{operation:"create", arguments:{slug,name,purpose}, decision:{...}}` and is
required by `registry.py:290-303`. `decision` must be an explicit dict with
`selected_slug` or `create_distinct:true`, matching `projects.create` (`:94-148`).
After a successful create, issue `projects.agent_context(session, created.slug)`
(`projects.py:151-157`) and use that capability and slug for both mutation and
`persist_sdb_state`/`persist_sdb_artifact` (`agent_chat.py:177-241`,
`tukulpan.py:268-303`). For rename/archive/merge, task scope must equal
`authorization.slug`; otherwise return failed evidence
`project-capability-scope-mismatch` with expected and requested slugs.

The approved `decision` MUST be part of what the consumed approval validates, not
free-floating: the project payload is canonicalized by `canonical_project_payload`
(`approval.py:45-57`) and folded into the validated digest, so a consumed approval
cannot be replayed with a different `decision` or `arguments`. Lifecycle writes
(`project.rename/archive/merge`) targeting a run-active namespace are rejected by
design by the `_has_active_run` guards (`projects.py:219-220,241-242,264-265`);
that rejection MUST remain a truthful failed attempt with its evidence, never a
silent success or a retried mutation.

Schemas use frozen order (ties break by `order`, then `task_id`):

```text
result: {task_id, order, tool, status, read_only, result, error, evidence}
checkpoint: {run_id, sequence, order, task_id, tool, status, error, result_ref}
audit.after: {run_id, order, task_id, tool, status, error, evidence, proyecto}
event: {type, run_id, sequence, order, task_id, tool, status, error, evidence, checkpoint, audit_ref, proyecto}
```

`persist_sdb_state` stores results by task id and `recover_events` (`recovery.py:11-19`)
dedupes on `(run_id,sequence,type,task_id,tool)` then sorts by
`(sequence,order,type,task_id)`; identical keys retain the first event. This is a
deliberate change of `recover_events` semantics: today it dedupes on
`(run_id,sequence,type)` and sorts by `sequence` alone (`recovery.py:11-19`), which
cannot keep per-task ordering stable across recovery.

## Persistence, Recovery, and VERIFY

Services flush only. `get_db` (`app/panel/deps.py:15-27`) commits after the
endpoint returns and rolls back on exception. If commit raises, the endpoint
returns bounded 5xx/recovery evidence, leaves `execution_status="pending"`
and `recoverable=true` where possible, and records no successful delivery; it
must not retry blindly. `_run_sdb_tasks` does not classify commit uncertainty.

Add `revalidate_sdb_resume(thread, plan, approval, task, order)` in
`recovery.py`: recompute the whole-plan digest, then require the selected
binding's membership, hash, tool, arguments, and order before every resumed
task. Any failure stops closed, persists failed/recoverable evidence, and
requires operator reconciliation. `sdb_verify` (`nodes.py:291-299`) compares
SPEC to results per frozen order: task id, order, tool, status, and mutation
evidence; aggregate input is persisted prior results plus new results, with
deterministic frozen ordering. DELIVER succeeds only when every comparison and
durable commit passes.

## File Changes

| File | Action | Description |
|---|---|---|
| `app/chat/assistant/approval.py` | Modify | Whole-plan ordered bindings and per-task validation. |
| `app/chat/assistant/{state,tools/registry}.py` | Modify | Five-tool write boundary and project decision. |
| `app/services/agent_chat.py` | Modify | Approval forwarding, capability propagation, schemas, endpoint-safe recovery. |
| `app/chat/assistant/{recovery,nodes}.py` | Modify | Resume revalidation and SPEC evidence verification. |
| `tests/unit/*`, `tests/integration/*` | Modify | Strict RED→GREEN requirement-group coverage. |

## Testing Strategy

RED tests cover binding substitution/reorder/hash/expiry/replay, all five schemas
and gate order; ordered dispatch, audit/checkpoint/result/event schemas and first
failure; create capability and lifecycle scope mismatch; persistence rollback
and endpoint commit exception with no retry; resume revalidation; deterministic
`recover_events`; exact SPEC evidence verification and canonical `consumed`
routing. Existing read-only, auth, SSE, cost, and project-decision suites stay green.

## Threat Matrix

| Boundary | Applicability | Safe/failure behavior and RED test |
|---|---|---|
| Documentation-like paths | N/A — no executable-file classification | No task/test. |
| Git repository selection | N/A — no VCS automation | No task/test. |
| Commit state | N/A — no commit automation; DB commit is handled by `get_db` | No task/test. |
| Push state | N/A — no VCS push | No task/test. |
| PR commands | N/A — no PR automation | No task/test. |

## Migration / Rollout

No migration, feature flag, queue, table, ledger, external idempotency layer, or
second approval protocol. Existing reads remain available.

## Open Questions

None.

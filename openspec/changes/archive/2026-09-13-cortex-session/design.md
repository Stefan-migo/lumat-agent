# Design: Cortex-session Planning Surface

## Technical Approach

Extend the existing LangGraph panel assistant with a validated thread-scoped gate and literal command parser. Persist nested session state in the existing thread JSONB and decisions/report through Tukulpan. Closing produces an SDB SPEC proposal and reuses exact approval. No new table, bus, planner, executor, or research-agent layer.

Graphify is degraded read-only: the worktree has no usable graph artifact and refresh is blocked at `c4d13da7`. Consulted graph nodes/edges from the prior map: `NAVIGATION` → `PanelShell`, `PanelShell` → `AgentChat`, `submit_message` → assistant graph, `record_decision` ↔ `list_for_entity`, and `chat.py` → approval service.

## Architecture Decisions

| Seam | Choice | Alternative rejected | Rationale |
|---|---|---|---|
| Gate | Validate active `assistant_state["cortex_session"]` immediately after context/cost preflight and before ordinary guardrails | UI-only flag | Every client and turn is fail-closed. |
| State | Recursive merge; Cortex state is nested under `cortex_session` | Replace whole JSONB object | Preserves SDB, planner, evidence, compaction, and unrelated keys. |
| Memory closure | `upsert()` writes the report, then existing `set_mark(..., status=MemoryStatus.ARCHIVED)` marks it closed; JSONB carries exact `status: "closed"` | Add a `closed` enum/migration or status parameter | `MemoryStatus` only has `active`, `needs_review`, `archived`; reuse is the smallest truthful mapping. |
| Handoff | Build the report-derived SPEC and reuse `POST /chat/threads/{thread_id}/approval`; execution remains the existing `not-implemented` stub | New approval engine/executor | Preserves the established exact-plan and atomic-claim contract. |

## Data Flow

`button or /planning command → open/close service → thread JSONB → Cortex graph turn → Tukulpan decisions/report → SDB SPEC → existing approval route → truthful approved-plan delivery`

## Requirement Coverage

- **HL-3 / IAC-2**: `submit_message()` calls `assemble_context()` then `compact_session()` before `run_assistant`; failed recap returns `flushed:false, failed:true`. `resume_thread()`/`recover_events()` treat DB state as authoritative. Recursive Cortex merge preserves other keys; cost gate precedes `plan_llm`, and blocked mode persists a deterministic reply without LLM. No WhatsApp state.
- **IAC-3**: serializers/UI render `cortex_session.status`, report, indicator, recoverable action, blocked state, and stream error. Reload uses persisted messages/state; an incomplete SSE turn remains failed/processing, never completed.
- **SDB-4**: the closed report is `current_plan.sdb.spec`; `approve_plan()` validates its canonical digest and atomically claims execution. `resume_thread()` uses checkpoints and `resumable_sdb_tasks()`. `_run_sdb_tasks()` emits `not-implemented` results/checkpoints and approved-plan/degraded delivery only; VERIFY cannot claim completed work.
- **AC-9**: `agent/registry.yaml` declares Cortex classes/commands. `load_registry()`/`get_registry()` validate persona, prompt, tool, and runtime references, raising `RegistryError` before startup; reference-only skills are not executed.

## File Changes

| File | Action | Description |
|---|---|---|
| `app/chat/assistant/{graph,nodes,state}.py` | Modify | Gate, parser, Cortex state/classification and loop. |
| `app/services/{agent_chat,tukulpan}.py` | Modify | Recursive persistence, lifecycle, report closure, handoff/recovery. |
| `app/panel/api/routes/chat.py`, serializers | Modify | Planning endpoints and response shapes. |
| `agent/registry.yaml`, `app/agent_registry.py`, `app/services/prompts.py` | Modify | Validated Cortex runtime declaration. |
| `web/src/**`, `tests/**` | Modify/Create | Controls, indicator, browse/recovery UI, RED tests. |

## Interfaces / Contracts

State is `assistant_state["cortex_session"]`: `{slug, topic, status: "active"|"closed", opened_at, closed_at, turn_index, next_decision, last_class, decision_keys, report_key, handoff:{status:"none"|"pending"|"approved", sdb_phase:"SPEC"|"APPROVE"|null}}`.

Memory decisions use `cortex-session/{slug}:decision:{n}` and report uses `cortex-session/{slug}:report`, `scope="panel"`, `entity_id="thread:{id}"`; report `tipo=SUMMARY`, DB `status=archived` means closed, and JSON/report/API status is `closed`. Closure is exactly `upsert(..., tipo=MemoryType.SUMMARY, ...)` followed by `set_mark(..., status=MemoryStatus.ARCHIVED)`.

| Operation | Contract |
|---|---|
| Open | `POST /planning/sessions`, `require_admin_json`; body `{topic:string, thread_id?:int}`; returns `201 {session,thread_id}`. Button calls it; `/planning <topic>` calls the same service. Invalid topic `400`; missing/unauthorized `401/403`; unknown thread `404`. |
| Close | `POST /planning/sessions/{slug}/close`, empty body; returns `{session,report,handoff}`. `/planning close` uses the same service. Missing auth `401/403`, unknown slug/thread `404`, inactive session `409`. |
| Browse | `GET /planning/sessions` and `GET /planning/sessions/{slug}`; `require_admin_json`; list/detail shapes remain `{sessions:[...]}` and `{session,thread,decisions,report}`. Auth `401/403`, unknown slug `404`. |
| Reopen | `POST /planning/sessions/{slug}/reopen`, empty body; returns `{session,thread_id}`; auth `401/403`, unknown slug `404`, already active `409`. |
| Approve | Reuse existing `POST /chat/threads/{thread_id}/approval`, `ApprovalBody {run_id,token,reject=false}`; returns `{status,message}`. Auth `401/403`, unknown thread `404`, invalid/expired/consumed token `409`. |

## Testing Strategy

Strict RED-first pytest tests cover gates/parser/merge, compaction/recovery, blocked cost, report `upsert` + `set_mark(ARCHIVED)`, digest approval, resume/stub truth, registry failures, endpoint auth/404/409, and SPA states/control equivalence.

## Threat Matrix

| Boundary | Applicability | Safe/failure behavior and RED test |
|---|---|---|
| Documentation-like paths | N/A — no executable-file classification | No task/test. |
| Git repository selection | N/A — no VCS automation | No task/test. |
| Commit state | N/A — no commit automation | No task/test. |
| Push state | N/A — no push automation | No task/test. |
| PR commands | N/A — no PR automation | No task/test. |

## Migration / Rollout

No migration required. Existing threads remain normal; SDB EXECUTE remains a stub.

## Open Questions

None.

Ponytail review: `delete:` separate planning service, event bus, executor, new approval route, and new closed-status migration. `shrink:` lifecycle, report closure, and handoff reuse existing service seams. Net: -6 speculative components.

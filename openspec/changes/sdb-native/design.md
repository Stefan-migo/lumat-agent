# Design: Native SDB Seven-Phase Subgraph

## Technical Approach

Extend LangGraph after `plan_llm` with a structured trigger gate. SDB uses the same state, transaction, events, approval, and `evidence -> END`; ordinary plans retain `guardrails -> execute/respond`. JSONB is authoritative for recovery; Tukulpan stores bounded typed artifacts.

## Architecture Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| Topology | `plan_llm -> sdb_trigger_gate`; SDB is `CLARIFY -> SPEC -> PLAN -> APPROVE -> EXECUTE -> VERIFY -> DELIVER -> evidence -> END`. Pending approval resumes at `EXECUTE`. | Separate runtime; tool wrapper | Preserves cost, audit, replay, and normal routing. Graph path: `graph.py -> nodes.py -> tukulpan.py` (stale, `c4d13da7` vs `267821ee`). |
| Trigger contract | Planner emits `classification: "normal"|"sdb"`; authenticated admin supplies `sdb_requested`. Valid explicit request wins; malformed/conflicting signals fail closed. | Infer from tool text; all `complex` means SDB | Structured trust boundary without broad `complex` behavior. |
| Persistence | `PATTERN` SPEC, `SESSION` checkpoint STATE, `DISCOVERY` RESULT; keys `sdb:{run_id}:spec`, `sdb:{run_id}:state:{seq}`, `sdb:{run_id}:result:{task_id}`. Every seam accepts `proyecto: str = "default"`, passes it to `upsert`, and preserves `_guard_writable_project()`. | New artifact/checkpoint tables | JSONB and unique memory keys hold bounded state without schema or Projects scope. |
| Approval/recovery | Canonical SDB payload uses existing SHA-256/TTL approval; claims require `active_run_id`. SPEC digest makes mutation invalidate approval. | New token or worker | Reuses atomic claim semantics and prevents duplicate work. |

## Data Flow

```text
plan_llm -> trigger_gate -> normal guardrails -> execute/respond -> evidence -> END
                      -> CLARIFY -> SPEC -> PLAN -> APPROVE
                                      -> EXECUTE -> VERIFY -> DELIVER -> evidence -> END
```

SPEC freezes scope and stores its digest/reference. PLAN creates bounded task IDs and one output contract each. EXECUTE claims one task, writes a checkpoint/event, and never reruns completed work. VERIFY emits bounded evidence (`task_ids`, `artifact_refs`, `status`) against SPEC.

## File Changes

| File | Action | Description |
|---|---|---|
| `app/chat/assistant/{graph,state,nodes}.py` | Modify | Gate, phases, typed fields, routing, scope freeze, evidence. |
| `app/chat/assistant/{approval,recovery}.py` | Modify | Canonical digest and run-scoped claims. |
| `app/services/agent_chat.py` | Modify | Persist state/events and resume from checkpoint. |
| `app/services/tukulpan.py` | Modify | Typed artifact/checkpoint seams with parameterized `proyecto`. |
| `app/panel/api/routes/chat.py` | Modify | Explicit authenticated trigger and approval/resume integration. |
| `agent/registry.yaml`, `agent/prompts/assistant_plan.md` | Modify | Declare SDB classification and output contract. |
| `tests/integration/`, `tests/spec/` | Create/modify | RED coverage for routing, persistence, approval, recovery, evidence. |
| `db/migrations/009_memory.sql` | No change | JSONB plus `memories` schema is sufficient. |

## Interfaces / Contracts

```python
SDBState = {
  "trigger": "classified" | "admin",
  "phase": "CLARIFY" | "SPEC" | "PLAN" | "APPROVE" | "EXECUTE" | "VERIFY" | "DELIVER",
  "spec_ref": {"topic_key": str, "sha256": str}, "current_task": str | None,
  "checkpoint_seq": int, "verification": {"status": str, "task_ids": list[str], "artifact_refs": list[str]},
}
```

Payloads are capped before write (SPEC 8 KiB, checkpoint/result 4 KiB; IDs/refs length-limited). Calls use `scope="panel"`, `entity_id=f"thread:{thread_id}"`, and propagated `proyecto` default.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | Gate, transitions, digest, bounds, idempotency | Pure node/approval tests with malformed and mutated SPEC. |
| Integration | Entry, typed rows, JSONB/events, claims, resume | PostgreSQL fixtures; assert normal plans unchanged and completed tasks not rerun. |
| E2E | Approval-to-delivery and degraded persistence/provider paths | Existing panel API test client and SSE event replay. |

## Threat Matrix

| Boundary | Minimum adversarial cases | Applicability | Design response | Planned RED tests |
|---|---|---|---|---|
| Routing/trigger | malformed, conflicting, unauthorized, normal plan | Applicable | Fail closed; preserve normal route | One test per case |
| Documentation-like paths | executable Markdown/README | N/A — no executable-file classification | None | None |
| Git repository selection | relative/absolute paths | N/A — no Git automation | None | None |
| Commit state | staged/empty index | N/A — no commit operation | None | None |
| Push state | tracking/explicit refspec | N/A — no push operation | None | None |
| PR commands | explicit head/environment prefix | N/A — no PR automation | None | None |

## Migration / Rollout

No migration required. Enable only validated classification/admin input; persist failed evidence when Tukulpan/provider calls fail. Non-default `proyecto` still raises before writes.

## Open Questions

None blocking.

## Graph Nodes Consulted

Nodes consulted: `assistant/graph.py`, `nodes.py`, `AssistantState`, `plan_llm()`, `approval.py`, `agent_chat.py`, `recovery.py`, `tukulpan.py`, `upsert()`, `InternalChatThread`, `registry.py`; paths `graph.py -> nodes.py -> tukulpan.py`, `nodes.py -> approval.py`, `agent_chat.py -> models.py <- state.py` (EXTRACTED; stale).

## Ponytail Design Cuts

`delete:` separate runtime, tables, project registry/UI, sub-agents, and broad search. `yagni:` new approval/checkpoint service; use existing digest, JSONB, event replay, and Tukulpan. `shrink:` one SDB persistence seam handles all three typed artifact mappings instead of three adapters.

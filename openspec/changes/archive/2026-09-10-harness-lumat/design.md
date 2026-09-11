# Design: Harness Lumat

## Technical Approach

Extend the panel `AssistantState` graph, retaining persistence, SSE, tools,
approval, audit, attachments, and recovery:
`START → assemble_context → plan_llm → guardrails → execute_tool|respond_stream
→ persist/evidence → END`. `InternalChatThread` and message rows remain the
session source of truth: no second loop and no LangGraph checkpointer.

## Architecture Decisions

| Decision | Choice | Alternatives / rationale |
|---|---|---|
| Runtime | Extend `app/chat/assistant/*`. | Avoids duplicate persistence/recovery from a second loop or checkpointer. |
| Tokens/budget | `ceil(len(text.encode("utf-8"))/4)`; 4,000-token injection budget. | No `tiktoken`; deterministic estimate for all injected context. |
| History | Read messages ordered by `(created_at,id)`; retain newest rows to 4,000 tokens; truncate attachments last. | Existing index; no summary table. |
| Tukulpan | `load_panel_context(session, thread_id)` returns `{pinned, panel}` from read-only `panel` scope for `thread:{id}`; pinned first, newest next, within 4,000 tokens. | No internals or automatic search; `hybrid_search` stays explicit. |
| Rolling session | 8,000-token window; preflight at 4,000, flush recap/evidence, retain newest 2,000, persist rotation. | Observable compaction. |
| Planner | Strict Pydantic: `kind` (`tool|respond|complex`), optional `tool`, object `arguments`, `summary`, `requires_approval`; forbid extras; tool required iff `kind=tool`. `complex` signals a hook. Invalid output becomes bounded `respond` with error evidence/audit. | Free-form JSON permits unchecked execution. |
| Guardrails | Schema → whitelist → typed arguments → cost → exact write approval → handler → `record_audit` → evidence/events. | Boundaries precede side effects; reuse digest/audit. |
| State/config | Add optional JSONB keys below; preserve existing keys. Extend `prompts.py` for validated registry data; never load skills. | JSONB/renderer avoid columns or duplicate loaders. |

## Data Flow

```text
Client/API  agent_chat  assemble_context  plan_llm  guardrails  tool/response  persist
   |           |              |              |          |             |            |
   |--submit-->|              |              |          |             |            |
   |           |--turn------->|              |          |             |            |
   |           |              |--DB history->|          |             |            |
   |           |              |--attachments>|          |             |            |
   |           |              |--Tukulpan panel/pinned->|             |            |
   |           |              |--registry prompts/tools->|             |            |
   |           |              |------------->|--plan---->|             |            |
   |           |              |              |          |--whitelist/cost/approval/audit->|
   |           |              |              |          |--execute/respond_stream------->|
   |           |              |              |          |             |--evidence------>|
   |<----------------------------SSE + persisted response----------------------------|
```

```text
Turn preflight       Threshold check       Memory flush       Compaction       Persist rotation
      |                    |                    |                 |                  |
      |-- estimate ------->|                    |                 |                  |
      |<-- below 50% ------|                    |                 |                  |
      |-- (if reached) --->|-- flush request --> |                 |                  |
      |                    |                    |-- recap/evidence ->             |
      |                    |                    |<-- flushed ---------------------|
      |                    |                    |                 |-- retain 2k ---->|
      |                    |                    |                 |                  |-- metadata -->
      |<--------------------------- continue assembled turn ------------------------|
```

## `assistant_state` JSONB Contract

Preserve `stage`, `recoverable`, `approval`, `execution_status`, `events`.
New keys are optional/additive; no column or migration is added:

| Key | Value shape | Meaning |
|---|---|---|
| `context_meta` | `{"message_ids": list[int], "attachment_ids": list[int], "tukulpan_ids": list[str], "estimated_tokens": int, "truncated": bool}` | Sources and bounded result. |
| `planner` | `{"kind": str, "tool": str \| None, "arguments": dict, "summary": str, "requires_approval": bool, "valid": bool}` | Validated plan; `valid=false` records fallback. |
| `guardrails` | `{"whitelisted": bool, "arguments_valid": bool, "cost_allowed": bool, "approval_required": bool, "decision": str}` | Pre-side-effect deterministic decisions. |
| `compaction` | `{"window_tokens": int, "threshold_tokens": int, "before_tokens": int, "after_tokens": int, "flushed": bool, "rotated_at": str}` | Flush/rotation evidence. |
| `extension_hooks` | `{"sdb": str, "panel_subagents": str}` | Hook status (`"deferred"`/`"not_implemented"`); never executable. |

## File Changes

| File | Action | Description |
|---|---|---|
| `app/chat/assistant/{state,graph,nodes,recovery}.py` | Modify | Context/planner/guardrails/recovery. |
| `app/chat/assistant/tools/registry.py` | Modify | Whitelist dispatch. |
| `app/services/agent_chat.py` | Modify | History/state/compaction/events. |
| `app/services/prompts.py`, `app/config.py` | Modify | Registry seam/budgets. |
| `agent/{registry.yaml,README.md,skills/sdb.md}` and grep consumers | Modify | Config/SDB inventory. |
| `tests/` | Modify | Tests. |

## Interfaces / Contracts

`load_panel_context` and `flush_panel_session` are Tukulpan seams. Future hooks
accept validated `AssistantState` and return metadata only.
Mapping: HL-1 assembly; HL-2 planner/guardrails; HL-3 JSONB;
IAC-2/IAC-6 history/auth/SSE; AO-1..AO-3 graph/approval/audit; AT-1 dispatch;
AC-6/AC-9 loader.

## Testing Strategy

Run `uv run pytest tests/` under strict TDD. Unit tests cover estimator, schema,
ordering, and guardrails; integration/API tests cover history, attachments,
whitelist, approval, cost, compaction, recovery, SSE, serialization, and config.

## Threat Matrix

Only internal LangGraph routing changes; all rows are `N/A` (no external boundary):

| Boundary | Applicability | Reason |
|---|---|---|
| Documentation-like paths | N/A | No execution/classification. |
| Git repository selection | N/A | No Git selection. |
| Commit state | N/A | No commit automation. |
| Push state | N/A | No push/ref handling. |
| PR commands | N/A | No PR automation. |

## Migration / Rollout

No migration. Roll out behind the assistant boundary, preserving fields; disable
by configuration for rollback. Revert graph/loader/config/docs while retaining
JSONB rows and recovery. Inventory SDB consumers before renaming the Lumat
surface to “Gates deterministas / Guardrails”; do not rename Tukulpan or
implement SDB internals.

## Open Questions

None; budgets, fallback, ordering, JSONB, hooks, config are resolved.

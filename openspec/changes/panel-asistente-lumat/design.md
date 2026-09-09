# Design: Panel Asistente Lumat

## Technical Approach

Build a second LangGraph boundary under `app/chat/assistant/`; WhatsApp keeps `ConversationState`, `app/chat/graph.py`, and DeepSeek unchanged. `app/services/agent_chat.py` persists `AssistantState`; `app/panel/api/routes/chat.py` adds admin-only message, approval, SSE, upload, and capability endpoints. Five slices: boundary, tools, UX, config, uploads.

## Architecture Decisions

| Decision | Choice | Rejected | Rationale / graph nodes |
|---|---|---|---|
| Graph boundary | New `assistant/graph.py`: planner → approval → execution → evidence; rebuild from DB | Reuse WhatsApp graph | `graph.py`, `state.py`, and `InternalChatThread` are coupled to WhatsApp/old chat; path confirms `graph.py → run_internal_conversation() → InternalChatThread`. |
| Approval | Opaque random token; store SHA-256 token, canonical JSON argument digest, tool, expiry, consumed timestamp | Client boolean/JWT-only approval | Atomic row lock and consume-once prevent replay and tampering; `record_audit` is the existing audit hub. |
| Tools | Pydantic argument models in `assistant/tools/registry.py`; executor calls services directly | Panel-route calls/MCP | Existing service seams (`customers`, `conversations`, `scheduling`, `cases`, `kb`, `memory`, `dashboard`) avoid HTTP/auth recursion; `automation.create_rule()` at line 72 preserves worker behavior. |
| Streaming/provider | Dedicated `StreamingResponse` SSE; extend `llm.py` with explicit provider/model factory and `assistant_chat_*` settings | Global WebSocket or changing default | `AgentChat.tsx → api.ts` is an isolated frontend seam; explicit OpenRouter settings preserve DeepSeek WhatsApp behavior. |

## Data Flow

`POST message` → persist inbound/context → planner (OpenRouter) → commit plan → `GET /assistant/stream` emits events → approval validates digest/consumes token → typed executor (short transaction) → evidence/audit → commit. Reload reads persisted state; unique execution key prevents duplicates. The approval row stores `tool_name`, canonical `arguments_json`, `arguments_sha256`, token hash, `expires_at`, and `consumed_at`; `SELECT FOR UPDATE` rejects mismatch, expiry, replay, or tampering.

## File Changes

| File | Action | Description |
|---|---|---|
| `app/chat/assistant/{state,graph,nodes,approval,evidence,search}.py`, `app/chat/assistant/tools/{__init__,registry}.py` | Create | State machine, registry, approval, DDG/httpx adapter, evidence. |
| `app/services/agent_chat.py`, `app/panel/api/routes/chat.py` | Modify | Replace `run_internal_conversation()` backend; add plan/approval/SSE/recovery/upload, retain old shapes. |
| `app/models.py`, `app/panel/api/serializers.py`, `app/config.py`, `app/services/llm.py` | Modify | Metadata models, safe serializers, assistant provider/limits, explicit client factory. |
| `app/agent_registry.py`, `agent/registry.yaml`, `agent/personas/`, `agent/prompts/` | Modify/Create | Real assistant references, tool declarations, existence validation, capability view. |
| `app/services/automation.py` | Modify | Permit only executor-originated `actor="assistant"`; existing CRUD/history remains unchanged. |
| `web/src/components/pages/AgentChat.tsx`, `web/src/api.ts`, `web/src/types.ts` | Modify | Fetch-based SSE, plan approval/rejection, evidence, attachment UI and recovery states. |
| `db/migrations/020_assistant_metadata.sql`, `021_assistant_approvals.sql`, `022_assistant_attachments.sql` | Create | Thread/message JSON metadata; approvals plus unique executions; private attachment metadata. |

## Interfaces / Contracts

Tools are allow-listed admin-only reads: customers, conversations, appointments, cases, KB (`kb.retrieve`), memory/KPIs, and `web.search`; `automation.create_rule` is the sole v1 write. Each has a Pydantic model, schema, read/write flag, bounded result, and evidence. Writes call `automation.create_rule(session, args, actor="assistant")` in the executor transaction. SSE order is `plan`, `approval`, `tool`, `evidence`, `status`, `response`, `error`, each with `thread_id`, `run_id`, sequence; `status` carries lifecycle state, while `response` carries final assistant text after execution completes.

Attachments use `media_dir/assistant/{thread_id}/{opaque-id}`; responses expose no path. Validate MIME/extension/size/count and ownership; cleanup only assistant rows. PDF/CSV/txt use `kb.extract_text()`; images become OpenRouter multimodal parts after limits. `agent_registry.py` validates persona, prompt, and tool references; `/panel/api/assistant/capabilities` is read-only.

Requirement map: AO-1→state/metadata/recovery; AO-2→approval rows; AO-3→SSE/audit; AT-1→registry/executor; AT-2→automation transaction; AT-3→search adapter; IAC-2/3/6→service/routes/UI; AC-4/9/10→registry/capability endpoint; AR-6/7→automation actor/audit; AA-1/2/3→upload/context/cleanup.

## Testing Strategy

RED integration tests cover every mapped requirement: role denial, recovery, digest tamper/replay/expiry, consume-once execution, direct-service calls, automation audit/worker visibility, ordered SSE/reconnect, registry failures, upload isolation/extraction, and vision limits. Unit tests cover hashing, schemas, DDG failures, and SSE; React tests cover panel states and approval/attachments.

## Threat Matrix

| Boundary | Applicability and response | RED tests |
|---|---|---|
| New assistant routes/SSE | **Applicable**: signed-session `require_admin_json`; no data before authorization; bounded sessions per event | operador gets 403; cross-thread 404/403; event order/reconnect |
| Documentation-like paths | N/A — no executable path handling | None |
| Git repository selection | N/A — no VCS automation | None |
| Commit state | N/A — no commit automation | None |
| Push state | N/A — no push automation | None |
| PR commands | N/A — no PR automation | None |

## Migration / Rollout

Apply 020–022 through the existing runner. `020` adds nullable `assistant_state`, `current_plan`, and `active_run_id` JSONB/ID metadata to internal chat rows; `021` adds approval/execution records with `tool_name`, canonical args/digests, `expires_at`, `consumed_at`, and unique constraints; `022` adds attachment ownership, digest, MIME, size, and lifecycle metadata. Rollback hides routes/UI and leaves WhatsApp, dashboard, rules, and threads intact.

## Open Questions

- [ ] Validate `google/gemini-2.5-flash` availability, image format, and OpenRouter pricing before locking the vision model.
- [ ] Set assistant per-run/token/image budget using existing `costs.py` guardrails.
- [ ] Set attachment expiry/orphan cleanup interval and maximum size/count from deployment storage capacity.

## Graph Check Consulted

Nodes/edges: `graph.py → run_internal_conversation() → InternalChatThread`; `AgentChat.tsx → api.ts`; `automation_rules.py → AutomationRule → worker.py`; `services/kb.py → extract_text`; `agent_registry.py → agent/registry.yaml`; `record_audit → AuditLog`; `llm.py → get_settings`. `GRAPH_REPORT.md` god nodes consulted: `record_audit`, `User`, `Conversation`, `Customer`, `Case`, `session_scope`.

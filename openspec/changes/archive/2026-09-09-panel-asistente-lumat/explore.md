## Exploration: panel-asistente-lumat

### Status
Ready for proposal.

### Executive Summary

The current panel assistant is a persisted, admin-only text chat. `run_internal_conversation()` calls the OpenAI-compatible Chat Completions API, already supports token callbacks and `stream=True`, but deliberately has no business context, tools, actions, or planner. The WhatsApp LangGraph is reusable for graph construction conventions, LLM access, memory, audit, and streaming; its customer/phone state and safety gates should not be reused as the panel assistant state. Build a separate assistant graph boundary with `AssistantState`, planner, approval gate, tool execution, and evidence nodes. Keep `InternalChatThread` persistence as the starting boundary, but plan metadata/approval persistence explicitly.

### Area Feasibility

- **`app/chat/` — reuse patterns, build a separate graph.** `StateGraph` and node routing fit the request → visible plan → approval → execution → evidence cycle. `ConversationState` is WhatsApp-specific and has no checkpointer; do not couple the assistant to it. Existing `run_internal_conversation()` is the replacement seam. `llm.py` already supports OpenRouter/DeepSeek and OpenAI SDK streaming.
- **Tools — reuse domain services, build a typed registry/executor.** Existing services cover customers, conversations/cases, scheduling, KB, memory, and audit. `orchestrate.is_tool_whitelisted()` is only a minimal precedent; function schemas, argument validation, role scope, read/write classification, confirmation tokens, and evidence are missing. Invoke services directly, not panel HTTP routes.
- **Websearch — build a thin adapter.** `pyproject.toml` has `httpx` but no Tavily/DDG package. Use a bounded DuckDuckGo adapter over existing `httpx` for a no-dependency v1, behind one interface; defer Tavily unless result quality/operational support justifies a key and dependency.
- **Attachments — partial reuse, new assistant boundary.** `kb.extract_text()` already handles PDF, CSV, and text-like content; `media_dir` stores WhatsApp downloads. There is no assistant upload metadata, lifecycle, authorization, or model-ready image path. Reuse the storage primitive and extraction functions, but add thread-scoped upload handling and private references; send images as multimodal OpenRouter content and extracted document text as context.
- **Frontend — reuse primitives, API and realtime conventions; build assistant UX.** `AgentChat.tsx` has threads, retry, state rendering, and token display. `api.ts` supports multipart uploads; the existing WebSocket already carries token/message events. The fixed v1 SSE decision means add a dedicated assistant SSE stream rather than silently extending global realtime semantics. Add attachments, plan/evidence cards, approval/rejection, and streaming fetch handling.
- **Agent config — reuse loader/validation shape, rebuild runtime config.** `agent_registry.py` fail-fast validation is useful, but registry tools are limited to `kb.retrieve`, four referenced personas are absent, and `prompts.py` is WhatsApp-oriented. Add an assistant persona, real files, tool declarations, and existence validation without making panel editing a v1 feature.
- **Permissions — keep admin-only in v1.** `require_admin_json` protects chat and mutation routes; `PanelShell` hides chat from `operador`. The existing role model has `admin`/`operador`, not a distinct owner role, so owner access currently maps to admin. Revisit operator access only as an explicit authorization decision.
- **Automations — safe to reuse transactionally.** `automation.create_rule()` validates, flushes, and audits; the route commits. The worker later evaluates `DomainEvent` rows. The agent tool should call the service in the same request transaction after confirmation, never call the HTTP endpoint, and return the audited rule as evidence.

### Open Questions Answered

1. **Websearch:** DuckDuckGo via existing `httpx` is the leanest v1; isolate it so Tavily can replace it.
2. **Multimodal model:** OpenRouter is technically ready, but no vision capability/model selection exists. Start design with a configurable OpenRouter vision-capable candidate (for example `google/gemini-2.5-flash`), then validate current availability, price, limits, and image format before locking it.
3. **Attachment storage:** reuse `media_dir` as private server storage, but add assistant ownership/thread references and cleanup; do not expose raw filesystem paths or WhatsApp URLs.
4. **Operator permission:** admin-only is the verified v1 behavior and safest default.

### Recommended Slices

1. Assistant graph boundary: state, planner, confirmation, native tool protocol, evidence, persistence, SSE.
2. Read tools plus confirmed writes: business reads, automation creation, audit/evidence, websearch.
3. Frontend assistant UX: SSE stream, plan approval cards, evidence, thread recovery.
4. Agent configuration: real personas/prompts/registry and validation plus read-only capability view.
5. Attachments: private upload lifecycle, PDF/CSV/txt extraction, OpenRouter image messages and cost limits.

### Risks

- Approval state must be durable and bound to the exact planned tool arguments; never trust a client-side “approved” flag.
- Streaming and synchronous DB sessions need careful transaction boundaries; do not hold a request transaction across an unbounded model stream.
- Customer data and external search/upload content require prompt-injection isolation, least-privilege tools, audit, and size/cost limits.
- Do not touch `panel-dashboard-operativo`, dashboard files, or dashboard navigation.

### Graph Check Consulted

`GRAPH_REPORT.md` (4213 nodes, 8665 edges) identifies `graph.py`, `chat.py`, `llm.py`, `state.py`, `api.ts`, `PanelShell.tsx`, `automation_rules.py`, `worker.py`, `services/kb.py`, `User`, and `agent/registry.yaml` as hubs. Queried paths/edges: `run_internal_conversation() <-calls- submit_message()`; `orchestrate.py -> graph.py -> models.py <- automation.py`; `automation_rules.py -> models.py <- worker.py`. The frontend attachment query connected `AgentChat()`, `api.ts`, `uploadKbDocument()`, and `extract_text()`; no direct `AgentChat.tsx -> extract_text` path exists, confirming a new backend boundary is needed.

### Next Recommended

`propose`

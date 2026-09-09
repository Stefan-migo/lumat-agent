# Proposal: Panel Asistente Lumat

## Intent

Replace the constrained admin chat with an executive operations assistant that reads business data, shows a structured plan, executes approved actions, and returns auditable evidence without coupling to WhatsApp state.

## Scope

### In Scope
- LangGraph `AssistantState` with planner, exact-argument approval, typed tools, evidence, audit, metadata, and SSE.
- Admin-only reads for customers, conversations, appointments, cases, KB, memory/KPIs, and web; confirmed automation creation through the existing service.
- React chat with threads, plan/evidence cards, approval, recovery, and attachments.
- Verified `agent/` registry/personas/prompts plus a read-only capability view.

### Out of Scope
- MCP, Gmail/Drive/Sheets, Tavily, operator access, panel config editing, and global realtime changes.
- WhatsApp pipeline/state/model changes, dashboard files, or `panel-dashboard-operativo`.

## Capabilities

### New Capabilities
- `assistant-operations`: graph, tools, approvals, evidence, persistence, audit, and SSE.
- `assistant-attachments`: uploads, PDF/CSV/txt extraction, and image context.

### Modified Capabilities
- `internal-agent-chat`: add plans, approvals, tools, evidence, and SSE.
- `agent-config`: add existence-validated assistant registry/personas/prompts.
- `automation-rules`: allow confirmed assistant-created rules through the existing service and audit/history.

## Approach

Five chained slices: graph/persistence/approval/SSE; domain tools, automation, audit, and `httpx` DuckDuckGo; chat UX; agent configuration/view; attachments, `kb.extract_text`, vision validation, and limits. Reuse services, `InternalChatThread`, auth, audit, memory, KB, and worker; tools never call panel routes.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `app/chat/`, panel chat routes, `app/services/agent_chat.py` | Modified/New | Graph, tools, approval, SSE |
| `app/services/`, `agent/`, `app/agent_registry.py` | Modified | Adapters and verified config |
| `web/src/components/pages/AgentChat.tsx`, `web/src/api.ts` | Modified | Chat and evidence UX |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Approval replay/tampering | High | Durable server approval bound to exact arguments; audit execution |
| Vision cost/quality | Med | Validate `google/gemini-2.5-flash`; enforce budget and size limits |
| Streaming transactions | Med | Commit before streams; recover from persisted state |
| Untrusted search/uploads | Med | Isolate content, constrain tools, limit inputs, record evidence |

## Rollback Plan

Disable assistant exposure and revert graph, UI, migrations, and config. Preserve existing threads/rules; do not alter WhatsApp or worker semantics.

## Open Questions for Spec/Design

- Vision model/budget; attachment storage/cleanup; search quality; operator-access revisit.

## Ponytail Check

- `delete`: MCP, Google integrations, Tavily, editable config, and global realtime; defer until justified.
- `native`: reuse LangGraph, `httpx`, services, storage, audit, and worker; add no framework or route proxy.
- `shrink`: admin-only, confirm every write, and one bounded DuckDuckGo interface.

## Success Criteria

- [ ] Admin sees plans, approves exact writes, and receives recoverable SSE evidence.
- [ ] Business reads and automation creation use existing services/history/worker.
- [ ] Every tool execution is audited; WhatsApp and dashboard behavior remain unchanged.

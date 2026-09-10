# Proposal: Panel Conversations Redesign

## Intent

Unify Conversaciones and Casos into one operational queue with a workspace thread and Dashboard-quality styling (style reference, not layout template). The generic DataTable lacks search, pagination, prioritization, and case context; the backend is blind to cases.

## Scope

### In Scope
- Backend: embed case context in list/detail payloads through serializer and query join; add `q`, limit/offset pagination, and soft-redirect support.
- Frontend: unified queue with Todas, Humanas, Emergencias, Casos, and Cerradas tabs, live counts, priority ordering, search, pagination, and Tomar/Reconocer actions.
- Frontend workspace: thread plus RIGHT panel with case/customer blocks and collapsible `captured_data` key/value rendering; route `/cases` to Casos and retire `CasesList`.

### Out of Scope
- KPI row, cursor pagination, virtualization, infinite scroll, fixed `captured_data` schema, case detail page, database schema changes, or RLS work.

## Capabilities

### New Capabilities
- `unified-conversation-queue`: Operational queue, filters, counts, ordering, search, pagination, and queue actions.

### Modified Capabilities
- `panel-app`: Conversation workspace, case context, and `/cases` compatibility routing change.
- `conversation-realtime`: Snapshot payloads and queue refresh behavior include embedded case context.

## Approach

Use the conversation endpoint as the unified read model while preserving case mutations. Implement auto-chain slices: (1) backend embedding plus search/pagination, (2) queue UI, (3) workspace and compatibility route. Use batched case lookup or a SQL read-model query to avoid N+1 amplification. Specify case-selection semantics, tab-count scope, closed-row behavior, `captured_data` source, and snapshot refresh/debounce before implementation.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/panel/api/{serializers.py,routes/conversations.py}` | Modified | Read-model payload, filters, pagination |
| `app/panel/api/routes/cases.py` | Preserved | Existing case mutations remain authoritative |
| `web/src/components/pages/{ConversationsList,ConversationThread,CasesList}.tsx` | Modified/Removed | Queue, workspace, and retired case list |
| `web/src/components/domain/{AppShell,panelRoutes.ts}` | Modified | Soft redirect and active tab |
| `web/src/{api.ts,types.ts,realtime.ts}` | Modified | API types and refresh contract |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Multiple cases share a conversation | High | Define explicit selection precedence before specs |
| Embedded context worsens N+1/realtime cost | Med | Batched join/query and snapshot refresh limits |
| Tab count scope is ambiguous | Med | Specify global versus filtered counts |

## Rollback Plan

Revert the frontend route and queue slices independently, then revert the backend contract slice. Preserve case mutation endpoints and `/cases` compatibility during rollback.

## Dependencies

- Existing design-system tokens, conversation API, case mutations, and realtime snapshots.

## Success Criteria

- [ ] Operators can find, prioritize, filter, page, take, and acknowledge conversations from one queue.
- [ ] List and workspace payloads expose accurate case/customer context without per-row case queries.
- [ ] Existing `/cases` bookmarks resolve to the unified Casos tab and current conversation actions remain functional.

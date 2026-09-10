# Exploration: Panel conversations redesign

## Current State

The cached Cortex report is substantially confirmed. The panel has separate conversation and case surfaces, with conversations rendered through a generic table and a message thread, while cases use an independent table with inline status/assignee controls. The conversation serializer does not include case data. The conversation list accepts only `state` and `responsible_id`; it has no search, pagination, case filtering, or priority ordering. The thread has no case, customer ficha, or captured-data side panel.

Cases are structurally joinable to conversations: `Case.conversation_id` is an ORM `mapped_column` with `nullable=False` and a foreign key. `get_or_create_case()` always receives both conversation and customer IDs, and is used by intent classification and emergency handling. However, it selects the latest case by descending ID and does not enforce one case per conversation; a conversation can therefore have multiple case rows over time.

The existing route layer already treats `/panel/app/cases` as a compatibility view and `AppShell` maps it to the cases segment, but it still renders `CasesList`; it is not yet a redirect to the unified conversation queue. The realtime WebSocket sends a full snapshot containing serialized conversations and persisted activity, then emits process-local events. Current list and thread components refetch on snapshot, conversation, and message events.

## Affected Areas

- `app/panel/api/serializers.py` — `to_conversation_dict()` currently ends at conversation/message metadata and has no case or captured-data context.
- `app/panel/api/routes/conversations.py` — list supports only state/assignee filters and unbounded activity ordering; `_conversation_payload()` already performs per-conversation message queries that must be considered when adding case data.
- `app/panel/api/routes/cases.py` — existing open-case list, update, and acknowledge mutations remain the source of case actions; there is no case detail endpoint.
- `app/services/cases.py` — `get_or_create_case()` establishes the non-null conversation link but returns the latest case by ID, not necessarily the latest open case.
- `app/models.py` — `Conversation.captured_data` is JSONB; `Case` has free-string status/priority and no ORM relationships to conversation/customer.
- `web/src/api.ts` and `web/src/types.ts` — client filters and `Conversation` shape must evolve together with the API envelope; current `Case` fields are stricter than nullable ORM columns for some values.
- `web/src/components/pages/ConversationsList.tsx` — current table/filter implementation has no tabs, counts, search, pagination, priority treatment, or case quick action.
- `web/src/components/pages/ConversationThread.tsx` — current workspace is thread-only; it already owns state mutations, reply-window handling, retry, and realtime refresh.
- `web/src/components/pages/CasesList.tsx` — current case controls provide the behavior to preserve or move into the unified workspace, then the page can retire.
- `web/src/components/domain/AppShell.tsx` and `web/src/components/domain/panelRoutes.ts` — existing compatibility route/tab state needs to become a soft redirect/active Casos tab without breaking bookmarks.
- `web/src/realtime.ts` and `app/panel/api/routes/realtime.py` — snapshot shape is `{conversations, activity}` and snapshot serialization currently reuses `_conversation_payload()` for every conversation.
- `web/src/components/primitives/primitives.css` — a CSS-only `.pagination` primitive exists; there is no dedicated Pagination component.
- `web/DESIGN_SYSTEM.md` — mandates operational priority, explicit emergency/handoff/reply-window states, right-side workspace context, semantic Spanish labels, token reuse, and complete state coverage.
- `tests/functional/test_api_conversations.py`, `tests/functional/test_api_cases.py`, `web/src/components/pages/{ConversationsList,ConversationThread}.test.tsx`, `web/src/components/domain/panelRoutes.test.ts`, and AppShell/page stories — existing tests assert exact payload keys and current route/page ownership, so the contract changes will require deliberate updates rather than additive assertions only.

## Approaches

1. **Unified conversation read model with embedded latest case context** — Extend the conversation list/detail payload with a nullable case object selected by an explicit rule (recommended: latest relevant case, with open/unacknowledged cases taking precedence), add `q`, `limit`, and `offset`, and keep case mutations on existing endpoints.
   - Pros: one queue request, preserves existing mutation boundaries, supports the workspace without a new case endpoint, and fits the non-goals.
   - Cons: requires a batched case lookup or join to avoid worsening the current N+1 read pattern; selection semantics must be specified because multiple cases are possible.
   - Effort: Medium

2. **Separate conversation and case requests composed in the frontend** — Keep conversation payloads unchanged and fetch cases independently for tabs/workspace.
   - Pros: smaller serializer change initially.
   - Cons: duplicates joins/client state, makes tab counts and row priority inconsistent across requests, adds loading/race states, and contradicts the report's mandatory backend context requirement.
   - Effort: High

## Recommendation

Proceed to proposal with approach 1. Treat the conversation endpoint as the unified queue read model and preserve `/cases/{id}/update` and `/cases/{id}/ack` as mutation endpoints. Define the case-selection rule before implementation: the service permits multiple rows per conversation, so “latest case” cannot remain an implicit `id DESC` assumption if an older unacknowledged emergency coexists with a newer routine case. Use a batched case query keyed by conversation IDs (or one SQL read-model query) and keep the existing per-thread delivery/reply semantics intact. Keep limit/offset pagination deliberately simple, but return enough count information for tab counts without inventing KPI metrics.

The proposal should explicitly address whether tab counts are global counts or counts for the current search/filter, whether closed conversations participate in the default query, and whether `captured_data` is exposed directly from `Conversation` or only through the case bundle. It should also define that queue refreshes are debounced or limited to snapshot events, because the current components refetch for every conversation/message event and the full snapshot serializes every conversation.

## Risks

- **Case ambiguity:** multiple cases can share one conversation; an unspecified selection rule can show the wrong emergency/status in the queue.
- **Read amplification:** `_conversation_payload()` already performs latest-inbound and delivery-summary queries per row; naïvely querying a case per row will compound N+1 behavior, especially for realtime snapshots.
- **Index mismatch:** `idx_conversations_active_recency` covers only non-null `last_message_at` for bot/human states. The current list includes closed/null-recency rows, and priority ordering involving case fields will not be covered by that partial index.
- **Realtime load:** the snapshot is a full conversation list and is serialized through the same payload helper; adding case context increases snapshot work and payload size.
- **Count semantics:** the backend currently returns only rows, while live tab counts need a defined scope and likely a count field or a bounded count strategy.
- **Compatibility behavior:** `/panel/app/cases` currently remains a distinct selected segment and renders `CasesList`; changing it to the unified queue must preserve bookmarked URL behavior and active-tab state.
- **Contract drift:** frontend mocks/types and functional tests assert exact serializer keys; changing the payload without updating those fixtures will create misleading failures.

## Ready for Proposal

Yes. The existing architecture supports the change, and the report's primary facts are verified. The proposal should carry forward the unified read-model approach and resolve the case-selection, count-scope, captured-data source, and realtime-refresh semantics before specification.

## Graph Check

- Graph exists and is non-empty: `graphify-out/graph.json`; report read from `graphify-out/GRAPH_REPORT.md`.
- God nodes consulted: `Conversation` (99 edges), `Case` (65), `Message` (96), `Customer` (102), and `session_scope()` (51).
- Communities consulted: `Panel API Serializers`, `Conversation API Tests`, `Case API Tests`, `Cases Service`, `Case Management API`, `Conversation API Client`, `Conversation List Stories`, `Realtime Client`, `Panel WebSocket`, `Panel UI & Routing`, `Cases List UI`, `Design System Primitives`, and `UI Components Grammar`.
- Queried paths: `routes/conversations.py -> serializers.py` (imports); `routes/conversations.py -> models.py <- routes/cases.py`; `ConversationsList.tsx -> api.ts <- ConversationThread.tsx`; `panelRoutes.ts <- CasesList.tsx`.
- Focused graph query: panel conversations/cases/serializer/routes/realtime and `ConversationsList`/`RealtimeSnapshot` queue refresh dependencies.

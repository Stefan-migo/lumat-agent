# Design: Panel Conversations Redesign

## Technical Approach

Keep `/panel/api/conversations` as the unified read model and preserve case mutations. A SQLAlchemy query joins `Conversation`/`Customer` to a ranked case subquery; list, detail, and snapshot use the same serializer. The SPA uses local state plus `api.ts`/`realtimeClient`.

## Architecture Decisions

| Decision | Choice | Alternatives / rationale |
|---|---|---|
| Case read model | Ranked `Case` subquery (`row_number` per conversation), outer-joined to conversations/customer; serialize query tuples. | Avoids N+1 without a materialized table or new schema. Graph nodes: `Conversation`, `Case`, `serializers.py`, `routes/conversations.py`. |
| Case precedence | Unacknowledged emergency, then open/unacknowledged, then newest remaining; ties use `created_at DESC, id DESC`. “Open” means `closed_at IS NULL` and status is not a closed/finalized value. | Case list order is not reused: selection is a deterministic operational rule shared by list/detail/snapshot. |
| Queue contract | `{items, total, offset, limit, counts}`; retain `conversations` temporarily if needed. `q` uses SQL `ILIKE` over customer name, phone, and summary. Clamp `limit`; reject negative offset. | No cursor, client filtering, or N count queries. |
| Counts | One grouped conditional-count query over the same filtered base relation; counts are global to the current search/legacy filters, while tabs apply locally in the UI. | Five requests or five correlated queries add complexity without value. |
| Frontend state | Local `useState`/`useEffect` plus existing API client; tab, query, page, selected row, loading, and mutation state live in the queue/workspace. | No state library or cache layer: one consumer and authoritative refetches do not justify it. Graph nodes: `ConversationsList.tsx`, `api.ts`, `realtime.ts`. |

## Data Flow

Current GET is unpaginated and only filters state/assignee, with per-row read work. The unified endpoint adds SQL search, selected case/customer context, limit/offset, and counts.

`GET conversations (q, limit, offset)` → filtered base → ranked case join → rows + total + grouped counts → queue.

`GET conversation/{id}` → conversation/customer + selected case + chronological messages → thread and right context panel.

Case ack/take/state command → existing mutation → authoritative queue/thread refetch. Snapshot → update realtime state → one debounced queue refetch; the open thread may refresh immediately. The recency ordering uses the existing `last_message_at` partial index; the query must retain `last_message_at DESC NULLS LAST, id DESC`.

## File Changes

| File | Action | Description |
|---|---|---|
| `app/panel/api/serializers.py`, `app/panel/api/routes/conversations.py` | Modify | Add customer, nullable selected-case fields, flexible `captured_data`; implement joined read model, q, pagination, counts, and detail parity. |
| `app/panel/api/routes/realtime.py` | Modify | Produce the same queue rows/counts and case precedence as REST snapshot. |
| `web/src/types.ts`, `web/src/api.ts`, `web/src/realtime.ts` | Modify | Type envelope/case/customer/captured data, query parameters, counts, and snapshot refresh contract. |
| `web/src/components/pages/ConversationsList.tsx` | Modify | Queue tabs, priority ordering, search, pagination, selected rows, Tomar/Reconocer. |
| `web/src/components/pages/ConversationThread.tsx` | Modify | Thread-main/right-panel workspace with case, customer, and collapsible captured data. |
| `web/src/components/domain/AppShell.tsx`, `panelRoutes.ts` | Modify | Resolve `/cases` to conversations with `Casos`; stop mounting `CasesList`. Retire `CasesList.tsx` after compatibility tests pass. |

## Interfaces / Contracts

```text
Conversation: { ..., customer: CustomerSummary, case: CaseSummary | null,
  case_id: number | null, emergency: boolean, acknowledged_at: string | null,
  case_status: string | null, case_priority: string | null,
  captured_data: Record<string, unknown> | null }
QueueResponse: { items: Conversation[], total: number, offset: number,
  limit: number, counts: { all: number, human: number, emergency: number,
  case: number, closed: number } }
```

## Testing Strategy and Auto-chain Slices

| Slice (≤400 authored lines) | Scope and RED→GREEN tests |
|---|---|
| A — Backend read model | `tests/functional/test_api_conversations.py`: case precedence, nullable context, q fields, limit/offset envelope, counts, ordering, and detail parity; `tests/functional/test_api_cases.py`: ack remains authoritative. `tests/functional/test_api_realtime.py`: snapshot parity. |
| B — Queue UI | `ConversationsList.test.tsx`, `api.test.ts`, and relevant primitive tests: tabs/counts/order, q/page requests, empty/error states, direct DOM rows, Tomar/Reconocer refresh. |
| C — Workspace and routing | `ConversationThread.test.tsx`, `panelRoutes.test.ts`, `AppShell.test.tsx`: right blocks, arbitrary captured data/empty state, live refresh coalescing, `/cases` soft redirect, and no `CasesList` mount. |

Each slice is independently testable and revertible; B can use a typed fixture contract, and C can use controlled thread data while A is merged.

## Threat Matrix

Routing is applicable: `/panel/app/cases` resolves safely to conversations with `Casos`; malformed paths fall back to dashboard; parsing performs no mutation. RED tests cover bookmarked/malformed routes and no `CasesList` mount. Other matrix boundaries are N/A: documentation-like paths (no execution), Git repository selection (no Git command), commit state (no commit automation), push state (no push), and PR commands (no PR automation).

## Migration / Rollout

No database migration required. Ship A, then B, then C. Keep case mutation routes unchanged; remove `CasesList` only after route and regression tests pass. Roll back slices independently, frontend first.

## Open Questions

- [ ] Confirm the project’s exact closed-case status vocabulary before implementing the “open” predicate.

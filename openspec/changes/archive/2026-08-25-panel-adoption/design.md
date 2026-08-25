# Design: Panel Adoption — Real SPA consumes the design system + JSON API

## Technical Approach

Extract the redesigned page components from story files into `web/src/components/pages/` as data-driven components (controlled via props for stories/tests, self-fetching for the app), preserve every story export through thin wrappers (R7), wire AppShell's existing D7 state routing to real pages, add the single missing backend endpoint (`GET /panel/api/conversations`, AP-9), and adapt the Dashboard to real `compute_kpis` counts. No router, no new deps, no pagination, no composer/activity feed (ponytail).

## Architecture Decisions

| Decision | Options | Choice | Rationale |
|---|---|---|---|
| D1 Routing | react-router vs D7 state | **D7**: AppShell `useState<PanelView>`; drill-downs via onClick state (PNL-APP-1) | Already implemented; zero deps; router is a documented follow-up |
| D2 Extraction | Rewrite stories vs extract+wrapper | **Extract to `components/pages/`; story files become thin wrappers** | R7: story tests import views from story files with `{state}` props; wrappers map story state → real props + mockData; mockData stays story-only (PNL-APP-5) |
| D2b Component contract | Presentational vs self-fetching | **Dual-mode**: `{data?, state?, onRetry?, actions?}` — `state` given → controlled; omitted → `useAsyncData` self-fetch | One component, both consumers, ~5 lines; container/presentational split is yagni at this scale |
| D3 Data layer | Per-page state machines vs shared hook | **`useAsyncData<T>(fetcher)` in new `web/src/hooks/useAsyncData.ts`** (~25 lines) | 9 consumers justify one tiny hook; kills ~15 lines × 9 pages of duplicate fetch state |
| D3b api.ts | Per-resource helpers vs generic | **Add only `postJson<T>(path, body?)`** | 5+ POST sites (login/logout/case/kb/settings); GET reads stay one-line `apiFetch<T>`; no client class (yagni) |
| D4 Auth | Token vs cookie | **Keep same-origin cookie**; LoginForm `POST /panel/api/login`; logout button in PanelShell user block → App `onLogout` resets gate to `anon` | Backend contract confirmed (`api/routes/auth.py`: `{ok, role}`, 401 details verbatim); UI never reveals account existence |
| D5 Backend | Skip vs add list endpoint | **Add route to `api/routes/conversations.py`** | Envelope `{"conversations": [...]}` + `to_conversation_dict` (no assignee — confirmed in serializers.py); ordering `last_message_at DESC NULLS LAST, id DESC`; extend existing `test_api_conversations.py` |
| D6 Dashboard | Backend parity vs adapt | **Adapt**: 3 StatCards (contacts, derived, visit_requests) + motivos list + window caption | `compute_kpis` has no deltas/autonomy/response-time; parity = inventing metrics (YAGNI); activity feed dropped (PNL-APP-8) |
| D7 Delivery | One PR vs chained | **6 slices, stacked-to-main, ≤400 lines, RDD review per slice** | Review budget 400; S3/S5/S6 split internally when estimates exceed |

## Data Flow

```
LoginForm ─POST /login─► session cookie ─► App ─probe /me─► AppShell ─view─► PanelShell nav
                                                                │
                    ┌── useAsyncData ── apiFetch<T> ──► JSON API ──► serializers ──► DB
                    ▼
        components/pages/XXX ── StateMessage/DataTable/StatCard (_shared) ──► DOM
```

## Preserved Story Exports (R7 — thin wrappers only)

| Story file | Exports preserved by wrapper |
|---|---|
| `Dashboard.stories.tsx` | `DashboardOverview` |
| `Login.stories.tsx` | `LoginAuth`, `LoginDefault`, `LoginError`, `LoginLoading` |
| `ClientesList.stories.tsx` | `ClientesListView`, `ClientesListEmpty` |
| `ClientFicha.stories.tsx` | `ClientFichaView`, `NoMemo` |
| `ConversationsList.stories.tsx` | `ConversationsListView`, `ConversationsListEmpty`, `assigneeForConversation` (demo helper stays story-local; real page drops the Asignado column) |
| `ConversationThread.stories.tsx` | `ConversationThreadView`, `ConversationThreadBubbles`, `NoReplyNote` |
| `CasesList.stories.tsx` | `CasesListView`, `CasesListEmpty` |
| `KbList.stories.tsx` | `KbListView`, `KbListEmpty` |
| `Settings.stories.tsx` | `SettingsView` |

Not touched (non-goals / already domain): `InboxThread`, `ChatWithAgent`, `PanelEntry`, `ClientMemories` stories.

## File Changes

| Slice | File | Action |
|---|---|---|
| S1 | `web/src/api.ts` | Modify — add `postJson` |
| S1 | `web/src/components/pages/LoginAuth.tsx` | Create — real form (loading/error, username preserved) |
| S1 | `web/src/app.tsx` | Modify — anon → LoginAuth; `onLogout` |
| S1 | `web/src/components/domain/{AppShell,PanelShell}.tsx` | Modify — `onLogout` prop + user-block "Cerrar sesión" button |
| S1 | `web/src/stories/pages/Login.stories.tsx` | Modify — wrapper |
| S2 | `web/src/hooks/useAsyncData.ts` | Create |
| S2 | `web/src/components/pages/Dashboard.tsx` | Create — Kpis → StatCards + motivos |
| S2 | `web/src/components/domain/AppShell.tsx` | Modify — view→page map (unwired views keep placeholder) |
| S2 | `web/src/stories/pages/Dashboard.stories.tsx` | Modify — wrapper |
| S3a | `web/src/components/pages/ClientesList.tsx` + `ClientesList.stories.tsx` | Create/Modify — `?q=` search |
| S3b | `web/src/components/pages/ClientFicha.tsx` + `ClientFicha.stories.tsx` | Create/Modify — drill-down; reuses domain `ClientMemories` |
| S4 | `web/src/components/pages/CasesList.tsx` + `CasesList.stories.tsx` | Create/Modify — update/ack + refetch |
| S5a | `app/panel/api/routes/conversations.py` | Modify — list route |
| S5a | `tests/functional/test_api_conversations.py` | Modify — shape, ordering, 401 |
| S5a | `web/src/types.ts` | Modify — `ConversationsResponse` |
| S5a | `web/src/components/pages/ConversationThread.tsx` + story | Create/Modify |
| S5b | `web/src/components/pages/ConversationsList.tsx` + story | Create/Modify — no Asignado; thread drill-down |
| S6a/b | `web/src/components/pages/{KbList,Settings}.tsx` + stories | Create/Modify — 403 → denied state; save flows |

## Interfaces / Contracts

```ts
// api.ts
export async function postJson<T>(path: string, body?: unknown): Promise<T>

// hooks/useAsyncData.ts
// returns { data: T | null; state: 'loading'|'ready'|'empty'|'error'|'denied'; retry(): void }
// 'denied' = ApiError status 403 (admin views, PNL-APP-6)

// types.ts — add
export interface ConversationsResponse { conversations: Conversation[] }

// components/pages/XXX props
{ data?: T | null; state?: PageState; onRetry?: () => void; ...pageActions }
```

```python
# app/panel/api/routes/conversations.py — add
@router.get("/conversations")
def conversations_list(
    session: Session = Depends(get_db),
    current: User = Depends(require_user_json),
) -> dict:
    rows = session.scalars(
        select(Conversation).order_by(
            Conversation.last_message_at.desc().nulls_last(),
            Conversation.id.desc(),
        )
    ).all()
    return {"conversations": [to_conversation_dict(c) for c in rows]}
```

## Testing Strategy

| Slice | Layer | What | How |
|---|---|---|---|
| S1 | vitest | login ok/401/lock; logout resets gate | `app.test.tsx` fetch-stub pattern; Login story test stays green |
| S2 | vitest | Dashboard counts, no deltas/feed; nav switch | fetch-stub `/kpis`; `AppShell.test.tsx` |
| S3/S4 | vitest | search, ficha sections, update/ack refetch | fetch-stub per endpoint |
| S5a | pytest | 200 shape, nulls-last ordering, 401 | extend `test_api_conversations.py` |
| S5b | vitest | inbox rows, no Asignado, thread drill-down | fetch-stub list + thread |
| S6 | vitest | 403 → denied (operador); save flows | fetch-stub 403 |

## Threat Matrix

N/A — no shell command, subprocess, VCS/PR automation, executable-classification, or process-integration boundary in this change. The single new FastAPI route is declarative with the same `require_user_json` dep as its siblings; chained-PR mechanics live in the orchestrator, not in the changed code.

## Migration / Rollout

No data migration. Per-slice revert — each slice lands independently (stacked-to-main). The endpoint is additive: dropping S5a removes route + tests only. RDD review per slice (auto | both | auto-chain, budget 400).

## Open Questions

- [ ] Dashboard card labels/copy for raw counts (honest Chilean-Spanish labels + window caption format)
- [ ] ConversationsList columns without Asignado (which real fields replace the demo column)
- [ ] `stale`/`partial-error` story states: app-side or story-only (ponytail: story-only unless the page refetches)
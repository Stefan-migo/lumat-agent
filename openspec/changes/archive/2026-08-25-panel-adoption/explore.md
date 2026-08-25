# Exploration — Panel Adoption (2026-08-24-panel-adoption)

> Phase: sdd-explore · Artifact store: hybrid (openspec + Engram) · Session: auto | both | auto-chain | review budget 400
> Graph: `graphify-out/` present (stale vs HEAD @ a84a188a; NOT rebuilt — session-close refresh only).

## Current State

The real SPA (`web/`) is only an auth gate:

- `web/src/main.tsx` mounts `<App/>`; `web/src/app.tsx` probes `GET /panel/api/me` and renders:
  - `authed` → `<AppShell user/>` (role-gated nav + placeholder page)
  - `anon` → inline "Para continuar debes iniciar sesión." stub (comment: "LoginForm replaces it in T11.1 (B11)" — **no LoginForm exists anywhere**)
  - `error` → inline retry
- `web/src/api.ts` has only `apiFetch<T>` + `ApiError` (same-origin, `credentials: 'include'`, JSON-401 aware). No typed endpoint helpers, no login/logout calls.
- `web/src/types.ts` already mirrors the JSON serializers (User, LoginResponse, Customer, CustomerNote, Memory, Kpis, Conversation, Message, ConversationThread, UserRef, Case, CasesResponse, Doc, DocsResponse, SpendSnapshot, Settings, ClientFichaResponse). No conversation-*list* type.
- **Routing: D7 decision, documented in AppShell.tsx** — *no router* (`ponytail:` no URL shareability; upgrade path = react-router hash router). `web/package.json` has **no router dependency** (only react/react-dom). AppShell keeps `useState<PanelView>` view switching; PanelShell owns the chrome + `NAVIGATION` map (6 views: dashboard, clients, conversations, cases, kb, settings; kb+settings `adminOnly`).
- **No logout affordance** in PanelShell today (sidebar user block is display-only).

The design system (Calma Operacional) is complete: primitives in `web/src/components/primitives/` (Button, Input, Select, Textarea, Badge, Avatar, StatusBadge, SearchInput, Card, Tabs, Dialog, FieldShell) + `web/src/components/domain/` (AppShell, PanelShell, **ClientMemories**). The page-level helpers — **DataTable, StateMessage, FlashMessage, EmptyState, PageHeader, PageFrame, StatCard, toneMaps — live under `web/src/stories/pages/_shared/`, not in components/** (the launch brief's "primitives" list overstates this). Precedent: `components/domain/ClientMemories.tsx` already imports `_shared/DataTable` + `PageHeader`, so importing from `stories/_shared` is the established (if awkward) pattern.

The 10 redesigned page stories all define their page components **inline in the story file** (e.g. `DashboardOverview` in `Dashboard.stories.tsx`, `LoginAuth` in `Login.stories.tsx`) with `excludeStories` exports; story tests import the view from the story file (`import { DashboardOverview } from "./Dashboard.stories"`). None are importable by the app as-is.

## Backend API surface (JSON, all `require_user_json` / `require_admin_json`, 401/403 JSON never 302, same-origin cookie, no CSRF — same_site=lax)

| Endpoint | Auth | Shape | Matches story? |
|---|---|---|---|
| `POST /panel/api/login` | — | `{username, password}` → `{ok, role}`; 401 `invalid credentials`/`account locked` | Login story (needs form) |
| `GET /panel/api/me` | user | `{username, role}` | app gate |
| `POST /panel/api/logout` | user | `{ok}` | **no UI exists** |
| `GET /panel/api/kpis` | user | `compute_kpis`: `{contacts, motivos:[(service,count)], derived, visit_requests, window_days, window_start}` | **PARTIAL — see risk R1** |
| `GET /panel/api/clients?q=` | user | `{clients:[to_customer_dict], query}` (cap 100) | ClientesList ✓ |
| `GET /panel/api/clients/{id}` | user | `{customer, history, notes, memo, states}` | ClientFicha ✓ |
| `POST /panel/api/clients/{id}/state` · `/notes` · `/memories` (GET/POST/DELETE/mark) | user | CR-3/CR-4/MEM-6 wrappers | Ficha actions ✓ |
| `GET /panel/api/cases` | user | `{cases:[to_case_dict + embedded customer], users}` — **open cases only**, escalated first | CasesList ✓ (mock includes closed rows that never appear) |
| `POST /panel/api/cases/{id}/update` · `/ack` | user | `{ok, case}` | CaseActions (display-only today) |
| `GET /panel/api/conversations/{id}` | user | `{conversation, messages}` (read-only thread) | ConversationThread ✓ |
| **`GET /panel/api/conversations` (list) — DOES NOT EXIST** | — | — | ConversationsList ✗ (story itself documents the gap) |
| `GET/POST /panel/api/kb` · `POST /kb/{id}/edit|disable|restore` | **admin** | `{docs:[to_doc_dict]}` | KbList ✓ |
| `GET /panel/api/settings` · `POST /settings/{scope,keywords,tone,limits,meta}` | **admin** | full Settings shape + snapshot | Settings ✓ |

Jinja templates confirm: `conversations/thread.html` exists, **no conversations list template** — the redesigned ConversationsList (inbox) view has no backend counterpart at all. InboxThread's state controls (tomar/cerrar/devolver) and composer have **no backend support** (conversations read-only by design, HH-5). ChatWithAgent is a deliberate non-model mock (H4 future capability), not in NAVIGATION.

## Mock-data ↔ serializer drift

- **Dashboard (R1 — the big one)**: mock `kpis` are presentation cards `{label, value, delta, deltaTone}` (Conversaciones / Resolución autónoma / Tiempo de respuesta with deltas) — `compute_kpis` returns raw SQL counts and computes **no deltas, no autonomy %, no response time**. The story's `activity` feed (Avatar + event rows) has **no backend source** in the JSON API.
- **Cases**: shapes match exactly; mock's `cerrado` rows never come from the API (open-only endpoint).
- **Conversations**: `Conversation`/`Message` match serializers exactly; the inbox's **Asignado column is demo-only** (conversations have no responsible field — the story comment says so).
- **Clients, KB, Settings**: match serializers field-for-field (snake_case, ISO strings, nullable timestamps).

## Affected Areas

- `web/src/app.tsx` — anon stub → real LoginForm; gate wiring
- `web/src/api.ts` — login/logout (and possibly per-resource) helpers or stay generic `apiFetch`
- `web/src/components/domain/AppShell.tsx` — view switch renders real pages (D7 state routing)
- `web/src/components/domain/PanelShell.tsx` — logout affordance (user block / header)
- `web/src/stories/pages/*.stories.tsx` (10) — extract inline components → thin story wrappers re-importing from `components/pages/` (keeps story tests green)
- `web/src/stories/pages/_shared/*` — DataTable/StateMessage/PageFrame/EmptyState/FlashMessage/PageHeader/StatCard/toneMaps: consumed by extracted pages (import path decision)
- `web/src/components/pages/*` (NEW) — extracted page components consuming props (data) instead of mockData
- `web/src/types.ts` — possibly a `ConversationsListResponse` if a list endpoint lands
- `app/panel/api/routes/conversations.py` (+serializers) — **only if** the list endpoint is added (recommended)
- `app/panel/api/routes/dashboard.py` — **only if** an activity/trend source is added (optional)
- `web/src/app.test.tsx`, `api.test.ts`, `AppShell.test.tsx` + new page tests; backend `tests/functional/test_api_*.py` if endpoints are added

## Approaches

1. **Full adoption with thin backend additions** (recommended)
   Add `GET /panel/api/conversations` (thin wrapper over a conversation+customer list query, same serializer pattern, ~80-100 lines + tests) and adapt the Dashboard to render `compute_kpis` in the designed card style (map contacts/derived/visit_requests → cards, motivos → list; **drop the activity feed and fabricated deltas** — or add a small activity endpoint later). Extract all 10 story components into `components/pages/` with `data` props + state variants; keep importing `_shared` helpers (ClientMemories precedent); wire AppShell view switch; real LoginForm; logout; admin pages handle 403.
   - Pros: every NAVIGATION view becomes real; no dead UI; conversations list is a small, pattern-following addition
   - Cons: backend changes expand scope; Dashboard loses the designed "wow" cards unless backend extends
   - Effort: High (~1600-2000 lines total, chained)

2. **Frontend-only adoption, scope pages to existing API**
   Adopt only pages with a live endpoint (Dashboard adapted to counts, ClientesList, ClientFicha, CasesList, ConversationThread, KbList, Settings). **Skip ConversationsList + InboxThread** (no backend) or render them with a "no data" state; ChatWithAgent stays story-only.
   - Pros: zero backend risk; smaller surface
   - Cons: a designed nav view (Conversaciones) dead-ends — worse product outcome; the gap stays forever
   - Effort: Medium (~1300 lines, chained)

3. **Adopt + full backend parity** (Dashboard activity/trend endpoints too)
   Everything in (1) plus new backend metrics (autonomy %, response time, trend deltas, activity feed) to match the story cards exactly.
   - Pros: pixel-faithful to the reference design
   - Cons: inventing product metrics that don't exist anywhere (YAGNI risk); significantly larger backend surface
   - Effort: High (backend-heavy)

## Recommendation

**Approach 1** — adopt all NAVIGATION views with real API consumption, adding only the minimal backend gap that makes a designed nav view functional (`GET /panel/api/conversations`), and adapt the Dashboard to the *real* KPI data in the designed card style rather than inventing metrics. Keep the D7 no-router decision (homegrown view state — already implemented, `ponytail:` note documents the upgrade path). Do NOT move `_shared` helpers out of stories in this change (import from them as ClientMemories already does; a cleanup slice can come later). Keep ChatWithAgent + InboxThread composer/state-controls story-only (out of scope, no backend). Logout goes into the PanelShell user block.

## Chained slices (review budget 400, stacked-to-main)

1. **S1 Auth + gate** (~400): LoginForm extraction (`LoginAuth` → real `<form>` + submit → `POST /panel/api/login`, error/loading), `app.tsx` anon → LoginForm, logout button + `POST /panel/api/logout`, `api.ts` helpers, tests.
2. **S2 Shell wiring + Dashboard** (~380): AppShell view → page map (placeholders for unwired views), extract `Dashboard` → `components/pages/Dashboard.tsx` consuming `Kpis` (adapted cards), fetch `/kpis`, tests.
3. **S3a ClientesList** (~200) + **S3b ClientFicha** (~250): list with `?q=` search + ficha drill-down (history/notes/state/memories — ClientMemories already exists), tests.
4. **S4 CasesList** (~350): `/cases` list + CaseActions wired to update/ack with refetch, tests.
5. **S5 Conversations** (~420 → split if needed): **backend `GET /panel/api/conversations`** (~100, + tests) + `ConversationThread` drill-down (~150) + `ConversationsList` inbox (~170, no assignee column or "—").
6. **S6a KbList** (~200) + **S6b Settings** (~230): admin pages with 403 handling, save flows, tests.

Total ~1800-2000 changed lines → **chained PRs mandatory** (auto-chain already chosen by orchestrator). Each slice lands independently against main.

## Risks

- **R1 Dashboard mock→API drift**: designed cards (autonomy %, response time, deltas) + activity feed have no backend computation. Must decide: adapt-to-real (recommended) vs backend parity (scope creep).
- **R2 Conversations list endpoint missing** (backend) + **Asignado column demo-only** (conversations have no responsible field). Either add the endpoint (recommended) or drop the view.
- **R3 InboxThread interactions have no backend** (conversations read-only, HH-5): composer + tom/cerrar/devolver controls can't be wired; adopt read-only thread or keep story-only.
- **R4 Router**: D7 says no router; story links use `#/clientes/1` hash hrefs that are inert without a router. State-based views mean no URL shareability — accepted tradeoff (documented), deep links need onClick handling.
- **R5 `_shared` helpers live under stories/**: adoption deepens the coupling (ClientMemories precedent). Accept + `ponytail:` note, or dedicate a slice to relocating them (wide mechanical diff).
- **R6 Role gating**: kb/settings are adminOnly — extracted pages must render a 403/empty state for operadores (ApiError status 403) and nav already hides them.
- **R7 Tests**: story tests import views from story files — extraction must preserve export names (thin re-export) or update ~10 test files. App-level tests follow the `app.test.tsx` fetch-stub pattern. Backend tests needed only for the new conversations endpoint.
- **R8 Budget**: total well over 400 lines; every slice must stay ≤400 and land independently (stacked-to-main). Slice S5 may need splitting (backend + thread vs inbox).

## Ready for Proposal

**Yes.** The scope decision for `sdd-propose` is Approach 1 vs 2 — the pivotal question is whether the backend additions (conversations list; possibly dashboard adaptation instead of parity) are in scope. The orchestrator should confirm with the user: (a) add `GET /panel/api/conversations` (recommended) vs drop the Conversaciones view; (b) Dashboard renders real `compute_kpis` counts (recommended) vs extend backend for the designed cards.

## Graph nodes consulted

`AppShell.tsx` (View/VIEW_LABELS/AppShell), `PanelShell.tsx` (NAVIGATION/PanelView/PanelShell), `app.tsx` (App/GateState), `api.ts` (apiFetch/ApiError), `types.ts` (User/Kpis/Settings/Case/ClientFichaResponse), `Dashboard.stories.tsx` (DashboardOverview), `Login.stories.tsx` (LoginAuth), `ConversationsList.stories.tsx` (ASSIGNEE_BY_CONV), `InboxThread.stories.tsx`, `CasesList.stories.tsx`, `ClientesList.stories.tsx`, `KbList.stories.tsx`, `Settings.stories.tsx`, `ClientFicha.stories.tsx`, `ConversationThread.stories.tsx`, `ChatWithAgent.stories.tsx`, `PanelEntry.stories.tsx`, `ClientMemories.tsx`, `app/panel/api/{routes/auth,dashboard,clients,cases,conversations,kb,settings}.py`, `app/panel/api/{deps,serializers}.py`, `app/panel/routes/dashboard.py` (compute_kpis), `app/models.py` (Case), `stories/pages/_shared/*`, `mockData/{dashboard,cases,conversations,settings,clients,kb,chat}.ts`, `app.test.tsx`, `api.test.ts`, `AppShell.test.tsx`, `Dashboard.stories.test.tsx`, `vite.config.ts`, `web/package.json`, `web/index.html`.
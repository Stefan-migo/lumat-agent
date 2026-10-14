# ODD — chatbot-metrics-panel

Feature: `chatbot-metrics-panel` (Frente 2, unit 5 — UI)
Branch: `odd/chatbot-metrics-panel` · Cut from `origin/main` = `41e517ff`
Delivery: single PR · Test runner: `uv run pytest tests/` (backend) + `npm test` / `npm run build` (web)

## Objective

Give the owner a **panel surface for the chatbot's quality metrics** — the one Frente 2 gap.
Today `analytics.chatbot_metrics` / `chatbot_conversations` are reachable **only** by asking the
assistant chat; the panel dashboard shows operational KPIs (contacts/cases/appointments), nothing
about the bot. Ship a **new admin-only page** that renders those metrics with a window selector and
a **drilldown** to the conversations that tripped each failure signal. Read-only: no writes, no
migrations, no assistant-tool changes.

## Specs

**S1 — New backend router `app/panel/api/routes/analytics.py`, registered in
`app/panel/api/__init__.py`.** `router = APIRouter(tags=["panel-api-analytics"])`, included under
the existing `/api` prefix (full path `/panel/api/analytics/...`). Delegates to `app/services/analytics.py`;
**no business logic in the route**.

**S2 — `GET /panel/api/analytics/chatbot?window_days=` → `analytics.chatbot_metrics(session, window_days)`.**
Auth `require_admin_json` (`app/panel/api/deps.py:64`). Returns the service dict unchanged:
`conversations`, `handoffs`, `handoff_rate`, `containment_rate`, `handoff_reasons`,
`unknown_intents`, `kb_hits`, `kb_misses`, `kb_hit_rate`, `turns_to_resolve`,
`cost_per_conversation`, `window_days`.

**S3 — `GET /panel/api/analytics/chatbot/conversations?signal=&window_days=&limit=` →
`analytics.chatbot_conversations(session, window_days, signal, limit)`.** Auth `require_admin_json`.
`signal` ∈ `CHATBOT_SIGNALS = ("escalation", "unknown_intent", "kb_miss", "any")` — anything else
refused (422/400), never a silent default. Returns `{window_days, signal, conversations:[{conversation_id,
customer_id, wa_phone, state, last_message_at, signals:{escalation,unknown_intent,kb_miss}}]}`.

**S4 — Authorization.** ADMIN → 200. OPERADOR/TECNICO → 403. Unauthenticated → **JSON 401**
(`{"detail": ...}`), never a 302 to the HTML login page (panel JSON dependency, PDW-AUTH-1).

**S5 — Frontend route + nav.** New `PanelView` `chatbot-metrics` in
`web/src/components/domain/PanelShell.tsx`: add to the `PanelView` union, to `NAVIGATION` with
`adminOnly: true` and a bot/metrics icon + Spanish label, add the `BREADCRUMB_OVERRIDES` entry; add
`'chatbot-metrics': '/panel/app/chatbot-metrics'` to `PANEL_ROUTES` in `panelRoutes.ts`; add the
`view === 'chatbot-metrics' ? <ChatbotMetrics />` branch in `AppShell.tsx`. Non-admins never see the
nav item (`adminOnly` filter already exists).

**S6 — Page `web/src/components/pages/ChatbotMetrics.tsx`** (+ `ChatbotMetrics.css` + `.test.tsx`):
renders the metrics as stat cards/figures; loading/empty/error states reuse the existing
`PageFrame` / `StateMessage` / `EmptyState` primitives.

**S7 — Window selector.** 7 / 30 days, default **7**. Changing it refetches both endpoints with the
new `window_days`.

**S8 — Drilldown.** Each failure signal (`unknown_intent`, `kb_miss`, escalation/handoff) is
clickable → fetches `.../chatbot/conversations?signal=...` and shows a table (conversation id,
customer, signal counts, last message). Clicking a row opens the existing `ConversationThread`
via the router (`navigateToRoute({ view: 'conversations', conversationId })`) — do NOT build a new
thread view.

**S9 — Client + types.** `web/src/api.ts`: `getChatbotMetrics(windowDays)` and
`getChatbotConversations({signal, windowDays, limit})` using the existing `apiFetch` helper.
`web/src/types.ts`: `ChatbotMetrics` and `ChatbotSignalConversations` types mirroring S2/S3.

**S10 — No assistant-tool changes.** This unit touches no `app/chat/assistant/**` file, so the four
pinned tool tests (`test_tool_tiers.py`, `test_effective_config.py`, the planner-catalog SHA-256 in
`test_assistant_delegation.py`, the OPERADOR set in `test_assistant_tool_roles.py`) must stay green
**unchanged**.

## Tasks

| ID | Task | Specs | Route |
|---|---|---|---|
| T1 | RED+GREEN: `routes/analytics.py` + register router + tests (admin 200 shape, operator 403, unauth JSON 401, bad signal refused) | S1,S2,S3,S4,S10 | inline |
| T2 | RED+GREEN: nav/route wiring (`PanelView` + `NAVIGATION adminOnly` + `panelRoutes.ts` + `AppShell.tsx`) + test (admin sees item, operator does not) | S5 | inline |
| T3 | RED+GREEN: `ChatbotMetrics.tsx` + css + `api.ts` clients + `types.ts` + tests (KPIs render, window switch refetches, drilldown opens thread) | S6,S7,S8,S9 | inline |
| T4 | Checks: `npm test` + `npm run build` + targeted + full `uv run pytest tests/` | — | inline |

Single writer (parent, inline per logbook); each task closes with one work-unit commit (≤5 files).

## Constraints (verified)

- **Graph Check (Step 1) is mandatory before editing.** Graph exists at `graphify-out/`; query the
  affected modules per task and record nodes. Refresh runs once at session close.
- **Frontend type-check:** `tsc -b` lives **only** inside `npm run build`. A green Vitest suite does
  NOT prove the tree type-checks — run **both**.
- **New worktree lacks `node_modules` / `.venv` / `infra/.env`.** Provision: `npm install` in `web/`;
  `uv sync` + `cp ../lumat-agent/infra/.env infra/.env`; test DB `bash infra/test-db.sh up` +
  `eval "$(bash infra/test-db.sh env)"`.
- **Admin-only is the panel convention** for this data: `routes/settings.py` uses
  `require_admin_json`; U3 (`settings.update`) is ADMIN-only. Consistency is the rationale (D3).
- **`kpis` route caps `window_days` at `ge=1, le=31`.** Our selector stays inside that (7/30); the
  analytics route should still validate `window_days` (`ge=1, le=90` or similar) rather than trust
  the client.
- **`cost_per_conversation` iterates `conversation_spend` per conversation** (`analytics.py:63-67`).
  Keep the default window small (7) to bound query cost; no caching in this unit.
- **`require_admin_json` returns 403 for non-admins and a JSON 401 when unauthenticated** — assert
  both, do not assume a redirect.
- **Pre-merge (MANDATORY):** integrate `origin/main` into the branch + run `npm test`,
  `npm run build` and `uv run pytest tests/` over the merged tree; merge only with the PR `CLEAN`
  and HEAD == `headRefOid`.
- **RDD nativo:** do not invoke without confirming with the owner first (thread rule).

## Acceptance criteria

- AC-1: both endpoints are registered and admin-only; OPERADOR → 403; unauthenticated → JSON 401.
- AC-2: `GET /analytics/chatbot` returns the `chatbot_metrics` dict shape for a bounded window.
- AC-3: `GET /analytics/chatbot/conversations?signal=` returns the filtered conversations; an invalid
  signal is refused, not silently defaulted.
- AC-4: the new nav item is visible to ADMIN only; an OPERADOR session never sees it (and gets 403
  from the API).
- AC-5: the page renders the KPIs, a 7/30 window selector (default 7), and a working drilldown whose
  row click opens the existing `ConversationThread`.
- AC-6: `npm test` green, `npm run build` green (type-check), backend targeted + full pytest green,
  and the four pinned assistant-tool tests unchanged.
- AC-7: no file under `app/chat/assistant/**` changed.

## Checks

- `cd web && npm test && npm run build`
- `uv run pytest tests/functional/test_api_chatbot_analytics.py tests/unit/test_tool_tiers.py tests/unit/test_effective_config.py tests/unit/test_assistant_delegation.py tests/unit/test_assistant_tool_roles.py -q`
- `uv run pytest tests/ -q`

## Graph nodes consulted

`require_admin_json()` (`app/panel/api/deps.py:64`), `analytics.py` (`app/services/analytics.py:1`,
community `models.py`), `chatbot_metrics()` / `chatbot_conversations()`, `api_router`
(`app/panel/api/__init__.py:36`), `PanelShell.tsx` (`web/src/components/domain/PanelShell.tsx:1`,
community `AppShell.tsx`), `AppShell.tsx`, `types.ts` / `api.ts` (community `api.ts`),
`ConversationThread.tsx` (community `ConversationThread.tsx`), `apiFetch()` / `postJson()`
(`web/src/api.ts`). `graphify query "panel api routes analytics chatbot metrics require_admin_json"`
(879 nodes, BFS depth 2).

## Log

**L1 (user, 2026-10-14, verbatim):** "hey chat continuamos desde aca odd/handoffs/chatbot-assistant-optimizer-unit5-ui.md. dame un overview antes de continuar"

**L2 (user, 2026-10-14, verbatim):** "ok vamos con esa conversacion de scope" → scope decisions
captured in `rapso-session` `2026-10-14-chatbot-optimizer-unit5-ui` (D1-D4). Reports:
`.rapsodia-code/sessions/ready-for-odd/2026-10-14-chatbot-optimizer-unit5-ui/{session,report}.md`.

**L3 (user, 2026-10-14, verbatim):** "si abre el worktree" → explicit consent for
`rapso worktree create chatbot-metrics-panel`.

**L4 (evidence, 2026-10-14):** grounding that shrank the scope — Settings panel already edits
tone/messages/hours (`routes/settings.py`), Conversations already has a panel
(`routes/conversations.py` + `ConversationsList.tsx` + `ConversationThread.tsx`), and the four
candidate "new UI" surfaces collapse to one real gap: the chatbot metrics view. `chatbot_metrics`
lives in `app/services/analytics.py:13` and is otherwise exposed only via the assistant tools
U1/U2 (`app/chat/assistant/tools/registry.py:426,432`).

**L5 (design ref, `odd/handoffs/chatbot-assistant-optimizer-unit5-ui.md`):** U5 = new sections in
Settings + metrics/conversations view; "la parte de mensajes quedó resuelta por el catálogo (D7)".

**L6 (evidence, 2026-10-14):** T1 done. RED observed — all 6 new functional tests failed `404`
(routes absent). GREEN after `app/panel/api/routes/analytics.py` + registration in
`app/panel/api/__init__.py`: 6/6 pass. Targeted regression set green (pinned tool tests + panel
delivery + kb/settings panel API + analytics service, 241 tests). Full backend suite
`uv run pytest tests/` green (only pre-existing warnings). No `app/chat/assistant/**` file touched —
S10 held.

**L7 (evidence, 2026-10-14):** T2+T3+T4 done (`419306cb` feat, `16b2dbef` test). New
`PanelView chatbot-metrics` (NAVIGATION `adminOnly`, `Activity` icon), route in `panelRoutes.ts`,
`AppShell` branch with `onOpenConversation` → existing `ConversationThread`, page
`ChatbotMetrics.tsx` (+css), `api.ts` clients, `types.ts`. **Test-first note:** T1 had a true
RED→GREEN; for T2/T3 the surface is brand new, so the page test was authored with the component and
the nav-pinning tests were updated to the new expected state — no meaningful pre-existing RED. The
page test **did** catch a real bug: `useAsyncData` refetches only on `enabled`/`refreshKey` change,
not on a new fetcher closure, so the window selector needed `refreshKey = windowDays` (fixed in
`ChatbotMetrics.tsx`). Checks: `npm run build` green (tsc + vite — the real type-check);
full `npm test` 1188 passed + **1 pre-existing flaky** (`AgentChat > renders new stream content
while a previous markdown snapshot is stale`, timing-sensitive; passes 69/69 in isolation and no
AgentChat file was touched). Nav-pinning tests updated (`PanelShell.test.tsx` rail count 9→10 +
restricted list, `AppShell.test.tsx` drawer count 9→10 + labels + admin/operador assertions,
`panelRoutes.test.ts` key list).

## Progress

- [x] T1 — `97ac3b89` feat: admin-only `/panel/api/analytics/chatbot` + `/analytics/chatbot/conversations` (+6 functional tests)
- [x] T2 — `419306cb` feat: `chatbot-metrics` `PanelView` + nav item (adminOnly) + route + `AppShell` branch
- [x] T3 — `419306cb`/`16b2dbef` feat+test: `ChatbotMetrics.tsx` (+css) + `api.ts` clients + `types.ts` + page tests
- [x] T4 — checks: `npm run build` green (tsc + vite); full `npm test` 1188 passed + 1 pre-existing flaky; backend suite green

## Next step

Feature complete on the branch. Pending: pre-merge integration (`origin/main` into the branch +
`npm test` + `npm run build` + `uv run pytest tests/` over the merged tree) and PR.

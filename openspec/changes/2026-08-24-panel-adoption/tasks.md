# Tasks: Panel Adoption — Real SPA consumes design system + JSON API

`pages/` = `web/src/components/pages/`.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1,800–2,000 (6 slices) |
| 400-line budget risk | S1 400 Med · S2 380 Med · S3 450 High · S4 350 Med · S5 420 High · S6 430 High |
| Suggested split | PR1=S1 … PR6=S6, stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Medium

Sub-units (S3a/b, S5a/b, S6a/b) build sequentially; promote the second sub-unit to its own PR if the diff nears 400. Test base: frontend `cd web && npm test`, backend `pytest tests/`.

### Suggested Work Units

| Unit | PR | Focused test | Harness | Rollback |
|------|----|--------------|---------|----------|
| S1 | PR1 | `cd web && npm test -- app api` | N/A (fetch-stub) | revert S1 commit |
| S2 | PR2 | `cd web && npm test -- AppShell Dashboard` | N/A (fetch-stub) | revert S2 commit |
| S3 | PR3 | `cd web && npm test -- ClientesList ClientFicha` | N/A (fetch-stub) | revert S3 commits |
| S4 | PR4 | `cd web && npm test -- CasesList` | N/A (fetch-stub) | revert S4 commit |
| S5a | PR5 | `pytest tests/functional/test_api_conversations.py` | `curl /panel/api/conversations` w/ cookie | drop route+tests |
| S5b | PR5 | `cd web && npm test -- ConversationsList ConversationThread` | N/A (fetch-stub) | revert S5b commit |
| S6 | PR6 | `cd web && npm test -- KbList Settings` | N/A (fetch-stub) | revert S6 commits |

## Phase 1 — S1 Auth + gate (commit: `feat(web): real login gate with logout`)

- [x] 1.1 RED `app.test.tsx`+`api.test.ts`: login ok/401-keep-username/locked; logout→login; `postJson` POST+error
- [x] 1.2 GREEN `api.ts` `postJson<T>`; create `pages/LoginAuth.tsx` (loading/error, keeps username, no account leak)
- [x] 1.3 GREEN `app.tsx` anon→LoginAuth+`onLogout`; `AppShell`/`PanelShell` `onLogout`+"Cerrar sesión" in user block
- [x] 1.4 GREEN `Login.stories.tsx` wrapper (exports `LoginAuth/LoginDefault/LoginError/LoginLoading`); story test green

## Phase 2 — S2 Shell+Dashboard (commit: `feat(web): shell view map + real KPI dashboard`)

- [x] 2.1 RED `AppShell.test.tsx`+Dashboard tests: nav→pages; StatCards counts; no deltas/feed
- [x] 2.2 GREEN create `hooks/useAsyncData.ts` (loading/ready/empty/error/denied+retry; 403→denied)
- [x] 2.3 GREEN create `pages/Dashboard.tsx` — Kpis→StatCards (contacts/derived/visit_requests)+motivos+window caption
- [x] 2.4 GREEN `AppShell.tsx` view→page map (unwired placeholder); `Dashboard.stories.tsx` wrapper (`DashboardOverview`)

## Phase 3 — S3 Clientes (commit: `feat(web): client list search + ficha drill-down`)

- [ ] 3.1 RED ClientesList tests: `?q=` search, empty "No hay registros"
- [ ] 3.2 GREEN create `pages/ClientesList.tsx` + wrapper (`ClientesListView/ClientesListEmpty`)
- [ ] 3.3 RED ClientFicha tests: sections render, no-memo state
- [ ] 3.4 GREEN create `pages/ClientFicha.tsx` (reuses `ClientMemories`) + wrapper (`ClientFichaView/NoMemo`)

## Phase 4 — S4 Cases (commit: `feat(web): cases list with update/ack refetch`)

- [ ] 4.1 RED CasesList tests: rows render; update/ack POST→refetch
- [ ] 4.2 GREEN create `pages/CasesList.tsx` (CaseActions→update/ack+refetch) + wrapper (`CasesListView/CasesListEmpty`)

## Phase 5 — S5 Conversations, backend first (commits: `feat(panel): add GET /panel/api/conversations list endpoint`; `feat(web): conversations inbox + read-only thread`)

- [ ] 5.1 RED extend `tests/functional/test_api_conversations.py`: 200 shape `{"conversations":[...]}`, no assignee key, `last_message_at DESC NULLS LAST, id DESC`, 401 JSON
- [ ] 5.2 GREEN add `/conversations` list route (`app/panel/api/routes/conversations.py`, select+order_by, `to_conversation_dict`); add `ConversationsResponse` to `types.ts`
- [ ] 5.3 RED ConversationsList/Thread tests: rows (no Asignado), thread drill-down
- [ ] 5.4 GREEN create `pages/ConversationsList.tsx` (no Asignado)+`ConversationThread.tsx` (read-only)+wrappers (`ConversationsListView/...Empty`, `ConversationThreadView/...Bubbles/NoReplyNote`)

## Phase 6 — S6 KB+Settings (commits: `feat(web): kb admin list with 403 denied`; `feat(web): settings admin save with 403 denied`)

- [ ] 6.1 RED KbList tests: admin list; operador 403→denied, no crash
- [ ] 6.2 GREEN create `pages/KbList.tsx` + wrapper (`KbListView/KbListEmpty`)
- [ ] 6.3 RED Settings tests: save flow; 403 denied
- [ ] 6.4 GREEN create `pages/Settings.tsx` + wrapper (`SettingsView`)

# Apply Progress: Panel Adoption — Corrective Phase 7 AppShell live view wiring

## Corrective Phase 7 Status
- Work unit: Corrective Phase 7 / S7, tasks 7.1–7.2
- Mode: Strict TDD
- Delivery: `auto-chain`, `stacked-to-main`, corrective slice under the 400-line review boundary
- Completed: 24/24 tasks
- Rollback: revert `web/src/components/domain/AppShell.tsx`, `web/src/components/domain/AppShell.test.tsx`, `web/src/components/pages/ClientesList.tsx`, `web/src/components/pages/Dashboard.tsx`, `web/src/app.test.tsx`, `web/src/stories/pages/PanelEntry.stories.test.tsx`, and `web/src/stories/pages/Settings.stories.test.tsx`; preserve the page implementations and prior S1–S6 behavior.

### S7 TDD Cycle Evidence
| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 7.1 | `web/src/components/domain/AppShell.test.tsx` | Component integration with native fetch stubs | ✅ 19/19 AppShell tests passed before corrective additions | ✅ Live navigation and drill-down assertions written before wiring; failed on placeholders/missing callback | ✅ 21/21 focused AppShell tests passed | ✅ All five non-dashboard NAVIGATION pages plus ClientFicha and ConversationThread drill-downs | ✅ Reused D7 `PanelView`, existing page components, `useAsyncData`, and callbacks; no router/dependency |
| 7.2 | `web/src/components/domain/AppShell.test.tsx`, `web/src/app.test.tsx`, `web/src/stories/pages/PanelEntry.stories.test.tsx`, `web/src/stories/pages/Settings.stories.test.tsx` | Component/integration regression proof | ✅ Existing focused suites established the prior regressions | ✅ Regression assertions exposed Dashboard malformed-response crash, stale PanelEntry heading, auth fixture call ordering, and Settings effect timing | ✅ `npm test -- app PanelEntry`: 32/32; full suite: 319/319 | ✅ Dashboard/auth/PanelEntry/Settings regressions and all existing page/story paths | ✅ Minimal fallback/test-fixture corrections only; approved scope unchanged |

### S7 Work Unit Evidence
| Evidence | Result |
|----------|--------|
| Focused test command and exact result | `cd web && npm test -- AppShell` — PASS; 2 files, 21 tests passed. |
| Runtime harness command/scenario and exact result | N/A — frontend-only work unit; live page API boundaries are exercised through native `fetch` stubs in the AppShell integration regression tests, with no server runtime boundary assigned. Native SDD settlement is tracked separately in the provider ledger. |
| Complete frontend suite | `cd web && npm test` — PASS; 44 files, 319 tests passed. |
| Typecheck | `cd web && npx tsc -b` — PASS; exit code 0. |
| Rollback boundary | Revert only the S7 files listed above; this removes live D7 mapping, drill-down callback wiring, and corrective regression proof without removing S1–S6 page implementations. |

### S7 Graph and Minimalism Evidence
- Graph check passed: `graphify-out/graph.json` exists and is non-empty; `graphify-out/GRAPH_REPORT.md` was read. No graph refresh was run.
- Consulted nodes: `AppShell()` / `web/src/components/domain/AppShell.tsx`, `PanelShell()` / `PanelShell.tsx`, `ClientesList`, `ClientFicha`, `CasesList`, `ConversationsList`, `ConversationThread`, `KbList`, `Settings`, `Dashboard`, `AppShell.test.tsx`, `app.test.tsx`, and `PanelEntry.stories.test.tsx`.
- Consulted edges: `AppShell.tsx → PanelShell.tsx`; `AppShell → ClientesList → ClientFicha`; `AppShell → ConversationsList → ConversationThread`; each live page → `useAsyncData → apiFetch`; `AppShell → Dashboard`; `PanelEntry → DashboardOverview → Dashboard`.
- Graph commands: `graphify query "AppShell PanelShell D7 state routing live ClientesList CasesList ConversationsList KbList Settings drill-down ClientFicha ConversationThread"`; `graphify path` attempted across AppShell and affected pages (directed paths unavailable/ambiguous in the existing graph).
- Pre-apply Ponytail review: keep the existing `useState<PanelView>` D7 contract and page components; no router, route abstraction, dependency, or unrelated cleanup.

### Native Attempt Settlement
- Native attempt was acquired and settled by the orchestrator after S7 verification; this is separate from the N/A application runtime harness above.

### Next Recommendation
- `sdd-verify` — all implementation tasks and regression proof are complete; final RDD review remains pending.

## Historical cumulative status before corrective S7
- The following sections are historical evidence retained for traceability; current completion is defined by the corrective S7 section above.
- Change: `2026-08-24-panel-adoption`
- Work unit: Original S1–S6 implementation sequence
- Mode: Strict TDD
- Delivery: `auto-chain`, `stacked-to-main`, PR6 S6b focused boundary
- Commit: historical per-slice worktree state; corrective S7 is the active finalization slice
- Rollback: remove only `web/src/components/pages/Settings.tsx`, the Settings story wrapper, and S6b focused tests; preserve S1–S6a.
- Completed before corrective slice: 22/22 original tasks (S1: 1.1–1.4; S2: 2.1–2.4; S3a: 3.1–3.2; S3b: 3.3–3.4; S4: 4.1–4.2; S5a: 5.1–5.2; S5b: 5.3–5.4; S6a: 6.1–6.2; S6b: 6.3–6.4)

## Historical Completed Tasks
- [x] 1.1 RED coverage for successful login, invalid/locked login, logout-to-login, and `postJson` success/error.
- [x] 1.2 Added `postJson<T>` and production `LoginAuth` with loading/error, username preservation, and generic auth failures.
- [x] 1.3 Replaced the anonymous stub with the real login gate and wired logout through `AppShell` and `PanelShell`.
- [x] 1.4 Converted `Login.stories.tsx` into a thin wrapper preserving its named exports.
- [x] 2.1 Added RED coverage for shell navigation, real dashboard rendering, KPI counts, motivos, and removal of fabricated metrics/activity.
- [x] 2.2 Added `useAsyncData<T>` with loading/ready/empty/error/denied states, retry, and `ApiError(403)` mapping.
- [x] 2.3 Added the live Dashboard page using `/panel/api/kpis`, three `StatCard`s, motivos, and the backend window caption.
- [x] 2.4 Wired D7 AppShell state to Dashboard; corrective S7 later replaced the historical placeholders for all remaining views.

## Historical Prior S1 Evidence (preserved)
| Task | Test file | Layer | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `web/src/app.test.tsx`, `web/src/api.test.ts` | Integration-style component/API fetch stubs | 25 existing focused tests passed | Written; failed on missing `postJson`, `LoginAuth`, and logout | 30 focused tests passed | Success, locked-login, logout, POST success/error cases | Clean |
| 1.2 | `web/src/app.test.tsx`, `web/src/stories/pages/Login.stories.test.tsx` | Component integration | Existing login story coverage passed | Written before `LoginAuth` existed | 30 focused + 6 Login tests passed | Loading, invalid/locked error, username preservation, and success paths | Clean |
| 1.3 | `web/src/app.test.tsx` | Component integration | AppShell baseline passed | Written before gate/logout wiring | Logout and successful-login tests passed | Authenticated admin and return-to-login paths | Clean |
| 1.4 | `web/src/stories/pages/Login.stories.test.tsx` | Component | Existing story tests passed | Wrapper import/export contract written before wrapper change | 6/6 Login story tests passed | Structural wrapper/export preservation; one contract surface | Clean |

### Historical Prior S1 Work Unit Evidence
- Focused: `cd web && npm test -- app api` — PASS; 4 files / 30 tests.
- Story: `cd web && npm test -- Login` — PASS; 1 file / 6 tests.
- Typecheck: `cd web && npx tsc -b` — PASS; exit 0.
- Runtime harness: N/A; S1 had no server/runtime boundary and used native fetch stubs.
- Rollback: revert the S1 commit; removes LoginAuth, postJson, gate/logout wiring, tests, and Login wrapper only.

### Historical Prior S1 Graph Evidence
- Nodes: `App()` / `web/src/app.tsx`, `AppShell()` / `web/src/components/domain/AppShell.tsx`, `PanelShell()` / `web/src/components/domain/PanelShell.tsx`, `api.ts`, `Login.stories.tsx`, backend `api/routes/auth.py` and `login()`.
- Edges: `app.tsx --imports_from--> AppShell.tsx`; `AppShell.tsx --imports_from--> PanelShell.tsx`; `app.tsx --imports_from--> api.ts`; Login story → LoginAuth wrapper; `app.tsx → AppShell.tsx → PanelShell.tsx` shortest path.

## Historical TDD Cycle Evidence
| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 2.1 | `web/src/components/domain/AppShell.test.tsx`, `web/src/stories/pages/Dashboard.stories.test.tsx` | Component integration | 26 baseline tests passed | Written before S2 production changes; failed on old placeholder/mock dashboard | `npm test -- AppShell Dashboard`: 24 passed | Navigation, counts, motivos, no fabricated metrics/feed, loading/empty/error | Clean; updated heading assertions for shell header + page heading |
| 2.2 | `web/src/hooks/useAsyncData.test.tsx` | Hook/component unit | N/A (new file) | RED contract covered loading, retry, empty, 403, and generic error before final hook behavior | `npm test -- useAsyncData`: 3 passed | Ready→retry, empty/denied, generic error | Clean; fetcher ref stabilized to avoid render-loop on inline fetchers |
| 2.3 | `web/src/stories/pages/Dashboard.stories.test.tsx` | Component integration | Dashboard baseline included in 26 tests | Written before Dashboard implementation | Focused suite passed | Non-empty motives and zero-motives branch; counts and caption | Clean; no deltas/autonomy/response-time/activity markup |
| 2.4 | `web/src/components/domain/AppShell.test.tsx`, `web/src/stories/pages/Dashboard.stories.test.tsx` | Component integration | AppShell/story baseline included | Written before view-map/wrapper changes | Focused suite passed | Dashboard route; S7 later completed the remaining live view map | Clean |

## Historical Work Unit Evidence
| Evidence | Result |
|----------|--------|
| Focused test command and exact result | `cd web && npm test -- AppShell Dashboard` — PASS; 3 files, 24 tests passed. |
| Hook test command and exact result | `cd web && npm test -- useAsyncData` — PASS; 1 file, 3 tests passed. |
| Type check | `cd web && npx tsc -b` — PASS; exit code 0. |
| Runtime harness command/scenario and exact result | N/A — S2 has no live server boundary; Dashboard and hook behavior use native fetch stubs/promises in Vitest. |
| Rollback boundary | Revert the S2 commit; removes `Dashboard`, `useAsyncData`, S2 tests, AppShell map, and Dashboard wrapper without touching S1 or later slices. |

## Historical S3a TDD Cycle Evidence
| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 3.1 | `web/src/stories/pages/ClientesList.stories.test.tsx` | Component integration with fetch stub | ✅ 11/11 existing ClientesList tests | ✅ Written first; failed because `components/pages/ClientesList` did not exist | ✅ 14/14 focused tests passed | ✅ `Jorge` query plus encoded `Marcela Fuentes` query; empty result companion | ✅ Clean; reused existing API, hook, table, and state primitives |
| 3.2 | `web/src/stories/pages/ClientesList.stories.test.tsx` | Component integration | ✅ 11/11 existing ClientesList tests | ✅ Wrapper/page import contract failed before page creation | ✅ 14/14 focused tests passed | ✅ Non-empty customer rows and controlled empty state | ✅ Thin story wrapper; no new dependency or abstraction |

## Historical S3a Work Unit Evidence
| Evidence | Result |
|----------|--------|
| Focused test command and exact result | `cd web && npm test -- ClientesList` — PASS; 1 file, 14 tests passed. |
| Type check | `cd web && npx tsc -b` — PASS; exit code 0. |
| Runtime harness command/scenario and exact result | N/A — frontend-only slice; API interaction is exercised through native `fetch` stubs in Vitest, with no live server boundary assigned to S3a. |
| Rollback boundary | Revert the S3a commit; removes `web/src/components/pages/ClientesList.tsx`, its focused tests, and the ClientesList story wrapper only, preserving S1/S2 and leaving ClientFicha untouched. |

## Historical Graph Check
Graph was present and non-empty at `graphify-out/graph.json`; `graphify-out/GRAPH_REPORT.md` was read before implementation. No graph refresh was run.

Consulted nodes:
- `AppShell()` / `web/src/components/domain/AppShell.tsx`
- `AppShell.tsx`
- `PanelShell()` / `web/src/components/domain/PanelShell.tsx`
- `Dashboard.stories.tsx` / `web/src/stories/pages/Dashboard.stories.tsx`
- `DashboardOverview()`
- `StatCard()` / `web/src/stories/pages/_shared/StatCard.tsx`
- `kpis()` / `app/panel/api/routes/dashboard.py`
- `Kpis` / `web/src/types.ts`
- `ClientesList.stories.tsx` / `web/src/stories/pages/ClientesList.stories.tsx`
- `ClientesListView()` / `ClientesListEmpty()` story exports
- `ClientesList()` / `web/src/components/pages/ClientesList.tsx`
- `DataTable()` / `web/src/stories/pages/_shared/DataTable.tsx`
- `StateMessage()` / `web/src/stories/pages/_shared/StateMessage.tsx`
- `PageFrame()` / `web/src/stories/pages/_shared/PageFrame.tsx`
- `apiFetch()` / `web/src/api.ts`
- `clients_list()` / `app/panel/api/routes/clients.py`

Consulted edges:
- `AppShell.tsx --imports_from--> PanelShell.tsx`
- `Dashboard.stories.tsx --imports_from--> StatCard.tsx`
- `AppShell()` → `PanelShell()` shell relationship from the graph query
- `Dashboard` → `/panel/api/kpis` contract validated against `kpis()` and `compute_kpis()` source
- `ClientesList.stories.tsx --imports_from--> DataTable.tsx`
- `ClientesList` → `apiFetch()` → `/panel/api/clients?q=` contract validated against `clients_list()` / `search_customers()`
- `ClientesList` → `PageFrame()` → `StateMessage()` / `DataTable()` shared rendering path

## Historical Pre-apply Ponytail Review
- Clean slate: no router, dependency, pagination, client class, or speculative abstraction was added; the page reuses existing API, hook, table, state, and design-system primitives.

## Historical S6b TDD Cycle Evidence
| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 6.3 | `web/src/stories/pages/Settings.stories.test.tsx` | Component integration with native fetch stubs | Existing Settings story matrix passed; 23 tests before S6b additions | Written before `Settings.tsx`; import failed | 25 focused tests passed | Tone save and limits save; admin 200 and operador 403 paths | Clean; reused `postJson`, `useAsyncData`, and StateMessage |
| 6.4 | `web/src/stories/pages/Settings.stories.test.tsx` | Component integration | RED baseline above | Wrapper/page import contract absent before extraction | 25 focused tests and typecheck passed | Controlled story states plus self-fetching save/denied paths | Thin wrapper; no new dependency or abstraction |

## Historical S6b Work Unit Evidence
| Evidence | Result |
|----------|--------|
| Focused test command and exact result | `cd web && npm test -- Settings` — PASS; 2 files, 25 tests passed, including the tone-save timing correction. |
| Typecheck command and exact result | `cd web && npx tsc -b` — PASS; exit code 0. |
| Runtime harness command/scenario and exact result | N/A — frontend-only slice; admin GET/POST and operador 403 behavior are exercised through native `fetch` stubs in Vitest, with no live server boundary assigned to S6b. |
| Rollback boundary | Remove `web/src/components/pages/Settings.tsx`, `web/src/stories/pages/Settings.stories.tsx`, and the S6b additions in `Settings.stories.test.tsx`; preserve S1–S6a. |

## Historical S6b Graph and Minimalism Evidence
- Graph was present and non-empty at `graphify-out/graph.json`; `graphify-out/GRAPH_REPORT.md` was read. No refresh was run.
- Consulted nodes: `Settings.stories.tsx`, `Settings.stories.test.tsx`, `PageFrame.tsx`, `StateMessage.tsx`, `DataTable.tsx`, `Input.tsx`, `Textarea.tsx`, `Button.tsx`, `api.ts` / `apiFetch()` / `postJson()`, `useAsyncData.ts`, `types.ts` / `Settings`, `api/routes/settings.py`, `require_admin_json()`, `Admin Panel`, and `settings` mock data.
- Consulted edges: `Settings.stories.tsx → Settings()`; `Settings → useAsyncData → apiFetch → GET /panel/api/settings`; save buttons → `postJson → POST /panel/api/settings/{scope,keywords,tone,limits,meta}`; `ApiError(403) → useAsyncData denied → StateMessage`; Settings → PageFrame / Card / Input / Textarea / DataTable / StateMessage.
- Directed backend paths were unavailable for the story-to-route query in the existing graph; undirected story-to-`PageFrame` and story-to-`StateMessage` edges plus the focused Settings/API authorization query were consulted.
- Pre-apply Ponytail review: `shrink:` extract only the Settings page, thin `SettingsView` wrapper, and save/403 tests; no router, dependency, client class, CSS system, mutation abstraction, or unrelated settings feature was added.

## Historical Task Ledger Before Corrective S7
- [x] Phase 3 / S3a ClientesList tasks 3.1–3.2
- [x] Phase 3 / S3b ClientFicha tasks 3.3–3.4
- [x] Phase 4 / S4 Cases tasks 4.1–4.2
- [x] Phase 5 / S5a Conversations backend tasks 5.1–5.2
- [x] Phase 5 / S5b Conversations frontend tasks 5.3–5.4
- [x] Phase 6 / S6a KB tasks 6.1–6.2
- [x] Phase 6 / S6b Settings tasks 6.3–6.4
- [x] Phase 7 / S7 AppShell live view wiring and regression proof tasks 7.1–7.2

## Historical Issues
- Backend `pytest tests/` was not attempted for this frontend-only slice; no backend collection limitation is claimed for S2.
- Existing story-domain tests emit React `act(...)` warnings because the real Dashboard starts its fetch effect during shell renders; all focused assertions and typecheck pass.

## Historical S3b TDD Cycle Evidence
| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 3.3 | `web/src/stories/pages/ClientFicha.stories.test.tsx` | Component integration with fetch stubs | ✅ 14/14 prior ClientFicha tests | ✅ New page import failed before `ClientFicha.tsx` existed | ✅ 3/3 focused tests passed | ✅ Populated ficha/memories and empty memo/no memories paths | ✅ API-contract assertions replace mock-only behavior |
| 3.4 | `web/src/stories/pages/ClientFicha.stories.test.tsx` | Component integration | ✅ RED baseline above | ✅ Wrapper import/export contract failed before extraction | ✅ 3/3 focused tests passed | ✅ `ClientFichaView` and `NoMemo` variants | ✅ Reused `useAsyncData`, `ClientMemories`, and shared primitives |

## Historical S3b Work Unit Evidence
| Evidence | Result |
|----------|--------|
| Focused test command and exact result | `cd web && npm test -- ClientFicha` — PASS; 1 file, 3 tests passed. |
| Type check | `cd web && npx tsc -b` — PASS; exit code 0. |
| Runtime harness command/scenario and exact result | N/A — frontend-only; API boundaries use native `fetch` stubs in Vitest and no live server boundary is assigned to S3b. |
| Rollback boundary | Remove `web/src/components/pages/ClientFicha.tsx`, `web/src/stories/pages/ClientFicha.stories.tsx`, and the focused tests; preserve S1, S2, and S3a. |

## Historical S3b Graph and Minimalism Evidence
- Consulted nodes: `ClientFicha.stories.tsx`, `ClientFicha()`, `ClientMemories()`, `DataTable()`, `PageFrame()`, `StateMessage()`, `apiFetch()`, `client_ficha()`, and `client_memories_list()`.
- Consulted edges: story wrapper → production page; `ClientFicha` → `ClientMemories` → shared table/header; `ClientFicha` → `apiFetch` → `/panel/api/clients/{id}` and `/panel/api/clients/{id}/memories` → backend client routes.
- Graph was present and non-empty; `GRAPH_REPORT.md` was read and no refresh was run.
- Pre-apply Ponytail review: clean slate. No router, dependency, duplicate memory table, new CSS, or speculative abstraction was added.

## Historical S4 TDD Cycle Evidence
| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 4.1 | `web/src/stories/pages/CasesList.stories.test.tsx` | Component integration with fetch stubs | ✅ 10/10 existing CasesList tests | ✅ Added API row, update POST→refetch, and ack POST→refetch tests before `CasesList.tsx` existed; import failed | ✅ 13/13 focused tests passed | ✅ Separate update and acknowledgement mutation paths, plus populated API rows | ✅ Reused `apiFetch`, `postJson`, `useAsyncData`, `DataTable`, `StateMessage`, and existing primitives |
| 4.2 | `web/src/stories/pages/CasesList.stories.test.tsx` | Component integration | ✅ RED baseline above | ✅ Wrapper/page import contract failed before extraction | ✅ 13/13 focused tests passed; typecheck passed | ✅ Controlled story variants and self-fetching mutation path | ✅ Thin story wrapper; no router, dependency, or new abstraction |

## Historical S4 Work Unit Evidence
| Evidence | Result |
|----------|--------|
| Focused test command and exact result | `cd web && npm test -- CasesList` — PASS; 1 file, 13 tests passed. |
| Typecheck command and exact result | `cd web && npx tsc -b` — PASS; exit code 0. |
| Runtime harness command/scenario and exact result | N/A — frontend-only; API interaction is exercised through native `fetch` stubs in Vitest and no live server boundary is assigned to S4. |
| Rollback boundary | Remove only the S4 CasesList page, wrapper, and focused tests; preserve S1–S3b and all later slices. |

## Historical S4 Graph and Minimalism Evidence
- Consulted nodes: `CasesList.stories.tsx`, `CasesList.stories.test.tsx`, `CasesListView()`, `CaseActions()`, `types.ts` / `Case` / `CasesResponse`, `api.ts` / `apiFetch()` / `postJson()`, `useAsyncData()`, `DataTable()`, `Select()`, `Button()`, `cases.py` / `case_update()` / `case_ack()`.
- Consulted edges: `CasesList.stories.tsx → CasesListView() → CasesList()`; `CasesList() → useAsyncData() → apiFetch() → GET /panel/api/cases`; `CaseActions() → postJson() → POST /panel/api/cases/{id}/update|ack → retry() → GET /panel/api/cases`; `CasesList() → DataTable() → Select()/Button()`; API paths validated against `app/panel/api/routes/cases.py`.
- Graph was present and non-empty; `graphify-out/GRAPH_REPORT.md` was read and no refresh was run.
- Pre-apply Ponytail review: clean slate. The slice adds no router, dependency, pagination, client class, CSS, or speculative abstraction; it reuses the existing API layer, async hook, shared table/state primitives, and story wrapper pattern.

## Historical S5a TDD Cycle Evidence
| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 5.1 | `tests/functional/test_api_conversations.py` | Functional HTTP/API | ✅ Project environment collected successfully after `uv sync` installed the already-declared dependency | ✅ Added list 401 and authenticated shape/order/no-assignee scenarios before route implementation | ✅ Test scenarios cover non-empty ordering, id tie-break, nulls-last, and anonymous JSON 401 | ✅ One authenticated dataset plus a separate anonymous path exercise the required branches | ✅ Reused existing seed/login conventions; no test abstraction added |
| 5.2 | `tests/functional/test_api_conversations.py`, `web/src/types.ts` | Functional API + TypeScript contract | N/A (production route/type additions) | ✅ Route was absent while RED tests referenced `/panel/api/conversations`; response type was absent | ✅ `uv run pytest` passed 7 tests; `py_compile` and frontend typecheck pass | ✅ Authenticated ordering/shape and anonymous JSON 401 paths exercised | ✅ Minimal route reuses `require_user_json`, `to_conversation_dict`, and SQLAlchemy ordering |

## Historical S5a Work Unit Evidence
| Evidence | Result |
|----------|--------|
| Focused test command and exact result | `uv sync` installed the already-declared `psycopg[binary]` dependency; `pytest tests/functional/test_api_conversations.py` — PASS; 7 tests passed in 5.40s. |
| Static/type evidence | `python -m py_compile app/panel/api/routes/conversations.py tests/functional/test_api_conversations.py` — PASS; `cd web && npx tsc -b` — PASS; exit code 0. |
| Runtime harness command/scenario and exact result | PASS — authenticated and anonymous TestClient paths exercised by the focused functional suite. |
| Rollback boundary | Revert only `app/panel/api/routes/conversations.py`, `tests/functional/test_api_conversations.py`, and `web/src/types.ts` changes for S5a; this removes the additive list endpoint and contract without touching S1–S4 or S5b. |

## Historical S5a Graph and Minimalism Evidence
- Graph was present and non-empty at `graphify-out/graph.json`; `graphify-out/GRAPH_REPORT.md` was read. No refresh was run.
- Consulted nodes: `api/routes/conversations.py`, `conversation_thread()`, `Conversation`, `Message`, `to_conversation_dict()`, `require_user_json()`, `tests/functional/test_api_conversations.py`, `functional/conftest.py`, `types.ts`, and `ConversationsList.stories.tsx`.
- Consulted edges: `conversations.py → require_user_json() → get_current_user_json()`; `conversations.py → to_conversation_dict()`; `conversation_thread() → Conversation/Message`; functional test → TestClient → `/panel/api/conversations`; `types.ts → Conversation` response contract.
- Directed graph paths between route/test and serializer/types were unavailable; the relevant BFS query and node relationships were consulted instead.
- Pre-apply Ponytail review: `shrink:` keep S5a to one additive list route, focused functional coverage, and one response interface; reuse existing auth, serializer, SQLAlchemy query, and no new dependency/abstraction.

## Historical S5a Issues
- `psycopg[binary]>=3.2` was already declared in `pyproject.toml` and present in `uv.lock`; `uv sync` installed it into the project `.venv`, enabling the S5a proof.

## Historical S5b TDD Cycle Evidence
| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 5.3 | `web/src/stories/pages/ConversationsList.stories.test.tsx`, `ConversationThread.stories.test.tsx` | Component integration with native fetch stubs | ✅ S5a frontend type contract remained green | ✅ New production page imports failed before page creation | ✅ 9 focused tests passed: API list, no Asignado, row activation, thread fetch, read-only/empty paths | ✅ Removed duplicated mock page implementations; wrappers now provide controlled story data |
| 5.4 | Same focused story tests | Component integration | ✅ RED baseline above | ✅ Wrapper/page imports and behavior were absent | ✅ 9/9 focused tests passed; typecheck passed | ✅ API and controlled story modes exercise non-empty, empty, loading, and drill-down paths | ✅ Reused `apiFetch`, `useAsyncData`, `DataTable`, `PageFrame`, and `StateMessage`; no new dependency |

## Historical S5b Work Unit Evidence
| Evidence | Result |
|----------|--------|
| Focused test command and exact result | `cd web && npm test -- ConversationsList ConversationThread` — PASS; 2 files, 9 tests passed. |
| Typecheck command and exact result | `cd web && npx tsc -b` — PASS; exit code 0. |
| Runtime harness command/scenario and exact result | N/A — frontend-only slice; list/thread HTTP behavior is exercised through native `fetch` stubs, with no live server boundary assigned to S5b. |
| Rollback boundary | Revert `web/src/components/pages/ConversationsList.tsx`, `web/src/components/pages/ConversationThread.tsx`, the two story wrappers, and their focused tests; preserve S1–S5a and S6. |

## Historical S5b Graph and Minimalism Evidence
- Graph was present and non-empty at `graphify-out/graph.json`; `graphify-out/GRAPH_REPORT.md` was read. No refresh was run.
- Consulted nodes: `ConversationsList.stories.tsx`, `ConversationThread.stories.tsx`, `ConversationsList`, `ConversationThread`, `Conversation`, `Message`, `types.ts`, `apiFetch()`, `useAsyncData()`, `DataTable()`, `PageFrame()`, `StateMessage()`, `conversation_thread()`, `to_conversation_dict()`, and `panel/deps.py` JSON auth dependencies.
- Consulted edges: story wrappers → extracted page components; `ConversationsList` → `useAsyncData` → `apiFetch` → `/panel/api/conversations`; `ConversationThread` → `useAsyncData` → `apiFetch` → `/panel/api/conversations/{id}`; both pages → shared `DataTable`/`PageFrame`/`StateMessage`; backend thread route → `Conversation`/`Message` serializer shape.
- Pre-apply Ponytail review: `shrink:` keep S5b to two page components, thin wrappers, and focused component tests; no router, new dependency, pagination, assignee field, mutation control, or speculative abstraction.

## Historical S6a TDD Cycle Evidence
| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 6.1 | `web/src/stories/pages/KbList.stories.test.tsx` | Component integration with native fetch stubs | Existing KbList story coverage was preserved | New `KbList` import and admin/403 scenarios failed before page creation | 14/14 focused tests passed | Admin non-empty list plus operator 403 denied path; existing empty/state matrix remains green | Clean |
| 6.2 | `web/src/stories/pages/KbList.stories.test.tsx` | Component integration | RED baseline above | Wrapper/page contract was absent before extraction | 14/14 focused tests and typecheck passed | Controlled story data, empty state, API list, and denied state | Thin wrapper; reused existing API, async hook, table, frame, state, and primitives |

## Historical S6a Work Unit Evidence
| Evidence | Result |
|----------|--------|
| Focused test command and exact result | `cd web && npm test -- KbList` — PASS; 1 file, 14 tests passed. |
| Typecheck command and exact result | `cd web && npx tsc -b` — PASS; exit code 0. |
| Runtime harness command/scenario and exact result | N/A — frontend-only slice; admin 200 and operador 403 behavior are exercised through native `fetch` stubs in Vitest, with no live runtime boundary assigned to S6a. |
| Rollback boundary | Remove `web/src/components/pages/KbList.tsx`, `web/src/stories/pages/KbList.stories.tsx`, and the S6a additions in `KbList.stories.test.tsx`; preserve S1–S5b and leave Settings untouched. |

## Historical S6a Graph and Minimalism Evidence
- Graph was present and non-empty at `graphify-out/graph.json`; `graphify-out/GRAPH_REPORT.md` was read. No refresh was run.
- Consulted nodes: `KbList.stories.tsx`, `StateMessage.tsx`, `DataTable.tsx`, `PageFrame.tsx`, `api.ts` / `apiFetch()`, `useAsyncData.ts`, `types.ts` / `Doc` / `DocsResponse`, `Knowledge Base`, `Admin Panel`, and `panel/deps.py` JSON authorization dependencies.
- Consulted edges: `KbList.stories.tsx --imports_from--> StateMessage.tsx`; `KbList` → `useAsyncData` → `apiFetch` → `/panel/api/kb`; `KbList` → `PageFrame` / `StateMessage` / `DataTable`; `ApiError(403)` → `useAsyncData` `denied` state.
- Directed paths from the story to backend KB service/route were unavailable in the existing graph; the focused query and the `StateMessage.tsx` ← `KbList.stories.tsx` edge were consulted instead.
- Pre-apply Ponytail review: `shrink:` extract only the KbList page and thin story exports; no router, dependency, API abstraction, mutation flow, CSS, or Settings work was added.

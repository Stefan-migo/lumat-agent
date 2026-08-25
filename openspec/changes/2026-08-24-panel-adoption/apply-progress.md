# Apply Progress: Panel Adoption — S3a ClientesList

## Status
- Change: `2026-08-24-panel-adoption`
- Work unit: Phase 3 / S3a ClientesList, tasks 3.1–3.2
- Mode: Strict TDD
- Delivery: `auto-chain`, `stacked-to-main`, PR3 focused boundary
- Commit: `feat(web): client list search and empty state`
- Rollback: revert the S3a commit
- Completed: 10/28 tasks (S1: 1.1–1.4; S2: 2.1–2.4; S3a: 3.1–3.2)

## Completed Tasks
- [x] 1.1 RED coverage for successful login, invalid/locked login, logout-to-login, and `postJson` success/error.
- [x] 1.2 Added `postJson<T>` and production `LoginAuth` with loading/error, username preservation, and generic auth failures.
- [x] 1.3 Replaced the anonymous stub with the real login gate and wired logout through `AppShell` and `PanelShell`.
- [x] 1.4 Converted `Login.stories.tsx` into a thin wrapper preserving its named exports.
- [x] 2.1 Added RED coverage for shell navigation, real dashboard rendering, KPI counts, motivos, and removal of fabricated metrics/activity.
- [x] 2.2 Added `useAsyncData<T>` with loading/ready/empty/error/denied states, retry, and `ApiError(403)` mapping.
- [x] 2.3 Added the live Dashboard page using `/panel/api/kpis`, three `StatCard`s, motivos, and the backend window caption.
- [x] 2.4 Wired D7 AppShell state to Dashboard while retaining placeholders for later views; converted Dashboard story to a thin `DashboardOverview` wrapper.

## Prior S1 Evidence (preserved)
| Task | Test file | Layer | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `web/src/app.test.tsx`, `web/src/api.test.ts` | Integration-style component/API fetch stubs | 25 existing focused tests passed | Written; failed on missing `postJson`, `LoginAuth`, and logout | 30 focused tests passed | Success, locked-login, logout, POST success/error cases | Clean |
| 1.2 | `web/src/app.test.tsx`, `web/src/stories/pages/Login.stories.test.tsx` | Component integration | Existing login story coverage passed | Written before `LoginAuth` existed | 30 focused + 6 Login tests passed | Loading, invalid/locked error, username preservation, and success paths | Clean |
| 1.3 | `web/src/app.test.tsx` | Component integration | AppShell baseline passed | Written before gate/logout wiring | Logout and successful-login tests passed | Authenticated admin and return-to-login paths | Clean |
| 1.4 | `web/src/stories/pages/Login.stories.test.tsx` | Component | Existing story tests passed | Wrapper import/export contract written before wrapper change | 6/6 Login story tests passed | Structural wrapper/export preservation; one contract surface | Clean |

### Prior S1 Work Unit Evidence
- Focused: `cd web && npm test -- app api` — PASS; 4 files / 30 tests.
- Story: `cd web && npm test -- Login` — PASS; 1 file / 6 tests.
- Typecheck: `cd web && npx tsc -b` — PASS; exit 0.
- Runtime harness: N/A; S1 had no server/runtime boundary and used native fetch stubs.
- Rollback: revert the S1 commit; removes LoginAuth, postJson, gate/logout wiring, tests, and Login wrapper only.

### Prior S1 Graph Evidence
- Nodes: `App()` / `web/src/app.tsx`, `AppShell()` / `web/src/components/domain/AppShell.tsx`, `PanelShell()` / `web/src/components/domain/PanelShell.tsx`, `api.ts`, `Login.stories.tsx`, backend `api/routes/auth.py` and `login()`.
- Edges: `app.tsx --imports_from--> AppShell.tsx`; `AppShell.tsx --imports_from--> PanelShell.tsx`; `app.tsx --imports_from--> api.ts`; Login story → LoginAuth wrapper; `app.tsx → AppShell.tsx → PanelShell.tsx` shortest path.
- Issue: `pytest tests/` was attempted during S1 but collection was blocked by pre-existing missing `psycopg` in `tests/conftest.py`.

## TDD Cycle Evidence
| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 2.1 | `web/src/components/domain/AppShell.test.tsx`, `web/src/stories/pages/Dashboard.stories.test.tsx` | Component integration | 26 baseline tests passed | Written before S2 production changes; failed on old placeholder/mock dashboard | `npm test -- AppShell Dashboard`: 24 passed | Navigation, counts, motivos, no fabricated metrics/feed, loading/empty/error | Clean; updated heading assertions for shell header + page heading |
| 2.2 | `web/src/hooks/useAsyncData.test.tsx` | Hook/component unit | N/A (new file) | RED contract covered loading, retry, empty, 403, and generic error before final hook behavior | `npm test -- useAsyncData`: 3 passed | Ready→retry, empty/denied, generic error | Clean; fetcher ref stabilized to avoid render-loop on inline fetchers |
| 2.3 | `web/src/stories/pages/Dashboard.stories.test.tsx` | Component integration | Dashboard baseline included in 26 tests | Written before Dashboard implementation | Focused suite passed | Non-empty motives and zero-motives branch; counts and caption | Clean; no deltas/autonomy/response-time/activity markup |
| 2.4 | `web/src/components/domain/AppShell.test.tsx`, `web/src/stories/pages/Dashboard.stories.test.tsx` | Component integration | AppShell/story baseline included | Written before view-map/wrapper changes | Focused suite passed | Dashboard route plus later-view placeholder | Clean |

## Work Unit Evidence
| Evidence | Result |
|----------|--------|
| Focused test command and exact result | `cd web && npm test -- AppShell Dashboard` — PASS; 3 files, 24 tests passed. |
| Hook test command and exact result | `cd web && npm test -- useAsyncData` — PASS; 1 file, 3 tests passed. |
| Type check | `cd web && npx tsc -b` — PASS; exit code 0. |
| Runtime harness command/scenario and exact result | N/A — S2 has no live server boundary; Dashboard and hook behavior use native fetch stubs/promises in Vitest. |
| Rollback boundary | Revert the S2 commit; removes `Dashboard`, `useAsyncData`, S2 tests, AppShell map, and Dashboard wrapper without touching S1 or later slices. |

## S3a TDD Cycle Evidence
| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 3.1 | `web/src/stories/pages/ClientesList.stories.test.tsx` | Component integration with fetch stub | ✅ 11/11 existing ClientesList tests | ✅ Written first; failed because `components/pages/ClientesList` did not exist | ✅ 14/14 focused tests passed | ✅ `Jorge` query plus encoded `Marcela Fuentes` query; empty result companion | ✅ Clean; reused existing API, hook, table, and state primitives |
| 3.2 | `web/src/stories/pages/ClientesList.stories.test.tsx` | Component integration | ✅ 11/11 existing ClientesList tests | ✅ Wrapper/page import contract failed before page creation | ✅ 14/14 focused tests passed | ✅ Non-empty customer rows and controlled empty state | ✅ Thin story wrapper; no new dependency or abstraction |

## S3a Work Unit Evidence
| Evidence | Result |
|----------|--------|
| Focused test command and exact result | `cd web && npm test -- ClientesList` — PASS; 1 file, 14 tests passed. |
| Type check | `cd web && npx tsc -b` — PASS; exit code 0. |
| Runtime harness command/scenario and exact result | N/A — frontend-only slice; API interaction is exercised through native `fetch` stubs in Vitest, with no live server boundary assigned to S3a. |
| Rollback boundary | Revert the S3a commit; removes `web/src/components/pages/ClientesList.tsx`, its focused tests, and the ClientesList story wrapper only, preserving S1/S2 and leaving ClientFicha untouched. |

## Graph Check
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

## Pre-apply Ponytail Review
- Clean slate: no router, dependency, pagination, client class, or speculative abstraction was added; the page reuses existing API, hook, table, state, and design-system primitives.

## Remaining Tasks
- [x] Phase 3 / S3a ClientesList tasks 3.1–3.2
- [ ] Phase 3 / S3b ClientFicha tasks 3.3–3.4
- [ ] Phase 4 / S4 Cases tasks 4.1–4.2
- [ ] Phase 5 / S5 Conversations tasks 5.1–5.4
- [ ] Phase 6 / S6 KB + Settings tasks 6.1–6.4

## Issues
- Backend `pytest tests/` was not attempted for this frontend-only slice; no backend collection limitation is claimed for S2.
- Existing story-domain tests emit React `act(...)` warnings because the real Dashboard starts its fetch effect during shell renders; all focused assertions and typecheck pass.

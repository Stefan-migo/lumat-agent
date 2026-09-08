# Tasks: Panel Operational Views

Strict RED→GREEN TDD; stacked slices.

## Phase 1: Slice 1
- [x] 1.1 RED — Test `web/src/components/pages/ClientFicha.test.tsx` for state/note POSTs, states, errors, and refresh; est 80; deps none; evidence Vitest fails.
- [x] 1.2 GREEN — Modify `web/src/components/pages/ClientFicha.tsx`, `web/src/api.ts`, `web/src/types.ts` for typed mutations, `ApiError`, refetch; est 140; deps 1.1; evidence Vitest passes.

## Phase 2: Slice 2
- [x] 2.1 RED — Test `web/src/stories/pages/KbList.stories.test.tsx` for `FormData`, lifecycle, validation, 403, refresh; est 95; deps Slice 1; evidence Vitest fails.
- [x] 2.2 GREEN — Modify `web/src/components/pages/KbList.tsx`, `web/src/api.ts`, `web/src/types.ts` for multipart/JSON mutations, errors, refresh; est 165; deps 2.1; evidence Vitest passes.

## Phase 3: Slice 3
- [x] 3.1 RED — Test `web/src/stories/pages/ClientesList.stories.test.tsx` for export URLs and denied-download behavior; est 45; deps Slice 2; evidence Vitest fails.
- [x] 3.2 GREEN — Modify `web/src/components/pages/ClientesList.tsx` for `/panel/export/clients.csv` and `cases.csv`; remove data URIs; est 55; deps 3.1; evidence Vitest passes.

## Phase 4: Slice 4
- [x] 4.1 RED — Test `web/src/components/domain/{panelRoutes.test.ts,AppShell.test.tsx}` and `web/src/components/pages/AdvancedDashboard.test.tsx` for nav, `aria-current`, states, 403; est 105; deps Slices 1–3; evidence Vitest fails.
- [x] 4.2 GREEN — Modify `web/src/components/domain/{panelRoutes.ts,PanelShell.tsx,AppShell.tsx}`, `web/src/components/pages/AdvancedDashboard.tsx`, `web/src/{api.ts,types.ts}` for nav and three calls; est 155; deps 4.1; evidence Vitest passes.

## Phase 5: Slice 5
- [x] 5.1 RED — Convert `tests/functional/{test_auth.py,test_clients.py,test_cases.py,test_kb_settings.py,test_dashboard_export.py}` to API/SPA contracts; est 125; deps Slices 1–4; evidence legacy HTML assertions removed before API replacements; focused pytest passed after replacement.
- [x] 5.2 GREEN — Update those tests and `tests/functional/conftest.py`, preserving auth, roles, audit, validation, CSV; est 115; deps 5.1; evidence `uv run pytest tests/functional/ -q` and `uv run pytest tests/` pass.

## Phase 6: Slice 6
- [x] 6.1 RED — Add `tests/integration/test_panel_delivery.py` checks for absent Jinja, retained API/export/WS, and `compute_kpis`; est 65; deps Slice 5; evidence focused pytest failed 7 retirement/import assertions before implementation.
- [x] 6.2 GREEN — Delete `app/panel/routes/{auth,dashboard,clients,cases,conversations,kb,settings}.py` and `app/panel/templates/**`; move KPI code to `app/services/dashboard.py`, clean `app/panel/deps.py`, update `app/panel/routes/__init__.py`; est 235; deps 6.1; evidence focused delivery tests 13 passed and full suite 573 passed.

## Phase 7: Slice 7
- [ ] 7.1 RED — Extend `test_panel_delivery.py` for redirects, deep links, API/WS/export precedence, no fallback, unchanged agent, and immutable artifact; est 90; deps Slice 6; evidence delivery tests fail.
- [ ] 7.2 GREEN — Modify `infra/nginx/panel.lumat.cl.conf`, leave `agente.lumat.cl.conf` unchanged, verify Docker static copy, and sync `openspec/changes/panel-operational-views/specs/**`; est 170; deps 7.1; evidence `uv run pytest tests/` plus `cd web && npx vitest run && npx tsc -b && npm run build` passes.

## Review Workload Forecast
| Slice | Lines | Test / harness | Rollback |
|---|---:|---|---|
| 1 | 220 | `cd web && npm test` / ficha | page/API/types |
| 2 | 260 | `cd web && npm test` / KB | page/API/types |
| 3 | 100 | `cd web && npm test` / export | list controls |
| 4 | 260 | `cd web && npm test` / link | route/nav/page |
| 5 | 240 | pytest / TestClient | tests/fixtures |
| 6 | 300 | pytest / startup import | Jinja/deps seam |
| 7 | 260 | pytest + build / proxy | nginx/spec/tests |
| **Total** | **1640** | Seven | Revert one |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

## Work Unit Evidence — Slice 6
- Focused test command: `uv run pytest tests/integration/test_panel_delivery.py -q` — 13 passed.
- Runtime harness: `uv run pytest tests/` — 573 passed, 1 pre-existing RuntimeWarning (`_publish_all` was never awaited).
- Rollback boundary: revert the Slice 6 commit to restore the seven legacy route modules, nine templates, KPI location, dependency cleanup, router aggregation, and delivery assertions.
- Graph consulted: `panel/deps.py`, `compute_kpis()`, `app/services/dashboard.py`, `test_panel_delivery.py`; edges `api/routes/dashboard.py → compute_kpis()`, `routes/__init__.py → api_router/export/realtime`.

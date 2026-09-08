# Apply Progress: Panel Operational Views

Change: `panel-operational-views`  
Branch chain: **7 stacked slices**, PRs **#119–#125**, merged in order to `main`  
Mode: **Strict TDD**  
Artifact store: **hybrid** (OpenSpec + Engram)  
Verified implementation HEAD: `02534eabd871dc5b709c338b6184146a2d8e185c`

Status: **complete — all 14 tasks checked**

## Completed Tasks

- [x] **1.1–1.2** ClientFicha state/note mutations, typed API helpers, safe feedback, disabled controls, and authoritative ficha/memory refresh.
- [x] **2.1–2.2** Knowledge-base upload/edit/disable/restore mutations, multipart-safe upload, validation/permission feedback, and refresh behavior.
- [x] **3.1–3.2** Authenticated client and case CSV export links using same-origin server-controlled downloads without fabricated data URIs.
- [x] **4.1–4.2** AdvancedDashboard route, navigation, deep links, active state, three API resources, loading/error/403 states, and drilldown rendering.
- [x] **5.1–5.2** Legacy functional-test migration to API/SPA contracts, duplicate test removal, auth edge-case preservation, and CSV coverage preservation.
- [x] **6.1–6.2** Jinja delivery retirement, legacy route/template deletion, KPI relocation to `app/services/dashboard.py`, and retained API/export/WebSocket contracts.
- [x] **7.1–7.2** Nginx SPA narrowing, explicit backend-prefix precedence, root/deep-link redirects, immutable static-artifact checks, and delivery-spec synchronization.

## TDD Cycle Evidence (Strict TDD)

Counts are observable cases in the RED test files currently present on `main`. Parametrized cases are shown with their expanded runtime count where applicable. Every RED entry is grounded in a real test file; no RED state is inferred from a commit message.

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 1.1 | `web/src/components/pages/ClientFicha.test.tsx` | Frontend unit (Vitest/jsdom) | ✅ 442 frontend tests | ✅ Written | ✅ Passed (final gate: 459 frontend tests) | 5 cases: layout, retained content, mutations/refresh, safe errors, empty-note validation | ➖ None needed |
| 1.2 | `web/src/components/pages/ClientFicha.test.tsx` | Frontend unit (Vitest/jsdom) | ✅ 442 frontend tests | ✅ Written | ✅ Passed (final gate: 459 frontend tests) | 5 declared cases | ➖ None needed |
| 2.1 | `web/src/stories/pages/KbList.stories.test.tsx` | Frontend unit/API seam (Vitest/jsdom) | ✅ 447 frontend tests | ✅ Written | ✅ Passed (final gate: 459 frontend tests) | 20 runtime cases (19 declared; one `it.each` expands to 2) | ➖ None needed |
| 2.2 | `web/src/stories/pages/KbList.stories.test.tsx` | Frontend unit/API seam (Vitest/jsdom) | ✅ 447 frontend tests | ✅ Written | ✅ Passed (final gate: 459 frontend tests) | 20 runtime cases | ➖ None needed |
| 3.1 | `web/src/stories/pages/ClientesList.stories.test.tsx` | Frontend unit (Vitest/jsdom) | ✅ 453 frontend tests | ✅ Written | ✅ Passed (final gate: 459 frontend tests) | 17 cases: exports, same-origin navigation, denied-download safety, views, states, and search API behavior | ➖ None needed |
| 3.2 | `web/src/stories/pages/ClientesList.stories.test.tsx` | Frontend unit (Vitest/jsdom) | ✅ 453 frontend tests | ✅ Written | ✅ Passed (final gate: 459 frontend tests) | 17 declared cases | ➖ None needed |
| 4.1 | `web/src/components/domain/panelRoutes.test.ts`, `web/src/components/domain/AppShell.test.tsx`, `web/src/components/pages/AdvancedDashboard.test.tsx` | Frontend unit/integration (Vitest/jsdom) | ✅ 455 frontend tests | ✅ Written | ✅ Passed (final gate: 459 frontend tests) | 28 cases: 6 route + 18 shell + 4 dashboard | ➖ None needed |
| 4.2 | `web/src/components/domain/panelRoutes.test.ts`, `web/src/components/domain/AppShell.test.tsx`, `web/src/components/pages/AdvancedDashboard.test.tsx` | Frontend unit/integration (Vitest/jsdom) | ✅ 455 frontend tests | ✅ Written | ✅ Passed (final gate: 459 frontend tests) | 28 declared cases | ➖ None needed |
| 5.1 | `tests/functional/test_auth.py`, `tests/functional/test_dashboard_export.py` | Functional API/TestClient | ✅ 611 backend tests before duplicate retirement | ✅ Written | ✅ Passed (final gate: 574 backend tests) | 8 focused migrated cases | ➖ None needed |
| 5.2 | `tests/functional/test_auth.py`, `tests/functional/test_dashboard_export.py` | Functional API/TestClient | ✅ 611 backend tests before duplicate retirement | ✅ Written | ✅ Passed (final gate: 574 backend tests) | 8 focused migrated cases | ➖ None needed |
| 6.1 | `tests/integration/test_panel_delivery.py` | Integration/static delivery contract | ✅ 566 backend tests | ✅ Written | ✅ Passed (final gate: 574 backend tests) | 13 focused delivery cases | ➖ None needed |
| 6.2 | `tests/integration/test_panel_delivery.py` | Integration/static delivery contract | ✅ 566 backend tests | ✅ Written | ✅ Passed (final gate: 574 backend tests) | 13 focused delivery cases | ➖ None needed |
| 7.1 | `tests/integration/test_panel_delivery.py` | Integration/static delivery contract | ✅ 573 backend tests | ✅ Written | ✅ Passed (final gate: 574 backend tests) | 14 focused delivery cases | ➖ None needed |
| 7.2 | `tests/integration/test_panel_delivery.py` | Integration/static delivery contract | ✅ 573 backend tests | ✅ Written | ✅ Passed (final gate: 574 backend tests) | 14 focused delivery cases | ➖ None needed |

## Test Summary

- `uv run pytest tests/` → **574 passed**, exit 0; one pre-existing `RuntimeWarning` about `_publish_all` not being awaited.
- `cd web && npx vitest run && npx tsc -b && npm run build` → **459 passed**, exit 0; typecheck and production build passed.
- `uv run pytest tests/integration/test_panel_delivery.py -q` → **14 passed**, exit 0.

## Work Unit Evidence

- **Slice 1 / PR #119:** focused ClientFicha Vitest — 1 file, 5 passed; full frontend reached 447; typecheck passed; backend client-focused tests passed (30).
- **Slice 2 / PR #120:** focused KB suite — 20 passed; full frontend reached 453; frontend typecheck/build passed; backend KB harness passed (62 passed, 549 deselected).
- **Slice 3 / PR #121:** focused export suite — 1 file, 16 passed before the final denied-download assertion correction; full frontend reached 455; export backend harness passed (9 passed, 602 deselected); final file contains 17 observable cases.
- **Slice 4 / PR #122:** focused dashboard/navigation regression — 3 files, 28 passed; full frontend reached 459; typecheck passed; dashboard backend harness passed (15 passed, 596 deselected).
- **Slice 5 / PR #123:** focused migration tests — 8 passed; functional suite passed (177); full backend passed (566) with the pre-existing warning; duplicate legacy modules were removed.
- **Slice 6 / PR #124:** `uv run pytest tests/integration/test_panel_delivery.py -q` — 13 passed; full backend passed (573) with the pre-existing warning.
- **Slice 7 / PR #125:** `uv run pytest tests/integration/test_panel_delivery.py -q` — 14 passed; full backend passed (574); frontend Vitest passed (459), typecheck passed, and production build passed.

## Files Changed Summary

Grouped from the verified implementation commits:

- **Slice 1 / PR #119:** `web/src/components/pages/ClientFicha.test.tsx`, `ClientFicha.tsx`, `web/src/api.ts`, `web/src/types.ts`.
- **Slice 2 / PR #120:** `web/src/stories/pages/KbList.stories.test.tsx`, `web/src/components/pages/KbList.tsx`, `web/src/api.ts`, `web/src/types.ts`.
- **Slice 3 / PR #121:** `web/src/stories/pages/ClientesList.stories.test.tsx`, `web/src/components/pages/ClientesList.tsx`.
- **Slice 4 / PR #122:** `web/src/components/domain/{panelRoutes.test.ts,panelRoutes.ts,AppShell.test.tsx,AppShell.tsx,PanelShell.tsx}`, `web/src/components/pages/{AdvancedDashboard.test.tsx,AdvancedDashboard.tsx}`, `web/src/{api.ts,types.ts}`.
- **Slice 5 / PR #123:** `tests/functional/{conftest.py,test_auth.py,test_dashboard_export.py}`; deleted `tests/functional/{test_clients.py,test_cases.py,test_kb_settings.py}`.
- **Slice 6 / PR #124:** `tests/integration/test_panel_delivery.py`, `app/services/dashboard.py`, `app/panel/api/routes/dashboard.py`, `app/panel/deps.py`, `app/panel/routes/__init__.py`; deleted seven legacy route modules and nine Jinja templates.
- **Slice 7 / PR #125:** `tests/integration/test_panel_delivery.py`, `infra/nginx/panel.lumat.cl.conf`.

## Deviations from Design

- Review advisories remain non-blocking follow-ups: **R3-001** around the Slice 1 `AppShell.tsx:126` area; **R3-001/R3-002** around Slice 2 `KbList`; **R3-001** around the Slice 3 `ClientesList` test; **R2-001** around Slice 5 `tasks.md`; and **R2-001** around Slice 6 `routes/__init__.py`.
- The Slice 6 advisory concerned the `export` aggregation versus the `/panel/login` redirect. Slice 7 resolves the delivery behavior through the nginx redirect and explicit backend-prefix locations; it is retained here as historical review context, not an implementation blocker.
- No source, test, or specification deviation blocked the final gates. The single backend warning is pre-existing and non-blocking.

## Graph Record

Graph Check passed before inspection. Consulted `graphify-out/GRAPH_REPORT.md` and the graph query for panel operational views. Relevant nodes included `Panel Operational Views — change tasks`, `panel-operational-views/design.md`, `AppShell.tsx`, `panelRoutes.ts`, `KbList.tsx`, `ClientesList.tsx`, `services/dashboard.py`, `test_panel_delivery.py`, `panel.lumat.cl`, and the SPA delivery specification. Consulted relationships included `AppShell → panelRoutes`, `api.ts → AdvancedDashboard`, `AdvancedDashboard → dashboard service`, `Dockerfile → panel SPA artifact`, `panel nginx → SPA index`, and `panel delivery test → nginx locations`.

The report records graph build commit `eb990dcf`; the verified implementation is `02534eab`. No graph refresh was performed while reconstructing this artifact, and no graph files were modified.

## Delivery / Branch / Commit

All slices used `stacked-to-main` and were merged through the following PRs:

| Slice | PR | Work-unit commit(s) | Merge commit on `main` |
|---|---:|---|---|
| 1 | #119 | `74c8fb95` | `67afd8c1c31a8611fc6064627d49982ceb648eae` |
| 2 | #120 | `da880981` | `ece686643b75385f15d7acf0c512bb09421bf305` |
| 3 | #121 | `ab9e56a4`, `6e5a700f` | `37edea60df84c58dd854f7fada43ee8bccbb3447` |
| 4 | #122 | `a6da009f`, `38b749df` | `f751d9a618596f8ad9c3c04d74e67cdad60e8ac2` |
| 5 | #123 | `4523c954`, `58f971c0` | `eb990dcfe9935d3704ba1964d24dc3f59b411be7` |
| 6 | #124 | `a6d176a0` | `36ec03111971ca3372a3fe419b8f954d6d7485c4` |
| 7 | #125 | `a8b5670c` | `02534eabd871dc5b709c338b6184146a2d8e185c` |

The seven-slice implementation chain is complete on `main`. This artifact is the canonical cumulative apply-progress record and is ready for global Strict-TDD verification.

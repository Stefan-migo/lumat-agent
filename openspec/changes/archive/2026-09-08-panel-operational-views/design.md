# Design: Panel Operational Views

## Technical Approach

Complete the React pages with `api.ts` contracts and refreshes, then expose AdvancedDashboard through the native History API table. Retire HTML routes/templates; auth API, conversations/realtime, CSV export, agente host, and visual grammar do not change. Narrow `panel.lumat.cl` to redirects, SPA assets, and backend prefixes.

Graph nodes consulted: target pages, shell/routes, `api.ts`, client/KB/dashboard APIs, serializers, deps, export, dashboard service, nginx. Edges: `AppShell → panelRoutes`, `api.ts → AdvancedDashboard`, clients/KB routes → serializers/services, advanced dashboard → dashboard service, nginx → SPA index.

## Architecture Decisions

| ID | Choice | Alternatives / rationale |
|---|---|---|
| D1 | Mutations use typed helpers and refetch the authoritative resource after success. | Optimistic updates risk stale audit-visible state; existing `useAsyncData` makes refresh simple and reversible. |
| D2 | Upload uses `FormData` with no manually supplied `Content-Type`; edit/disable/restore use JSON POST helpers. | A new upload abstraction is unnecessary; native browser multipart handles boundaries correctly. |
| D3 | Exports remain native same-origin downloads to `/panel/export/*.csv`. | API fetch/blob would duplicate browser download handling; session cookies already accompany same-origin navigation. |
| D4 | Move `compute_kpis` from the retiring HTML `routes/dashboard.py` into `app/services/dashboard.py`; API dashboard remains unchanged. | Leaving an API import pointing at deleted Jinja code violates retirement; duplicating logic risks drift. |
| D5 | Add `advanced-dashboard` as a normal `PanelView`/nav item and load summary, trend, and drilldown together. | No router dependency or new endpoint; mirror Agenda/Automations wiring. |

## Data Flow

`SPA page → api.ts (credentials: include) → /panel/api → JSON serializer/service → state refresh → shared StateMessage/DataTable`

Exports use `window.location`/an anchor, so the browser requests `/panel/export/clients.csv` or `cases.csv` with the session cookie.

## File Changes and Slice Boundaries

| Slice / rollback boundary | Files and implementation |
|---|---|
| 1. Client ficha; revert page/client helpers | `web/src/components/pages/ClientFicha.tsx`, `web/src/api.ts`, `web/src/types.ts`; state and note forms POST to `/state` and `/notes`, show safe `ApiError` feedback, then refetch ficha plus memories. Reuse `PageFrame`, `Card`, `EmptyState`, `DataTable`, `StateMessage`; preserve calendar retry. |
| 2. KB mutations; revert UI/API wiring | `web/src/components/pages/KbList.tsx`, `web/src/api.ts`, `web/src/types.ts`; upload with `FormData`, edit, disable, restore, map validation, handle admin 403, and refresh after every commit. |
| 3. Client exports; revert list controls | `web/src/components/pages/ClientesList.tsx`; replace data URI with same-origin anchor/window navigation to `/panel/export/clients.csv` and `/panel/export/cases.csv`; do not fabricate a file on auth failure. |
| 4. Advanced dashboard route; revert route/nav wiring | `web/src/components/domain/{PanelShell,panelRoutes,AppShell}.tsx`, `AdvancedDashboard.tsx`, `api.ts`; add typed view/nav, mirror Agenda/Automations selection, call summary/trend/drilldown under `require_user`, and render loading/empty/403/error states. |
| 5. Test migration; revert tests only | Migrate `tests/functional/{test_auth,test_clients,test_cases,test_kb_settings,test_dashboard_export}.py` HTML/form assertions to API contracts; add/update page tests and stories for mutation, refresh, error, denied, and export behavior. |
| 6. Jinja retirement; restore deleted files to roll back | Delete `app/panel/routes/{auth,dashboard,clients,cases,conversations,kb,settings}.py` and `app/panel/templates/**`; move `compute_kpis` to `app/services/dashboard.py`; remove Jinja-only imports/functions from `app/panel/deps.py`; update `app/panel/routes/__init__.py` to retain API aggregation, `export.py`, and realtime only. |
| 7. Delivery/spec boundary; revert nginx/spec/test commit | Update `infra/nginx/panel.lumat.cl.conf` redirects `/`, `/panel/`, `/panel/login` to `/panel/app/`, retain explicit API/WS/export proxies, remove broad `/panel/` fallback; confirm `agente.lumat.cl.conf` unchanged and Dockerfile static copy remains valid. Update delivery tests and delta artifacts. |

## Interfaces / Contracts

`api.ts` adds typed mutation helpers. JSON errors remain `ApiError(status, detail)`; UI maps 400/422 to field/action text, 401/403 to auth/permission state, and other failures to safe generic alerts. Dashboard calls retain `start`, `end`, `timezone`, `metric`, and `bucket`, adding `/drilldown` for bucket selection.

## Testing Strategy

Backend tests retain API auth, audit, validation, and CSV coverage. SPA tests cover loading/empty/403/error, mutation refresh, multipart shape, and real export URLs. Delivery tests assert redirects, proxy precedence, no broad fallback, agent exclusion, immutable artifact, and Jinja absence. Gates: `uv run pytest tests/`; `cd web && npx vitest run && npx tsc -b && npm run build`.

## Threat Matrix

| Boundary | Applicability | Safe/failure behavior | Planned RED tests |
|---|---|---|---|
| Documentation-like paths | N/A — no file execution | None | None |
| Git repository selection | N/A — no VCS automation | None | None |
| Commit state | N/A — no commit automation | None | None |
| Push state | N/A — no push automation | None | None |
| PR commands | N/A — no PR command execution | None | None |
| SPA routing | Applicable | Canonical entry redirects, deep links serve index, backend prefixes bypass fallback, unknown paths safely resolve dashboard | Redirect/proxy precedence, deep-link, unknown-path, and `aria-current` tests |

## Migration / Rollout

No migration or feature flag. Deliver seven stacked-to-main slices in order; each is reviewable under 400 authored lines and reversible at its listed seam. Roll back nginx first, then restore deleted Jinja files if smoke checks fail; data is not rolled back.

## Open Questions

None.

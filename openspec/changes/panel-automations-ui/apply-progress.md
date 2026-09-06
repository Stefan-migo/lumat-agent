# Apply Progress: Panel Automations UI

## Slice 1 — Backend CRUD, Validation, Audit

**Mode:** Strict TDD (RED → GREEN → triangulate → refactor)
**Delivery:** auto-chain, stacked-to-main, branch `feat/panel-automations-backend`
**Boundary:** backend API/service only; no `web/` changes
**Estimated authored lines:** ~300, within the 400-line slice budget

### Completed Tasks

- [x] 1.1 AP-12 access and envelope tests
- [x] 1.2 AR-4/5/6 CRUD, validation, atomicity, and audit tests
- [x] 1.3 Automation authoring validation and CRUD/status service helpers
- [x] 1.4 Authenticated automation-rules API, serializer, and router registration

### TDD Cycle Evidence

| Task | Test file | Layer | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 1.1 | `tests/functional/test_api_automation_rules.py` | Functional HTTP | N/A (new file) | ✅ 5 tests failed with route 404/fixture setup errors | ✅ 5 passed | ✅ Anonymous, operator, admin, 404, and method cases | ✅ Shared login/create helpers and local rule cleanup |
| 1.2 | `tests/functional/test_api_automation_rules.py` | Functional HTTP | N/A (new file) | ✅ CRUD/validation/audit assertions failed before route/service existed | ✅ 5 passed | ✅ Valid CRUD, boundary cooldown, scalar/null values, nested/list rejection, idempotent status | ✅ Atomic validation before mutation and snapshot helper |
| 1.3 | `tests/functional/test_api_automation_rules.py` | Functional HTTP | Existing automation evaluator behavior covered by full suite | ✅ Tests referenced missing service behavior | ✅ 5 focused tests passed | ✅ Multiple events/channels/cooldowns/condition shapes | ✅ Reused evaluator allowlists; authoring cooldown remains service-only |
| 1.4 | `tests/functional/test_api_automation_rules.py` | Functional HTTP | Existing panel API suite passed in full gate | ✅ Endpoint requests returned 404 | ✅ 5 focused tests passed | ✅ Read/admin/operator/anonymous/status/not-found paths | ✅ Thin routes delegate to service and serializer |

### Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command and exact result | `uv run pytest tests/functional/test_api_automation_rules.py` → **5 passed** in 6.78s |
| Runtime harness command/scenario and exact result | Same real FastAPI `TestClient` path through login/session, JSON routes, PostgreSQL test DB, mutation, and audit persistence → **5 passed** |
| Rollback boundary | Revert `app/services/automation.py`, `app/panel/api/routes/automation_rules.py`, `app/panel/api/serializers.py`, `app/panel/api/__init__.py`, and `tests/functional/test_api_automation_rules.py`; evaluator remains unchanged |

### Gate Evidence

- `uv run pytest tests/` → **583 passed** in 4m39s.
- `uv run pytest tests/functional/test_api_automation_rules.py` → **5 passed** in 6.78s.
- No `web/` files were modified.

### Graph Check

Consulted `AutomationRule`, `automation.py`, `record_audit()`, `AuditLog`, `panel/deps.py`, `serializers.py`, `routes/notifications.py`, and `AR-6 CRUD Audit Trail`. Consulted edges included `AutomationRule ↔ models.py`, `automation.py → AutomationRule`, `automation.py → record_audit()`, `routes/notifications.py → require_user_json()`, and `routes/settings.py → require_admin_json()`.

### Deviations / Issues

None from the corrected design. The shared functional fixture does not truncate `automation_rules`, so the new test file owns cleanup for that table to keep tests isolated.

## Slice 2 — Frontend Route, Navigation, Client, List

**Mode:** Strict TDD (RED → GREEN → triangulate → refactor)
**Delivery:** auto-chain, stacked-to-main, branch `feat/panel-automations-page` from `main` `400fc551`
**Boundary:** frontend route/navigation/client/list only; backend unchanged
**Estimated authored lines:** ~260, within the 400-line slice budget

### Completed Tasks

- [x] 2.1 RED: canonical list/detail routing, malformed-ID fallback, deep links, `aria-current`, operator visibility, and browser-back coverage
- [x] 2.2 RED: list page loading, empty, error/retry, forbidden, accessible table, fields, and notification event/content labeling
- [x] 2.3 GREEN: Rule types, six API functions, route parsing/dispatch, operator-visible navigation entry
- [x] 2.4 GREEN: `AutomationRulesPage` with `PageFrame`, `DataTable`, `StateMessage`, `EmptyState`, and accessible detail links

### TDD Cycle Evidence

| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 2.1 | `web/src/components/domain/{panelRoutes,AppShell}.test*` | Integration/jsdom | Existing domain suite preserved; final 20/20 then 23/23 focused | ✅ New route/detail and navigation assertions failed before implementation | ✅ `npx vitest run src/components/domain` → 20/20, final focused domain 20/20 | ✅ Canonical list/detail, malformed IDs, operator nav, active state, deep link, back path | ✅ Reused `PanelRoute` parser/history seam and kept existing routes intact |
| 2.2 | `web/src/components/pages/AutomationRulesPage.test.tsx` | Component/jsdom | N/A (new file) | ✅ Collection failed to resolve missing page before implementation | ✅ `npx vitest run src/components/pages/AutomationRulesPage.test.tsx` → 3/3 | ✅ Data table plus loading, empty, error/retry, forbidden, API-loaded states | ✅ Shared async/state primitives and pure column mapping |
| 2.3 | Domain tests + page API path | Integration/jsdom | Full web suite after change: 394/394 | ✅ Route tests referenced missing automation route/type | ✅ Focused domain/page tests and `npx tsc -b` passed | ✅ Read API shapes, list/detail URL generation, PATCH/status client functions | ✅ Thin API wrappers mirror existing `apiFetch`/`postJson` patterns |
| 2.4 | `web/src/components/pages/AutomationRulesPage.test.tsx` | Component/jsdom | N/A (new file) | ✅ Import failed before page existed | ✅ 3/3 focused tests | ✅ Non-empty table and all state branches exercised | ✅ Reused existing page primitives; no template selector or mutation controls |

### Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command and exact result | `cd web && npx vitest run src/components/domain src/components/pages/AutomationRulesPage.test.tsx` → **3 files, 23 tests passed** |
| Runtime harness command/scenario and exact result | Vitest jsdom runtime exercised deep-link parsing, History API push/back, operator navigation, API-backed list loading, and all list states → **23 passed** |
| Rollback boundary | Revert `web/src/api.ts`, `web/src/types.ts`, `web/src/components/domain/{panelRoutes,PanelShell,AppShell}.tsx`, `web/src/components/pages/AutomationRulesPage.tsx`, and the two modified/new test files; Slice 1 backend remains untouched |

### Gate Evidence

- `cd web && npx vitest run src/components/domain src/components/pages/AutomationRulesPage.test.tsx` → **23 passed**.
- `cd web && npx vitest run` → **394 passed**.
- `cd web && npx tsc -b` → **passed**.
- `uv run pytest tests/` → **583 passed** in 260.51s; no backend files were changed.

### Graph Check

Consulted `GRAPH_REPORT.md` god/community nodes `domain/AppShell.tsx`, `domain/PanelShell.tsx`, `api.ts`, `types.ts`, `AgendaPage.tsx`, `automation_rules.py`, and `Panel Automations UI Design`. Consulted edges included `AppShell.tsx → panelRoutes.ts`, `api.ts → AgendaPage.tsx`, `AppShell.tsx → AgendaPage.tsx`, `automation_rules.py → serializers.py`, and `panelRoutes.ts → pathForRoute()/parsePanelPath()`.

### Deviations / Issues

The detail route is canonical and history-addressable in Slice 2, while the full detail/edit surface remains intentionally deferred to Slice 3. The list uses `template_event` as notification event/content text and does not expose a template-version selector. Existing Vitest output contains pre-existing React `act(...)` warnings in AppShell tests; assertions and exit status pass.

## Slice 3 — Detail, Edit, Enable/Disable

**Mode:** Strict TDD (RED → GREEN → triangulate → refactor)
**Delivery:** auto-chain, stacked-to-main, branch `feat/panel-automations-detail` from `main` `116aad78`
**Boundary:** frontend detail/edit/status mutations only; backend untouched
**Estimated authored lines:** ~290, within the 400-line slice budget

### Completed Tasks

- [x] 3.1 RED: admin form validation, operator read-only controls, confirmation, enable/disable, API errors, and refresh-after-mutation
- [x] 3.2 GREEN: detail/edit form, bounded fields, Dialog confirmation, refresh-after-mutation, and AppShell detail dispatch

### TDD Cycle Evidence

| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 3.1 | `web/src/components/pages/AutomationRuleDetailPage.test.tsx` | Component/jsdom | N/A (new file) | ✅ Import failed before detail page existed | ✅ Focused command passed: 5/5 | ✅ Admin validation, edit refresh, operator read-only, confirmation/status refresh, API error | ✅ Shared validation/input mapping and mutation error path |
| 3.2 | `web/src/components/pages/AutomationRuleDetailPage.test.tsx` + `AppShell.tsx` | Component/jsdom | ✅ Existing domain/list suite preserved | ✅ Tests referenced missing detail implementation | ✅ Focused 5/5; full suite 399/399; typecheck passed | ✅ Detail route dispatch, PATCH refresh, status confirmation/refresh, role boundary | ✅ Reused `PageFrame`, `Button`, `Dialog`, `StateMessage`, and `useAsyncData`; no new dependency |

### Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command and exact result | `cd web && npx vitest run src/components/pages/AutomationRuleDetailPage.test.tsx` → **1 file, 5 tests passed** |
| Runtime harness command/scenario and exact result | Vitest jsdom exercised admin edit validation/PATCH refresh, operator read-only rendering, Dialog-confirmed disable/refresh, and mutation error rendering → **5 passed** |
| Rollback boundary | Revert `web/src/components/pages/AutomationRuleDetailPage.tsx`, `web/src/components/pages/AutomationRuleDetailPage.test.tsx`, and the detail dispatch line/import in `web/src/components/domain/AppShell.tsx`; Slices 1–2 API/list/routing remain intact |

### Gate Evidence

- `cd web && npx vitest run` → **399 passed** across 60 files.
- `cd web && npx tsc -b` → **passed**.
- Backend files untouched; backend suite not rerun per slice scope.
- Existing AppShell tests continue to emit non-failing React `act(...)` warnings.

### Graph Check

Consulted `GRAPH_REPORT.md` god/community nodes `AppShell.tsx`, `AutomationRulesPage.tsx`, `api.ts`, `types.ts`, `Dialog.tsx`, `PageFrame.tsx`, `StateMessage.tsx`, `useAsyncData.ts`, and `Panel Automations UI Design`. Consulted edges included `AppShell.tsx → panelRoutes.ts`, `AppShell.tsx → AutomationRulesPage.tsx`, `api.ts → getAutomationRule()/updateAutomationRule()/enableAutomationRule()/disableAutomationRule()`, `AutomationRuleDetailPage.tsx → Dialog()`, and `AutomationRuleDetailPage.tsx → useAsyncData()`.

### Deviations / Issues

None from the Slice 3 design. The detail component also supports an optional create mode for the design's create/edit wording, while the existing canonical route only dispatches persisted rule IDs. No backend or Slice 2 list behavior changed.

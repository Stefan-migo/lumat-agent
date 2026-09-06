# Tasks: Automation Rules Panel

## Review Workload Forecast

| Slice | Lines | Risk | PR boundary |
|---|---:|---|---|
| 1 | 300 | Medium | Backend CRUD/validation/audit |
| 2 | 320 | Medium | Route, navigation, client, list |
| 3 | 300 | Medium | Detail/edit/status mutations |
| 4 | 180 | Low | Stories and final gates |
| Total | 1100 | High | Four |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | PR | Test command | Harness | Rollback |
|---|---|---|---|---|---|
| 1 | AR-4/5/6, AP-12 backend | PR 1 | `uv run pytest tests/functional/test_api_automation_rules.py` | pytest | Revert backend/API |
| 2 | ARP-1/2 route and list | PR 2 | `cd web && npx vitest run src/components/pages/AutomationRulesPage.test.tsx src/components/domain` | Vitest jsdom | Revert route/list/client |
| 3 | ARP-3 detail mutations | PR 3 | `cd web && npx vitest run src/components/pages/AutomationRuleDetailPage.test.tsx` | Vitest + userEvent | Revert detail/status |
| 4 | ARP-1/2/3 stories and gates | PR 4 | `cd web && npx vitest run && npx tsc -b && npm run build` | Story fixtures | Revert stories/tests |

## Phase 1: Slice 1 — Backend CRUD, Validation, Audit

- [x] 1.1 RED: add AP-12 tests for anonymous/operator/admin access, envelopes, 404, and HTML redirects; command: `uv run pytest tests/functional/test_api_automation_rules.py`.
- [x] 1.2 RED: add AR-4/5/6 tests for CRUD, `created_by`, no delete, allowlists, cooldown `0..2592000`, scalar conditions, atomic rejection, and audit snapshots.
- [x] 1.3 GREEN: modify `app/services/automation.py` with `validate_rule_input()` and CRUD/status helpers, reusing `ALLOWED_EVENTS`/`ALLOWED_CHANNELS`; evaluator semantics stay unchanged (AR-4/5/6).
- [x] 1.4 GREEN: create `app/panel/api/routes/automation_rules.py`; modify serializers and `app/panel/api/__init__.py` for `/panel/api/automation-rules`, admin mutations, idempotent status actions, and audit (AR-4/6, AP-12).

## Phase 2: Slice 2 — Route, Navigation, Client, List

- [x] 2.1 RED: test canonical list/detail routes, malformed-ID dashboard fallback, deep links, `aria-current`, operator visibility, and back behavior; command: `cd web && npx vitest run src/components/domain` (ARP-1/2).
- [x] 2.2 RED: test `AutomationRulesPage` loading, empty, error/retry, forbidden, accessible table, fields, and event/content labeling (not template selector); command: `cd web && npx vitest run src/components/pages/AutomationRulesPage.test.tsx` (ARP-1/2).
- [x] 2.3 GREEN: modify `web/src/{api.ts,types.ts}` and `web/src/components/domain/{panelRoutes,PanelShell,AppShell}.tsx` with rule types, six API functions, route dispatch, and nav entry (ARP-1/2).
- [x] 2.4 GREEN: create `web/src/components/pages/AutomationRulesPage.tsx` using `PageFrame`, `DataTable`, `StateMessage`, and accessible links (ARP-1/2).

## Phase 3: Slice 3 — Detail, Edit, Enable/Disable

- [x] 3.1 RED: test admin create access, form validation, operator read-only controls, confirmation, enable/disable, API errors, and refresh-after-mutation; command: `cd web && npx vitest run src/components/pages/AutomationRuleDetailPage.test.tsx src/components/pages/AutomationRulesPage.test.tsx` (ARP-3, AP-12).
- [x] 3.2 GREEN: create `web/src/components/pages/AutomationRuleDetailPage.tsx` with bounded fields, accessible admin create flow, detail/edit mode, `Dialog` confirmation, and API refresh after every mutation (ARP-1/3).

## Phase 4: Slice 4 — Stories and Gates

- [x] 4.1 RED/GREEN: add stories/tests for data, loading, empty, error, forbidden, create, edit, and confirmation; command: `cd web && npx vitest run` (ARP-1/2/3).
- [x] 4.2 Run `uv run pytest tests/`; then `cd web && npx tsc -b && npm run build`; verify no delete, template linkage, or evaluator changes (AR-4/5/6).

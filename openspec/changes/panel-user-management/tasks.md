# Tasks: Panel User Management

Strict TDD: every GREEN follows RED. PRs stack to main as `feat/panel-user-management-sliceA` and `feat/panel-user-management-sliceB` (mirror house naming).

## Slice A — Backend (PR A: `feat/panel-user-management-sliceA`)

- [x] **A.1 RED — API contract/security.** PR A; add `tests/functional/test_api_users.py` covering every endpoint’s JSON 401/403, safe ordered shape/no hashes-locks, valid roles, blank/short/invalid input, duplicate no-row, missing target, audits, and self toggle/reset 403. Test: `.venv/bin/python -m pytest tests/functional/test_api_users.py`. Depends: none. Estimate: ~150 lines.
- [ ] **A.2 GREEN — service/routes.** PR A; extend `app/services/users.py` with `list_users`, `create_user`, `set_user_active`, `reset_password`; add `to_admin_user_dict` in `app/panel/api/serializers.py`; create/register `app/panel/api/routes/users.py` and router in `app/panel/api/__init__.py` using `require_admin_json`, hashing, commits, and `record_audit`. DoD: focused pytest, then `.venv/bin/python -m pytest tests/`; depends A.1. Estimate: ~190 lines.

## Slice B — Frontend (PR B: `feat/panel-user-management-sliceB`, stacked on Slice A)

- [ ] **B.1 RED — SPA route/view/security.** PR B; add `web/src/components/pages/UserManagement.test.tsx` and update `web/src/components/domain/{AppShell.test.tsx,PanelLinks.test.tsx,panelRoutes.test.ts}` plus `web/src/stories/pages/PanelEntry.stories.test.tsx` for admin route/nav count 9, non-admin filtering/denial, all role/status labels, safe shape, state matrix, validation/conflict, self-disabled actions, confirmation and mutation outcomes. Test: `cd web && npx vitest run src/components/pages/UserManagement.test.tsx src/components/domain/AppShell.test.tsx src/components/pages/PanelLinks.test.tsx src/components/domain/panelRoutes.test.ts src/stories/pages/PanelEntry.stories.test.tsx`. Depends: Slice A. Estimate: ~170 lines.
- [ ] **B.2 GREEN — SPA integration.** PR B; add `AdminUser` to `web/src/types.ts`, four fetchers to `web/src/api.ts`, and `UserManagement.tsx`; update `PanelShell.tsx` (admin-only Usuarios, Técnico), `panelRoutes.ts`, and `AppShell.tsx` with existing primitives and `window.confirm`. DoD: Vitest suite + `cd web && npx tsc -b`; depends B.1. Estimate: ~190 lines.

## Review Workload Forecast

| Slice | Estimated lines | Risk | Rollback boundary |
|---|---:|---|---|
| A | ~340 | Medium | Backend service, serializer, router, and API test |
| B | ~360 | Medium | Frontend page, wiring, navigation, and tests |
| **Total** | **~700** | **High across change** | Revert B, then A; no migration |

Decision needed before apply: No
Chained PRs recommended: Yes — auto-chain session
Chain strategy: stacked-to-main
400-line budget risk: Medium per slice; High total

## Ponytail Plan Review

- `A.1/A.2`: shrink: keep one focused API test module and one implementation task; no separate serializer/audit tasks.
- `B.1/B.2`: shrink: keep existing panel primitives, `window.confirm`, and route helpers; no modal, table, router, or state framework.
- `Forecast`: delete: migration, hard delete, role editing, timestamps, self-service, and extra verification task; existing contracts cover them.

Net: -3 additions from the task plan.

## Graph Check

Consulted `users.py`, `User`, `record_audit`, `serializers.py`, `api/deps.py`, `PanelShell()`, `AppShell()`, `panelRoutes`, `pathForRoute()`, `UserManagement SPA page`, `AppShell.test.tsx`, `PanelLinks.test.tsx`; edges: route → admin guard/service/serializer/audit and `AppShell → PanelShell → panelRoutes → UserManagement`. Graph report: 4196 nodes, 8841 edges, 516 communities; extraction warnings remain documented in `GRAPH_REPORT.md`.

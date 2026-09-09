# Tasks: Operational Dashboard Panel

Strict TDD: every GREEN follows RED. PRs stack as `feat/panel-dashboard-operativo-sliceN`.

## Slice 1 — Dashboard (PR 1: `feat/panel-dashboard-operativo-slice1`)

- [x] **1.1 RED — API.** Slice 1/PR1. Add `tests/functional/test_api_dashboard.py`: 401/403/422, timezone/DST, cancellation, ordering, predicates, caps, `new_customers`. Test: `.venv/bin/python -m pytest tests/functional/test_api_dashboard.py`. Depends: none.
- [x] **1.2 GREEN — API.** Slice 1/PR1. Modify `app/panel/api/routes/dashboard.py`, `app/panel/api/serializers.py`, `app/services/dashboard.py` for bounded today queries and additive KPI key. Verify: focused pytest. Depends: 1.1.
- [x] **1.3 RED — UI.** Slice 1/PR1. Extend `web/src/components/pages/Dashboard.test.tsx` for HOY navigation, role bento, four accents, trend/chips, loading/empty/error/403. Test: `cd web && npx vitest run src/components/pages/Dashboard.test.tsx`. Depends: none.
- [x] **1.4 GREEN — UI.** Slice 1/PR1. Modify `Dashboard.tsx` with existing `useAsyncData`, state primitives, `onNavigate`/`pathForView`, CSS bars. Verify Vitest + `cd web && npx tsc -b`. Depends: 1.2, 1.3.
- **Budget/DoD:** ~360/Medium; pytest + Vitest + typecheck. Rollback: dashboard files/tests.

## Slice 2 — Technician (PR 2: `feat/panel-dashboard-operativo-slice2`, stacked on PR1)

- [ ] **2.1 RED — role/auth.** Slice 2/PR2. Extend `tests/integration/test_migrations.py`, `tests/functional/test_api_auth.py` and denial tests for enum, login/me, restricted 403. Test: focused pytest. Depends: PR1.
- [ ] **2.2 RED — agenda/privacy.** Slice 2/PR2. Add `tests/functional/test_api_technician.py` for owned past/today/future ordering, forgery, exact keys and forbidden values. Test: focused pytest. Depends: 2.1.
- [ ] **2.3 GREEN — backend.** Slice 2/PR2. Create `db/migrations/019_tecnico_role.sql`; modify `app/models.py`, `app/panel/api/deps.py`, `app/services/scheduling.py`, `app/panel/api/{serializers.py,routes/technician.py,__init__.py}` with `require_tecnico`, ownership SQL and allow-list. Verify: `.venv/bin/python -m pytest tests/`. Depends: 2.1–2.2.
- [ ] **2.4 RED — SPA.** Slice 2/PR2. Extend `web/src/{app.test.tsx,components/domain/AppShell.test.tsx}` for tecnico shell, agenda, logout, no nav/forbidden DOM. Test: focused Vitest. Depends: 2.3.
- [ ] **2.5 GREEN — SPA.** Slice 2/PR2. Create `TechnicianShell.tsx`, `TechnicianAgenda.tsx`; modify `web/src/{types.ts,api.ts,app.tsx}`. Verify: Vitest + `npx tsc -b`. Depends: 2.4.
- **Budget/DoD:** ~350/Medium; pytest + web suite + typecheck. Rollback: technician files; never edit `001_init.sql`.

## Slice 3 — Permission fixes (PR 3: `feat/panel-dashboard-operativo-slice3`, stacked on PR2)

- [ ] **3.1 RED — automation.** Slice 3/PR3. Update `tests/functional/test_api_automation_rules.py`, `AppShell.test.tsx`, `PanelEntry.stories.test.tsx`, `AppShell.stories.test.tsx` for both GET 403, admin access, hidden nav and safe deep links. Test: focused pytest/Vitest. Depends: PR2.
- [ ] **3.2 GREEN — guards.** Slice 3/PR3. Modify `app/panel/api/routes/automation_rules.py` (both GETs `require_admin_json`) and `PanelShell.tsx` (`adminOnly: true`). Verify: full pytest + web suite + typecheck. Depends: 3.1.
- **Budget/DoD:** ~150/Low. Rollback: automation guards/navigation/tests.

## Review Workload Forecast

| Slice | Lines | Risk | PR / rollback |
|---|---:|---|---|
| 1 | ~360 | Medium | PR1 / dashboard files |
| 2 | ~350 | Medium | PR2 / technician files; enum retained |
| 3 | ~150 | Low | PR3 / automation files |
| **Total** | **~860** | **High** | **Three PRs** |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High; Low per slice

## Ponytail Review

Section "Tasks": shrink: keep RED/GREEN separate; no extra verification task. Section "Frontend": native: CSS bars and History API replace chart/router dependencies. Section "Technician": yagni: one named guard and minimal shell, not a generic framework. Net: -2 additions.

## Graph Check

Nodes: `services/dashboard.py`, `routes/dashboard.py`, `scheduling.py`, `appointments.py`, `serializers.py`, `models.py`, `panel/deps.py`, `PanelShell`, `AppShell`, `panelRoutes`, `Dashboard`, `StateMessage`, `test_migrations.py`. Edges: `routes → services`, `appointments → serializers`, `AppShell → PanelShell → panelRoutes`, `Dashboard → StateMessage`.

# Proposal: Operational Dashboard Panel

## Intent

The panel is fragmented, and its role model does not distinguish technicians. Rebuild it around action, clarify navigation, and add a privacy-bounded agenda.

## Scope

### In Scope
- **Slice 1 — Dashboard:** one authenticated, timezone-aware endpoint for today’s appointments, active/unanswered conversations, and urgent cases; HOY lists, role-specific bento navigation, and compact 7-day KPIs/trend/chips. “Unanswered” means inbound without later outbound; “today” uses the scheduling timezone; new customers means created in-window.
- **Slice 2 — Technician:** add `tecnico` and an additive migration; show only owned past/today/future appointments, enforcing `technician_id == current.id`. Serialize only customer name/address/comuna/phone, service, and `Case.summary`; reject chat, admin routes, and realtime.
- **Slice 3 — Fixes:** hide automation navigation from operators, preserve backend checks, fix Contactos accent, update role tests.

### Out of Scope

Agent upgrades; technician KB/configuration/editing; user-management UI; technician realtime/chat; responsible filtering.

## Capabilities

### New Capabilities
- `technician-agenda`: authenticated, ownership-enforced, privacy-minimal view.

### Modified Capabilities
- `advanced-dashboards`: operational projections and seven-day view.
- `admin-panel`: dashboard and role boundaries.
- `panel-app`: role routing, shells, navigation, and types.
- `service-scheduling`: technician-owned agenda reads.
- `automation-rules-panel`: operator navigation.

## Approach

Use bounded projections in one route, local-day semantics from `scheduling.list_for_range`, and KPI/summary/trend services. Add the role migration without editing `001_init.sql`, an allow-list serializer, ownership filtering, mobile view, and role routing. Keep slices under 400 lines with strict TDD.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `app/models.py`, `db/migrations/`, panel API/services | Modified/New | Role/data contracts |
| `web/src/components/pages/Dashboard.tsx`, domain shell/routes | Modified | Dashboard/routing |
| `tests/`, `web/src/**/*.test.tsx` | Modified | TDD and role coverage |

## Ponytail YAGNI Check

Shrunk three requests to one; reused existing services and History API; cut technician data to an allow-list. No chart dependency, generic permission layer, user UI, or realtime.

## Graphify Feasibility Check

Validated nodes `Dashboard.tsx`, `PanelShell.tsx`, `AppShell.tsx`, `panelRoutes.ts`, `services/dashboard.py`, `appointments.py`, `serializers.py`, `models.py`, `services/realtime.py`, `types.ts`, `test_migrations.py`, plus `appointments.py → serializers.py`. Graph stale (`eb990dcf` vs HEAD); queried, not rebuilt.

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Technician privacy leak | High | Dedicated allow-list, ownership tests, server enforcement |
| Migration/two-role assumptions break | Med | Numbered migration and test updates |
| Hidden automation route readable | Med | Verify backend GET permission |
| Definition drift | Med | Timezone/proxy tests |

## Rollback Plan

Revert slices in reverse order: navigation/tests, technician route/migration/UI, then dashboard route/UI. Restore the prior dashboard; never rewrite `001_init.sql`.

## Success Criteria

- [ ] Admin/operator dashboard shows approved HOY, bento, and 7-day sections.
- [ ] Technicians see only permitted agenda fields and no admin/chat/realtime surface.
- [ ] Required backend, migration, privacy, timezone, and web tests pass.

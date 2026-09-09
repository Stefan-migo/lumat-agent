# Design: Operational Dashboard Panel

## Context and goals

Rebuild the admin/operator dashboard around bounded HOY work, retain a compact seven-day block, and add a privacy-minimal, ownership-enforced technician agenda. Preserve JSON sessions, History API navigation, `useAsyncData`, and shared state primitives. Deliver three stacked-to-main slices under 400 lines.

## Constraints

Do not edit `001_init.sql`; the next migration is `019_tecnico_role.sql`. No router, chart dependency, generic permission framework, technician realtime/editing, or user-management UI.

## Architecture decisions

| Decision | Choice | Rationale |
|---|---|---|
| HOY API | Add `GET /panel/api/dashboard/today?timezone=...` in `routes/dashboard.py`; admin/operator only. | One bounded operational projection; local-day bounds follow `scheduling._zone` and UTC `[start,end)`; each collection is capped at 20. |
| Queries | Appointments join customer/case, exclude `CANCELLED`, order `starts_at,id`. Unanswered uses latest inbound plus `NOT EXISTS` later outbound, states `BOT/HUMAN`. Urgent uses `(escalated_at IS NOT NULL OR emergency) AND closed_at IS NULL`, escalation-first. | Correlated predicates avoid history loads and a new read model. |
| KPIs/trend | Extend `compute_kpis` with `new_customers` from `Customer.created_at >= start`, preserving existing keys. Dashboard calls `/kpis` and `/dashboard/trend` for seven days and contacts. | One compatible KPI contract; CSS bars replace a chart dependency. |
| Technician API | Add `GET /panel/api/technician/agenda`, `require_tecnico`, and `scheduling.list_for_technician`; server-filter `technician_id == current.id`, order `starts_at,id`. | A dedicated dependency/route makes ownership auditable and forbids client-selected ownership. |
| Technician surface | `to_technician_appointment_dict` emits exactly `id, service, local_start, starts_at, ends_at, timezone, customer{name,address,comuna,phone}, case_summary`; no status, history, sync, email, consent, messages, notes, or operational fields. Add `TechnicianAgenda`/`TechnicianShell`, never `PanelShell`. | Separate shell prevents navigation/data exposure. |
| Navigation/permissions | Keep `pathForView`/History API; dashboard receives `onNavigate`. Set automation `adminOnly: true` and both GETs to `require_admin_json`; guard conversation routes for tecnico; retain realtime's existing role check. | Reuses current seams instead of adding policy/routing abstractions. |

## Data flow and contracts

```text
AppShell role gate -> Dashboard -> today + kpis + trend -> bounded sections/states
login/me -> tecnico branch -> TechnicianShell -> technician/agenda -> allow-list serializer
```

Today returns `{tz, local_date, appointments_today: [{id,service,customer_name,local_start,starts_at,ends_at}], unanswered_conversations: [{id,customer_name,last_message_at,state}], urgent_cases: [{id,customer_name,service,summary,emergency,escalated_at}]}`. Invalid timezone 422; absent session 401; insufficient role 403. KPI adds `new_customers`; trend remains zero-filled daily buckets.

## Data model and file changes

| File | Action | Description |
|---|---|---|
| `db/migrations/019_tecnico_role.sql` | Create | `ALTER TYPE user_role ADD VALUE 'tecnico'`. |
| `app/models.py`, `app/panel/api/deps.py` | Modify | Enum member and `require_tecnico`. |
| `app/services/{dashboard,scheduling}.py` | Modify | KPI count, bounded projections, owned agenda query. |
| `app/panel/api/routes/{dashboard,technician,conversations,automation_rules}.py`, `api/__init__.py` | Create/modify | Endpoints, guards, registration. |
| `app/panel/api/serializers.py` | Modify | Today and strict technician serializers. |
| `web/src/{types.ts,api.ts,app.tsx}` | Modify | Contracts, fetchers, tecnico branch. |
| `web/src/components/{domain/{AppShell,PanelShell,TechnicianShell}.tsx,pages/{Dashboard,TechnicianAgenda}.tsx}` | Create/modify | Role-safe dashboard and shell. |
| `tests/`, `web/src/**/*.test.tsx`, `Dashboard.stories.tsx` | Create/modify | Strict RED-GREEN coverage. |

## State, security, and testing

Use `StateMessage`/`EmptyState`; `ApiError` distinguishes 401/403 and retries never fabricate rows. RED tests cover timezone/DST bounds, cancelled exclusion, unanswered/urgent ordering, new customers, exact serializer keys, ownership forgery, login/me, denied admin/chat/realtime, automation GET guards, row navigation, role routing, and forbidden DOM fields. Run `.venv/bin/python -m pytest tests/`, `cd web && npx vitest run`, and `cd web && npx tsc -b`.

## Design review

`ponytail-plan` was applied manually because its CLI is unavailable: `Section "HOY API": yagni: separate read model. Query existing models with bounded limits.` `Section "Frontend": native: chart dependency. CSS bars and existing primitives.` `Section "Permissions": yagni: generic policy registry. Reuse dependencies plus one technician guard.` `Section "Technician UI": shrink: full shell. One minimal agenda shell.` Net: -4 items cut.

## Threat matrix

| Boundary | Applicability | Safe/failure behavior | Planned RED tests |
|---|---|---|---|
| Documentation-like paths | N/A — no executable classification | None | None |
| Git repository selection | N/A — no Git automation | None | None |
| Commit state | N/A — no commit automation | None | None |
| Push state | N/A — no push automation | None | None |
| PR commands | N/A — no PR automation | None | None |
| SPA/API routing | Applicable — role branch, History routes, new endpoints | Unknown/deep links stay safe; API returns JSON 401/403 | AppShell deep-link/role and endpoint denial tests |

## Graphify deep-dive

Read `graphify-out/GRAPH_REPORT.md` (built `eb990dcf`, stale versus HEAD), queried dashboard/technician/role/navigation, and inspected dashboard/shell/route/service/model/API/migration/test nodes. Directed cross-layer paths were absent/ambiguous; consulted edges were `AppShell -> PanelShell -> panelRoutes`, `routes -> services`, and `appointments -> serializers`. No rebuild.

## Slices, rollout, and open questions

Slice 1 dashboard service/API/UI/tests; Slice 2 migration, technician API/UI/tests; Slice 3 automation/role fixes and regressions. Apply in that order, stacked to main, with strict TDD. Roll back by reverting slices; never remove the enum value. No feature flag. Confirm deployed PostgreSQL permits `ALTER TYPE ... ADD VALUE` in the migration transaction; otherwise run it outside the transaction.

# Design: Panel User Management

## Context and Goals

Add admin-only user management to the existing JSON panel API and SPA. Reuse `User`, bcrypt, signed sessions, audits, History API, and Settings conventions.

## Constraints

- Preserve roles `admin`, `operador`, and `tecnico`; use English artifacts and snake_case API keys.
- Every endpoint uses `require_admin_json`; denied requests return JSON 401/403 before service work.
- No password hash, lockout counters, timestamps, hard delete, role editing, self-service, or migration.
- Strict TDD: `.venv/bin/python -m pytest tests/`; `cd web && npx vitest run`; `cd web && npx tsc -b`.

## Architecture Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Service location | Extend `app/services/users.py` with `list_users`, `create_user`, `set_user_active`, `reset_password`. | Lookup and hashing already live there; another module adds a one-consumer abstraction. Keep explicit sessions and caller commits. |
| Serializer | Add `to_admin_user_dict`; do not reuse `to_user_dict`. | The existing serializer is intentionally `{id, username}` for case embeds, so it lacks role/active. An allow-list prevents sensitive drift. |
| Duplicate handling | Return HTTP 409 Conflict for an existing username. | Duplicate identity is a resource conflict, not 422 validation; hide database details. |
| UI actions | Use native controls and existing `PageFrame`, `Card`, `DataTable`, `StateMessage`, `Button`, and `Input`. | Mirrors Settings; no new modal/table/state framework. Browser confirmation protects reset. |

## API Contracts and Data Flow

```text
SPA UserManagement -> /panel/api/users -> require_admin_json -> users service -> User/AuditLog
       ^                    |                    |
       +---- safe {id, username, role, active} <-+
```

`GET /panel/api/users` returns `{ "users": UserAdminView[] }`, ordered `username ASC, id ASC`.
`POST /panel/api/users` accepts `{username,password,role}` and returns 201 `{user: UserAdminView}`. Require non-empty username, password ≥8, and a `UserRole` value; duplicate is 409.
`POST /panel/api/users/{id}/toggle-active` flips the target and returns `{user: UserAdminView}`; self is 403 and missing target 404.
`POST /panel/api/users/{id}/reset-password` accepts `{password}` ≥8, hashes it, returns the safe shape, and rejects self with 403. Mutations audit `user.create`, `user.toggle_active`, or `user.reset_password` with actor, entity/id, and safe `after` data.

## Data Model

No migration. `users` already contains `id`, `username`, `password_hash`, `role`, `active`, `failed_logins`, and `locked_until`; no `created_at`/`updated_at` is introduced.

## Frontend Structure

`PanelShell` adds `users: {label: "Usuarios", icon: UsersIcon, adminOnly: true}` and maps `tecnico` to `Técnico`. `panelRoutes` adds `/panel/app/users`; `AppShell` imports `UserManagement` and switches on `users`. The page mirrors Settings, loads `fetchUsers`, renders translated role/status, and provides create/toggle/reset controls; the current row disables actions. `types.ts` adds `UserAdminView`; `api.ts` adds four fetchers.

## State and Error Handling

`useAsyncData` supplies loading/error/denied/empty states with existing primitives. Mutations expose pending/success/error without fabricated rows; create/toggle refresh the list, reset reports completion and never displays a password. Preserve username/role after errors; clear only password. Render 401/403 as denial and 409 as actionable feedback.

## Testing Strategy

Backend RED tests in `tests/functional/test_api_users.py` cover auth, safe order/shape, roles, validation, duplicate/no row, audits, missing targets, and self-protection. `UserManagement.test.tsx` covers states, Técnico, safe shape, create/mutations, confirmation, and self row. Update `AppShell.test.tsx` (admin nav becomes nine) and `PanelLinks.test.tsx` for denial.

## Security and Threat Matrix

Server-side self-protection is authoritative; serializers allow-list fields; bcrypt is write-only; audits contain no plaintext. SPA filtering is not authorization.

| Boundary | Applicability | Safe/failure behavior | Planned RED tests |
|---|---|---|---|
| Documentation-like paths | N/A — no executable classification | None | None |
| Git repository selection | N/A — no Git automation | None | None |
| Commit state | N/A — no commit automation | None | None |
| Push state | N/A — no push automation | None | None |
| PR commands | N/A — no PR automation | None | None |
| SPA/API routing | Applicable — new History route and API routes | Canonical `/panel/app/users`; non-admin deep link is denied; API is JSON 401/403 | AppShell/PanelLinks route and every-endpoint auth tests |

## Slice Boundaries and Sequencing

Slice A: backend service, serializer, router registration, API tests. Slice B: types/API/page/navigation/routes/AppShell and Vitest regressions. Stack B on A, merge to main; each stays under 400 authored lines. No flag or migration.

## Rollback

Revert Slice B, then Slice A. Existing login, seeded admin, and audit behavior remain intact; no database rollback is required.

## Ponytail Review Result

`Section "Service": yagni: separate user-admin module. Extend users.py.`
`Section "Frontend": native: custom modal/table/state framework. Use confirm and existing primitives.`
`Section "Scope": delete: timestamps, hard delete, role editing, and self-service. Keep CRUD-lite.`
Net: -3 items cut.

## Graphify Deep-Dive

Consulted `GRAPH_REPORT.md` (4171 nodes, 8823 edges, 516 communities; built from `f4033580`, with extraction warnings). Nodes: `users.py`, `User`, `api/deps.py`, `routes/settings.py`, `serializers.py`, `record_audit`, `PanelShell()`, `NAVIGATION`, `AppShell()`, `pathForRoute()`, `Settings()`, `apiFetch()`, `postJson()`, and `test_api_automation_rules.py`. It validates route→auth/serializer, Settings style, AppShell→PanelShell→panelRoutes, and service audit seams. Ambiguous directed paths were resolved by source reads.

## Open Questions

- [ ] None blocking; implementation should confirm the exact existing error-envelope helper, if any, before introducing a local 409 handler.

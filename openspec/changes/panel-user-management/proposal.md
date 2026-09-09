# Proposal: Panel User Management

## Intent

Admins need to create operators and technicians, deactivate access, and reset passwords from the panel instead of using database access. Preserve the existing `admin | operador | tecnico` role model.

## Scope

### In Scope
- Admin-only list showing username, role, and active status; never serialize password hashes.
- Create users with username, role, and initial password.
- Toggle `active` and reset another user's password.
- Prevent admins from deactivating or resetting their own account.
- Audit create, activation changes, and password resets.

### Out of Scope
- Hard delete; deactivation is the soft-lifecycle operation.
- Self-registration, self-service, role changes, password framework, analytics, profiles, timestamps, or technician self-service.

## Capabilities

### New Capabilities
- `users-service`: Administrative user CRUD-lite and password resets.

### Modified Capabilities
- `admin-panel`: Admin-only user routes and authorization.
- `panel-app`: Admin-only user view/navigation and Técnico display.

## Approach

Deliver two stacked slices, each under 400 authored lines:

- **Slice A — Backend:** Extend `app/services/users.py`; add routes using `require_admin_json`; reuse `hash_password` and `record_audit`; test authorization, validation, self-protection, safe serialization, and audits.
- **Slice B — Frontend:** Mirror the settings/view-switch pattern in `PanelShell`/`panelRoutes`; add create/list/active/reset interactions, admin navigation, Técnico labeling, and Vitest coverage.

No migration: use existing `User` columns and order by username, then id. Ponytail cuts hard delete, timestamps, password framework, self-service, and role-change.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/users.py`, `app/panel/api/routes/` | Modified/New | User-management service and routes |
| `app/panel/api/deps.py`, `app/models.py` | Modified | Existing admin guard and role contract |
| `tests/` | Modified/New | Backend TDD and security/audit coverage |
| `web/src/` | Modified/New | Admin view, navigation, types, and tests |

## Graphify Feasibility Check

Queried `users` and attempted `auth.py → PanelShell.tsx`; the stale graph had no directed path. `GRAPH_REPORT.md` is unavailable; no rebuild. Validated `users.py`, `auth.py`, `deps.py`, `models.py`, `PanelShell`, and `panelRoutes`.

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Admin self-lockout | High | Reject self-deactivation and self-reset server-side and test it |
| Credential/hash exposure | High | Allow-list response fields and hash only on write |
| Role drift | Med | Reuse enum and test all three role labels |

## Rollback Plan

Revert the backend and frontend slices in reverse order. Existing seeded-admin and authentication behavior remains unchanged; no migration rollback is required.

## Dependencies

- Dashboard work must close before implementation begins.

## Success Criteria

- [ ] Only admins can access every user-management route and view.
- [ ] Create, list, activate/deactivate, and reset-password flows work without exposing hashes.
- [ ] Self-protection, audit, role, and frontend tests pass.

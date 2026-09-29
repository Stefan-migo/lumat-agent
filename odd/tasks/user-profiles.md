# ODD Task: user-profiles

Status: **in progress** — slice 1 (backend) authorized 2026-09-29
Worktree: `../lumat-agent-odd-user-profiles`
Branch: `odd/user-profiles`
Base: `dfb9eca2` (`main`, merge of PR #436)
Thread: **hilo multi usuarios** (Engram `odd/multi-usuarios/thread-status`)
Source: investigation of the panel users surface, 2026-09-29
Delivery strategy: `ask-on-risk`
Chain strategy: **stacked-to-main** (owner-confirmed 2026-09-29)

## Objective

Give every panel user a profile ficha with editable personal data, and make the
password flows actually work. Today the `Usuarios` panel lists four fields, cannot
change a password usefully, and hides account lockout entirely.

## Why this unit exists

The `usuarios-aislamiento` unit isolated projects and agent memory per user, and
`agent-role-access` opened the chat per role. Both are closed. What neither did is
give the person behind the account any identity beyond `username`, and neither
touched the password flows.

Two defects motivate the unit:

1. **The admin password reset is a dead end.** The UI generates a random UUID
   client-side, sends it, and never shows it to anyone (`UserManagement.tsx:55-64`,
   `:86`). The admin resets the account to a password nobody knows.
2. **Nobody can change their own password.** No self-service endpoint exists, and
   the only endpoint that sets a password is admin-only and explicitly refuses self
   (`users.py:125-126`).

## Decisions

| ID | Decision | Rationale | Rejected alternative |
|---|---|---|---|
| P1 (owner, 2026-09-29) | Scope **B**: an editable profile ficha with personal data, not just a read-only identity card. | Owner chose B over the smaller read-only option. | Scope A (identity + owner-scoped data, no migration). |
| P2 (owner, 2026-09-29) | The profile fields are `email`, `name`, `phone`, `position` (cargo/etiqueta libre). All nullable. | Owner selected all four. | Fewer fields, or an enum catalog for the cargo. |
| P3 (owner, 2026-09-29) | Slice 1 is the backend, delivered first and reviewed before the frontend slice. | Estimate exceeds the ~400-line review budget, so the chain is forced by size. | One PR with `size:exception`. |
| P4 (architect) | A non-admin edits **no** profile field; only their own password. Field editing is admin-only. | Matches the owner's framing of B; keeps the privilege boundary the two previous units established. | Let any user edit their own `name`/`phone`/`position`. |
| P5 (architect) | `email` is optional and unique case-insensitively **when present** (partial unique index on `lower(email) WHERE email IS NOT NULL`). | Mirrors `Customer.email` (`001_init.sql:54`, nullable `VARCHAR(200)`); a NOT NULL requirement would force a backfill of existing users. | Required + backfilled email. |
| P6 (architect) | The admin reset endpoint is **not** changed. The UI fix is to let the admin type the password (with a generate button that shows it in the field). | Avoids ever transporting a secret back through the API; the current backend contract is already correct. | Have the API generate and return the plaintext password once. |
| P7 (architect) | Email-based self-service recovery stays **out of scope**. | `send_email` exists (`app/services/notify.py:98`) but there is no token store, expiry, single-use consumption, or public route, and the panel is cookie-based same-origin with **no CSRF tokens** (`auth.py` module docstring) — a public recovery route changes the threat model and is its own unit. | Add a token table + public route in this slice. |

## Verified facts

All line numbers re-verified on this worktree at `dfb9eca2`.

- **The `users` table has seven columns and has never been altered.** `CREATE TABLE
  users` at `db/migrations/001_init.sql:64-72`: `id`, `username` (unique),
  `password_hash`, `role` (`user_role` enum, default `operador`), `active`,
  `failed_logins`, `locked_until`. A repository-wide search for `ALTER TABLE users`
  finds **zero** hits, so no email/name/phone/created_at/last_login exists.
- `User` model: `app/models.py:255-268`, identical to the table.
- Latest migration is `db/migrations/038_customer_merge.sql`; this unit opens with
  **039**. `db/migrate.sh` records only the version name in `schema_migrations`
  (no content hash), so a comment-only edit to an already-applied migration cannot
  invalidate a database.
- Serializers (`app/panel/api/serializers.py`): `to_user_dict` at `:191-193`
  returns `{id, username}`; `to_admin_user_dict` at `:196-203` returns
  `{id, username, role, active}`. **`locked_until` and `failed_logins` are
  serialized nowhere**, so a locked account is invisible to the admin.
- Users routes (`app/panel/api/routes/users.py`): `GET /users` `:48`,
  `GET /technicians` `:55`, `POST /users` `:65`, `POST /users/{id}/toggle-active`
  `:92`, `POST /users/{id}/reset-password` `:117`. There is **no** `GET /users/{id}`
  and **no** `PATCH /users/{id}`.
- Both self-targeting mutations are refused: `toggle_active` at `:99-100`,
  `reset_user_password` at `:125-126` (`403 admins cannot ... their own ...`).
- `app/services/users.py` is deliberately thin: `hash_password` `:35`,
  `verify_password` `:43`, `get_user_by_username` `:52`, `is_locked` `:57`,
  `record_failed_login` `:65`, `reset_login_state` `:79`, `list_users` `:84`,
  `create_user` `:89`, `set_user_active` `:107`, `reset_password` `:112`. No
  self-service password change and no profile update. Lockout policy is
  `MAX_FAILED_LOGINS = 5` / `LOCK_MINUTES = 15` at `:26-27`.
- Auth routes (`app/panel/api/routes/auth.py`): `POST /login` `:63`,
  `GET /me` `:126` (returns `{id, username, role}`), `POST /logout` `:132`. The
  session carries `user_id`, `username`, `role` only. Login audits
  `auth.login` / `auth.login_failed` / `auth.login_locked` / `auth.logout`.
- Guards (`app/panel/api/deps.py`): `require_user_json` `:46` (any authenticated
  panel user, technician included), `require_operator_json` `:51`,
  `require_dashboard_user` `:57`, `require_tecnico` `:58`, `require_admin_json`
  `:64`, and `require_agent_surface_json` `:78` over
  `AGENT_SURFACE_ROLES = {admin, operador, tecnico}` at `:74`.
- **Precedent for a profile PATCH body:** `CustomerProfileBody` at
  `app/panel/api/routes/clients.py:85` — follow its shape and validation style.
- `list_audit_entries` (`app/services/audit.py:41`) exists and its docstring says
  "Admin reads use `list_audit_entries`", but **no route calls it**.
- Frontend: `web/src/components/pages/UserManagement.tsx` is 88 lines — admin gate
  `:26-30`, create card `:78-85`, reset handler `:55-64`, columns `:66-70`, data
  table with the two row actions `:86`. Tests: 5 cases in
  `UserManagement.test.tsx` (108 lines).
- Frontend API (`web/src/api.ts`): `fetchUsers` `:210`, `createUser` `:212`,
  `toggleUserActive` `:213`, `resetUserPassword` `:214`.
- Frontend types (`web/src/types.ts`): `Role` `:8`, `User` `:10-14`,
  `AdminUser` `:16`, `AdminUsersResponse` `:17`.
- Drill-down precedent for a ficha route: `clients/:id` — `clientId` on
  `PanelRoute` (`panelRoutes.ts:6`), parsed at `:123-130`, rendered at
  `AppShell.tsx:120`. A `users/:id` ficha mirrors it.
- Shared role labels live in `web/src/roleLabels.ts` (added in #436); reuse it.

### Graph check

Graph queried in this worktree at `dfb9eca2`:
`graphify query "panel users API, user management page, and profile data model"`
and `graphify path "UserManagement.tsx" "users.py"` (no directed path — the two
communities connect only through `api.ts`/`types.ts`, which is why this unit has to
wire both sides).

Nodes consulted: `User` (`models.py:255`), `users.py`, `UserManagement.tsx`,
`serializers.py`, `api.ts`, `types.ts`, `panel/deps.py`, `CustomerProfileBody`
(`clients.py:85`), `PageFrame()`, `AppShell.tsx`, `ClientFicha.tsx`,
`ClientesList.tsx`.

Edges consulted: `UserManagement.tsx -> api.ts -> types.ts`;
`serializers.py -> models.py`; `AppShell.tsx -> UserManagement.tsx`.

## Scope

**In scope**

- Migration `039_user_profile.sql`: nullable `email`, `name`, `phone`, `position`
  on `users`, with a partial unique index on `lower(email)` where not null, plus a
  documented rollback.
- `GET /panel/api/users/{id}` (admin) — one user ficha.
- `PATCH /panel/api/users/{id}` (admin) — edit the four profile fields.
- `POST /panel/api/me/password` (any authenticated role) — self-service password
  change requiring the current password.
- `POST /panel/api/users/{id}/unlock` (admin) — clear `locked_until`/`failed_logins`.
- Serializers: the four new fields plus `locked_until`/`failed_logins` in the admin
  shape.
- Audit entries for every new mutation.
- Frontend (slice 2): `users/:id` ficha route, the profile page, the corrected
  admin reset flow, and a reachable self-service password change for every role,
  including inside `TechnicianShell`.

**Out of scope**

- Email-based self-service password recovery (P7).
- Avatar or any file upload.
- Editing `role` after creation.
- Making `name` replace `username` in the agenda or the technician picker — a ripple
  into another surface; record it as a follow-up.
- Active sessions or device listing; the panel uses a signed cookie, not a session
  table.
- Forcing email to be required, or any backfill of existing users.

## Slices

### Slice 1 — backend (this slice)

- **S1.1** Migration `039_user_profile.sql` + `User` model columns + rollback doc.
- **S1.2** Serializers: extend `to_admin_user_dict` with the four fields and the
  lockout state; add whatever self-read shape the ficha needs.
- **S1.3** `GET /panel/api/users/{id}` (admin).
- **S1.4** `PATCH /panel/api/users/{id}` (admin), following `CustomerProfileBody`.
- **S1.5** `POST /panel/api/me/password` (any authenticated), with current-password
  verification, the same ≥8 rule as `users.py:35-38`, an audit entry, and a
  successful reset of the lockout state.
- **S1.6** `POST /panel/api/users/{id}/unlock` (admin).
- **S1.7** Tests: unique-email conflict, case-insensitive email identity, patch
  validation, non-admin denial on every admin route, self password change happy
  path and wrong-current-password rejection, unlock, and lockout visibility in the
  admin shape.

Estimated authored size: 250–380 changed lines.

### Slice 2 — frontend ficha

- **S2.1** `users/:id` on `PanelRoute` + parse + `AppShell` drill-down + clickable
  rows in `UserManagement`.
- **S2.2** `UserProfile.tsx`: identity header, the four editable fields, lockout
  state with unlock, and a password card when viewing self.
- **S2.3** Fix the admin reset flow: a dialog where the admin types the password,
  with a generate button that shows it in the field (P6).
- **S2.4** Reach the profile / password change from the panel user menu and from
  `TechnicianShell`, so every role has a path.
- **S2.5** Tests for all of the above, including the technician path.

Estimated authored size: 300–450 changed lines.

## Acceptance criteria

| Criterion | Evidence required |
|---|---|
| A user row carries `email`, `name`, `phone`, `position` | Migration + model + serializer test |
| Email is unique case-insensitively when present, and may be null | Conflict test plus two-null-email test |
| An admin can read and edit one user's ficha | Route tests per field |
| A non-admin is denied on every admin users route | Per-route denial matrix |
| Any role can change its own password, proving the current one | Happy path + wrong-current-password test |
| A successful self password change clears the lockout state | Test asserting `locked_until`/`failed_logins` after the change |
| An admin can unlock a locked account | Unlock test plus the admin shape exposing the lock state |
| Every new mutation is audited | Audit row assertions |
| Existing isolation and role boundaries still hold | The full backend suite |
| Backend suite, web suite, and the web build pass | `uv run pytest tests/`, `cd web && npm test`, `cd web && npm run build` |

## Checks

- `uv run pytest tests/` — full backend suite.
- `cd web && npm test` — full frontend suite (slice 2).
- `cd web && npm run build` — the repository's only frontend type check.
- Migration through `db/migrate.sh` against the per-worktree test database; verify
  idempotence and rehearse the documented rollback.
- `git diff --check`.

## TDD

Strict TDD is active (`openspec/config.yaml:38`). Every unit of behavior starts with
a failing test (RED), then the minimal implementation (GREEN), then refactor with the
suite green. Backend runner `uv run pytest tests/`; web runner `cd web && npm test`.

## Risks and carried-forward context

- **The `me/password` route widens the mutation surface for every role.** It must
  require the current password, must not leak whether a password was correct beyond
  a single generic failure, and must be audited.
- **Email uniqueness is a cross-row constraint.** Normalize before comparing and
  rely on the partial unique index rather than an application-level check alone.
- **Two pre-existing network-dependent tests** hang on real outbound calls and are
  deselected in this repository's runs:
  `tests/integration/test_assistant_harness_context.py::test_assistant_graph_carries_context_metadata_into_evidence`
  and, intermittently,
  `tests/integration/test_assistant_harness_compatibility.py::test_exact_approval_replay_is_rejected_after_first_consumption`.
  Not caused by this unit; report if they fire.
- **`AgendaPage.test.tsx` is load-flaky** under concurrent suite load; passes in
  isolation.
- Carried from the thread audit, not fixed here: `assistant.capabilities` and the
  planner catalog remain unfiltered by role (`agent-role-access.md:200`).
- No push, PR, or merge happens without separate explicit owner authorization.
- `origin/main` is a moving target in this repository — re-verify it immediately
  before any merge decision.

## Progress

- [x] Thread audited and the profile scope chosen with the owner (P1, P2, P3).
- [x] Graph check run in this worktree; the plan recorded.
- [x] S1.1 — migration `039_user_profile.sql` and the `User` columns. (`9da4562b`)
- [x] S1.2 — serializers expose the four fields and the lockout state. (`f3e746e2`)
- [x] S1.3 — `GET /panel/api/users/{id}`. (`40da381e`)
- [x] S1.4 — `PATCH /panel/api/users/{id}`. (`40da381e`)
- [x] S1.5 — `POST /panel/api/me/password`. (`40da381e`)
- [x] S1.6 — `POST /panel/api/users/{id}/unlock`. (`40da381e`)
- [x] S1.7 — slice 1 tests. (`9da4562b`, `f3e746e2`, `40da381e`)

## Next step

Implement slice 1 (backend) with strict TDD, RED first, then stop for owner review
before slice 2.

# Apply Progress — panel-user-management

> Change: `panel-user-management` · Project: LumatAgent · Phase: sdd-apply · Strict TDD active (pytest + vitest + tsc) · Delivery: auto-chain, stacked-to-main (PR A = Slice A backend → PR B = Slice B frontend).

## Slice A — Backend (PR A: `feat/panel-user-management-sliceA`)

Status: **A.1 + A.2 complete** (focused green; full-suite gated by pre-existing assistant-stale tests → issue #143).

### Completed Tasks

- [x] **A.1** `tests/functional/test_api_users.py` — JSON 401/403, safe ordered shape (no hash/lockout fields), valid roles, blank/short/invalid input, duplicate no-row, missing target, audits, self toggle/reset 403.
- [x] **A.2** `app/services/users.py` (`list_users`, `create_user`, `set_user_active`, `reset_password`), `to_admin_user_dict` in `app/panel/api/serializers.py`, `app/panel/api/routes/users.py` + router registration in `app/panel/api/__init__.py` (`require_admin_json`, hashing, commits, `record_audit`).

### TDD Cycle Evidence (backend — pytest)

| Task | Phase | Result |
|---|---|---|
| A.1 | RED — wrote test module (no implementation) | Confirmed scope contract (authz/validation/audit/self-protect) |
| A.2 | RED — wrote service+route contract tests | Failed until service/routes implemented |
| A.2 | GREEN — implemented service + serializer + router | `.venv/bin/python -m pytest tests/functional/test_api_users.py` → **6 passed** |

### Full-suite notes

`pytest tests/` is gated by 4 pre-existing failures on `main` from the assistant work (migrations `020/022` assertion lag + `test_h4_chat.py` chat bug), **outside this change** — documented in issue #143. Focused backend evidence is green.

## Slice B — Frontend (PR B: `feat/panel-user-management-sliceB`, stacked on Slice A)

Status: **B.1 + B.2 complete** (vitest + tsc green).

### Completed Tasks

- [x] **B.1** `web/src/components/pages/UserManagement.test.tsx` + updates to `AppShell.test.tsx`, `PanelLinks.test.tsx`, `panelRoutes.test.ts`, `PanelEntry.stories.test.tsx` — admin route/nav count 9, non-admin filtering/denial, all role/status labels, safe shape, state matrix, validation/conflict, self-disabled actions, confirmation, mutation outcomes.
- [x] **B.2** `AdminUser` in `web/src/types.ts`, 4 fetchers in `web/src/api.ts`, `UserManagement.tsx`; `PanelShell.tsx` (admin-only Usuarios, Técnico), `panelRoutes.ts`, `AppShell.tsx` using existing primitives + `window.confirm`.

### TDD Cycle Evidence (frontend — vitest)

| Phase | Action | Result |
|---|---|---|
| RED | Added route/nav/view tests before wiring (B.1) | **FAIL** — 4 test files failed, 1 passed (missing route + navigation seams) |
| GREEN | Implemented `UserManagement.tsx` + wiring (B.2) | **PASS** — `cd web && npx vitest run` (5 files) → **59 passed** |

### Typecheck

`cd web && npx tsc -b` → **clean**.

## Scope Guardrails

- No backend files changed in Slice B; no frontend files changed in Slice A.
- No migrations, no hard-delete, no role-change, no self-service introduced.
- Reused existing panel primitives + `window.confirm` (no modal/table/router/state framework; Ponytail).

## Cross-cutting

- Artifact store: hybrid (OpenSpec files + Engram mirrors). Engram `apply-progress` mirrored under topic key `sdd/panel-user-management/apply-progress`.
- Environment note: backend suite requires `DATABASE_URL="postgresql+psycopg://app:app@localhost:5432/lumat" TEST_ADMIN_DB_URL="postgresql://lumat:lumat@localhost:5432/lumat"`; without `TEST_ADMIN_DB_URL` the conftest falls back to the `app` role which lacks `CREATEROLE` (env-only, not a change defect).

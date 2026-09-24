# ODD: agenda-operator-technicians

## Objective

Make the Agenda create-appointment flow work for the `operador` role by replacing the dialog's
admin-only technician lookup with an operator-readable, minimal technician list.

Prerequisite of the `agenda-booking` frontier. Deliberately separate from the availability work
(PR-2) because it is a defect in slice 1, not new capability.

## Problem

The role contract and the shipped dialog disagree.

- The panel navigation exposes `agenda` to every role (`web/src/components/domain/PanelShell.tsx:43,129`
  — no `adminOnly`), and every appointment route accepts `admin` and `operador`
  (`require_operator_json`, `app/panel/api/deps.py:46-49`).
- Slice 1's create dialog loads its technician options with `fetchUsers()` →
  `GET /panel/api/users` (`AgendaPage.tsx:116`), which requires **admin**
  (`app/panel/api/routes/users.py:47-51`, `require_admin_json`, `app/panel/api/deps.py:64-68`).
- Therefore an authenticated `operador` opens "Nueva visita" and receives `403`: the dialog shows
  "No pudimos cargar las opciones de la visita" and no appointment can be created. The headline
  capability slice 1 shipped does not work for a role the routes were opened to.
- The tests did not catch it because they mock `fetchUsers`
  (`web/src/components/pages/AgendaPage.test.tsx:240`). The mock hid the authorization mismatch.
- The operator-readable `GET /panel/api/cases` already returns `users: [{id, username}]`
  (`app/panel/api/routes/cases.py:68`) through `to_user_dict`
  (`app/panel/api/serializers.py:171-173`), but that projection deliberately omits `role`
  (`D8 — embedded in cases, no /users`), so the dialog cannot pick technicians out of it.

## Why a dedicated endpoint

- **Relaxing `GET /panel/api/users` is the wrong direction.** It would hand every operator the
  administrative projection (`role`, `active`) for every account. Least privilege wins.
- **Adding `role` to `to_user_dict` would silently widen `/cases`.** That contract is asserted by
  tests and documented as minimal; do not touch it.
- **A dedicated `GET /panel/api/technicians` returns exactly what a picker needs.** Role-filtered,
  `{id, username}` only, reusing the existing minimal serializer. Both existing contracts stay
  byte-identical.

## Scope

**In:**

1. `GET /panel/api/technicians` — operator-readable, `{"technicians": [{id, username}]}` for users
   with role `tecnico`, ordered by username.
2. Web client `fetchTechnicians()` and its response type.
3. The Agenda create dialog switches from `fetchUsers` to `fetchTechnicians`.
4. Tests: pytest for the new route (operator 200 + exact key set + role filter; unauthenticated 401;
   `tecnico` 403), Vitest updates for the dialog.

**Out (deliberate):**

- Any change to `GET /panel/api/users`, its guard, or its projection.
- Any change to `to_user_dict` or the `GET /panel/api/cases` payload.
- Availability endpoints and the availability editor (PR-2).
- `UserManagement.tsx` keeps using `fetchUsers` — it is an admin page and that is correct.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-agenda-booking-slice2`
- Branch: `odd/agenda-operator-technicians`
- Base: `66cc868a`
- Files:
  - `odd/tasks/agenda-operator-technicians.md`
  - `app/panel/api/routes/users.py`
  - `tests/functional/test_api_users.py`
  - `web/src/api.ts`
  - `web/src/types.ts`
  - `web/src/components/pages/AgendaPage.tsx`
  - `web/src/components/pages/AgendaPage.test.tsx`

Any file outside this list needs a scope update here first.

## Constraints

- **Strict TDD: ON** — source `openspec/config.yaml:38`. Python runner `uv run pytest tests/`; web
  runner `cd web && npm test`. Observe RED before the source change; never invent RED evidence.
- No linter, no type checker, no formatter. The only type check is `cd web && npm run build`
  (`tsc -b`).
- This worktree's test database is `lumat-test-lumat-agent-odd-agenda-booking-slice2` on host port
  `6303`: `eval "$(./infra/test-db.sh env)"` then `uv run pytest`.
- `graphify-out/` is absent in this worktree (gitignored). Graph Check ran against the primary
  worktree's graph. Nodes consulted: `Technician Privacy Allow-List`
  (`openspec/specs/technician-agenda/spec.md`), `to_user_dict()`, `routes/cases.py`, `users.py`,
  `AgendaPage.tsx`, `api.ts`, `types.ts`, `useAsyncData()`, `User`.
- **D6 language:** code, identifiers, comments, tests and this record are English. Operator-facing
  copy in the panel stays Spanish (`AgendaPage` strings already are).
- Work-unit commits are authorized. **Push and PR are separate decisions.**
- Delivery: `stacked-to-main`. This unit is PR-1 and merges to main alone; PR-2 (availability,
  branch `odd/agenda-booking-slice2`) starts from the updated main afterwards, in this same
  worktree.

## Decisions

- **D1 — Do not relax `/users`; add a dedicated minimal endpoint.** Smallest change that fixes the
  defect without widening any existing contract.
- **D2 — Reuse `to_user_dict`; add no serializer.** The payload is exactly the established minimal
  projection, just role-filtered server-side.
- **D3 — The route lives in `users.py` with `require_operator_json`.** Per-route auth is the
  established pattern in this codebase (no router-level guards), and `to_user_dict` is imported
  there. The admin routes in the same module keep `require_admin_json`.
- **D4 — No `active` filter.** `GET /cases` returns the full minimal user list unfiltered, and
  `book()` does not check technician activity either. Adding an `active` filter here would create an
  inconsistency and hide technicians who already own appointments or availability. Recorded as an
  observation, not fixed in this unit.
- **D5 — No availability work here.** It is PR-2.
- **D6 — The endpoint is read-only and returns no role field.** The server filters by role; the
  client never needs it.

## Route per task

| Task | Route | Trigger evidence |
| --- | --- | --- |
| T1–T4 | delegated (one bounded writer) | 6 non-trivial files across Python and TypeScript; the writer trigger fired |

## Tasks

- [ ] **T1 — RED (backend).** Functional test: an authenticated `operador` gets `200` from
  `GET /panel/api/technicians`, with only `tecnico` users and exactly `{id, username}` keys;
  unauthenticated gets `401` JSON; a `tecnico` gets `403` JSON.
- [ ] **T2 — GREEN.** Add the operator-readable route with the role-filtered minimal projection.
- [ ] **T3 — Web client.** `fetchTechnicians()` plus `TechniciansResponse` in `types.ts`.
- [ ] **T4 — Dialog.** `AgendaPage` loads technician options from `fetchTechnicians`; update the
  Vitest mocks and assert the operator path no longer depends on the admin endpoint.
- [ ] **T5 — Evidence.** Run the checks below and record actual results.
- [ ] **T6 — Record.** Update this document with the verification evidence and commit the work units.

## Acceptance criteria

1. An authenticated `operador` receives `200` with only `tecnico` users and exactly `{id, username}`
   per row.
2. Unauthenticated → `401` JSON; `tecnico` → `403` JSON. No redirects.
3. The Agenda create dialog reads its technician options from the operator-readable endpoint; no
   dialog test relies on mocking `fetchUsers`.
4. `GET /panel/api/users` is still `403` for `operador` and `tecnico`, and the `GET /panel/api/cases`
   payload is unchanged.
5. The new pytest case fails before the route exists (RED observed) and passes after; the full suite
   exits `0`; `cd web && npm test` is green; `cd web && npm run build` passes.
6. Only the files in Authorized scope change.

## Checks

- `eval "$(./infra/test-db.sh env)" && uv run pytest tests/functional/test_api_users.py -q`
- `uv run pytest tests/ -q`
- `cd web && npm test`
- `cd web && npm run build`
- `git diff --check`

## Progress

- [x] Created this ODD record before the first source change.
- [ ] T1–T6 pending.

## Verification evidence

To be filled with observed output, not copied from a worker report.

## Recovery

Resume with `mem_context`, then the project-scoped `mem_search` for `agenda-operator-technicians`,
then `mem_get_observation` for the full document, then read this file.

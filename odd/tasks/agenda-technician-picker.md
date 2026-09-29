# ODD — agenda-technician-picker

## Objective

Make the Agenda appointment flows actually work for the `operador` role: replace the admin-only
technician lookup in the create dialog **and** in the reschedule action with an operator-readable
minimal technician list.

## Problem — verified live in `main`

An authenticated `operador` can open Agenda, but cannot create or reschedule an appointment. The
authorization contract and the shipped UI disagree:

| Pieza | Evidencia |
| --- | --- |
| `GET /panel/api/users` requires admin | `app/panel/api/routes/users.py:47-49` (`require_admin_json`), `app/panel/api/deps.py:64-68` |
| Appointment routes accept the operator | `app/panel/api/routes/appointments.py:72` (`create_appointment`), `:132` (`reschedule_appointment`) — both `require_operator_json` (`deps.py:46-49`) |
| Agenda is exposed to every role | `web/src/components/domain/PanelShell.tsx:440` — only `chat` is admin-gated |
| The dialog loads options from the admin endpoint | `web/src/components/pages/AgendaPage.tsx:160` (`openCreate`, inside a `Promise.all`) |
| The reschedule action does the same | `web/src/components/pages/AgendaPage.tsx:240` (the `Reprogramar` button handler) |
| The fix never landed | `fetchTechnicians` and `/panel/api/technicians` do not exist in `main` |

Resulting behaviour for an `operador`: the `fetchUsers()` call is rejected with `403`, the
`Promise.all` throws, the `catch` at `AgendaPage.tsx:164-166` sets
`"No pudimos cargar las opciones de la visita"`, `setTechnicians` never runs, the technician
`Select` keeps only its placeholder, and `create()` rejects with
`"Completa todos los campos de la visita"`. The capability is authorized by the server and blocked
by the client.

The tests did not catch it because they mock `fetchUsers`
(`web/src/components/pages/AgendaPage.test.tsx`), which hides the authorization mismatch.

## Provenance — the parked branch

A previous attempt exists on the remote branch `odd/agenda-operator-technicians` (tip `14907dc5`,
base `66cc868a`, 2026-09-24). Its record — `odd/tasks/agenda-operator-technicians.md` on that
branch — diagnosed this defect correctly and its decisions are reused here with credit.

That branch is **not merged and cannot be merged as-is**:

1. It is **556 commits behind** `main`; the diff conflicts.
2. It predates the reschedule action. It patches only the `openCreate` call site; `main` now has
   **two**. Cherry-picking it would fix half the defect.
3. Its own record flags its implementation as **unverified**: *"No RED was observed, no test run was
   recorded, and no build was run for it."* Strict TDD still applies — observe RED first, then decide
   whether any part of it satisfies the test.

Design decisions carried over (credited to that record):

- **D1** — do not relax `/users`; add a dedicated minimal endpoint. Smallest change that fixes the
  defect without widening an existing contract.
- **D2** — reuse `to_user_dict` (`app/panel/api/serializers.py:191-193` → `{id, username}`); add no
  serializer.
- **D3** — the route lives in `users.py` with `require_operator_json`; per-route auth is the
  established pattern here. The admin routes in the same module keep `require_admin_json`.
- **D4** — no `active` filter. `GET /cases` returns the full minimal list unfiltered and `book()`
  does not check technician activity. Recorded as an observation, not fixed here.
- **D5** — no availability work (that was a separate slice).
- **D6** — read-only endpoint, no `role` field in the payload; the server filters.

## Scope

**In**

1. `GET /panel/api/technicians` — operator-readable, `{"technicians": [{id, username}]}` for users
   with role `tecnico`, ordered by username.
2. Web client `fetchTechnicians()` and its `TechniciansResponse` type.
3. `AgendaPage` switches **both** call sites — `openCreate` and the reschedule handler — from
   `fetchUsers` to `fetchTechnicians`.
4. Tests: pytest for the new route, Vitest for both dialog paths.

**Out (deliberate)**

- Any change to `GET /panel/api/users`, its guard, or its projection.
- Any change to `to_user_dict` or the `GET /panel/api/cases` payload.
- `UserManagement.tsx` keeps using `fetchUsers` — it is an admin page and that is correct.
- The `active` filter (D4) and availability work (D5).

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-agenda-technician-picker`
- Branch: `odd/agenda-technician-picker`
- Base: `e77da7d7` (`main`)
- Files:
  - `odd/tasks/agenda-technician-picker.md`
  - `app/panel/api/routes/users.py`
  - `tests/functional/test_api_users.py`
  - `web/src/api.ts`
  - `web/src/types.ts`
  - `web/src/components/pages/AgendaPage.tsx`
  - `web/src/components/pages/AgendaPage.test.tsx`
  - `web/src/stories/pages/AgendaPage.stories.test.tsx` (its API mock also exercises rescheduling)

Any file outside this list needs a scope update here first.

## Constraints

- **Strict TDD: ON** — source `openspec/config.yaml` (`testing.strict_tdd: true`). Python runner
  `uv run pytest tests/`; web runner `cd web && npm test`. Observe RED before the source change;
  never invent RED evidence.
- No linter, no type checker, no formatter. The only type check is `cd web && npm run build`
  (`tsc -b`).
- This worktree's test DB is its own compose project:
  `eval "$(bash infra/test-db.sh env)"` then `uv run pytest`.
- **D6 language:** code, identifiers, comments, tests and this record in English. Operator-facing
  panel copy stays Spanish (`AgendaPage` strings already are).
- Work-unit commits are authorized, one concern per commit, tests and docs travel with their code.
  No `Co-Authored-By`. **Push, PR and merge are separate decisions.**
- Ponytail: the smallest diff that fixes the defect. One route, one client function, one type, two
  swapped call sites. No abstraction, no shared hook.

## Graph Check (rapso-persona Step 1)

Query: `graphify query "panel users technicians authorization agenda appointment"`.

Nodes consulted: `AgendaPage.test.tsx` (`web/src/components/pages/AgendaPage.test.tsx`),
`types.ts` (`web/src/types.ts`), `TechnicianShell.tsx` (`web/src/components/domain/TechnicianShell.tsx`),
`Agenda section` (`web/DESIGN_SYSTEM.md`), `Panel dashboard section` (`web/DESIGN_SYSTEM.md`),
`users` mock data (`web/src/stories/pages/_shared/mockData/users.ts`).

Graph status: **degraded — stale** (report last marked `16ba9cbf`; `graphify --update` unavailable,
402). The query returns nodes; no refresh is claimed.

## Tasks

- [x] **T1 — RED (backend).** Functional test: an authenticated `operador` gets `200` from
  `GET /panel/api/technicians` with only `tecnico` users and exactly `{id, username}` keys;
  unauthenticated gets `401` JSON; a `tecnico` gets `403` JSON. Run it and **observe it fail**
  against the current code. Record the failure output.
- [x] **T2 — GREEN (backend).** Add the operator-readable route with the role-filtered minimal
  projection. Re-run T1 and observe it pass.
- [x] **T3 — Web client.** `TechniciansResponse` in `types.ts`; `fetchTechnicians()` in `api.ts`.
- [x] **T4 — Dialog, both call sites (RED first).** Swap `openCreate` **and** the reschedule handler
  to `fetchTechnicians`; `technicians` state becomes `UserRef[]`. Update the Vitest mocks and assert
  the operator path no longer depends on the admin endpoint. Observe the dialog test fail before the
  swap where feasible, then pass.
- [x] **T5 — Evidence.** Run every check below and record observed results.
- [x] **T6 — Record + commit.** Update this document with the evidence and commit the work units.

## Acceptance criteria

1. An authenticated `operador` receives `200` with only `tecnico` users and exactly
   `{id, username}` per row, ordered by username.
2. Unauthenticated → `401` JSON; `tecnico` → `403` JSON. No redirects.
3. Both Agenda paths — create and reschedule — read technician options from the operator-readable
   endpoint; no dialog test relies on mocking `fetchUsers`.
4. `GET /panel/api/users` is still `403` for `operador` and `tecnico`, and the `GET /panel/api/cases`
   payload is unchanged.
5. RED observed before GREEN for T1 and T4; the full pytest suite exits `0`; `cd web && npm test` is
   green; `cd web && npm run build` passes.
6. Only the files in Authorized scope change.

## Checks

- `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/functional/test_api_users.py -o addopts='' -q`
- `uv run pytest tests/ -o addopts='' -q`
- `cd web && npm test -- --run`
- `cd web && npm run build`
- `git diff --check`

## Route declaration

| Task | Route | Trigger evidence |
| --- | --- | --- |
| T1–T6 | **delegated — one bounded writer** | 7 files across Python and TypeScript (writer trigger); the writer must read the route module, the serializers, the dialog and its test (preparation trigger) |

## Delivery

- Forecast: ~20 backend lines + ~30 test lines + ~15 web lines + ~40 dialog-test lines → well under
  400. Single PR, no chain.
- Strategy: `ask-on-risk`. Branch `odd/agenda-technician-picker` → `main`. Label `type:bug` (a defect
  in a shipped slice, not new capability).
- RDD: **on** (global). Native review before delivery, on the committed candidate via
  `--base-ref <merge-base> --committed-only` (the selectorless STATUS projects only uncommitted
  work — see the `odd/followup-email-spanish` record).

## Progress

| When | State |
| --- | --- |
| 2026-09-29 | Worktree created and provisioned (backend + `npm ci`); task record authored. |
| 2026-09-29 | T1 RED observed: `test_technician_list_is_operator_readable_minimal_and_ordered` failed at `assert unauthenticated.status_code == 401`; observed `404 == 401` because the route did not exist. T2 GREEN: focused users tests passed (`7 passed in 4.61s`). |
| 2026-09-29 | T4 RED observed before swapping AgendaPage call sites: `AssertionError: expected "spy" to be called once, but got 0 times` at `expect(fetchTechnicians).toHaveBeenCalledOnce()` in the reschedule path. The create test had the same missing call; other tests in that deliberately early run also errored because its dialog was still calling `fetchUsers`. After both swaps, `npm test -- --run src/components/pages/AgendaPage.test.tsx`: `1 passed (37 tests)`. |
| 2026-09-29 | Focused backend GREEN: `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/functional/test_api_users.py -o addopts='' -q` → `7 passed in 4.61s`. |
| 2026-09-29 | Full backend check, first attempt without loading this shell's test DB env: **failed** at setup (`662 passed, 1063 errors`), because `db/migrate.sh` received `psycopg.errors.InsufficientPrivilege: permission denied to alter role` (`Only roles with the CREATEROLE attribute and the ADMIN option on role "app" may alter this role`). Retried with `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/ -o addopts='' -q`: timed out at 300s (~58% progress); retry timed out at 600s (~58% progress). No full-suite result is claimed. |
| 2026-09-29 | Web check: `cd web && npm test -- --run` → **failed**: `89 passed, 1 failed; 851 passed, 1 failed (852 tests)`; `AgendaPage.test.tsx > shows validation instead of throwing when the selected case has no service` timed out after 5000 ms. Earlier run exposed a missing `fetchTechnicians` mock in the Storybook test; that mock was fixed within this task's scope before this latest run. |
| 2026-09-29 | Storybook test recheck: `npm test -- --run src/stories/pages/AgendaPage.stories.test.tsx` → passed (`1 passed`, `12 tests`). |
| 2026-09-29 | `cd web && npm run build` → passed (`tsc -b && vite build`; Vite emitted the existing >500 kB chunk advisory). `git diff --check` → passed (no output). |
| 2026-09-29 | Graph consulted: `AgendaPage.tsx` → `AgendaPage.test.tsx`/`AgendaPage.stories.test.tsx` (`imports_from`), `types.ts` and `api.ts` (`AgendaPage.tsx` dependencies), `users.py` → `require_operator_json` and `to_user_dict`. `graphify query "panel users technicians authorization agenda appointment"` and `graphify path "users" "AgendaPage"` found no directed path due ambiguous matches; targeted story path returned `AgendaPage.stories.test.tsx --imports_from--> AgendaPage.stories.tsx --imports_from--> AgendaPage.tsx`. Graph is stale (built at `ecc67e48` vs worktree base `e77da7d7`); no refresh was claimed. |
| 2026-09-29 | Commits: `991d7b8a` — `feat(agenda): add operator-readable technician list`; `1265e615` — `fix(agenda): load technicians for create and reschedule`. |
| 2026-09-29 | **Orchestrator verification — supersedes the two inconclusive rows above.** Full backend suite with this worktree's test DB env loaded: `uv run pytest tests/ -o addopts='' -q` → **`1725 passed, 2 warnings in 364.14s`**. The earlier timeouts were insufficient time windows, not a hang; a full-suite result is now claimed and observed. |
| 2026-09-29 | Web suite re-measured: `cd web && npm test -- --run` → `1 failed, 851 passed (852)`, the failure this time being `AppShell.test.tsx > renders live data pages for every navigation view` (5000 ms timeout) — a **different** test than the earlier run's `AgendaPage` timeout, in a file this change does not touch. Both pass in isolation (`AppShell.test.tsx`: `29 passed`; the `AgendaPage` case: `1 passed` in 3628 ms). With `--testTimeout=20000`: **`90 passed (90)`, `852 passed (852)`**. Conclusion: load-dependent timeout pressure — the pre-existing web-suite flake documented as **L8** — not a regression from this change. Recorded as an evidence-backed observation for L8: the suite is fully green when each test is given 20 s. |
| 2026-09-29 | Scope note: `web/src/stories/pages/AgendaPage.stories.test.tsx` was added to Authorized scope here (its API mock also exercises rescheduling) before it was touched. That is the protocol this record requires, not a scope violation. |
| 2026-09-29 | Both call sites confirmed: create → `Promise.all([fetchClients(), fetchCases(), fetchTechnicians()])`; reschedule → `fetchTechnicians().then((response) => setTechnicians(response.technicians))`. |

# ODD: agenda-booking

## Objective

Let the panel operator create an appointment from the Agenda screen using the scheduling engine
that already exists, and stop the create endpoint from turning a bad timezone into a 500.

Slice 1 of 2. Slice 2 (technician availability endpoints + editor) is scoped below and deliberate
`out` here.

## Problem

The engine is done and the guard rails are real; the UI never got wired to it, and one error path is
missing.

- The scheduling service is complete and timezone-safe: `book()` validates timezone/DST, the
  configured availability and overlapping bookings, and converts the database `IntegrityError` into
  `AppointmentConflict` (`app/services/scheduling.py:75-101`).
- Double booking is prevented **at the database**, per technician and per customer, with two
  `EXCLUDE USING gist` constraints (`db/migrations/011_h3_scheduling.sql:44-49`). Race-safe, not an
  `if` somebody can forget.
- `POST /panel/api/appointments` exists and maps conflicts to **409** (`app/panel/api/routes/appointments.py:53-66`).
- But the Agenda screen is read-only: `web/src/api.ts:129-137,169` exposes list / cancel /
  calendar-sync only, and `AgendaPage.tsx` is a 154-line read-only table.
- `scheduling.add_availability()` (`app/services/scheduling.py:123-134`) has **no panel route at
  all**, so `technician_availability` cannot be populated from the product. Because `book()` only
  enforces availability when at least one block exists (`scheduling.py:81-83`), the enforcement half
  of the engine is dormant. That is slice 2's reason to exist.

**Bug found while scoping, and in scope here:** `create_appointment()` catches
`UnlinkedAppointment`, `AppointmentConflict`, `Unavailable` and `ValueError`
(`appointments.py:57-64`) but **not `InvalidTimezone`**, which `local_interval()` can raise
(`scheduling.py:45-55`). Listing the agenda maps it (`appointments.py:37-40`); create does not. So a
bad timezone on create is an unhandled 500 today — and the new form will be sending a timezone.

## Why this is cheap

- The house create pattern is established and reusable: local form state + `useAsyncData` with a
  `refreshKey`, `postJson`, `ApiError.detail/status`, feedback through `StateMessage`
  (`web/src/components/pages/UserManagement.tsx:21-46`, `AutomationRuleDetailPage.tsx:77-123`).
- The primitives exist: `Input`, `Select`, `Button`, `Dialog`, `Card`, `StateMessage`, `FieldShell`
  under `web/src/components/primitives/` and `web/src/components/shared/`.
- `AgendaPage` already has a mutation + refetch pattern to copy for cancel and calendar retry
  (`AgendaPage.tsx:68-100`), and a controlled-data contract
  (`AgendaPageProps`: `data`/`state`/`onRetry`/`timezone`, `AgendaPage.tsx:17-24`) that the create
  action must not break.
- The data sources for the form already exist as endpoints: `GET /clients` (`clients.py:97`),
  `GET /cases` (`cases.py:55`), `GET /users` (`users.py:47`, already wrapped as `fetchUsers`,
  `api.ts:171`).

## Scope

**In (slice 1):**

1. `InvalidTimezone` mapped to a structured `400` on create.
2. Web API client: the create request type + `createAppointment`, plus whatever lookup helper the
   form needs that does not already exist.
3. A local-date/time + IANA timezone conversion helper on the web side, with explicit DST
   (nonexistent / ambiguous local time) signalling — the backend distinguishes those cases and the
   UI must not silently swallow them.
4. A create-appointment dialog inside the Agenda screen: customer, case, technician, service, local
   date, local time, duration, timezone; `409` surfaced as a specific "that technician is already
   booked at that time" message rather than a generic error.
5. Coverage: pytest for the backend mapping, Vitest for the conversion helper and the create flow.

**Out (deliberate):**

- Technician availability endpoints and editor (slice 2).
- Reschedule / edit of an existing appointment: no endpoint exists; it is a new capability.
- Free-slot search: no computation exists (`scheduling.availability()` only answers "is this exact
  interval free"), and it is a new capability.
- Business-hours enforcement inside `book()`: `is_open_at()` exists
  (`app/services/settings.py:259-299`) but `book()` never calls it, and there is no holiday model.
  Documented, not fixed.
- Appointment confirmation messaging to the customer: not part of the operator UI path.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-agenda-booking`
- Branch: `odd/agenda-booking`
- Base: `6b3214bd`
- Files: `odd/tasks/agenda-booking.md`, `app/panel/api/routes/appointments.py`,
  `tests/functional/test_api_scheduling.py`, `web/src/api.ts`, `web/src/types.ts`,
  `web/src/components/shared/agendaTime.ts`, `web/src/components/shared/agendaTime.test.ts`,
  `web/src/components/pages/AgendaPage.tsx`, `web/src/components/pages/AgendaPage.test.tsx`.

Any file outside this list needs a scope update here first.

## Constraints

- **Strict TDD: ON** — source `openspec/config.yaml:38` (`testing.strict_tdd: true`); Python runner
  `uv run pytest tests/`; web runner `cd web && npm test` (`vitest run`). Observe RED before the
  source change; never invent RED evidence.
- The repo has **no linter, no type checker and no formatter** configured; `web` type-checks through
  `npm run build` (`tsc -b`). Use that as the type check.
- Python tests need the worktree's own test database: `./infra/test-db.sh up`, then
  `eval "$(./infra/test-db.sh env)"`, then migrations as admin (a fresh database has no `app` role).
  `infra/.env` is gitignored and must be copied into a fresh worktree.
- **`graphify-out/` is absent in this worktree** (gitignored). Graph Check was performed against the
  primary worktree's graph. Nodes consulted: `availability()`, `scheduling.py`, `AgendaPage()`,
  `AgendaPage.test.tsx`, `api.ts`, `types.ts`, `useAsyncData()`, `appointments.py`, `Settings.tsx`.
- The planning heuristic is ~400 authored changed lines for the whole feature; slice 1 is forecast at
  ~230. Slice 2 is forecast at ~280, so the feature crosses the budget and delivery will be chained
  PRs (`ask-on-risk` is the cached strategy).
- Work-unit commits are part of this authorized route. **Push and PR are not** — separate decision.
- All artifacts in English.

## Decisions

- **D1 — Do not touch the scheduling service.** The engine is correct and tested. Slice 1 fixes one
  missing error mapping in the route layer and adds a caller. Any change to
  `app/services/scheduling.py` is out of scope; if the work seems to need one, stop and report.
- **D2 — The create flow lives inside `AgendaPage`, in a `Dialog`.** No new panel route, no
  `AppShell` change: `AppShell` mounts `<AgendaPage />` with no props (`AppShell.tsx:112-115`) and
  adding a route would touch navigation for no gain.
- **D3 — The create action must not break the controlled-data contract.** `AgendaPage` prefers
  `updatedData` over controlled `data` and never resets it when the period changes
  (`AgendaPage.tsx:47,63`). The create flow reuses `refreshAgenda()` and must leave `data`/`state`/
  `onRetry` semantics exactly as they are.
- **D4 — DST is surfaced, not swallowed.** The backend raises `NonexistentLocalTime` /
  `AmbiguousLocalTime` and maps both to `400 invalid_local_time`. The web helper must detect the same
  two conditions locally and tell the operator which one it is before the request is sent; the
  backend mapping stays the authority.
- **D5 — `409` is a first-class outcome, not an error.** The form must distinguish
  `appointment_conflict` / `technician_unavailable` (409) from `invalid_local_time` (400) and from a
  generic failure, because the operator's next action differs: pick another time versus fix the input.

## Tasks

- [ ] **T1 — RED (backend).** Functional test: `POST /panel/api/appointments` with an invalid IANA
  timezone returns `400` with a structured code, not a 500.
- [ ] **T2 — GREEN.** Map `InvalidTimezone` in `create_appointment` next to the existing handlers.
- [ ] **T3 — RED/GREEN (web helper).** `agendaTime`: compose a local date + clock + IANA timezone
  into the request payload parts, and report nonexistent / ambiguous local time distinctly. Vitest
  first.
- [ ] **T4 — Web API client.** Request type, `createAppointment`, and any lookup helper the form
  needs that is genuinely missing.
- [ ] **T5 — RED/GREEN (UI).** Create dialog in `AgendaPage` with the outcome handling of D5 and the
  refetch of D3. Vitest first.
- [ ] **T6 — Evidence.** Required checks run; results recorded below.

## Acceptance criteria

1. The backend test fails before the mapping change (RED observed) and passes after.
2. An invalid timezone on create returns `400` with a structured error code; a double booking still
   returns `409 appointment_conflict`; an unavailable technician still returns `409 technician_unavailable`.
3. The conversion helper rejects a nonexistent local time and an ambiguous local time with distinct
   messages, and a valid time produces the exact payload parts the backend expects.
4. The Agenda screen can create an appointment end to end and the new appointment appears in the
   list without a manual page reload.
5. The controlled-data contract of `AgendaPage` still works: the page renders correctly when
   mounted with props and when mounted bare.
6. `cd web && npm run build` passes (the only type check available).
7. Only the files in Authorized scope change.

## Checks

- `TEST_ADMIN_DB_URL=... uv run pytest tests/functional/test_api_scheduling.py -q`
- `uv run pytest tests/ -q` (full suite; a failure outside this unit must be reported, not fixed)
- `cd web && npm test`
- `cd web && npm run build`
- `git diff --check`

## Progress

- [x] Created this ODD record before the first source change.

## Verification evidence

| Command | Observed result |
| --- | --- |
| (pending) | |

## Recovery

Resume with `mem_context`, then the project-scoped `mem_search` for this feature, then
`mem_get_observation` for the full document, then read this file.

## Next step

Slice 1 implementation (T1). Slice 2 (technician availability) is scoped but not started.

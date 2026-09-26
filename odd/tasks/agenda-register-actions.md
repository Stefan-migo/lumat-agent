# ODD Task: agenda-register-actions

Status: in progress
Worktree: `../lumat-agent-odd-agenda-register-actions`
Branch: `odd/agenda-register-actions`
Base: `28fd4ad3` (main, after U5 `agenda-appointment-detail` and the CI frontend gate)
Depends on: `agenda-appointment-detail` (U5, PR #376, merged `7fb8cd10`)
Source: `.rapsodia-code/sessions/archived/2026-09-25-agenda-redesign/report.md` (U6 row, line 92)

## Objective

Close the Agenda family (U6, the last unit) with the two actions the register still cannot
perform on a `booked` visit:

1. **Register the outcome** — mark a visit `completed` or `no_show`.
2. **Reschedule** — move a `booked` visit to a new slot through a real, re-validated
   transition, not a bare row update.

## Objective drift found before planning (evidence, not impression)

The 2026-09-25 report assigned U6 = register filter (D3) + quick-action CRUD +
`completed`/`no_show` "if missing". Two facts change that picture:

1. **The register filter already shipped.** U5 delivered it in `423eb812`
   (`feat(agenda): split the register into active and non-active visits`):
   `registerView` (`AgendaPage.tsx:68`), the `Activas`/`No activas` `Tabs` (`:235`), and the
   active/non-active partition (`:192-194`). **AG-UI-6 is satisfied already**; this unit
   verifies it and does not rebuild it.
2. **`completed` and `no_show` are dead enum values.** `AppointmentStatus` declares them
   (`app/models.py:155-158`) and the web already renders their label and tone
   (`toneMaps.ts:37-38`), but *nothing can produce them*: `scheduling.py` exposes `book`
   (`:75`) and `cancel` (`:104`) only, `app/panel/api/routes/appointments.py` has no route
   for them, and no UI action exists. Today the non-active view can only ever show
   `cancelled`.
3. **The `PATCH /appointments/{id}` was deliberately dropped by U5.** U5's task doc listed it
   under **Out** ("the `PATCH /appointments/{id}` mentioned in the 2026-09-25 handoff, which
   AG-UI-5 does not require"). AG-UI-3 keeps authorizing it in prose. The owner folded it into
   this unit this session.

## Problem

1. An operator who finishes a visit has no way to say so: the visit stays `booked` forever
   or has to be cancelled, which lies in the data (a cancelled visit that was actually
   attended) and pollutes the register's non-active view with records that did happen.
2. An operator who booked the wrong slot can only `cancel` and `book` again. That is two
   audited actions, a `appointment.cancelled` customer event, and a broken audit trail for
   what was a single correction.
3. Rescheduling is the risky one: the report's own risk table names it — "a `PATCH`
   reschedule could skip booking validation — reschedule MUST re-run timezone, DST,
   availability and overlap validation, not a bare `UPDATE`". `book` (`scheduling.py:75-101`)
   holds that validation inline, so a second copy would drift.

## Why (approved decisions)

- **D-U6-1 — Close mirrors cancel.** `scheduling.close(...)` follows the exact shape of
  `cancel` (`scheduling.py:104-114`): guard `appointment.status is not AppointmentStatus.BOOKED`
  → `ValueError`, set the new status, `session.flush()`, `_history(...)`, `record_audit(...)`.
  One service function for both outcomes, parameterized by the target status.
- **D-U6-2 — Commands, not a status PATCH.** Closing is `POST /appointments/{id}/close` with
  `{"outcome": "completed" | "no_show"}`, mirroring `cancel`'s `POST` + body shape. A generic
  "set any status" PATCH would let a caller write `booked` back over a terminal row, which
  AG-UI-3 forbids. Rescheduling is `PATCH /appointments/{id}` because it is genuinely a
  replacement of the schedule, and AG-UI-3 already names it that way.
- **D-U6-3 — Reschedule replaces the whole slot.** The body carries the complete new slot
  (`local_date`, `local_time`, `timezone`, `duration_minutes`, `technician_id`). No partial
  merge logic to get wrong; the caller already has every field on screen.
- **D-U6-4 — One validation path.** Extract the inline validation of `book` into
  `_validate_slot(...)` and call it from both `book` and `reschedule`, so the two cannot
  drift. It covers `local_interval` (timezone + DST), technician availability, and overlap.
- **D-U6-5 — The overlap query must exclude the appointment itself.** `book`'s overlap query
  (`scheduling.py:86-91`) has no exclusion. Reused verbatim by `reschedule` it would make any
  no-change reschedule conflict with its own row. `_validate_slot` takes
  `exclude_appointment_id` and adds `Appointment.id != exclude_appointment_id`.
- **D-U6-6 — Terminal means terminal.** Only a `booked` visit can be closed or rescheduled.
  `cancelled`, `completed` and `no_show` are terminal and MUST NOT return to `booked` from the
  agenda. This is AG-UI-3's rule extended consistently, and it is why no reopen action exists.

## Scope

**In:**

- `app/services/scheduling.py` — `_validate_slot(...)`, `close(...)`, `reschedule(...)`; `book`
  switched to the shared validator with no behaviour change.
- `app/panel/api/routes/appointments.py` — `POST /appointments/{id}/close` and
  `PATCH /appointments/{id}`, reusing the existing `invalid_lifecycle` 409 code for a
  non-`booked` row.
- Backend tests for the RED→GREEN of every new branch: close both outcomes, close a
  non-booked row, reschedule happy path, reschedule DST/availability/overlap, reschedule
  self-overlap exclusion, reschedule a non-booked row.
- `web/src/api.ts` — `closeAppointment(id, outcome)` and `rescheduleAppointment(id, body)`.
- `web/src/components/pages/AgendaPage.tsx` — `Completar` and `No asistió` quick actions for
  `booked` rows only, plus `Reprogramar` opening a slot dialog.
- `web/src/components/pages/AppointmentDetail.tsx` — the same three actions (U5 built the page
  as the appointment's home but shipped it read-only).
- Vitest tests and Storybook coverage for the new states, per AG-UI-4.
- `openspec/specs/agenda-calendar-ui/spec.md` — a new `AG-UI-7` requirement for outcome
  registration, and concrete scenarios under `AG-UI-3` for the reschedule that its prose
  already authorizes but its scenarios never pinned.

**Out — stated explicitly so the gate can see it:**

- **No customer notification on reschedule or close.** `automation.ALLOWED_EVENTS`
  (`app/services/automation.py:15`) has no `appointment.rescheduled` / `appointment.closed`
  member, and adding one opens the automation-rule and template surface. Reschedule is
  validated and audited, but a silently-not-notified customer is a real product gap and is
  recorded as a follow-up, not fixed here.
- No appointment `DELETE` or any hard delete (D3). No reopen action (D-U6-6).
- No change to the non-active filter, the register partition, or the column set — already
  correct.
- No customer field CRUD, no service/technician reassignment beyond the slot's technician.
- No `size:exception`-style scope creep into the 2026-09-25 report's other leftover items.

## Constraints

- Work is born in this worktree on `odd/agenda-register-actions`; never touch `main`.
- **Strict TDD is ON** (`openspec/config.yaml:38`). RED → GREEN → REFACTOR, no exceptions.
- Runners: backend `eval "$(infra/test-db.sh env)"` then `uv run pytest tests/`;
  web `cd web && npm test` (Vitest); the only type check is `cd web && npm run build`
  (`tsc -b && vite build`). No linter, no formatter.
- `addopts = "-q"` in `pyproject.toml`: use `-o addopts='' -q` to see the count.
- Operator-facing UI copy stays **Spanish**. Code, comments, docs, commits are **English**.
- Append-only history: `AppointmentHistory` gains a row per transition; `_history` already
  does it, and no transition may mutate or delete an existing history row.
- The `PATCH` body replaces the schedule; `status` is never accepted from the client.

## Contract (`openspec/specs/agenda-calendar-ui/spec.md`)

- **AG-UI-3** — authorizes cancellation for `booked` only, and states that editing and
  rescheduling are allowed and MUST apply only to `booked` appointments; `cancelled` is
  terminal. Its scenario list pins cancellation only, so WU1 adds the reschedule scenarios its
  prose already promises.
- **AG-UI-6** — the non-active register filter. Satisfied by `423eb812`; verified, not rebuilt.
- **AG-UI-7 (new, WU1)** — the outcome-registration requirement this unit introduces.
- **AG-UI-2 / AG-UI-4** — the shared state contract and Storybook coverage apply to the new
  actions' feedback states.

## Work units

### WU0 — Worktree, environment, baselines, and this record

- [x] Worktree `../lumat-agent-odd-agenda-register-actions`, branch `odd/agenda-register-actions`,
      base `28fd4ad3`. `.env` (`infra/.env`), `uv sync`, `cd web && npm ci`, dedicated test DB
      `lumat-test-lumat-agent-odd-agenda-register-actions` on port **5496**.
- [x] Baseline backend: `uv run pytest tests/ -o addopts='' -q` — **1493 passed**, 2 warnings,
      243.93s.
- [x] Baseline web: `cd web && npm test` — **792 passed** (91 files), 92.95s.
- [x] Graph check below.
- [x] Slice B baseline/worktree: branch `odd/agenda-register-actions-chain`, base `8e5a978a`, backend **1506 passed**, web **799 passed (91 files)**.

### WU1 — Contract amendment

- [x] RED evidence is recorded under WU2/WU3; contract scenarios themselves do not execute.
- [x] `openspec/specs/agenda-calendar-ui/spec.md`: add **AG-UI-7 — Visit Outcome Registration**
      with scenarios for `completed`, `no_show`, and the terminal rule.
- [x] Add to **AG-UI-3** the two reschedule scenarios (happy path re-runs validation; a
      non-`booked` row refuses) that its prose already authorizes.
- **Verify**: the spec file reads coherently; no code and no test asserts an unimplemented
  requirement beyond WU2/WU4.
- **Commit**: `79ed4cc2` — `docs(agenda): specify visit outcomes and rescheduling`.

### WU2 — Backend: close a booked visit

- [x] RED observed in `tests/integration/test_scheduling.py`: `AttributeError: module 'app.services.scheduling' has no attribute 'close'` (3 failures, 3 passed).
- [x] `scheduling.close(session, appointment, *, outcome, actor)` — guard `BOOKED`, set
      `AppointmentStatus.COMPLETED | NO_SHOW`, `flush`, `_history(action=...)`,
      `record_audit(action=f"appointment.{outcome.value}", after={"outcome": ..., "reason": ...})`. No `publish_event`.
- [x] `POST /appointments/{id}/close` with `{"outcome": "completed" | "no_show"}`; 404 unknown id,
      409 `invalid_lifecycle` on a non-`booked` row, 422 on an unknown outcome.
- **Verify**: `uv run pytest tests/functional/test_api_scheduling.py tests/integration/test_scheduling.py -o addopts='' -q`.
- **Commit**: `b999a666` — `feat(agenda): record booked visit outcomes`. Focused result: **20 passed in 3.77s**; full backend result: **1499 passed, 2 warnings in 270.81s**. Route tests were run after implementation; no separate route RED was observed.

### WU3 — Front: close actions in the register and the detail page

- [x] RED observed from `npx vitest run src/components/pages/AgendaPage.test.tsx src/components/pages/AppointmentDetail.test.tsx`: **4 failed | 36 passed**; exact initial failure `Unable to find an accessible element with the role "button" and name "Cerrar visita"`.
- [x] `api.ts` — `closeAppointment(id, outcome)`.
- [x] `AgendaPage.tsx` — `Completar` and `No asistió` for `booked` rows only, with confirmation
      and success/failure feedback reusing `ActionFeedback`.
- [x] `AppointmentDetail.tsx` — the same two outcome actions; rescheduling remains excluded for WU5.
- [x] Storybook close-confirmation and terminal states with non-vacuous fact assertions.
- **Verify**: focused Vitest + `cd web && npm test` + `cd web && npm run build`.
- **Commits**: `06362764` — `feat(agenda): close booked visits from agenda and detail`; `fd7a1739` — `test(agenda): cover visit outcome story states`. Focused result: **57 passed (4 files)**; full web result: **799 passed (91 files)**; `npm run build` succeeded (`tsc -b && vite build`).

### WU3b — Post-writer normalization and the RED the writer could not show

The writer returned `partial`: it ran the route tests after writing the endpoint, so no
route-level RED was observed. Rather than accept a fabricated RED or let the gap stand, the
missing evidence was produced by restoring the pre-implementation route file
(`git show 8aa539a3:app/panel/api/routes/appointments.py`) over the working copy and running
the two route tests:

- `uv run pytest tests/functional/test_api_scheduling.py -o addopts='' -q -k close` →
  **3 failed** (both parametrized happy paths and the refusal test), each with
  `assert 404 == 409` / `404 Not Found` — the route genuinely did not exist. The route file
  was restored immediately afterwards.

Two real defects found by reading the diff, and fixed:

1. **Duplicate success feedback.** `AgendaPage` rendered the outcome success both as a row
   badge and as a page-level `StateMessage`. Since the row leaves the `Activas` view on
   refresh, the row badge was the invisible one; it was removed, keeping the page-level
   message that mirrors `createFeedback`.
2. **A failure the operator could never read.** `AppointmentDetail` kept its dialog open on
   failure but rendered the error at the page top, behind the modal. The error now renders
   inside the dialog, exactly as `AgendaPage`'s cancel and close dialogs already did.

Also in this pass:

- The `reason` parameter reached the audit log but **not** the appointment's own history,
  diverging from `cancel`. It now lands in `_history(details={"reason": ...})` and is pinned
  by an assertion, so the parameter has an observable effect instead of being half-wired.
- The service-level `invalid outcome` guard (unreachable from the API, which rejects through
  `Literal` first) was pinned by a new test; RED was observed by temporarily removing the
  guard — `Failed: DID NOT RAISE ValueError` — and the guard was restored.

- **Commit**: `cb336531` — `fix(agenda): keep the visit outcome feedback visible and traceable`.
- **Verify after normalization**: focused backend **21 passed**; full backend **1500 passed,
  2 warnings in 248.62s** (baseline 1493 + 7); focused web **57 passed (4 files)**; full web
  **799 passed (91 files)**; `npm run build` succeeded; `git diff --check` clean.

### WU4 — Backend: reschedule a booked visit

- [x] RED observed: service self-overlap test failed with `AttributeError: module 'app.services.scheduling' has no attribute 'reschedule'`; route test failed with `assert 405 == 200` (`405 Method Not Allowed`).
- [x] `_validate_slot(...)` extracted from `book`, with `exclude_appointment_id`; `book`
      switched to it with identical behaviour (its existing tests are the regression net).
- [x] `scheduling.reschedule(session, appointment, *, local_date, local_time, timezone_name,
      duration_minutes, technician_id, actor)` — guard `BOOKED`, validate the new slot, update
      `local_start`/`timezone`/`starts_at`/`ends_at`/`duration_minutes`/`technician_id`, `flush`,
      `_history(action="rescheduled", details={"from": ..., "to": ...})`, `record_audit`.
- [x] `PATCH /appointments/{id}` — specific exception mapping before bare `ValueError`
      (`invalid_local_time`, `technician_unavailable`, `appointment_conflict`, `invalid_timezone`)
      plus `invalid_lifecycle`.
- **Verify**: focused backend **23 passed in 3.69s**; full backend **1508 passed, 2 warnings in 223.49s**.
- **Commit**: `a2973185` — `feat(agenda): reschedule booked appointments`.
- **RED coverage note**: RED was observed for missing service/route behavior and fixed. Separate RED runs were not captured for every specific error mapping (DST, availability, conflict, lifecycle, unknown ID, and 422); do not treat those cases as independently evidenced RED.

### WU5 — Front: reschedule dialog

- [x] RED observed: AgendaPage failed with `Unable to find an accessible element with the role "button" and name "Reprogramar"`.
- [x] `api.ts` — `rescheduleAppointment(id, body)` using `patchJson` backed by `apiFetch`.
- [x] The `Reprogramar` dialog on `AgendaPage.tsx` (date, time, duration, technician) posting the
      complete new slot, wired to `AppointmentDetail.tsx`.
- [x] Storybook reschedule-dialog stories and fact-preserving story tests for both surfaces (AG-UI-4).
- **Verify**: focused Vitest **62 passed (4 files)**; full web **804 passed (91 files)**; `npm run build` succeeded (`tsc -b && vite build`); `git diff --check` clean.
- **Commits**: `e1e8475a` — `feat(agenda): add reschedule action to register`; `47590059` — `feat(agenda): reschedule visits from detail`; `166f4226` — `test(agenda): cover rescheduling story states`.
- **RED coverage note**: RED was observed for the missing Agenda action; detail's missing action was not independently run RED before implementation. The first full-web run had a transient unrelated `ConversationsList` empty-state failure; its isolated test and the second full suite passed.

### WU4b — Post-writer normalization and the coverage the writer left out

Slice B started from `main` at `8e5a978a` (Slice A merged as PR #380), on
`odd/agenda-register-actions-chain`. Baseline re-measured on that base: backend
**1506 passed**, web **799 passed** (91 files).

The writer returned `success`, but reading the diff found two defects and a coverage hole.

**Defect 1 — the register published its success through the close feedback state.**
`AgendaPage` called `setCloseFeedback({ id, tone: "success", title: "Visita reprogramada" })`,
so the message rendered correctly only because the close notice happens to render
`closeFeedback.title` at page level. `rescheduleFeedback` had no `tone`, so it could never
render its own success, and any later change to the close feedback would have silently
broken the reschedule notice. It now owns a toned notice, rendered at page level for success
and inside the dialog for failure.

**Defect 2 — the dialog submitted without validating, and mislabelled the failure.**
`Number(rescheduleForm.technician_id)` on an empty select is `0`, so an unset technician
reached the API as `technician_id: 0`. That is a valid integer, so nothing rejected it until
the FK constraint fired, and the service's `IntegrityError` translation reported it as
`appointment_conflict` — "an overlapping booking" for a missing field. Both surfaces now guard
the slot and answer with `Completa todos los campos de la reprogramación` before any request.

Also normalized:

- `AppointmentDetail` did not use `composeAgendaTime`, so the two surfaces of the same action
  validated the local time differently: the register rejected DST gaps and folds client-side
  and sent `HH:MM:SS`, the detail page sent `HH:MM` and learned about a gap only from the
  backend. Both now go through the shared helper the create flow already uses.
- `AppointmentDetail`'s test named "offers rescheduling only for booked appointments" asserted
  only the booked case; it now also asserts the action is absent on a terminal visit.
- The new `RescheduleDialog` story's `play` function was exercised by **no test** — the story
  test rendered `ConversationSummary.args` instead. It now runs the real play and asserts the
  dialog opens on the story's own slot while the appointment facts survive.
- Two duplicate `within` imports from `@testing-library/react` were merged.

**Coverage hole — nine required behaviours, two tests.** The writer added one service test
(the self-overlap pin) and one route happy path. Every error branch I named was untested,
including the whole exception-mapping block, which is the part of the diff most likely to be
wrong. Added:

- service: a slot taken by another booked appointment, a terminal appointment, both DST
  rejections (`2026-09-06 00:30` nonexistent, `2026-04-04 23:30` ambiguous), and an
  unavailable technician window;
- route: terminal (`409 invalid_lifecycle`), unknown id (`404`), both DST rejections
  (`400 invalid_local_time`), unknown timezone (`400 invalid_timezone`), `duration_minutes: 0`
  (`422`), a conflicting slot (`409 appointment_conflict`), and an unavailable window
  (`409 technician_unavailable`).

**RED evidence, produced honestly.** The writer could not show RED for the cases it did not
individually run, so the gap was closed at two levels instead of being papered over:

1. *Behaviour absent.* Restoring the pre-slice `scheduling.py` and `routes/appointments.py`
   over the working copy and re-running the reschedule tests gives
   `AttributeError: module 'app.services.scheduling' has no attribute 'reschedule'` and a route
   failure — the tests are not vacuous against the feature's absence.
2. *Mapping non-vacuous (mutation).* Deleting the reschedule route's four specific handlers so
   only the bare `except ValueError` remains makes exactly two of the new tests fail —
   `test_reschedule_maps_slot_errors_to_actionable_codes` and
   `test_reschedule_reports_conflict_and_unavailable_slots` — with
   `assert 'invalid_lifecycle' == 'appointment_conflict'`. The happy path and the
   lifecycle/404 tests still passed, as they should. That is the evidence the writer's two
   tests could not provide.
3. The missing-technician defect was observed RED first, through the real UI path:
   `AssertionError: expected "spy" to not be called at all, but actually been called 1 times`.

**Verify after normalization**: focused backend **31 passed** (both files); full backend
**1516 passed, 2 warnings in 231.86s** (baseline 1506 + 10); focused web **63 passed**
(4 files); full web **805 passed** (91 files); `npm run build` succeeded; `git diff --check`
clean.

**Commits**: `be8a0045` — `fix(agenda): validate the reschedule slot and keep its feedback
honest`; `eaf3003e` — `test(agenda): cover the reschedule error mapping and the dialog story`.

### WU6 — Full verification and closure

- [ ] Backend suite + web suite + `npm run build` on the frozen tree.
- [ ] Spec check scenario by scenario; acceptance criteria below.
- [ ] `ponytail:` ledger harvested; doc updated after each task.

## Delivery

Forecast **~800–950 authored lines** (additions + deletions) across backend service/routes, web
api/pages, tests, stories and the contract — roughly double the ~400-line review budget.

**Owner decision, this session: `delivery_strategy: chained`, `chain_strategy: stacked-to-main`.**
Two PRs, each merged to `main` in order, each with its own native review inside the ~400-line
budget. The split boundary is Slice A and Slice B:

- **Slice A — PR #1** = WU1 + WU2 + WU3 + WU3b: the contract amendment, the backend close
  transition, and the register/detail close actions. Range `28fd4ad3..cb336531`.
- **Slice B — PR #2** = WU4 + WU5 + WU6: `_validate_slot`, `reschedule`, `PATCH /appointments/{id}`,
  and the reschedule dialog. Branched from `main` after Slice A merges.

Slice A's actual size is measured in its own review receipt below; the ~800–950 forecast stays
as the whole-unit estimate that justified chaining.

## Non-goals carried out of the slice

- **Reschedule does not notify the customer.** `automation.ALLOWED_EVENTS`
  (`app/services/automation.py:15`) has no reschedule member. Deferred; a follow-up decides whether
  a new event type and template are warranted.
- **A `no_show` reason is not captured in the UI.** The service accepts an optional `reason` for
  parity with `cancel`, but no surface sends one and no product decision asked for it.

## Acceptance criteria

- An operator can mark a `booked` visit `completed` or `no_show` from the register and from the
  appointment page; the row moves to the `No activas` view with the right label and tone.
- Neither outcome can be applied to a non-`booked` visit, and no outcome can be undone.
- An operator can reschedule a `booked` visit from the register and the appointment page; the
  new slot passes timezone/DST, availability and overlap validation, and a reschedule that does
  not move the visit does not conflict with itself.
- Both actions are audited (`AppointmentHistory` + `record_audit`); no row is deleted and no
  history row is mutated.
- `changed` behaviour is proven by tests that were RED first; the pre-existing suites stay green.
- Vitest green, `tsc -b` build green, backend suite green.

## Graph check

- `graphify-out/GRAPH_REPORT.md` — **8077 nodes / 16539 edges / 760 communities**, built from
  `28fd4ad3` (matches the branch base; no staleness).
- `graphify query "appointment lifecycle status transitions completed no_show cancel"`
  (253 nodes, BFS depth 2) — confirmed the `cancel` → `_history` → `record_audit` →
  `Appointment` cluster and that no existing node produces `Completed`/`NoShow` transitions.
- `graphify path AgendaPage.tsx api.ts` → **1 hop**
  (`AgendaPage.tsx --imports_from--> api.ts`), the single wiring point for the new client calls.
- `graphify path scheduling.py appointments.py --undirected` — ambiguous/no directed path;
  the coupling is via `from app.services import scheduling` plus `scheduling.Appointment`,
  confirmed by reading both files.
- Nodes consulted: `book()` (`app/services/scheduling.py:75`), `cancel()` (`:104`),
  `_history()` (`:71`), `availability()` (`:117`), `local_interval()` (`:52`),
  `cancel_appointment()` (`app/panel/api/routes/appointments.py:92`), `record_audit()`
  (`app/services/audit.py:18`), `publish_event()` (`app/services/events.py:11`),
  `Appointment` (`app/models.py:596`), `AppointmentHistory` (`:632`), `AgendaPage.tsx`,
  `api.ts`, `toneMaps.ts`.

## Progress

- [x] WU0 — worktree, environment, baselines, and this record
- [x] WU1 — Contract amendment
- [x] WU2 — Backend: close a booked visit
- [x] WU3 — Front: close actions
- [x] WU3b — Post-writer normalization (`cb336531`); Slice A ready for review
- [x] WU4 — Backend: reschedule (`a2973185`)
- [x] WU5 — Front: reschedule dialog (`e1e8475a`, `47590059`, `166f4226`)
- [x] WU4b — Post-writer normalization and the missing coverage (`be8a0045`, `eaf3003e`)
- [ ] WU6 — Full verification and closure

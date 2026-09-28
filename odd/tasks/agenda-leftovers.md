# ODD Task: agenda-leftovers

Status: in progress
Worktree: `../lumat-agent-odd-agenda-leftovers`
Branch: `odd/agenda-leftovers`
Base: `dff26b76` (main, 2026-09-28)
Source: U6 follow-ups in `odd/tasks/agenda-register-actions.md`; read-only recon of 2026-09-28

## Objective

Close the technical leftovers the Agenda family (U1-U6, closed 2026-09-26) deliberately left open,
so the thread is clean and verified: two unit-doc `Status:` lines, two missing test assertions, and
two backend correctness bugs.

## Scope

The owner authorized the technical set only, 2026-09-28 ("Técnico, sin producto").

In scope:

| ID | Leftover | Nature |
|----|----------|--------|
| L1 | Unit-doc `Status:` drift in `agenda-register-actions.md` and `agenda-appointment-detail.md` | doc-only |
| L3 | R3-001A: ambiguous `CloseConfirmation` story assertion | test-only |
| L5 | AG-UI-3: missing explicit "no Reprogramar on a non-booked row" assertion | test-only |
| L4 | R3-001B: over-general `IntegrityError` handling in `app/services/scheduling.py` | code + tests |
| L7 | `cancel()` / `reschedule()` do not keep `AppointmentCalendarSync` consistent | code + tests |

Out of scope, deferred to owner product decisions (NOT this unit):

- L6 — customer notification on reschedule. `automation.ALLOWED_EVENTS` has no reschedule event;
  the U6 record defers it until a product decision on a new event/template.
- L9 — `no_show` reason capture in the UI. The service accepts an optional reason; no surface sends
  one and no product decision requested it.
- L2 — parked branch `odd/agenda-operator-technicians` (owner decides: rescue or delete).
- L8 — web-suite flake. No evidence-backed stabilisation exists; it stays documented.

## Constraints

- Strict TDD is ACTIVE (`openspec/config.yaml`: `apply.tdd=true`, `test_command: uv run pytest tests/`).
  For code tasks (L4, L7) observe RED before GREEN.
- Backend tests need this worktree's own test DB: `infra/test-db.sh up`, then
  `eval "$(infra/test-db.sh env)"` before running pytest. The worktree derives its own compose
  project and port; the main repo's test DB does not serve it.
- Web suite: `cd web && npm test`. The frontend type check lives ONLY in `cd web && npm run build`
  (`tsc -b`); a green Vitest suite does not prove the tree type-checks.
- One concern per commit; tests and docs travel with their code. No `Co-Authored-By`.
- Technical artifacts in English.
- Delivery (push, PR, merge) is the owner's explicit decision.

## Baseline (worktree @ dff26b76, before any change)

- Backend: **1534 passed** (`uv run pytest tests/ -o addopts='' -q`).
- Web: **822 passed**, 90 files (`npm test`).
- Build: **green** (`npm run build`).

## Acceptance criteria

- [ ] Each in-scope leftover closed with cited evidence.
- [ ] Backend suite green against baseline (>= 1534 passed, no new failures).
- [ ] Web suite green against baseline (>= 822 passed, no new failures).
- [ ] `npm run build` green.

## Tasks

- [ ] **L1** — unit-doc status lines (doc-only, inline).
      Replace `Status: in progress` in:
      - `odd/tasks/agenda-appointment-detail.md` → `Status: merged — PR #376 (`7fb8cd10`).`
      - `odd/tasks/agenda-register-actions.md` → two slices + closure:
        `Status: merged — PR #380 (`8e5a978a`) + PR #383 (`f5a6d68d`); unit record closed in PR #385 (`9eb48d8b`).`

- [ ] **L3** — R3-001A unambiguous story assertion (test-only).
      `web/src/stories/pages/AgendaPage.stories.test.tsx:95-110` renders the story a second time into
      `storyContainer`, runs `CloseConfirmation.play` against it, then asserts against the FIRST
      `container`. The assertion must target the second render's expected state, not the first
      container or a global query.

- [ ] **L5** — AG-UI-3 explicit register assertion (test-only).
      `web/src/components/pages/AgendaPage.test.tsx` (terminal-row tests near lines 216-221 and
      282-287 assert no close/cancel action, but not that `Reprogramar` is absent). Add an explicit
      assertion for a non-`booked` row: the `Reprogramar` action is absent and `rescheduleAppointment`
      is not called.

- [ ] **L4** — narrow the `IntegrityError` translation (code + tests, TDD).
      `app/services/scheduling.py:150-154` (`reschedule`) and `:100-104` (`book`) translate EVERY
      `IntegrityError` into `AppointmentConflict`, so an unrelated integrity failure (e.g. a
      nonexistent `technician_id` violating the FK) is misreported as a booking conflict. Translate
      only the known overlap/exclusion constraint violation; let unrelated integrity failures surface
      as their actual error. RED first: a test that triggers a non-overlap integrity failure and
      expects it NOT to be reported as `appointment_conflict`.

- [ ] **L7** — calendar-sync consistency on cancel/reschedule (code + tests, TDD).
      `book()`, `cancel()` and `reschedule()` in `app/services/scheduling.py` never update
      `AppointmentCalendarSync` (`app/models.py`), so a moved/cancelled appointment can leave exported
      ICS at the previous state. Keep the persisted appointment and its calendar representation
      consistent for both transitions, using the existing calendar sync/export path. RED first.

## Route declaration

- L1: **inline** — two mechanical doc lines, no research.
- L3, L5: **delegated writer** — 2 non-trivial test files (writer trigger).
- L4, L7: **delegated writer** — backend code plus tests (writer trigger).

One writer thread at a time; web tests and backend fixes are delegated sequentially.

## Progress / evidence

(append per task as each closes)

## Next step

Delegated writer for L3 + L5 (web test gaps), then L4 + L7 (backend bugs), then full verification.

# agenda-booking-slice2

## Objective

Let an operator define a **per-technician weekly availability schedule** in the panel, and
translate it into bookable appointment slots so the customer WhatsApp chatbot can offer and
confirm visits autonomously.

This closes the gap that makes `chatbot-intake-redesign` fall back to a human at the end of
every booking attempt: `open_slots_for_assignment()` finds zero slots because
`technician_availability` can never be populated from the product (there is no route and no
editor — only a read endpoint).

## Problem (verified from code)

| # | Finding | Evidence |
|---|---------|----------|
| 1 | Booking needs `TechnicianAvailability` rows to build slots. | `app/services/scheduling.py:227-271` (`open_slots_for_assignment`) |
| 2 | The table can only be written by `add_availability()`, whose only callers are **tests**. | `scheduling.py:392`; callers in `tests/functional/conftest.py:209,245`, `tests/integration/test_chat_booking.py:80`, `test_chat_manage.py:116`, `test_scheduling.py` |
| 3 | The panel exposes a **read-only** availability route; there is no POST/PUT and no editor. | `app/panel/api/routes/appointments.py:62-68`; `web/src/api.ts` has no availability client |
| 4 | The chatbot hands off when no slot is found. | `app/chat/nodes/booking.py:58-62` (`booking_unavailable`) → `app/chat/nodes/handoff.py:38-40` |
| 5 | The owner's configured "horarios" are **business hours**, a different concept. | `app/services/settings.py:166-167,255-310` (`hours.schedule`), consumed by `closure_gate.py` and as timezone only |
| 6 | Slice 2 was scoped and never started. | `odd/tasks/agenda-booking.md:25-28,265-266` |

## Why

The owner ran a real WhatsApp test: the customer gave name, email, comuna, address, failure,
availability and consent, and the bot still replied "Un asesor revisará tu caso…". Root cause
confirmed: no `TechnicianAvailability` rows exist and there is no product way to create them.
Option B (per-technician schedule editor) was chosen by the owner as the complete fix.

## Scope

**In:**
- A per-technician weekly schedule data model + migration.
- A service that persists the schedule and materializes rolling `TechnicianAvailability`
  blocks from it (Work Unit T2).
- Panel API routes to read and replace a technician's schedule (T3).
- Booking-path wiring so slots stay available over the rolling horizon (T4).
- A per-technician schedule editor in the panel (T5).
- Backend + frontend coverage (T6).

**Out (deliberate):**
- One-off overrides / exceptions (vacations, ad-hoc blocks). The existing `TechnicianAvailability.available=false`
  semantics stay unused by this slice; recorded as debt, not built.
- Changing the scheduling engine (`scheduling.py` slot/validation logic) — the materializer
  feeds the engine through the existing block model, so the engine is untouched.
- Business-hours enforcement inside `book()` and any holiday model (still documented debt in
  `agenda-booking.md:83-85`).
- Free-slot search beyond the existing 7-day horizon (unchanged).
- The `chatbot-intake-redesign` copy/flow redesign (separate units; H2/H3 also separate).

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-agenda-booking-slice2`
- Branch: `odd/agenda-booking-slice2`
- Base: `591f46eb` (`origin/main` at start)
- Files (expected):
  - `odd/tasks/agenda-booking-slice2.md` (this record)
  - `app/models.py` (new model)
  - `db/migrations/048_technician_weekly_schedule.sql` (new)
  - `app/services/technician_schedule.py` (new)
  - `app/panel/api/routes/appointments.py` (schedule routes)
  - `app/chat/nodes/booking.py` (ensure horizon before slot search)
  - `web/src/api.ts`, `web/src/types.ts`
  - `web/src/components/pages/AgendaPage.tsx` and its test
  - `web/src/components/shared/technicianSchedule.ts` (+ test, if a pure helper is extracted)
  - `tests/**` additions for the new behavior

Any file outside this list needs a scope update here first.

## Constraints

- **Strict TDD: ON** (`openspec/config.yaml`). Python runner: `uv run pytest tests/`; web runner:
  `cd web && npm test` (`vitest run`). Observe RED before the source change. Never invent RED evidence.
- Artifacts, code, comments, commits in **English**. Operator-facing UI copy in **Spanish (es-CL)**,
  consistent with `AgendaPage`/`Settings`.
- No linter / typechecker / formatter. `web` type-checks through `npm run build` (`tsc -b`).
- Test DB per worktree on host port **6303**; needs `infra/.env` and `uv sync` before `test-db.sh up`.
- **D1 — do not change the scheduling engine's behavior.** `open_slots_for_assignment`,
  `book()`, `_validate_interval` and `availability()` keep their semantics. The materializer writes
  `TechnicianAvailability` rows, which is the model the engine already reads.
- **D2 — idempotent materialization.** Generating blocks must never duplicate rows or wipe
  non-schedule data. Replacing a schedule deletes that technician's future materialized blocks and
  regenerates; the rolling ensure is insert-if-absent.
- **D3 — timezone.** Blocks are computed in the configured `hours.timezone` (`get_hours_timezone`),
  stored as UTC-aware, and use the existing `local_interval()` DST rules.

## Behavior spec (target)

1. An operator can set, per technician, a weekly pattern of `{weekday (1-7), opens_at HH:MM,
   closes_at HH:MM}` windows, one window per weekday (mirrors `hours.schedule` semantics and the
   `HoursEditor` rule "cada día pertenece a un solo horario").
2. Saving a schedule validates every entry (`1<=weekday<=7`, `opens_at < closes_at`) and returns a
   structured 400 on invalid input.
3. Saving a schedule materializes `TechnicianAvailability` True-blocks for a rolling horizon
   (default 14 local days) at the configured timezone.
4. The booking path (chatbot) ensures the horizon before searching slots, so slots stay available
   without any manual step.
5. Once a technician has a schedule, the chatbot's `open_slots_for_assignment` returns real slots and
   the booking flow offers and confirms a visit instead of handing off.

## Decisions

- **D4 — Materialize into `TechnicianAvailability`, not a new engine path.** The engine already reads
  those rows; this keeps `book()` validation and every existing scheduling test intact.
- **D5 — One window per weekday, normalized table.** A row per `(technician_id, weekday)`. Simpler than
  JSONB and integrity-checkable with a unique constraint.
- **D6 — Rolling horizon, idempotent ensure.** No background cron exists (the worker is
  DomainEvent-driven, `app/ops/worker.py`), so materialization is on-demand and idempotent rather than
  tick-based.
- **D7 — Editor home is the Agenda page.** Technicians are already listed there and scheduling is the
  agenda's domain; the dialog reuses the `HoursEditor` interaction pattern. (Owner may relocate later.)

## Work units (stable IDs)

### T1 — Schema + migration
- [ ] `TechnicianWeeklySchedule` model (`technician_id` FK `users.id`, `weekday` 1-7, `opens_at`
      `TIME`, `closes_at` `TIME`; unique `(technician_id, weekday)`).
- [ ] Migration `048_technician_weekly_schedule.sql` creating the table + constraint.
- [ ] Migration applies cleanly twice (`test_migrations.py` contract).

### T2 — Service (`app/services/technician_schedule.py`)
- [ ] `get_schedule(session, technician_id) -> list[dict]`.
- [ ] `set_schedule(session, technician_id, entries)` with validation; replaces rows and re-materializes.
- [ ] `materialize(session, technician_id, now, horizon_days=14)` — idempotent block generation.
- [ ] `ensure_horizon(session, now, horizon_days=14)` — rolling ensure for all scheduled technicians.
- [ ] RED→GREEN unit/integration tests.

### T3 — Panel API
- [ ] `GET /panel/api/technicians/{technician_id}/schedule` (operator).
- [ ] `PUT /panel/api/technicians/{technician_id}/schedule` (operator), structured 400 on invalid.
- [ ] Functional tests for both, including the invalid-input path.

### T4 — Booking wiring
- [ ] `app/chat/nodes/booking.py` ensures the horizon before `open_slots_for_assignment`.
- [ ] Functional test: a technician with a weekly schedule and **no** manually seeded blocks yields a
      slot offer (the end-to-end unblock).

### T5 — Frontend editor
- [ ] Web API client + types for the schedule routes.
- [ ] Per-technician weekly schedule editor (reuse `HoursEditor` pattern) reachable from `AgendaPage`.
- [ ] Vitest coverage for the editor behavior.

### T6 — Evidence
- [ ] Required checks run; results recorded below.

## Acceptance criteria

1. From the panel, an operator sets a technician's weekly schedule and it persists.
2. After saving, `open_slots_for_assignment()` returns slots for that technician without any manual
   seed — proven by a functional test.
3. The chatbot booking flow offers and confirms a visit instead of handing off when a schedule exists.
4. `book()` still validates against materialized blocks; all existing scheduling tests stay green.
5. Invalid schedule input returns a structured 400, never a 500.
6. Reproducible materialization: re-saving the same schedule does not duplicate blocks; changing it
   does not leave stale future blocks.
7. `uv run pytest tests/` green (known-flaky seed tests deselected as documented); `cd web && npm test`
   green; `cd web && npm run build` green.

## Checks

- `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/ -q` (exit code is the signal)
- `cd web && npx vitest run`
- `cd web && npm run build`
- `git diff --check`

## Graph Check (consulted)

`graphify query "technician availability weekly schedule editor panel routes settings"` on the main
worktree graph: `availability()` (`scheduling.py:386`), `open_slots_for_assignment` (`scheduling.py:227`),
`scheduling.py`, `appointments.py`, `HoursEditor()` (`Settings.tsx:96`), `Settings()`, `Users`,
`UserManagement.tsx`, `api.ts`, `postJson()`, `useAsyncData()`, `DayToggle`, `TechnicianAgenda.tsx`,
`is_open_at` (`settings.py:262`). `Users` (god node) and `scheduling.py` (community 36) are the
affected communities.

## TDD resolution

**Strict TDD is ACTIVE.** Follow RED → GREEN → REFACTOR. Python runner `uv run pytest tests/`; web
runner `cd web && npx vitest run`.

## Delivery strategy

- Forecast: **> ~400 authored changed lines** (model + migration + service + routes + booking wiring +
  editor UI + tests). `delivery_strategy`: `ask-on-risk`; `chain_strategy`: `stacked-to-main`.
  Planned slices: PR1 = backend (T1–T4), PR2 = frontend (T5). Confirm at the tasks gate.

## Progress log

- Worktree created from `origin/main` = `591f46eb`; branch `odd/agenda-booking-slice2`. Env: `uv sync`,
  `infra/.env` copied, test DB on port `6303`; sanity `tests/integration/test_scheduling.py` 18 passed
  (EXIT=0). Design settled (Option B). No source changes yet.

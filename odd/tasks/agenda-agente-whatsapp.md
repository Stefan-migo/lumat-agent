# ODD — agenda-agente-whatsapp

- Status: in progress
- Branch: `odd/agenda-agente-whatsapp`
- Base: `e98b6683` (origin/main)
- Worktree: `../lumat-agent-odd-agenda-agente-whatsapp`
- Engram mirror: `odd/agenda-agente-whatsapp/tasks`
- Created: 2026-09-28

## Objective

Make the WhatsApp agent book a visit autonomously and send the 24 h reminder, so the Hito 3
acceptance criterion (proposal line 109) is met:

> "Un cliente pide una hora por WhatsApp, el agente revisa disponibilidad, agenda la visita y
> envía recordatorio 24 h antes, todo automático."

## Problem / Why

The Agenda section covers the panel half of Hito 3, but the milestone cannot be signed off because
the agent cannot book. Verified state before this work:

- The WhatsApp graph (`app/chat/graph.py:214-270`) has no tool-execution node and does not import
  the assistant tool registry.
- `app/chat/assistant/tools/registry.py` belongs to the **internal panel assistant**, not to
  WhatsApp. Adding tools there has no effect on the acceptance criterion. See Engram
  `architecture/whatsapp-vs-panel-assistant`.
- `app/chat/nodes/capture.py:33` asks for availability as free text and `:37-40` closes by
  promising a human will coordinate the visit.
- There is no slot enumeration: `scheduling.availability()` is a boolean for one exact interval.
- There is no reminder trigger, no periodic sweep runner, and no WhatsApp reminder template.

## Scope

**In:** S1 slot enumeration, S2 booking step in the WhatsApp graph, S3 reschedule/cancel from
WhatsApp, S4 the 24 h reminder, S5 post-service follow-up.

**Out (deliberately):** technician panel + per-technician ICS (Workstream B); customer
self-booking web (M3, web on 3-month standby); payments/deposits (M3); automated no-show
consequences; configurable reminder lead time; two-way external calendar sync.

## Closed product decisions (owner, 2026-09-28)

1. **Autonomy**: the agent books autonomously, with explicit customer confirmation in the same
   conversation. No human operator approval for a booking.
2. **Reminder channel**: approved WhatsApp template, fallback to email.
3. **Reminder lead time**: fixed 24 h.
4. **Cancellation**: allowed, with customer confirmation. Reschedule is contracted (proposal line
   92) and therefore in scope.
5. **No-show**: no automated flow; the reminder is informative and an operator marks `no_show` in
   the panel.

## Accepted constraints (verified evidence)

- Booking must call the service layer, never panel routes.
- Slot offers must be deterministic; `respond.py` forbids the LLM from claiming availability.
- Ownership is enforced from trusted conversation state (customer/case), never model-supplied ids.
- `reschedule` publishes no event today; `close` audits but publishes nothing.
- Cancel does not reject a past/in-progress visit (only `status == BOOKED`).
- Reminders must be appointment-keyed and invalidated on cancel/reschedule; the sweep would
  otherwise deliver a reminder for a cancelled visit.
- "24 h before" is computed from the aware UTC `starts_at`, never from a naive local time (Chile
  DST).
- The notification queue delivers free-form WhatsApp text; business-initiated messages outside the
  24 h customer-service window need an approved Meta template.
- The generic notification sweep runs only at FastAPI startup; a periodic runner is required.

## Effective TDD

- Mode: **strict TDD ON** (`openspec/config.yaml`: `apply.tdd=true`)
- Source: `openspec/config.yaml`
- Runner: `uv run pytest tests/`
- Required: observed RED before implementation, then GREEN, then REFACTOR.

## Verification commands

```bash
bash infra/test-db.sh up                     # compose: lumat-test-lumat-agent-odd-agenda-agente-whatsapp, port 5945
eval "$(bash infra/test-db.sh env)"
uv run pytest tests/ -o addopts='' -q        # backend suite (of record)
cd web && npm test                           # frontend suite
cd web && npm run build                      # the only frontend type check (tsc -b)
```

## Delivery

- Strategy: `ask-on-risk`.
- Chain strategy: `stacked-to-main`, chosen by the owner on 2026-09-28. One small PR per slice,
  merged to main in order; main stays working because S1 is inert on its own and S2-S5 are additive.
- Forecast: > 400 authored changed lines across the five slices.
- Slice boundaries (one PR per slice, cumulative): PR1 = S1, PR2 = S2, PR3 = S3, PR4 = S4,
  PR5 = S5.
- RDD is ON (global): after each work-unit commit run
  `gentle-ai review assess --cwd <worktree> --agent opencode --base-ref <boundary> --committed-only --json`
  and follow the returned transitions exactly. First boundary is `e98b6683`.
- Commits: Conventional Commits, one concern per commit, tests and docs with the behavior, no
  `Co-Authored-By`.
- Push, PR and merge are the owner's explicit decision.

## Tasks

### S1 — Slot enumeration service

- [x] Add a bounded open-slot search to `app/services/scheduling.py` that returns concrete bookable
      slots for a technician (or the availability rules) over a bounded window, respecting:
      `available=True` blocks, existing booked appointments, service duration, and the existing
      policy that a technician with no availability blocks is unrestricted.
- [x] Reuse `local_interval()` and the DST validation; return local date/time, not raw
      UTC guesses.
- [x] Acceptance: given a technician with a known availability window and one booked visit, the
      search returns only free slots that can actually be booked, and a slot returned by the search
      is accepted by `book()` at commit time.
- [x] Route: delegated writer (new service surface + tests, 2+ files).
- [x] Checks: unit, integration, and full backend scheduling verification passed.

### S2 — Booking step in the WhatsApp graph

- [ ] Add the booking step to the WhatsApp conversation: consume the captured availability, offer
      concrete slots from S1, take the customer's explicit confirmation, then call
      `scheduling.book` with the customer/case from trusted conversation state.
- [ ] Replace the human-handoff copy (`capture.py:37-40`) on the booking path with a confirmation
      that names the booked slot; keep a safe fallback when no slot fits.
- [ ] Acceptance: a scripted conversation where the customer asks for a time and confirms gets a
      real `Appointment` row in `booked` status with history and audit; a customer who does not
      confirm books nothing; no booking is possible for a customer/case the conversation does not
      own.
- [ ] Route: delegated writer (new node + graph wiring + state + tests).
- [ ] Checks: focused assistant/chat tests plus the full backend suite.

### S3 — Reschedule and cancel from WhatsApp

- [ ] Expose reschedule and cancel through the same confirmation discipline, enforcing ownership
      and an explicit policy for already-started or past visits.
- [ ] Publish the missing `appointment.rescheduled` event (and keep the reminder queue consistent).
- [ ] Acceptance: a customer can move their own visit to a free slot and cancel it; a cancelled or
      rescheduled visit updates the pending reminder; reprogramming notifies the team.
- [ ] Route: delegated writer.

### S4 — 24 h reminder

- [ ] Enqueue an appointment-keyed reminder on booking (`appointment:{id}:reminder:24h`, due
      `starts_at - 24 h` in UTC), with an explicit policy for bookings made inside the 24 h window.
- [ ] Invalidate or reschedule the pending reminder on cancel and reschedule.
- [ ] Deliver via an approved WhatsApp template (template-aware dispatcher), with an email fallback
      recipient, replacing free-form text for this business-initiated message.
- [ ] Add a periodic runner: a CLI entrypoint on `app/ops/sweep.py` plus the cron wiring already
      used for ops jobs on the VPS.
- [ ] Acceptance: booking creates exactly one reminder due at the right UTC instant; a cancelled
      visit produces no reminder; the sweep delivers a due reminder through the template and falls
      back to email when WhatsApp fails; the sweep runs on a schedule, not only at process start.
- [ ] Route: delegated writer.

### S5 — Post-service follow-up

- [ ] Publish an `appointment.completed` (and `no_show`) domain event on `scheduling.close`,
      allow the event through `ALLOWED_EVENTS`, and schedule the post-service follow-up template.
- [ ] Acceptance: closing a visit as completed produces a follow-up scheduled once, idempotently.
- [ ] Route: delegated writer.

## Progress log

- 2026-09-28: worktree created on `e98b6683`; `uv sync`, `npm ci`, test DB up on port 5945; unit
  smoke `tests/unit/test_scheduling_unit.py` = 4 passed. Graph present but stale (`16ba9cbf`);
  refresh at session close.
- 2026-09-28: S1 implemented in `e6632c7f` (`feat(scheduling): add bounded open-slot search`).
  Strict TDD RED observed: test collection failed because `_candidate_starts` was not yet defined.
  GREEN: scheduling unit tests = 10 passed; scheduling integration tests = 15 passed; full backend
  suite = 1548 passed, 2 warnings. Graph checked nodes `local_interval()`, `_validate_slot()`,
  `availability()`, `book()`, `Appointment`, `TechnicianAvailability`, and `_linked_rows()`; the
  relevant extracted relationships connect `_validate_slot()` to `local_interval()` and
  `availability()`, and connect `book()` to `_validate_slot()`. Graph is stale from `16ba9cbf`.

# ODD — agenda-agente-whatsapp

- Status: in progress
- Branch: `odd/agenda-agente-whatsapp`
- Base: `f27077ec` (origin/main, after PR #403 merged S1+S2); S3 re-created the worktree from here
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
6. **Technician assignment** (2026-09-28): among the `tecnico` users whose availability block covers
   the slot, the lowest id. Deterministic, no new configuration. Prerequisite: the owner loads the
   work schedule in `technician_availability` (the proposal already requires this, line 107).
7. **Offer window and defaults** (orchestrator decision, vetoable): search the next 7 days, bounded
   by the technicians' availability rows; no new window configuration. `service` is the fixed label
   `Visita técnica` and `duration_minutes` is 60 (both adjustable later). If no slot exists, the
   agent hands off to a human instead of inventing one.
8. **Confirmation UX** (orchestrator decision, vetoable): the agent offers up to 3 numbered concrete
   slots; the customer confirms by number or by wording that normalizes unambiguously to exactly one
   offered slot (deterministic digit match first, then a constrained normalization that may abstain).
   Ambiguity re-asks once, then hands off. The exact slot is re-validated at commit; a conflict
   re-offers instead of failing the conversation. The LLM never states availability it did not
   receive from the scheduling service.
9. **S3 — already-started or past visits** (owner, 2026-09-28): the WhatsApp flow never cancels or
   reschedules a visit whose window already started (`starts_at <= now`, aware UTC); it explains and
   mutates nothing. The guard lives in the chat node, deliberately NOT in `scheduling.cancel()`, so the
   panel/operator keeps the authority to act on an in-progress visit.
10. **S3 — no cancellation cutoff** (owner, 2026-09-28): any moment before the start is valid; no new
    configuration is introduced.
11. **S3 — no cancellation reason** (owner, 2026-09-28): the agent cancels right after the customer's
    explicit confirmation, with `reason=None`.
12. **S3 — reschedule notifies the team through the domain event** (owner, 2026-09-28): `reschedule()`
    publishes `appointment.rescheduled` like `book`/`cancel`, and the event is allowed in
    `ALLOWED_EVENTS`. No default rule or template is seeded; the team configures a rule if it wants one.
13. **S3 — technician on reschedule** (owner, 2026-09-28): re-resolved with the same rule as booking
    (`open_slots_for_assignment`, lowest free id); the technician may change.
14. **S3 — several upcoming visits** (owner, 2026-09-28): the agent lists the customer's upcoming
    `booked` visits numbered and the customer chooses; deterministic resolution, same discipline as the
    slot offer. Ownership is the conversation's `customer_id`, so a visit booked in another
    conversation of the same phone is still manageable.
15. **S4 — bookings inside the 24 h window** (owner, 2026-09-28): if less than 24 h remain at booking
    time, **no reminder operation is created at all**. The customer is booking in that same
    conversation, so an immediate reminder adds nothing and pollutes the thread. No shortened-lead
    variant and no second lead-time configuration are introduced.
16. **S4 — reminder template identity** (owner, 2026-09-28): the Meta template does not exist yet, so
    the name is **configurable** through the settings KV (`notify.reminder_template_name`, default
    `appointment_reminder_24h`) and the content/policy gate is a published
    `NotificationTemplateVersion` row (`approved` required for a business-initiated WhatsApp send, see
    `app/services/templates.py:38-42`). Body parameters: the visit's **local date and time**, in that
    order, and nothing else — no customer name. When the template is approved in Meta, the operator
    changes the key from the panel; no code change.
17. **S4 — email fallback recipient** (owner, 2026-09-28): the fallback goes to the **customer's own
    email** (`Customer.email`, `app/models.py:232`), because the reminder is for the customer. If the
    ficha has no email, the operation ends `permanently_failed` with audit — no recipient is invented
    and the team's `notify.owner_email` is NOT used (that is the emergency pattern, a different
    purpose).

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

- [x] Add an assignment-aware slot search that reuses S1's `open_slots`, iterating `tecnico` users and
      returning `(technician_id, local_date, local_time)` for the lowest-id technician free at each
      slot. If no technician has availability rows at all, return no slots (do not treat everyone as
      unrestricted across multiple technicians).
- [x] Add a `booking` node to the WhatsApp graph, reachable after capture completes and re-entered
      while a pending offer exists:
  - no pending offer: compute up to 3 slots over the next 7 days; if none, hand off to a human;
    otherwise persist a frozen pending offer (technician id + the exact slots + created_at) on the
    conversation and reply with the numbered offer;
  - pending offer: resolve the customer's reply to exactly one offered slot (deterministic digit
    match first, then a constrained normalization allowed to abstain); ambiguous → re-ask once, then
    hand off; expired offer → re-offer or hand off.
- [x] Book with `scheduling.book` using the customer and case from trusted conversation state and
      `actor="assistant"`. On `Unavailable` or `AppointmentConflict`, re-offer instead of failing.
- [x] Replace the human-handoff copy (`capture.py:37-40`) on the booking path with a confirmation
      that names the booked slot; keep `summary` after a successful booking.
- [x] Acceptance: (a) a scripted conversation where the customer asks for a time and confirms
      produces a real `Appointment` in `booked` status with history and audit; (b) no confirmation
      books nothing; (c) no booking is possible for a customer/case the conversation does not own;
      (d) a slot taken between the offer and the confirmation re-offers rather than crashing;
      (e) with no technician availability configured, the agent hands off and books nothing.
- [x] Route: delegated writer (new node + graph wiring + state + tests).
- [x] Checks: focused chat/integration tests plus the full backend suite.

### S3 — Reschedule and cancel from WhatsApp

- [x] Expose reschedule and cancel through the same confirmation discipline, enforcing ownership
      and an explicit policy for already-started or past visits.
- [x] Publish the missing `appointment.rescheduled` event (and keep the reminder queue consistent).
- [x] Acceptance: a customer can move their own visit to a free slot and cancel it; reprogramming
      notifies the team (`appointment.rescheduled` is published and allowed in `ALLOWED_EVENTS`).
- [ ] Acceptance (deferred to S4): a cancelled or rescheduled visit updates the pending reminder.
      NOT testable in S3 — the reminder queue is only populated in S4. S3 publishes the event and keeps
      `appointment.id` stable so S4 can invalidate/re-key. No test was fabricated for this clause.
- [x] Route: delegated writer.

### S4 — 24 h reminder

- [x] Enqueue an appointment-keyed reminder on booking (`appointment:{id}:reminder:24h`, due
      `starts_at - 24 h` in UTC), with an explicit policy for bookings made inside the 24 h window
      (closed: skip the operation entirely, decision 15).
- [x] Invalidate or reschedule the pending reminder on cancel and reschedule.
- [x] Deliver via an approved WhatsApp template (template-aware dispatcher), with an email fallback
      recipient (closed: the customer's email, decision 17), replacing free-form text for this
      business-initiated message.
- [x] Add a periodic runner: a CLI entrypoint on `app/ops/sweep.py` plus the cron wiring already
      used for ops jobs on the VPS.
- [ ] Acceptance: booking creates exactly one reminder due at the right UTC instant; a cancelled
      visit produces no reminder; the sweep delivers a due reminder through the template and falls
      back to email when WhatsApp fails; the sweep runs on a schedule, not only at process start.
- [ ] Route: delegated writer. **Reuse the existing queue, do not invent one**: `NotificationOperation`
      (`app/models.py:794`) already has `next_attempt_at`, bounded retries with backoff and a
      `FOR UPDATE SKIP LOCKED` + advisory-lock sweep (`app/services/notifications.py:204-214`), and it
      already runs at startup (`app/main.py:74-83`) and on the webhook sweep path
      (`app/services/send.py:193`). The missing piece is a real periodic runner: `app/ops/sweep.py`
      today only exposes `run(limit=50)` with no `__main__`, and the ops contract for cron is the
      `cd /opt/lumat && .venv/bin/python -m app.ops.<script>` shape (`docs/ops.md` §2.8, the
      daily-summary entry).

#### S4 apply progress

- WU1: pending reminder enqueue on booking, UTC due instant, cancellation invalidation, and reschedule due-time update implemented in `app/services/scheduling.py` with integration coverage in `tests/integration/test_notifications.py`.
- RED observed: `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/integration/test_notifications.py -o addopts='' -q` → **2 failed, 3 passed**; both new assertions failed because booking/cancel had no appointment-keyed reminder operation.
- GREEN focused: same command after implementation → **5 passed**.
- Full suite: `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/ -o addopts='' -q` → **1576 passed, 2 warnings** (163.52 s).
- Graph Check: `graphify-out/GRAPH_REPORT.md` snapshot is stale at `16ba9cbf` (not refreshed per instruction). Queried `scheduling.py`, `notifications.py`, `notify.py`, `templates.py`, `sweep.py`, and `main.py`. Relevant nodes: `book()`, `cancel()`, `reschedule()`, `Appointment`, `Customer`, `NotificationOperation`, `create_operation()`, `sweep_due_operations()`, `process_operation()`, `send_template()`, `send_email()`, `validate_channel_policy()`, `NotificationTemplateVersion`, `run()`, `main.py`, `sweep.py`. Resolved graph paths: `validate_channel_policy() → TemplatePolicyError → NotificationTemplateVersion`; `main.py → sweep.py → sweep_due_operations()`. Requested paths from scheduling `book()` to `NotificationOperation`, notification operation to sweep, notify template to email, and sweep module to sweep function did not resolve in stale graph.
- Commit `ca34eb69` `feat(scheduling): enqueue and maintain the 24 h reminder` — tests, scheduling hooks, and this progress record. Rollback boundary: scheduling reminder maintenance and its tests only.
- WU2: added `notify.reminder_template_name` default, approved-template policy enforcement, local date/time body parameters, WhatsApp template dispatch, and fallback only to `Customer.email`; missing email is permanently failed and audited. Emergency template behavior remains defaulted to `emergency_alert`.
- RED observed: focused command before implementation → **3 failed, 4 passed** (two new reminder assertions failed; the existing generic operation was also incorrectly routed and was corrected before GREEN).
- GREEN focused: `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/integration/test_notifications.py tests/integration/test_h4_notifications.py -o addopts='' -q` → **14 passed**.
- Full suite: `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/ -o addopts='' -q` → **1578 passed, 2 warnings** (212.49 s).
- WU2 commit `8f538902` `feat(notify): deliver the reminder through the WhatsApp template with an email fallback` — dispatcher, settings default, template sender, tests, and this record. Rollback boundary: reminder dispatch/settings/template behavior and its tests only.
- WU3: added an argparse CLI (`--limit`, default 50) to `app.ops.sweep` and documented the five-minute cron command; no server was contacted and the cron was not installed.
- RED observed: `uv run pytest tests/unit/test_ops_sweep.py -o addopts='' -q` → **1 failed** because `sweep.main` did not exist.
- GREEN focused: `uv run pytest tests/unit/test_ops_sweep.py -o addopts='' -q` → **1 passed**; then `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/integration/test_notifications.py tests/integration/test_h4_notifications.py tests/unit/test_ops_sweep.py -o addopts='' -q` → **15 passed**.
- Full suite: `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/ -o addopts='' -q` → **1579 passed, 2 warnings** (181.72 s).
- WU3 commit `0121d054` `feat(ops): run the notification sweep as a scheduled entry point` — CLI, cron documentation, CLI test, and this record. Rollback boundary: scheduled invocation and its documentation/test only.
- Before the corrective round, unproven: reschedule invalidation/rescheduling had no dedicated integration assertion; template delivery success/name/date-time parameter ordering had not been asserted end-to-end (only fallback and approved policy setup were exercised). The cron had only been documented, not installed or observed firing (remote operation is expressly out of scope).
- 2026-09-28: bounded corrective proof round added the three requested integration tests. No implementation change was needed: the first required focused execution was already green, so **there is no RED result to claim** for these test-only assertions. `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/integration/test_notifications.py -o addopts='' -q` → **10 passed** (both before and after adding the explicit one-row counts). Full suite: `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/ -o addopts='' -q` → **1582 passed, 2 warnings** (208.71 s).
- Newly proven: decision 15 creates no operation for a booking <24 h away; reschedule preserves the same single keyed row and moves its due instant, and moving inside 24 h permanently fails that pending row; successful dispatch uses the configured `recordatorio_prueba` name, exactly two local date/time parameters in order, and marks the operation sent.
- Still honestly open: VPS cron installation/firing. Repository evidence is limited to the working CLI and the documented five-minute cron contract; installation is an authorized-ops action, not a repository test.
- Graph Check for the corrective round: stale report still says `16ba9cbf`; queried booking/24 h scheduling, reschedule/reminder operation, and approved template dispatch areas. Nodes consulted include `book()`, `reschedule()`, `NotificationOperation`, `Appointment`, `send_template()`, `scheduling.py`, `notifications.py`, `templates.py`, and the notification integration tests. No requested directed path resolved (`book()`→`_maintain_reminder()` node absent; `reschedule()`→`NotificationOperation` and `send_template()`→`process_operation()` not found). No graph rebuild/update attempted.
- Corrective round commit `150a1bc7` `test(notify): prove appointment reminder edge cases` — integration proof and apply-progress update. No production-code changes; rollback boundary is the three added test cases and this corrective progress entry.

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
- 2026-09-28: S2 implemented in `5a32d61a` (assignment search) and `b279b242` (WhatsApp booking).
  RED: assignment tests failed because `get_hours_timezone` was not yet imported; booking
  acceptance tests failed to receive offers/handoffs before the graph node existed. GREEN:
  scheduling/chat focused tests = 43 passed; full backend suite = 1555 passed, 2 warnings.
  Graph queries consulted `availability()`, `TechnicianAvailability`, `User`, `ConversationState`,
  `capture()`, `orchestrate()`, `summary()`, and `chat/graph.py`. Queried edges: `book()` and
  `availability()` are both contained in `scheduling.py`; `orchestrate()` and `capture()` are
  imported by `chat/graph.py`. The report's conversation pipeline hyperedge connects emergency,
  cost, handoff, receive, classification, and orchestration nodes. Communities include
  `scheduling.py` and `chat/graph.py`. Report remains stale at `16ba9cbf` by instruction.
  RDD assessment was attempted after the work-unit commits but returned `unassessable` for this
  runtime (changed paths/lines reported as 0); its suggested clone-local disable still failed, so
  the clone override was restored to unset and global RDD remains on. No RDD receipt was produced.
- 2026-09-28: S3 worktree re-created from `f27077ec` (PR #403 merge) and provisioned by hand (env,
  `uv sync`, `npm ci`, test DB `lumat-test-lumat-agent-odd-agenda-agente-whatsapp` on port 5945);
  unit smoke `tests/unit/test_scheduling_unit.py` = 10 passed.
- 2026-09-28: S3 product decisions 9-14 closed with the owner (see Closed product decisions).
- 2026-09-28: S3 implemented in three work-unit commits:
  - `631b58e8` `feat(scheduling): publish appointment.rescheduled event` — RED observed (event missing);
    focused 23 passed; full backend 1556 passed.
  - `8d51503b` `feat(chat): cancel appointment from WhatsApp` — RED observed (no confirmation offer);
    focused 11 passed; full backend 1562 passed. RDD review: medium, lens `review-reliability`,
    approved with no findings, authority burned (lineage `review-db26ae5a55d6075d`, candidate
    `sha256:b5dafad4…`, 425 lines).
  - `25f4a2aa` `feat(chat): reschedule appointment from WhatsApp` — RED observed (no slot offer);
    focused 16 passed; full backend 1567 passed. RDD assess over `8d51503b..HEAD`: medium,
    `review_due=false` (`under_budget`, 217 lines), boundary stays `8d51503b`.
- 2026-09-28: Graph Check ran on the stale snapshot (`16ba9cbf`); `graphify --update` still fails with
  HTTP 402. Nodes consulted: `cancel()`, `reschedule()`, `open_slots_for_assignment()`, `scheduling.py`,
  `DomainEvent`, `publish_event()`, `automation.py`, `evaluate_event()`, `graph.py`, `state.py`,
  `Conversation`, `Customer`, `Message`, `Appointment`, `record_audit()`; `graph.py`→`nodes/booking.py`
  did not resolve in the stale snapshot. No rebuild attempted.
- 2026-09-28: honest gaps from S3: the manage node returns `next_step: "end"` on reply turns (the
  `_after_manage` router maps anything outside `{summary, handoff}` to `END`; it works, but booking uses
  `summary` for the same situation — a candidate follow-up, not invented as a fix); the confirmation
  parser stays deterministic (same limitation as S2).
- 2026-09-28: delivery pending the owner's decision: PR3 = S3, three commits, ~642 authored lines
  against the 400-line budget (`ask-on-risk`), so either a size exception or a split into two chained
  PRs (cancel / reschedule).
- 2026-09-28: **delivery decided by the owner: split into two stacked PRs to `main`**, chain strategy
  `stacked-to-main`.
  - PR 1 (cancel slice, branch `odd/agenda-agente-whatsapp-s3-cancel`, head `dd8cddd8`) =
    `631b58e8` + `8d51503b`, 425 changed lines across 10 files; base `main`.
  - PR 2 (reschedule slice, branch `odd/agenda-agente-whatsapp`) = `25f4a2aa` + `58052dd0` + this
    record, 275 changed lines across 6 files; base = PR 1's branch until PR 1 merges, then
    rebased/retargeted to `main` (the reschedule path reuses the `manage` node created by cancel, so
    the slice genuinely depends on PR 1).
  - Split rationale: cancel is independently shippable and each slice then fits the 400-line review
    budget under `ask-on-risk`; a single 642-line PR would have needed `size:exception`.
- 2026-09-28: **post-crash recovery and post-merge verification.** The machine went down with all four
  worktree `db-test` containers exiting 255; the worktree itself was clean (`aa52c085`), no work was
  lost. The merged tree (which had not been verified after `aa52c085` merged `origin/main`) was
  re-verified:
  - full backend on the full S3 tree (branch `odd/agenda-agente-whatsapp`, `aa52c085`):
    `uv run pytest tests/ -o addopts='' -q` = **1571 passed**, 2 warnings (177 s).
  - full backend on PR 1's tree (`odd/agenda-agente-whatsapp-s3-cancel`, `dd8cddd8`) = **1566 passed**
    (217 s); the delta is the 5 reschedule tests absent from that slice.
  - frontend: `npm run build` (`tsc -b && vite build`) passed; `npm test` = 90 files, **826 passed**.
  - test DB re-provisioned through the repo helper (`infra/test-db.sh up`, worktree-derived project
    `lumat-test-lumat-agent-odd-agenda-agente-whatsapp` on port 5945).
  - the repository is honest about the frontend check: `tsc -b` only runs inside `npm run build`, and
    a green Vitest run does not prove the tree type-checks; both were run.
- 2026-09-28: **S4 started.** Worktree re-created from `b5ddfee1` (PR #406 merge) on
  `odd/agenda-agente-whatsapp`. Note: `rapso worktree provision` reported `provisioned: true` but
  created nothing (no `.venv`, no `web/node_modules`, no `infra/.env`); provisioning was done by hand
  (`cp ../lumat-agent/infra/.env infra/.env`, `uv sync`, `cd web && npm ci`, `infra/test-db.sh up`).
  Unit smoke `tests/unit/test_scheduling_unit.py` = 10 passed.
- 2026-09-28: S4 product decisions 15-17 closed with the owner (see Closed product decisions).
- 2026-09-28: S4 reconnaissance (read-only, delegated). Verified: the durable queue already exists
  (`NotificationOperation` with `next_attempt_at`, exponential retries, `permanently_failed` at
  `max_attempts`, `FOR UPDATE SKIP LOCKED` + advisory lock, injectable `now` — the test seam);
  the outbound WhatsApp path is free-form text (`send.send_text`, `app/services/send.py:39-60`) while
  the only template send is hard-coded to `emergency_alert` (`app/services/notify.py:52`, `:65-95`);
  the template registry with the `approved` policy gate exists (`app/services/templates.py:38-57`);
  email exists (`notify.send_email`, `:98-113`); hook points are `scheduling.book` (`:217-235`),
  `cancel` (`:238-249`) and `reschedule` (`:265-303`), none of which commit — they flush inside the
  caller's transaction. `app/ops/sweep.py` has no CLI entrypoint yet. Graph Check ran against the
  stale snapshot (`16ba9cbf`); the delegated explorer's interface had no graph query tool, so the
  orchestrator ran `graphify query "notification operation sweep reminder appointment"` (nodes:
  `NotificationOperation`, `notifications.py`, `sweep.py`, `notify.py`, `send.py`, `templates`-adjacent
  `NotificationTemplateVersion`, `Customer`, `session_scope()`, `record_audit()`, `automation.py`,
  `models.py`, `main.py`) and a stale-snapshot hit `Reminder sweep runs inside the existing webhook
  sweep (no scheduler)` (`tests/integration/test_emergency_notify.py:557`). `graphify path` did not
  resolve for module-level labels. No rebuild attempted (HTTP 402).

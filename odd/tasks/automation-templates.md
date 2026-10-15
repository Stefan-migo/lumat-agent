# automation-templates — recipes deliver approved Meta templates; appointment notifications move to the engine

Objective: let an automation recipe declare a business-initiated Meta template, migrate the 24h
customer reminder and the owner follow-up from `scheduling.py` into catalog recipes (full-engine),
and stop the confirmation recipe from double-confirming chat bookings (origin filter).
Branch: `odd/automation-templates` · Worktree: `../lumat-agent-odd-automation-templates` · Base: `main`
Delivery: chained PRs — PR1 = S1 (origin filter); PR2 = S2–S6 (template engine + recipes + cleanup).
Test runner: `uv run pytest` (backend, `tests/`), `npx vitest run` + `npm run build` (web).

## Specs

- **S1 — Confirmation fires only for panel bookings.** The `appointment.booked` payload carries
  `origin` ∈ {`assistant`, `panel`}: chat bookings (`app/chat/nodes/booking.py`, `actor="assistant"`)
  are `assistant`; panel bookings (`app/panel/api/routes/appointments.py`, `actor=current.username`)
  are `panel`. A recipe may declare exact-match `conditions` (compiled into `AutomationRule.conditions`),
  and `appointment_confirmation` declares `{"origin": "panel"}` so the chat path does not double-confirm
  (the chatbot confirms in-chat). Recipes with no conditions keep today's behavior (empty conditions).

- **S2 — A recipe can declare a business-initiated Meta template.** `RecipeDefinition` may declare a
  template: the registry `event` key (used to find the latest approved `NotificationTemplateVersion`
  for channel `whatsapp`, locale `es`), the Meta template-name setting, and a positional-param builder.
  When such a recipe's operation is delivered on WhatsApp, the send path calls `notify.send_template`
  after `templates.validate_channel_policy(channel="whatsapp", approved=<row.approved>,
  business_initiated=True)`, instead of free-form `send_text`. A missing or unapproved registry row
  raises `TemplatePolicyError` (no free-form fallback for a template recipe).

- **S3 — The 24h reminder is a catalog recipe.** `appointment_reminder` (recipient customer, channel
  whatsapp, template `appointment_reminder_24h`, 2 positional params: `dd/mm/YYYY`, `HH:MM`) is opt-in
  through an installation. The engine emits it 24h before a `booked` visit; a cancelled visit is never
  reminded (state filter) and a rescheduled visit is reminded at its new date. A visit booked with less
  than 24h notice gets no reminder (current behavior preserved). `scheduling._maintain_reminder` and its
  callers (`book`, `cancel`, `reschedule`) are removed in the same change.

- **S4 — The owner follow-up is a catalog recipe with delay.** `appointment_followup` (recipient admin,
  channel whatsapp, templates `appointment_followup` for `completed` and `appointment_followup_no_show`
  for `no_show`, 3 positional params: customer name, `dd/mm/YYYY`, `HH:MM`) triggers on
  `appointment.completed` / `appointment.no_show` and is delivered 24h after the event through a delay
  the recipe declares and the engine honors (`next_attempt_at`). `scheduling._schedule_followup` and its
  caller in `close()` are removed in the same change.

- **S5 — Email fallback preserved.** When WhatsApp template delivery fails, the reminder falls back to
  the customer email and the follow-up to `notify.owner_email`, each audited exactly as today
  (`notification.reminder_email_fallback`, `notification.followup_email_fallback`). A reminder with no
  customer email still fails permanently (`MissingReminderEmail`).

- **S6 — No double send; one source of truth.** The hardcoded reminder/follow-up operation creation is
  deleted in the same change that adds the recipes. No appointment notification is sent twice, and the
  only source for the appointment notification *message* (template + params + recipient target) is the
  recipe catalog.

- **S7 — Registry rows follow Meta approval.** The `NotificationTemplateVersion` rows the recipes need
  are created through the existing template flow with `approved: true` only *after* Meta approves the
  templates; the code ships without seeding unapproved rows. `docs/meta-templates.md` is updated with
  the recipe→template→params mapping.

## Tasks

- T1 (S1) — recipe `conditions` support + `origin` in the `appointment.booked` payload + `appointment_confirmation` filter. RED→GREEN backend tests.
- T2 (S2,S5) — `RecipeTemplate` on `RecipeDefinition` + generic WhatsApp-template send path in `notifications.py` (keeps email fallback). RED→GREEN tests.
- T3 (S3,S6) — `appointment_reminder` recipe + `_reminder_due` time-trigger evaluator + delete `_maintain_reminder`/callers. Tests.
- T4 (S4,S6) — `appointment_followup` recipe + engine delay (`delay_seconds`) + delete `_schedule_followup`. Tests.
- T5 (S6,S2) — delete the hardcoded `_send_appointment_reminder`/`_send_appointment_followup` branches (now driven by the recipe template); confirm no double send.
- T6 (S7) — `docs/meta-templates.md` mapping + frontend catalog check (new recipes appear; update page tests if they assert the catalog).

## Log

- L1 (2026-10-15, owner): "si arrancamos con WU-b (+C)" — start WU-B (engine with templates + `origin`
  filter) plus WU-C (migrate the 24h reminder and owner follow-up to recipes) from
  `odd/handoffs/automation-workunits.md`.
- L2 (2026-10-15, owner decision): WU-C mechanism = **full engine** (recordatorio vía cron 24h antes +
  followup con delay desde el evento; se borra el scheduler hardcodeado). Both paths preserve "no reminder
  if the visit is booked <24h ahead".
- L3: Graph Check consulted nodes `recipes.py`, `notifications.py`, `AutomationInstallation (recipe_id
  UNIQUE row)`, `time_triggers.py Tick Evaluation`, `send.py`, `templates.py`, `notify.py`,
  `AutomationRecipesPage.tsx`.
- L4: Recon + explorer handoff. Key facts: `evaluate_event` cannot express deferred send or invalidation
  (the reminder needs both); `AutomationRule.template_event` was dropped as redundant (migration 049);
  `NotificationOperation` has no template column, so the recipe is resolved at runtime via
  `AutomationExecution.operation_id → rule.installation_id → recipe_id`.
- L5: Worktree `odd/automation-templates` created and provisioned (venv + `infra/.env` + test DB).
- L6 (2026-10-15, owner decision): delivery = **chained PRs**. PR1 = T1 (S1, origin filter); PR2 =
  T2–T6 (template engine + recipes + cleanup).

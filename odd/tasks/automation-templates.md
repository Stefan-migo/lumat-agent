# automation-templates — recipes deliver approved Meta templates; appointment notifications move to the engine

Objective: let an automation recipe declare a business-initiated Meta template, migrate the 24h
customer reminder and the owner follow-up from `scheduling.py` into catalog recipes (full-engine),
and stop the confirmation recipe from double-confirming chat bookings (origin filter).
Branch: `odd/automation-templates` (PR1) · stacked `odd/automation-templates-engine` (PR2) · Worktree: `../lumat-agent-odd-automation-templates` · Base: `main`
Delivery: chained PRs — PR1 = S1 (origin filter, branch `odd/automation-templates`); PR2 = S2–S6 (template engine + recipes + cleanup, branch `odd/automation-templates-engine` stacked on PR1).
Test runner: `uv run pytest` (backend, `tests/`), `npx vitest run` + `npm run build` (web).

## Specs

- **S1 — Confirmation fires only for panel bookings.** The `appointment.booked` payload carries
  `origin` ∈ {`assistant`, `panel`}: chat bookings (`app/chat/nodes/booking.py`, `actor="assistant"`)
  are `assistant`; panel bookings (`app/panel/api/routes/appointments.py`, `actor=current.username`)
  are `panel`. A recipe may declare exact-match `conditions` (compiled into `AutomationRule.conditions`),
  and `appointment_confirmation` declares `{"origin": "panel"}` so the chat path does not double-confirm
  (the chatbot confirms in-chat). Recipes with no conditions keep today's behavior (empty conditions).

- **S2 — A recipe can declare a business-initiated Meta template.** `RecipeDefinition` may declare
  `template_event`, the registry key of the approved `NotificationTemplateVersion` (channel `whatsapp`,
  locale `es`) the recipe delivers. At send time the operation's recipe is resolved from its compiled
  rule (`AutomationExecution.operation_id → rule.installation_id → recipe_id`) and a WhatsApp operation
  routes to the renderer registered for that `template_event` (`notifications._TEMPLATE_RENDERERS`),
  which calls `notify.send_template` after `templates.validate_channel_policy(channel="whatsapp",
  approved=<row.approved>, business_initiated=True)`, instead of free-form `send_text`. The renderer
  owns the Meta template-name setting and the positional params. A missing or unapproved registry row
  raises `TemplatePolicyError` (no free-form fallback). Non-template and non-recipe operations keep the
  generic path. No template data is persisted: no column is added to `AutomationRule`/`NotificationOperation`.

- **S3 — The 24h reminder is a catalog recipe.** `appointment_reminder` (recipient customer, channel
  whatsapp, `template_event="appointment.reminder.24h"` → Meta `appointment_reminder_24h`, 2 positional
  params `dd/mm/YYYY`, `HH:MM`) is opt-in through an installation. A time-trigger scan
  (`time_triggers._reminder_due`) publishes `appointment.reminder_due` for visits that are `booked`,
  start inside the next 24h, and were booked with at least 24h notice (`created_at <= starts_at - 24h`);
  a cancelled visit is never reminded (status filter) and a rescheduled visit uses its current
  `starts_at`. `scheduling._maintain_reminder` and its callers (`book`, `cancel`, `reschedule`) are
  removed in the same change.

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

- T1 (S1) — recipe `conditions` support + `origin` in the `appointment.booked` payload + `appointment_confirmation` filter. RED→GREEN. commit `fc511da4` (PR1)
- T2 (S2,S5) — `RecipeDefinition.template_event` + recipe→renderer resolution in `notifications.py` (`_operation_template_event` + `_TEMPLATE_RENDERERS`), keeping the email fallback. RED→GREEN. commit `5bb2e25b`
- T3 (S3,S6) — `appointment_reminder` recipe + `time_triggers._reminder_due` + single `_EVALUATORS` map + delete `_maintain_reminder`/callers. Tests.
- T4 (S4,S6) — `appointment_followup` + `appointment_followup_no_show` recipes, `delay_seconds`, engine delay in `evaluate_event` + delete `_schedule_followup`. Tests.
- T5 (S6,S2) — delete the hardcoded `:reminder:24h` and `followup:*` branches in `process_operation`; `_send_appointment_reminder`/`_send_appointment_followup` stay as renderers.
  T3–T5 land in one commit: `f6a5ec18`
- T6 (S7) — `docs/meta-templates.md` recipe mapping + stale "known defect" corrected; frontend catalog untouched (its tests use local fixtures).
- T7 (verification) — independent probes from `gentle-ai-verify` committed as `tests/integration/test_verifier_probes.py` (23 tests, S1–S7).

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
- L7 (T1, S1): RED observed — `KeyError: 'origin'` (2 tests) and `conditions` mismatch (2 tests);
  GREEN after recipe `conditions` + `book()` origin. Updated `test_assistant_tools.py` and
  `test_h4_automations.py`, which simulated `appointment.booked` payloads without `origin`, to the
  real publisher shape (`origin: panel`). Focused green; full backend suite green (`EXIT=0`).
  Commit `fc511da4`.
- L8 (T2, S2/S5): design refined — the recipe declares only `template_event` (a registry key); the Meta
  template-name setting and the positional params stay in the renderer in `notifications.py`, so the
  catalog stays DB-free and no import cycle is introduced (`recipes` imports `automation`; `automation`
  imports `recipes` only inside `evaluate_event`). RED observed: `TypeError: RecipeDefinition.__init__()
  got an unexpected keyword argument 'template_event'`. Focused green; full suite `EXIT=0`. Commit `5bb2e25b`.
- L9 (T3–T5, S3/S4/S5/S6): delegated to a bounded worker (`gentle-ai-worker`) at the context backstop,
  with the design above fixed in advance. It reports 69 focused tests and 2299 full-suite tests green
  (`EXIT=0`); the parent re-ran the focused command (69 passed). Its `_reminder_due` keeps
  `created_at <= starts_at - 24h`, so a visit booked >24h ahead then rescheduled into <24h notice still
  gets a reminder (created_at is immutable) — flagged, not a regression of a tested rule. No production
  caller used `close(now=...)`, so dropping that unused parameter is safe. Executions' advisory: an
  operation whose rule was uninstalled before its delayed sweep falls back to the generic path.
  Commit `f6a5ec18`.
- L10 (verification, S1–S7): independent read-only verifier (`gentle-ai-verify`) over `bc36318c..HEAD`:
  every `S1..S7` **MET**, 0 blockers, 23 independent probes green. Advisories (accepted, not fixed):
  (a) uninstalling a rule before a delayed follow-up sweep makes that pending operation fall back to the
  generic free-form path; (b) `_reminder_due` omits the `installation.created_at` floor its sibling
  evaluators apply, so a first install reminds every already-booked visit inside the next 24h (intended:
  opt-in + imminent visits); (c) a visit booked >24h ahead then rescheduled into <24h notice is still
  reminded (immutable `created_at`); (d) pre-deploy pending operations keyed `appointment:{id}:reminder:24h`
  would free-form once after deploy. Probes committed as `tests/integration/test_verifier_probes.py`.
  Frontend (vitest/build) not run: no `web/` file changed. Native risk assessment: `medium`,
  `review_due=false` (`under_budget`).

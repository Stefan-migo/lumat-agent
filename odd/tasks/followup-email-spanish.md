# ODD — followup-email-spanish

## Objective

The appointment follow-up email fallback must be written in Spanish — the language of every other
user-facing string in this flow — and must tell the team which outcome happened, mirroring the
already-approved WhatsApp template contract.

## Problem

`_send_appointment_followup` (`app/services/notifications.py`) builds its email fallback with
hardcoded English strings:

```python
address = get_setting(session, "notify.owner_email")
subject = "Appointment follow-up"
body = f"Please follow up with {customer.name} about the appointment on {params[1]} at {params[2]}."
```

The reminder fallback in the same module is Spanish (`"Recordatorio de visita Lumat"` /
`"Te recordamos tu visita el ..."`). The follow-up email's recipient is the **team**
(`notify.owner_email`), which reads Spanish. (b) of handoff #5343 / Engram obs #5343.

### F2 — the same fallback does not distinguish the outcome

The single `subject`/`body` above is used for **both** outcomes (`completed` and `no_show`). The
approved contract (`docs/meta-templates.md`, committed in `2fceb5b4`) defines **two distinct
texts**, and it fixes the pattern that the email fallback *mirrors* the template wording (stated
explicitly for the reminder at `docs/meta-templates.md:41-42`).

Translating the English literally is not a valid fix: that text is outcome-neutral, and no approved
Spanish copy exists for a neutral form. Inventing one would be new copy. The only already-approved
Spanish text is the contract's, and it is per-outcome — so the fix reuses it verbatim.

**This is a deliberate, owner-vetoable decision.** It changes what the team receives. If the owner
prefers a single neutral Spanish line instead, that is a one-line adjustment.

## Why

The language defect is real and user-visible to the team. `no_show` and `completed` need different
actions from the operator ("reagendar" vs "hacer el seguimiento"), and the email currently tells
them neither.

## Scope

**In scope**

- `app/services/notifications.py` — the email-fallback `subject`/`body` inside
  `_send_appointment_followup` only.
- `tests/integration/test_notifications.py` — assertions covering both outcomes.

**Out of scope (do not touch)**

- WhatsApp template names, params, locale, or the registry/`approved` gate.
- `_send_appointment_reminder` — its fallback is already Spanish.
- `app/services/scheduling.py:64,79` — English `content` values ("Appointment reminder",
  "Appointment follow-up: ..."). These are stored on the operation, not sent: they carry no
  `user_id`, so `create_operation` writes no `PanelNotification` row, and the follow-up send path
  builds its own text instead of using `operation.content`. Same class of leak, no user-facing
  impact. Tracked here as **F3**; a separate cosmetic change if the owner wants it.
- Advisories S4 R3-001, S4 R3-002, S3 R3-001 (informational, per handoff #5343 §3a).

## Constraints

- Copy language: **neutral professional Spanish**, reused verbatim from the approved contract. No
  regional variant, no invented wording.
- Recipient (`notify.owner_email`), locale (`es`), audit action
  (`notification.followup_email_fallback`), and both idempotency keys stay unchanged.
- No new settings keys, no new dependencies, no new module.
- Ponytail: smallest diff that fixes the defect. Two strings and their outcome selector. No
  helper function, no copy table, no abstraction for two values.
- Technical artifacts in English; the email copy itself is Spanish by definition.

## Graph Check (Step 1 — rapso-persona gate)

Query: `graphify query "appointment followup email fallback notifications"`.

Nodes consulted:

| Node | Source | Community |
| --- | --- | --- |
| `_send_email_fallback()` | `app/services/notify.py` L232 | `get_setting` |
| `send_emergency_notification()` | `app/services/notify.py` L162 | `get_setting` |
| `notify.py` | `app/services/notify.py` L1 | `get_setting` |
| `get_setting()` | `app/services/settings.py` L175 | `get_setting` |
| Notifications Spec (modified H4) | `openspec/specs/notifications/spec.md` | `H4 Archive Report` |

Graph status: **degraded — stale**. The report is last marked `16ba9cbf` and `graphify --update`
is unavailable (402 Insufficient Balance, per handoff #5343 §4). The query itself returns nodes;
the refresh is not claimed. Reported, not skipped.

## TDD

- Mode: **strict** — source `openspec/config.yaml` → `testing.strict_tdd: true`.
- Runner: `uv run pytest`. Contract test command: `uv run pytest tests/`.
- RED before GREEN, observed. No implementation before a red test.
- Linter / type checker / formatter: **none configured** (measured, `openspec/config.yaml`
  `testing.quality`). Frontend not touched → no `npm run build`.

## Tasks

- [x] **T1 (RED)** In `tests/integration/test_notifications.py`, extend
  `test_followup_whatsapp_failure_falls_back_to_team_email_and_audits` to assert the captured
  subject and body, and add a `no_show` counterpart. Assert the Spanish text from the contract,
  including the interpolated customer name, date (`dd/mm/YYYY`) and time (`HH:MM`). Run it and
  **observe it fail** against the current English code. Record the failure output.
- [x] **T2 (GREEN)** Replace the hardcoded English `subject`/`body` in
  `_send_appointment_followup` with the per-outcome Spanish text mirroring
  `docs/meta-templates.md` templates 2 and 3. Reuse the existing `outcome` parameter; do not add
  a parameter or a helper. Re-run T1's tests and observe them pass.
- [x] **T3 (REFACTOR / verify)** Run the focused suite
  (`tests/integration/test_notifications.py`) and then the full suite. Confirm no other test
  depended on the English strings. Record observed results.
- [x] **T4 (commit)** One work-unit commit, Conventional Commit, source + tests together. Record
  the commit SHA in this document.

## Acceptance criteria

1. On WhatsApp failure for a `completed` follow-up, the team email subject and body are Spanish and
   state the visit was completed, mirroring contract template 2.
2. Same for `no_show`, mirroring contract template 3.
3. The recipient is still `notify.owner_email`; the audit action is unchanged.
4. No non-Spanish user-facing string remains in `_send_appointment_followup`.
5. Focused and full Python suites pass; the RED was observed before the fix.

## Checks

- Focused: `uv run pytest tests/integration/test_notifications.py -o addopts='' -q`
- Full: `uv run pytest tests/ -o addopts='' -q`
- Environment: `eval "$(bash infra/test-db.sh env)"` once per shell.

## Route declaration

| Task | Route | Trigger evidence |
| --- | --- | --- |
| T1+T2 (source + tests, 2 non-trivial files) | **delegated — one writer** | Writer trigger (2+ non-trivial files); preparation trigger (the writer must read `notifications.py` + the test file + the contract) |
| T3 | writer runs the focused+full suite in the foreground (RDD on) | Parent-authorized verification |
| T4 | writer | work-unit commit skill |

## Delivery

- Forecast: ~15 lines of source + ~35 lines of tests → **well under 400**. Single PR, no chain.
- Strategy: `ask-on-risk` (default). No split needed.
- Branch: `odd/followup-email-spanish`, base `2fceb5b4` (`main`).
- RDD: **on** (global). Native review after the writer returns, before delivery.

## Progress

| When | State |
| --- | --- |
| 2026-09-29 | Worktree created, provisioned, task doc written. No source change yet. |
| 2026-09-29 | T1 RED observed: `test_followup_whatsapp_failure_falls_back_to_team_email_and_audits[completed]` and `[no_show]` failed at `assert emails[0][1] == "Seguimiento de visita Lumat"`; actual was `'Appointment follow-up'`. Result: **2 failed, 15 passed in 4.83s**. |
| 2026-09-29 | T2 implementation: Spanish subject and outcome-specific, accented email body. `AppointmentStatus.NO_SHOW` verified in `app/models.py`. |
| 2026-09-29 | T3 GREEN: focused `uv run pytest tests/integration/test_notifications.py -o addopts='' -q` → **17 passed in 3.45s**. Full `uv run pytest tests/ -o addopts='' -q` → **1720 passed, 2 warnings in 368.86s**. Warnings: unawaited `_publish_all` coroutine and fastembed pooling notice. |
| 2026-09-29 | T4 source/test work-unit commit: `d3bae6fa` — `fix(notifications): localize follow-up email fallback`. |

# Meta WhatsApp template contract — appointments

The three business-initiated templates this system sends, and the exact contract each one must
match in Meta. Written 2026-09-29, before the templates exist.

**Why it exists.** `emergency_alert` was sent without ever going through the template registry, so
S4 (the 24 h reminder) introduced a policy gate: a WhatsApp send that is business-initiated
requires a published `NotificationTemplateVersion` row with `approved = true`
(`app/services/templates.py:38-42`). S5 added two more sends. The code is complete and deployed;
what is missing is the Meta side. This document is that handoff.

**Two independent artefacts must agree.** Meta holds the *real* message text and its placeholders.
The panel holds a *registry row* used only as the policy gate and the operator-facing record. Both
are required for a send to succeed. Getting one right and the other wrong fails at delivery time,
not at publish time.

**Opt-in.** These sends only happen when the matching catalog recipe is installed in the panel; the
code ships the recipes, not an active schedule. At send time the operation's recipe is resolved from
its compiled rule (`AutomationExecution -> AutomationRule -> installation -> recipe`), and the
recipe's `template_event` selects the renderer. Deleting a hardcoded send path in favour of the
recipe is what makes the catalog the single source of truth for these messages.

## Hard constraints (each one breaks the send if violated)

| Constraint | Why |
| --- | --- |
| Language must be exactly **`es`** | `app/services/notify.py:53` — `TEMPLATE_LANGUAGE = "es"` is hardcoded into every `send_template` call. `es_CL` / `es_MX` / `en_US` all fail with a language mismatch. |
| Placeholder count and order must match the code | The body parameters are positional. A template with 2 placeholders receiving 3 parameters fails, and swapping the order silently sends the time where the date belongs. |
| Category **Utility** | These are operational notifications tied to a specific appointment, not promotional content. |
| Names must exist verbatim | The panel settings keys hold the Meta names. A rename is a settings change, not a code change — see the table below. |
| Same WABA as `META_PHONE_NUMBER_ID` | A template approved on another number or WABA is invisible to this sender. |

## Template 1 — `appointment_reminder_24h` (customer-facing)

| Field | Value |
| --- | --- |
| Meta name | `appointment_reminder_24h` |
| Language | `es` |
| Category | Utility |
| Body parameters | **2**, positional |
| `{{1}}` | visit local date, `dd/mm/YYYY` |
| `{{2}}` | visit local time, `HH:MM` |
| Registry event (panel row) | `appointment.reminder.24h` |
| Settings key | `notify.reminder_template_name` |
| Recipe (panel catalog) | `appointment_reminder` — opt-in; fired by the time-trigger scan `appointment.reminder_due` on booked visits inside the next 24 h |
| Renderer | `app/services/notifications.py` `_send_appointment_reminder`, registered in `_TEMPLATE_RENDERERS` |

Recipient: the **customer's** WhatsApp number. The email fallback mirrors this wording
(`app/services/notifications.py:51-52`), which is why the body below reuses it.

Body text (Spanish, as it must be entered in Meta):

```
Te recordamos tu visita de Lumat el {{1}} a las {{2}}.
```

## Template 2 — `appointment_followup` (team-facing, completed)

| Field | Value |
| --- | --- |
| Meta name | `appointment_followup` |
| Language | `es` |
| Category | Utility |
| Body parameters | **3**, positional |
| `{{1}}` | customer name |
| `{{2}}` | visit local date, `dd/mm/YYYY` |
| `{{3}}` | visit local time, `HH:MM` |
| Registry event (panel row) | `appointment.followup.completed` |
| Settings key | `notify.followup_template_name` |
| Recipe (panel catalog) | `appointment_followup` — opt-in; triggers on `appointment.completed`, delivered 24 h later (`delay_seconds = 86400`) |
| Renderer | `app/services/notifications.py` `_send_appointment_followup`, registered in `_TEMPLATE_RENDERERS` |

Recipient: the **team's** number (`notify.owner_whatsapp`), not the customer. The customer name is
the first parameter precisely because the operator has to know who to call back.

Body text:

```
La visita de {{1}} del {{2}} a las {{3}} quedo cerrada como completada. Contacta al cliente para hacer el seguimiento.
```

> Accents are safe in Meta template bodies; they are written without them above only because this
> file is otherwise ASCII. Enter them with accents in Meta.

## Template 3 — `appointment_followup_no_show`

| Field | Value |
| --- | --- |
| Meta name | `appointment_followup_no_show` |
| Language | `es` |
| Category | Utility |
| Body parameters | **3**, positional (same order as template 2) |
| Registry event (panel row) | `appointment.followup.no_show` |
| Settings key | `notify.followup_no_show_template_name` |
| Recipe (panel catalog) | `appointment_followup_no_show` — opt-in; triggers on `appointment.no_show`, delivered 24 h later (`delay_seconds = 86400`) |
| Renderer | `app/services/notifications.py` `_send_appointment_followup`, registered in `_TEMPLATE_RENDERERS` |

Recipient: the **team's** number.

Body text:

```
La visita de {{1}} del {{2}} a las {{3}} quedo marcada como no asistida. Contacta al cliente para reagendar.
```

## After Meta approves: publish the registry rows

`POST /panel/api/templates` (operator-authenticated; `app/panel/api/routes/calendar_templates.py:43`).
The registry row's `content` uses **our** `{name}` syntax and is **not** the WhatsApp text — the real
text lives only in Meta. The row exists as the policy gate and the panel record.

```http
POST /panel/api/templates
Content-Type: application/json

{"event": "appointment.reminder.24h", "channel": "whatsapp", "locale": "es",
 "content": "Te recordamos tu visita de Lumat el {date} a las {time}.",
 "required_variables": ["date", "time"], "approved": true, "smtp_allowed": true}
```

```http
POST /panel/api/templates
Content-Type: application/json

{"event": "appointment.followup.completed", "channel": "whatsapp", "locale": "es",
 "content": "La visita de {customer_name} del {date} a las {time} quedo cerrada como completada.",
 "required_variables": ["customer_name", "date", "time"], "approved": true, "smtp_allowed": true}
```

```http
POST /panel/api/templates
Content-Type: application/json

{"event": "appointment.followup.no_show", "channel": "whatsapp", "locale": "es",
 "content": "La visita de {customer_name} del {date} a las {time} quedo marcada como no asistida.",
 "required_variables": ["customer_name", "date", "time"], "approved": true, "smtp_allowed": true}
```

**Do not publish these with `approved: true` before Meta approves the templates.** That flag mirrors
Meta's real approval; publishing it early makes the code attempt sends Meta will reject, turning a
clear "not configured yet" into a confusing delivery failure.

## Settings keys (only needed if a template is created under a different name)

| Key | Default |
| --- | --- |
| `notify.reminder_template_name` | `appointment_reminder_24h` |
| `notify.followup_template_name` | `appointment_followup` |
| `notify.followup_no_show_template_name` | `appointment_followup_no_show` |

## Verification once everything is in place

The dispatch path only fails visibly in the operation's audit trail, so verify it end to end rather
than assuming: close one visit as `completed` in the panel, confirm the follow-up operation exists
and is due 24 h later, then either wait for the five-minute sweep cron or read
`/home/deploy/lumat-sweep.log` on the VPS. A send that reaches Meta marks the operation `sent`; a
failure leaves it retryable, then falls back to the team email and audits
`notification.followup_email_fallback`.

## Follow-up email fallback language

The follow-up email fallback (`_send_appointment_followup` in `app/services/notifications.py`) is
Spanish, matching the rest of the flow: subject `"Seguimiento de visita Lumat"`, body
`"La visita de {name} del {date} a las {time} quedo ..."`. An earlier revision of this document
recorded an English fallback as a known defect; that no longer applies. The fallback writes
`notification.followup_email_fallback` to the audit trail.

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
| Code | `app/services/notifications.py:26-58` (`_send_appointment_reminder`) |

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
| Code | `app/services/notifications.py:61-108` (`_send_appointment_followup`) |

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
| Code | `app/services/notifications.py:61-108` (`_send_appointment_followup`) |

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

## Known defect found while writing this contract

`_send_appointment_followup` (`app/services/notifications.py`) builds its **email fallback** in
English — subject `"Appointment follow-up"`, body `"Please follow up with ..."` — while every other
user-facing string in this flow is Spanish (the reminder's fallback is
`"Recordatorio de visita Lumat"` / `"Te recordamos tu visita el ..."`). The recipient is the team,
which reads Spanish. Not yet fixed; it is a source change and therefore belongs to its own reviewed
change, not to this document.

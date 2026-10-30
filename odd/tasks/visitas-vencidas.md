# ODD: visitas-vencidas

Close the visits that stay `booked` after they start: surface the overdue ones where an operator
actually looks, and let many be closed in one action without ever guessing whether a visit happened.

Worktree `/home/stefan/repos/lumat-agent-odd-visitas-vencidas`, branch `odd/visitas-vencidas`, base
`ac5822d1` (`main`).

## Specs

### S1 — An overdue visit is visible and closable where the operator already works

A visit is **overdue** when `status = 'booked'` and `starts_at` has already passed. Measured in
production on 2026-10-30: **10 overdue visits**, the oldest starting 2026-09-25 (35 days), against a
book with **zero `completed` and zero `no_show`** rows.

Today the closing tool exists and is reachable — `web/src/components/shared/AppointmentClosureDialog.tsx`,
`AgendaPage.tsx:121`, `AppointmentDetail.tsx:174` — but only by navigating to the day the visit
happened, which nobody does. Rule: the panel surfaces the overdue set in one place, without navigating
to a past day, and each row can be closed right there.

### S2 — A bulk close never guesses the outcome

Owner's rule (L1): a bulk action exists for when visits accumulate. Rule: the bulk requires the
operator to choose `completed` or `no_show` **once for the batch**, shows how many visits and which
customers will be affected **before** confirming, and never infers an outcome from the time elapsed or
from any other silence. A batch is not all-or-nothing by accident: every row reports its own result, so
a visit already closed by someone else is reported as such instead of failing the whole batch.

### S3 — The single-visit closing paths keep their behaviour

Two paths exist and are the contract the bulk reuses:
`POST /panel/api/appointments/{id}/close` (operator, `require_operator_json`) and
`POST /panel/api/technician/appointments/{id}/close` (technician, own visits only,
`_owned_appointment`, response carries no customer or conversation data). Both go through
`scheduling.close()`, which writes appointment status, appointment history, `audit_log`, the
`appointment.completed` / `appointment.no_show` event, and notifies admins on no-show. Rule: the bulk
reuses that same function so history, audit, events and notifications stay identical, and neither
single path changes behaviour.

### S4 — Closing never destroys data

Closing is a state transition, not a deletion. Rule: no row is deleted, no `CASCADE` is added, and the
actor recorded is the authenticated user, so the audit answers *who* closed the visit and *when*.

## Tasks

| ID | Spec | Task | Route | Commit |
| --- | --- | --- | --- | --- |
| T1 | S1 | Backend: overdue query + list endpoint for operators, with tests | worker | — |
| T2 | S2, S3 | Backend: bulk close endpoint reusing `scheduling.close`, per-row result, with tests | worker | — |
| T3 | S1 | Frontend: overdue list with per-row close, reusing `AppointmentClosureDialog` | worker | — |
| T4 | S2 | Frontend: bulk selection, mandatory outcome, confirmation preview | worker | — |
| T5 | S1–S4 | Frontend gate (`npm ci` → `build` → `test`), docs, handoff | parent | — |

## Log

**L1** — owner, verbatim:

> La pregunta real que necesito de vos
>
> No es "¿construyo el cierre?" — ya está. Es cómo y cuándo alguien cierra:
>
> - ¿El técnico, desde su vista, al terminar o al no encontrar al cliente?
> - ¿El dueño, desde el panel, cerrando el día?
> - ¿Una lista de "visitas vencidas sin cerrar" en la agenda, para que no haya que ir a buscarlas?
>
> creo que las tres de arriba aplican como buenas practicas para mantenerlos limpias. el tecnico desde su panel. el admin/operador desde el panel, y un bulk para cuando se junten muchas

**L2** — evidence measured before opening this feature (read-only, production, 2026-10-30):

- `select count(*) from appointments where status='booked' and starts_at < now()` → **10**; the oldest
  is 2026-09-25 15:00Z (35 days), and the whole book is 10 `booked` + 1 `cancelled`.
- `completed` and `no_show` are both **zero**: the transition has never run in production.
- The mechanism is complete, not missing: `app/services/scheduling.py:451 close()` writes status,
  history, audit, event and the no-show notification; two panel routes call it
  (`app/panel/api/routes/appointments.py:159`, `app/panel/api/routes/technician.py:122`) and the web
  app already has the dialog and two entry points.
- Therefore the missing half of the owner's answer is **visibility** (S1) and the **bulk** (S2), not
  the closing itself. That is why this feature is scoped to T1–T4 and not to a new closing mechanism.

**L3** — risk declared before the first write: this feature **writes data** (S1–S4 are transitions on
real appointments) and **crosses a permission boundary** (operator vs technician roles, o§ E). Per the
orchestrator's risk list that is items 1 (data effects) and 2 (security), so each unit lands as its own
commit and gets an independent verifier before delivery. The bulk endpoint must never accept an
appointment the caller could not close individually.

**L4** — T1/T2 done (`9d65e826`, merged as PR #754 → `82edf2b1`). `scheduling.list_overdue()` filters
`booked` with `starts_at` in the past, oldest first, joined with customer, case and technician; all three
FKs are `nullable=False`, so the inner joins cannot silently drop an overdue visit. `GET
/appointments/overdue` projects through the same agenda serializer the day view uses, and is declared
**before** `/appointments/{appointment_id}`: declared after, the path parameter swallows it and the
request answers 422 — which is exactly the first RED this unit produced (the bulk answered 405 for the
same shape reason). `POST /appointments/bulk-close` takes one outcome for the batch, validated by
`Literal["completed","no_show"]`, never inferred; it reports per row, caps at 100 ids, keeps
`require_operator_json`, and reuses `scheduling.close()` so history, `audit_log`, the
`appointment.completed` / `appointment.no_show` event and the no-show notification stay identical to the
single-visit path.

Two defects the parent review caught before the commit, both fixed with a failing test first:

1. The overdue projection returned `to_appointment_dict()`, which carries `customer_id` but **no
   customer name** — S2 asks the batch to show which customers are affected, and raw ids cannot. It now
   goes through the agenda projection.
2. A database-level error during `scheduling.close()` left the session poisoned, so the next
   `session.get()` raised and the endpoint answered 500 — losing the per-row reporting S2 requires. It
   now catches `SQLAlchemyError`, rolls the row back and continues.

Verified: `quick` → exit 0; `db tests/functional/test_api_scheduling.py` → 30 passed; `db
tests/functional/test_api_technician.py` → 44 passed.

**L5** — T3/T4 done. `OverdueVisitsPanel` renders the overdue set with per-row close through the
existing `AppointmentClosureDialog` and the batch flow; `api.ts` gained the two typed clients;
`AgendaPage` fetches the set only when not driven by props (so Storybook stays offline) and refetches
after either close, with the bulk refresh wrapped on its own so a failed refresh cannot hide the
per-row report.

The S2 invariants were verified in the code before delivery: the batch outcome starts unselected and is
reset when the dialog opens; the confirmation lists the affected customers; results are attributed per
row to their own customer; the 100 cap is enforced in three places; nothing renders when the set is
empty.

**The independent verifier could not be produced.** `gentle-ai-verify` failed twice and `jd-judge-a`
once, all with the same opaque "assistant reported an error" and no output — three attempts across two
roles, so the runtime for those read-only reviewers is broken rather than the brief. Per the delegation
contract that is reported as unavailable, not retried further, and the parent ran the adversarial pass
itself. Recorded here so the gap is visible instead of implied.

That pass found one real defect: the batch sent `selectedIds` — the raw selection — while the dialog
names the visits it will close. A refetch while the dialog is open drops a row, so the preview showed
fewer customers than the batch would close, and a visit the operator could no longer see went through.
The batch now sends exactly the appointments the dialog is showing (`f013d433`), with a guard test that
selects two visits, drops one from the list while the dialog is open, confirms, and asserts only the
visible one is sent. Proven by mutation: restoring `selectedIds` makes that test fail.

**Deliberate non-change, recorded rather than hidden**: the single-visit close inherits the shared
dialog's `"completed"` default. That is the pre-existing behaviour S3 protects, and changing it here
would make the overdue panel behave differently from the agenda and the appointment detail. It still
deserves its own decision, because for a visit that is overdue by definition, `completed` is the
optimistic guess and `no_show` is at least as likely.

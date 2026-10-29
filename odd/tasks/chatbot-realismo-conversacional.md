# ODD: chatbot-realismo-conversacional

Make the customer-facing WhatsApp conversation read like a real conversation and stop losing
bookings: no courtesy tics, no redundant questions, no dead-end slot offers, no invented extras.

Branch `odd/chatbot-realismo-conversacional`, worktree
`/home/stefan/repos/lumat-agent-odd-chatbot-realismo-conversacional`, base `23d1d29f` (production
runs `v2026.10.11` = `046a1254`; the only difference is one docs commit, so every root cause below is
in the deployed code).

## Specs

Evidence source: production conversation **#23** (2026-10-29, `agente.lumat.cl`) and harness
conversations **#37–#46** (`lumat-harness`, db :5433). Quoted strings are the real messages.

### S1 — No courtesy tic on the opening turn; the name is not repeated (A1)

Turn 285 of #23 reads, verbatim:

```
Gracias Stefan. Stefan, cuéntame qué pasa con la caldera: ¿no enciende, no calienta o muestra algún código de error?
```

It thanks the customer before they have given anything, and it says the name twice in one message.
The turn the owner wants is:

```
Entiendo. Stefan, cuentame ....
```

Rules: the acknowledgement word is `Entiendo.`, never `Gracias`; the customer's name appears **at
most once** in a turn; an acknowledgement is only emitted when the turn actually delivered a data
point the flow was waiting for.

Constraint (measured in production): `settings["reply.texts"]["capture_ack"]` is stored as
`"Gracias {{nombre}}. "`, an explicit override of the shipped default. A code-only change does not
reach production, so the fix pairs a behaviour rule with a guarded data migration that rewrites the
stored text **only** when it is exactly the old shipped default.

### S2 — Address and evidence are separate questions; evidence comes last (C2)

Turn 296 of #23, verbatim:

```
¿Cuál es tu dirección, Stefan? ¿Tienes algo más para pasarle al técnico? (una foto, un audio…)
```

Two asks in one message, and the evidence ask is wasted there. Owner's rule: the evidence question
(`capture_evidence`, `¿Tienes algo más para pasarle al técnico? (una foto, un audio…)`) moves to the
end — after the appointment is confirmed, as the last thing before closing.

### S3 — A consent already given is not asked again (C1, blocked)

The customer is `customers.id = 2` with `consent_status = true` recorded on 2026-10-27 (conversation
#22). Turn 301 of #23 asks anyway:

```
Necesitamos guardar tus datos para gestionar la visita. ¿Nos darías tu autorización? (Responde sí o no)
```

Same root cause re-asks name, comuna, email and address: the capture flow never reads the customer
record. Owner's rule: if the customer already granted consent, do not ask again.

**Blocked on the owner's product decision** (see Log L5): silent skip vs. a short confirmation, and
what a "no" withdraws.

### S4 — "manutención" is a preventive maintenance request (A5)

Turn 284 of #23, verbatim:

```
Necesito hacerle manutención a la caldera en casa
```

and the bot answered with the fault interrogation (turn 285, see S1). `manutención` is a typo /
autocorrect variant of `mantención`. The preventive decision is 100% deterministic
(`any(keyword in normalized_window ...)` over `capture.preventive_keywords`), so no model can rescue
it. Rule: the preventive decision matches the canonical service catalogue with typo tolerance, and
`manutención` must not trigger the failure question.

### S5 — Out-of-coverage reply carries nothing extra (A2)

Harness conversation #46 (`estoy en maipu`), verbatim:

```
Todavía no tenemos visitas técnicas en Maipú para tu caldera, un asesor de Lumat se contactará contigo para ayudarte a la brevedad. El precio vigente de Mantención de caldera es $80.000. Un asesor coordinará contigo la visita; todavía no puedo confirmar fecha ni hora.
```

The owner's rule: the standard coverage message is enough. It must not quote a price nobody asked
for, and it must not repeat that an advisor will contact the customer.

### S6 — A closing that names a good day closes (A3)

Harness #45, verbatim:

```
eso seria todo muchas gracias! que tengas buen dia
```

answered with `Con gusto. ¿En qué más te puedo ayudar?` because `is_farewell` rejects any text longer
than 40 characters. Rule: a closing phrase plus courtesy closes, whatever its length.

### S7 — Natural consent answers are accepted (A4)

Harness #45, verbatim:

```
no se que marca es realmente el calefont. si autorizo
```

was answered with `Necesito que me confirmes si autorizas guardar tus datos. Responde sí o no.`
`_answer_consent` requires the whole message to be one allowlisted word, and `autorizo` is not there
— although the question itself asks for authorization. The same rejection happened in #37 (`sio`) and
#38 (`y parsi`). Rule: a short affirmative that contains an allowlisted consent token is consent; a
negation always wins.

### S8 — "después del mediodía" is an afternoon window (B1)

Production #23, turns 304/306/308/310, verbatim:

```
Podría ser después del mediodía ?
Podría ser para el 3 de noviembre después del mediodía?
Después de las 12 del mediodía?
3 de noviembre después de las 12 del mediodía
```

All four produced the same three morning slots (09:00, 09:30, 10:00) while the day's universe held 17
slots up to 17:00. Rule: `después del mediodía`, `después de las 12` and the same with `medio día`
resolve to the afternoon window.

### S9 — An abbreviated month keeps the requested day (B2)

Harness #45, turn 604, verbatim:

```
y para el dia 3 de nov podria ser en la tarde?
```

was answered with slots on **29/10 and 30/10** — days before the requested date — because `nov` is not
in `_MONTHS`. Rule: month abbreviations resolve, and when a day cannot be resolved the offer must
never silently move to an earlier date than the one asked for.

### S10 — A preference that cannot be served is said, not re-offered (B3)

Production #23, turns 305/307/309/311: `No pude identificar un único horario. Responde con el número
de una opción.` alternating with the identical three-slot offer, three times, with no escalation and
no explanation, until the customer stopped writing. Rule: after the second identical offer the reply
must say the requested window has nothing (or offer other days), and `attempts` must not reset so the
existing handoff limit is reachable.

### S11 — A past appointment is never offered (B4)

Production #23, turn 287, verbatim:

```
Tienes una visita agendada para el 28/10 a las 10:00. ¿Quieres que esa misma visita se use para la mantención?
```

The conversation happened on 29/10: the appointment was yesterday. Rule: the state loaded for the
prompt contains only appointments that have not started yet.

### S12 — "reagendar" opens the manage flow (B5)

Production #23, turn 289, verbatim:

```
Quiero reagendar la visita es posible?
```

classified `intent:reagendar_visita` and answered `¿En qué comuna te encuentras?`, re-capturing comuna
and address (`_asked.comuna = 2`, `_asked.address = 2`) for a customer who had both. Rule: a reschedule
request lists the customer's upcoming visits instead of starting a new capture.

### S13 — One question per turn (C3)

Production #23, turn 287 + 288, same second:

```
[saldo KB] ... ¿Quieres que esa misma visita se use para la mantención?
¿En qué comuna te encuentras?
```

Rule: when the KB answer already ends in a question, the pending capture question waits for the next
turn. `chat.conduct.max_preguntas_por_mensaje` is 1.

### S14 — The same input gives the same answer (C4)

Harness #43 and #44 sent identical messages. #43 (`case.service = calefont`) got
`No tengo ese dato. ¿Prefieres que te tome los datos para coordinar una visita, o que te atienda una
persona?`; #44 (`case.service = reparación de calefont`) got
`Sí, atendemos sábado de 09:00 a 18:00, siempre según la disponibilidad de técnicos.` Rule: the
retrieval fallback query is normalized against the service catalogue, so both resolve the same way.

### D — Investigation, no behaviour spec yet

- **D1** — `conversation_events` on 2026-10-28 12:04, 14:09 and 16:52 record `classified`,
  `handoff:booking_unclear` and `handoff:campo_sin_respuesta` with **no inbound message** in
  `messages`, including conversations whose appointment was already confirmed (#40, #42).
- **D2** — appointments stay `booked` after they start (production appointment #11 is `booked` for
  2026-10-28 and still open).

## Tasks

Order approved by the owner: A → B → C3 → C4 → C1 → C2 → D.

| ID | Spec | Task | Route | Commit |
| --- | --- | --- | --- | --- |
| A1 | S1 | Ack only with a delivered data point; `Entiendo.`; name at most once; guarded migration for the stored `capture_ack` | inline | f7a6162b |
| A2 | S5 | Remove the price append and the hardcoded coordination sentence from the coverage handoff | inline | 04b993c9 |
| A3 | S6 | `is_farewell` closes a long courtesy closing | inline | 63b890ec |
| A4 | S7 | Consent allowlist accepts natural affirmatives, negation wins | inline | 9c63dc20 |
| A5 | S4 | Preventive decision matches the canonical service catalogue with typo tolerance | inline | a15e0edb |
| B1 | S8 | Afternoon window from "después del mediodía" / "después de las 12" | inline | 0a7914cd |
| B2 | S9 | Month abbreviations; never move the offer to an earlier day | inline | 0a7914cd |
| B3 | S10 | No silent re-offer; `attempts` survives a rebuilt offer | inline | 4871dc62 |
| B4 | S11 | `state.booking` ignores appointments that already started | inline | see L13 |
| B5 | S12 | `reagendar_visita` routes to `manage` | inline | see L14 |
| C3 | S13 | One question per turn after a KB deviation | inline | |
| C4 | S14 | Normalized service as retrieval fallback query | inline | |
| C2 | S2 | Evidence question moves to after the booking confirmation | inline | |
| C1 | S3 | Seed capture from the customer record (consent + data) | inline | faaed3dc | blocked on L5.1 for the data half |
| D1 | D | Investigate the message-less escalations | inline | |
| D2 | D | Expired `booked` appointments | inline | |

## Log

**L1** — owner, verbatim:

> perfecto a esos descubrimientos que creaste. necesito que le pongas atencion a esto que es un error muy feo. puede ser marginal en tu analisis pero dentro de una conversacion es muy poco real.
>
> en la Conversación #23, turno 285. dice Gracias Stefan. no se por que esta agradeciendo de partida. deberia ser algo mas sencillo como un entiendo. no es necesario ser tan repetitivo con el nombre del cliente. ese turno seria mucho mas real si dijera: "Entiendo. Stefan, cuentame ...."
> el turno 296. aqui pregunta dos cosas. la direccion (aqui el nombre del cliente esta bien utilizado. pero igual puede llegar a ser redundante) ademas pregunta por si hay algo mas que pasarle al tecnico. esta pregunta de mas informacion para pasarle al tecnico la llevaria al final. como ultimo recurso antes de cerrar todo. quizas cuando ya se haya terminado de concretar la agenda. hacer esta pregunta.
>
> turno 301. yo ya estoy guardado como cliente de lumat. y mi consentimiento ya esta dado. aun asi me vuelve a preguntar por el consentimiento. si un cliente ya lo dio, no es necesario preguntar todas las veces verdad?
>
> ----
>
> respecto a la palabra manuntencion. aqui es donde tengo dudas com ofunciona la logica de que exista un llm evaluando los mensajes del cliente. aqui manuntencion es obvio que fue un error de tipeo y probablemente de corrector de palabras del celular. aqui el llm realmente no entendio que la intencion del cliente era mantencion?
>
>  necesito saber com ofunciona en este caso. es 100% deterministico esta parte?
>
> ----
>
> Despues en la conversacion con ORlando en local. testie preguntar por una comuna fuera de cobertura. viste la respuesta?
>
> ```
> cliente> estoy en maipu
>   bot | Todavía no tenemos visitas técnicas en Maipú para tu caldera, un asesor de Lumat se contactará contigo para ayudarte a la brevedad. El precio vigente de Mantención de caldera es $80.000. Un asesor coordinará contigo la visita; todavía no puedo confirmar fecha ni hora.
> ```
>
> con el mensaje estandar aqui era suficiente. pero agrego el valor que no le habian preguntado. y ademas vuelve a repetir que un asesor se contactara pero no puede confirmar fecha ni hora. lo cual no es necesario ya se dijo en el mensaje que le iban a hablar personalmente.
>
> agrega esto al analisis. que son cosas que observe yo. luego necesito que crees un plan para proceder con todas las mejoras descubiertas y sus fixes

**L2** — owner, verbatim: `me parece bien procede asi en ese orden` (authorizes the A → B → C3 → C4 → C1
→ C2 → D order and the worktree).

**L3** — evidence, root causes measured on 2026-10-29 (see Engram `#6955`, `#6957`):
`capture.py:663-665` + `settings.py:199` (S1); `capture.py:709-712` (S2); `capture.py:685` and
`_missing_fields` never reading `Customer` (S3); `capture.py:445` substring over
`capture.preventive_keywords` (S4) while the classifier returned `service = "visita técnica"`
(case #19); `handoff.py:177` + `_coverage_price_reply:85-111` (S5); `closure_gate.py:69` `len > 40`
(S6); `capture.py:208-215` (S7); `slot_window.py:82-84` (S8) and `:52-66` (S9); `booking.py:190-215,
302-315` (S10); `state.py:257-264` no `starts_at` filter (S11); `graph.py:_after_research_triage` +
`respond.py:528-538` (S13); `respond.py` retrieval fallback on `case.service` (S14).

**L4** — decision: the preventive matcher reads the canonical catalogue
(`booking.service_durations` + `tarifa.precios` labels) instead of growing a hand-written synonym
list, because `manutención`, `mantenimiento` and `mantnecion` are the same business request and a
keyword list will always lag one typo behind. `capture.preventive_keywords` stays as an explicit
override so no configured value loses its reader.

**L6** — A1 done (`f7a6162b`). RED reproduced production turn 285 verbatim:
`Gracias Stefan. Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de
error?`. The fix needed three parts, not one: (1) the acknowledgement now requires a field on record
as asked; (2) the old guard `if not available or not any({{...}} for key in available)` made a
placeholder-free text unrenderable, which is *why* the only shape the ack could ever take was
`Gracias {{nombre}}. ` — fixed so a plain phrase renders; (3) `059` rewrites the stored override only
when it equals the old default. Verified: `pytest tests/unit/test_capture_validation.py
tests/unit/test_capture_phrasing.py tests/unit/test_reply_texts.py` → 65 passed;
`bash scripts/test.sh quick` → exit 0; `bash scripts/test.sh db tests/integration/test_migrations.py`
→ 38 passed, including two new tests that prove 059 rewrites the old default, keeps the other keys in
the same JSON, and leaves a panel-edited text alone.

**L10** — A2–A5 delivered by `gentle-ai-worker` and committed as four units (`04b993c9`, `63b890ec`,
`9c63dc20`, `a15e0edb`). The writer's evidence was independent per unit, but parent review of the diff
found two defects that the delegated spec did not cover, both fixed before commit with four new failing
tests written first:

1. **The consent widen accepted questions and doubts.** With `_YES_WORDS` scanned anywhere in prose,
   `¿necesito autorización?` and `no se si autorizo` returned `True` — that is personal data stored
   without consent. Fixed by splitting the vocabulary: explicit first-person verbs inside a short
   sentence, bare affirmatives only when the whole message is just that, and a question or a doubt is
   never consent. `autorización` (a noun that appears in questions) was dropped from the allowlist.
2. **The catalogue match made a technical visit preventive.** `Visita técnica` is the generic repair
   visit; matching the whole catalogue meant "necesito una visita tecnica, mi caldera no enciende"
   skipped the fault question and the case would reach a technician with no symptom. Fixed by
   narrowing the catalogue to services whose own name says preventive.

Verified after the fixes: `pytest tests/unit/test_capture_consent.py tests/unit/test_capture_validation.py`
→ 33 passed; `bash scripts/test.sh quick` → exit 0; `bash scripts/test.sh db tests/integration/test_handoff.py
tests/integration/test_out_of_hours_and_farewell.py tests/integration/test_price_answers.py` → exit 0,
64 passed. The `sio` decision stands as the writer reported: a typo that is not an allowlisted word
stays unclear and gets one confirmation instead of being guessed.

**L14** — B5 done. The cause was not a missing route: `_dispatch` already sent
`reagendar_visita` to `manage`. It was the CI-2 rule that folds cancel/reschedule into
the pending capture field while mid-capture, which is exactly the state production #23 was in. The
two intents now win over the pending field, and the field itself is untouched so the agenda resumes on
the next message. `tests/unit/test_routing_table.py` had the old rule pinned
(`test_mid_capture_non_retrieval_is_pending_field_answer` parametrized over both intents); it now
covers `unknown`/`calefont` and a new test pins the manage route. Verified:
`pytest tests/unit/test_routing_table.py` → 44 passed; `bash scripts/test.sh quick` → exit 0;
`bash scripts/test.sh db tests/integration/test_chat_capture.py tests/integration/test_chat_booking.py
tests/integration/test_chat_manage.py` → exit 0.

**L13** — B4 done. RED reproduced the production prompt verbatim: the state carried
`{'service': 'Visita técnica', 'label': '28/10/2026 a las 21:42', 'status': 'booked'}` for a visit that
had already started. `from_db` now filters `starts_at > now`. Verified: `bash scripts/test.sh db
tests/integration/test_chat_state.py` → exit 0; `bash scripts/test.sh db tests/integration/test_chat_booking.py
tests/integration/test_handoff.py` → exit 0; `bash scripts/test.sh quick` → exit 0.

**L12** — B3 done (`4871dc62`). RED reproduced the loop on the harness: the same three-slot page came
back verbatim and the conversation never left `state=bot`. Two changes: `_new_offer` takes
`unchanged_against` and refuses to persist a page identical to the one on screen, and the rebuild path
carries `attempts + 1` instead of restarting at zero, so `MAX_INVALID_REPLIES` is finally reachable and
the second unservable preference hands off with `booking_unclear` (the reply the generic handoff text
provides, since no reply key invented here). A first attempt placed `attempts` after its use and the
integration run caught an `UnboundLocalError` across three tests, which is exactly why the DB tier runs
this file: the unit tier stubs the session and never enters `booking()`.

Verified: `bash scripts/test.sh db tests/integration/test_chat_booking.py` → exit 0 (all 24 cases,
including the six pre-existing window/offer cases); `bash scripts/test.sh quick` → exit 0;
`bash scripts/test.sh db tests/integration/test_chat_capture.py tests/integration/test_handoff.py` →
exit 0.

**L11** — owner decisions, verbatim: `1. push y abre prs. el merge lo guardamos para despues.` and
`2. c1. salto en silencio al bookign con el consentimiento ya dado.`

Consequences:

- **Chained delivery.** ~1000 authored lines do not fit one reviewable PR, so the branch is split into
  three stacked PRs, base chain `main ← odd/chatbot-realismo-ack ← odd/chatbot-realismo-agenda-window ←
  odd/chatbot-realismo-conversacional`: **#738** (spec + A1), **#740** (B1 + B2), **#741** (A2–A5).
  Merge stays the owner's decision.
- **C1 delivered as the consent half only** (`faaed3dc`). Owner chose the silent skip: when
  `customers.consent_status` is true the question is not asked again, the flow goes straight to booking,
  and `captured["_consent_previously_granted"]` records that nobody was asked in this conversation. The
  ficha write moved with it, otherwise booking would drop the address the customer just gave. The data
  half of S3 (reusing name/comuna/email/address from the record) stays open on L5.2 — an old address
  sending a technician to the wrong place is a worse failure than one extra question.

**L5** — open product decisions (owner):
1. Consent already given: silent skip to booking, or a short confirmation (`¿mantengo los datos de tu
   última visita?`), and does a "no" withdraw consent globally or only for this visit?2. TTL for stored customer data before it is offered back (e.g. 90 days), so an old address is not
   reused as if it were current.
3. Evidence question when the customer already sent a photo earlier in the conversation.
4. Price in the out-of-coverage reply: never, or only when the customer asked for a price.
5. Customer name in the acknowledgement: once per conversation, or never.

**L7** — delivery strategy and slice boundary (411 authored lines at `8536f71f`). Slice 1 = the ODD
document + A1 (`f7a6162b`). Slice 2 = A2–A5, slice 3 = B1–B5, slice 4 = C3/C4/C2, slice 5 = C1 once
L5.1 is decided. Each slice stays reviewable on its own, so the PR can be chained without rewriting
history. Nothing is pushed: push, PR and merge stay the owner's decision.

**L8** — B1 + B2 done (`0a7914cd`), landed ahead of the A2–A5 commit because `slot_window.py` is
outside that unit's surfaces. RED observed for all six cases (four afternoon phrasings from
production #23 turns 304/306/308/310, plus `3 de nov` and the month table); the boundary cases
`al mediodía` and `si, cualquier dia despues de las 6` stay unparsed, which is the existing rule, not
an oversight: one names an exact hour, the other would empty a 09:00–18:00 agenda. Verified:
`pytest tests/unit/test_slot_window.py tests/unit/test_booking.py tests/unit/test_scheduling_unit.py`
→ 42 passed; `bash scripts/test.sh quick` → exit 0. One test expectation of my own was wrong on the
first run (year rollover: with today 2026-10-29, `nov` and `dic` resolve inside 2026, not 2027) and
was corrected against `_next_month_day`, not worked around.

**L9** — B3 design note before coding it: carrying `attempts` across a rebuilt offer is not enough on
its own. The rebuilt offer has to be compared against what the customer already sees, and when it is
the same page the node must answer with an existing catalogue text (the loop cannot invent a new
reply key while `app/services/settings.py` is being edited by another unit, and a new key needs panel
validation anyway). Preferred: count it as an invalid attempt and let `MAX_INVALID_REPLIES` hand off
with `handoff_booking_unavailable`; that text already tells the customer a human will coordinate.

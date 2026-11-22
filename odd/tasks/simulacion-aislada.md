# simulacion-aislada

A tool that simulates conversations must not leave anything an operator can act on. Measured on
production (`v2026.11.13`, 2026-11-21 17:55Z): two simulations created a real customer, two
conversations, twelve messages, eight events and **two open cases** in the operational queue, and the
daily summary counts open cases.

Branch `odd/simulacion-aislada`. Owner decision (L1): explicit marker plus an environment guard.

## What exists today

`app/services/chat_simulation.py` states its own isolation rule: never stamp `last_message_at`, because
the panel's active-conversation query requires it (`app/panel/api/routes/conversations.py:224,275`). That
works for the inbox and for nothing else. `cases.list_open_cases` (`app/services/cases.py:241`) joins
`Case` with `Customer` and filters only on the case being open, so the simulated cases are listed; and
`app/ops/daily_summary.py:18` counts them for the 07:00 summary.

Measured rows from the incident, for the record and for the cleanup cut:

```
customers             id 5    phone_e164 +56900000000
conversations         id 43, 44        last_message_at NULL
messages              id 682-693
conversation_events   id 355-362
cases                 id 35, 36        status abierto
```

## Specs

### S1 — A simulation marks what it writes

A conversation a simulation drives, and any case that conversation opens, are persist-flagged as
simulated at write time. The flag is additive and defaults to false, so every existing row and every
real conversation keeps today's meaning.

Implementation constraint: the graph nodes open their own sessions and commit
(documented in `odd/tasks/asistente-operador.md` L8), so the marker cannot ride a caller transaction. It
must be set on the conversation before the graph runs and carried to the case the graph creates.

### S2 — Operational reads exclude what is simulated

Every surface an operator acts on ignores simulated rows: the open-case list, the panel conversation
list, the daily summary's counts, and the customer-facing counters the summary reports. Listing, not
hiding: a surface that *reports* simulation (the assistant's own tool result) keeps seeing them, and the
exclusion must be a single shared predicate rather than a condition copied per call site.

### S3 — The tool refuses unless the environment enables it

`chatbot.simulate` runs only when a setting explicitly enables it, default **disabled**, so production
refuses with a reason the operator can read instead of writing rows. The refusal must be a normal tool
error, not an exception that breaks the turn.

## Tasks

| ID | Spec | Route | Commit |
| --- | --- | --- | --- |
| T1 | S1 | inline | migration + models + write path |
| T2 | S2 | inline | shared predicate and the four reads |
| T3 | S3 | inline | setting + refusal |
| T4 | — | inline | tests, `quick`, `full`, PR |

## Log

**L1 (owner, verbatim)** — `1. Marca explicita + guarda` (the option: an additive `simulated` column
filtered in cases, inbox and summary, plus an environment setting that disables the tool), chosen when
asked how to isolate `chatbot.simulate`.

# pregunta-gana

A customer who asks for a time gets a time answered. Measured on production (`v2026.11.13`,
2026-11-21 17:55Z) inside two simulated conversations: both asked for availability and both read a
capture question back.

Branch `odd/pregunta-gana`.

## Specs

### S1 — A question outranks capture, with or without a pending field

A turn that asks something is answered before any capture step, whether or not a capture batch is
already pending. `_dispatch` today only lets `question` win inside the `mid_capture` block; with a
visit intent and no pending field the turn becomes a plain capture entry and the question is dropped
without a trace.

Measured, production conversation 43 turn 2:

> cliente: `¿Qué días tienen disponibles?`
> bot: `Entiendo. Cuéntame qué pasa con la caldera: ¿no enciende, no calienta o muestra algún código de error?`

The only event recorded for that turn was `classified · intent:solicitar_visita`: no `kb_retrieved`,
no `kb_miss`, no handoff. The question was never sent anywhere.

Pure decision as measured today (`app/chat/nodes/orchestrate.py`):

```
_dispatch("solicitar_visita", mid_capture=False, question=True) -> {"next_step": "capture"}
_dispatch("solicitar_visita", mid_capture=True,  question=True) -> research + capture_paused
```

After the fix the first line must route to the answer path exactly like the second, and the capture
agenda must resume on the next turn (`_pending` survives; `_after_research_triage` already handles the
resume, including its refusal to append a second question).

The escape hatches that must keep their precedence: `change_request` (an explicit reschedule outranks a
question), emergency/persona/injection escalations, and `quote_question`.

### S2 — Asking for a time is recognised without naming a weekday

The configured availability answer fires from an exact term list. A customer asking for availability
in the ordinary way does not hit it.

Measured today (`app/chat/nodes/respond.py:87`):

```python
_SCHEDULE_TERMS = ("sabado", "domingo", "festivo", "horario", "atienden", "cobertura")

asks_about_schedule("¿atienden los sábados?")               -> True
asks_about_schedule("¿Qué días tienen disponibles?")        -> False
asks_about_schedule("¿Tienen hora disponible esta semana?") -> False
```

`disponib*`, `días`, `hora`, `semana` and `agenda` must count as asking about availability. The
negative guard matters as much as the fix: a message that carries content ("tengo la caldera mala y
no sé si el jueves") must not be read as a pure schedule question.

Measured second case, production conversation 44 turn 3:

> cliente: `¿Tienen hora disponible esta semana?`
> bot: `Entiendo. Cuéntame qué pasa con la caldera: ¿no enciende, no calienta o muestra algún código de error?`

### S3 — The corpus catches this case

`real-solo-sabados` passed with the defect present, so the corpus does not measure it today. Add one
scenario (or one assertion on an existing one) whose expectation fails when an availability question is
answered with a capture question instead of the availability answer.

## Tasks

| ID | Spec | Route | Commit |
| --- | --- | --- | --- |
| T1 | S1 | inline | question outranks capture without a pending field |
| T2 | S2 | inline | agenda vocabulary + negative guard |
| T3 | S3 | inline | corpus scenario that fails on the measured reply |
| T4 | — | inline | `--only` measurement of the target scenarios, 3 judge reps |
| T5 | — | inline | `quick`, `full`, PR |

## Log

**L1 (owner, verbatim)** — `si pero el error no esta solo en que no es invisible la prueba si no que
ignoro una solicitud de agendamiento. en ambos pregunta para cuando tiene disponible o algo asi. y el
chatbot respondio ignorando la pregunta y con una respuestaque rompe la coherencia de la converascion`

**L2 (owner, verbatim)** — `si camos en ese orden`: first this cut, then the isolation of
`chatbot.simulate`, then the cleanup of the simulated production rows.

**L3 (measurement, first run)** — `--only` the seven affected scenarios: 5/7. `real-disponibilidad-dias`
scored 0.00 with **G6** (no anchor found): the turn no longer fell into `capture` — it went to the answer
path — but the answer was the KB-miss offer. `real-claudio-caldera-valvula` stayed 0.00 on the water-valve
path this cut does not touch.

**L4 (finding: the harness measured a product without production's configuration)** — the reason the new
scenario could not find its anchor is not the fix:

```
hours.schedule in production:  [{"days": [1..7], "open": "00:00", "close": "23:59"}]   (24/7)
hours.schedule in the eval DB:  []
```

With no window configured, `configured_answers.hours_reply` returns `None`, so the deterministic
availability answer cannot exist in the corpus at all. The corpus had been measuring a product without the
configuration production runs with — which is a worse blind spot than a red scenario, because it makes a
product that behaves differently look green. Setting `hours.schedule` to production's value in the eval DB
and re-measuring the same seven: **7/7**, and the new scenario answers
«Las visitas se agendan según la disponibilidad de los técnicos.» (judge 2.17, no hard fail). The others
held: `real-solo-sabados` 2.50, `real-dato-mas-pregunta` 3.33, `real-cobertura-condominio` 3.17,
`simple-cobertura-comuna` 2.33, `simple-horario-sabado` 2.33, `real-reagenda-mantencion` 3.17.

**Open follow-up, deliberately not done here:** the evaluator does not assert configuration parity with
production. Seeding settings from inside `conv_eval` would silently move every baseline, so it belongs in a
cut of its own with its own re-baseline, not in this one.

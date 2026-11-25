# calefont-answer-first — contestar lo que preguntó, después capturar

Pendiente 4 del handoff post-`v2026.11.19` (`complejo-agendar-calefont`). El flujo pide todos los
datos antes de contestar cobertura y precio; el juez lo castiga con un hard fail y la conversación
termina escalando.

## Specs

Aprobadas por el owner el 2026-11-25, verbatim:

- **S1** — «Contestar y después capturar.» · «Contestar cobertura y precio en el primer turno en que
  el cliente pregunta, y capturar después.»
- **S2** — Lo que el cliente ya entregó no se vuelve a preguntar: los campos capturados antes de la
  respuesta sobreviven al turno que contesta y la lista de pendientes no los repite.
- **S3** — Una sola pregunta por mensaje: la respuesta y la pregunta de captura no viajan juntas. La
  regla ya existe en `_after_research_triage` (no reanuda la captura si la respuesta termina en «?»).
- **S4** — Un turno de captura en curso sin pregunta explícita sigue yendo a captura: la apertura
  nueva del cliente es lo único que abre el camino de respuesta.

## Tasks

- T1 → S1, S2, S3, S4 · RED: la ruta del primer turno, la pausa, la reanudación y los dos guards · `-`
- T2 → S1, S2 · GREEN: la condición de apertura y `capture_paused` en el turno sin pendientes · `-`
- T3 → S1 · el precio alcanzable desde ese turno, reusando el helper existente · `-`
- T4 → S1-S4 · verificación (`focused`, `quick`, `shape`, y los escenarios vecinos) y cierre · `-`

## Log

L1 — pedido del owner, verbatim (pendiente 4 del handoff, más la decisión):

> 4. complejo-agendar-calefont: el flujo pide todos los datos antes de contestar cobertura y precio; el
> juez lo castiga y termina escalando.

> Contestar y después capturar

L2 — evidencia medida (24b, `odd/evals/conv-eval-rebaseline-2026-11-24b-conversaciones.md:97-121`):
cinco turnos, juez 0.00, **todos los gates declarados verdes** (G1, G4, G6, G8). El primer turno del
cliente —«hola, necesito mantener mi calefont, vivo en ñuñoa»— no recibe ni cobertura ni precio: recibe
una pregunta por el equipo, repetida casi literal en los cuatro turnos siguientes. El hard fail del
juez nombra exactamente «Pedir todos los datos antes de responder lo que el cliente preguntó».

L3 — dónde se decide hoy: `orchestrate` manda a captura en `app/chat/nodes/orchestrate.py:175-176`
(`if intent in CAPTURE_INTENTS`), antes de mirar el camino de respuesta, porque `_is_question` es
falso para «vivo en ñuñoa». La cobertura existe (`configured_answers.coverage_reply`) pero devuelve
`None` cuando el cliente sólo declara residencia; el precio existe (`tariff_price_reply`) pero está
atado a `intent == "valores"` y vive en `respond`.

L4 — alcance: se abre el camino de respuesta en el turno **sin pendientes** y se reanuda la captura en
el mismo turno, sin arista nueva (`orchestrate → research_triage → capture` ya existe). Quedan fuera
de alcance: `agent/prompts/*` (superficie de forma), el catálogo de mensajes y cualquier cambio de KB.

L5 — riesgo declarado: `simpre-horario-sabado`, `simple-dia-especifico`, `real-solo-sabados` y
`real-multi-equipo-un-mensaje` abren con comuna o precio y podrían cambiar de ruta, y
`super-burst-contradiccion` es media captura y no debe ganar una segunda respuesta. La verificación
de T4 los mira a mano.

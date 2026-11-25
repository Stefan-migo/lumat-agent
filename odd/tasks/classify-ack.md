# classify-ack — «Eso!» después del turno del bot no es incomprensión

Pendiente 3 del handoff post-`v2026.11.19`. El escenario `real-varias-reparaciones` falla G4
(`events_forbidden: [unknown_intent]`) en un «Eso!» que responde al turno anterior del bot.

## Specs

- **S1** — «real-varias-reparaciones: G4 por unknown_intent en un «Eso!» después de un rechazo de
  alcance. Es del clasificador, no de la KB.»
- **S2** — Un acuse breve y auto-contenido del cliente se enruta al camino de smalltalk que ya
  existe y **no** carga `unknown_intent`. Medido en 24b: turno 2 del escenario, «Eso!», respuesta
  `clarification` («Disculpa, no te entendí bien…»), evento `unknown_intent`
  (`odd/evals/conv-eval-rebaseline-2026-11-24b-conversaciones.md:561-565`).
- **S3** — El detector no dispara cuando hay una captura, una oferta de agenda o una oferta de
  gestión en curso: ahí un «sí», un «dale» o un «listo» es una respuesta, no un acuse. Tampoco
  dispara sobre un pedido real: «eso no funciona, necesito una visita» sigue siendo consulta.
- **S4** — La declaración del corpus es legítima y no se toca: el corpus conservó los dos lados del
  intercambio (`scripts/conv_eval_corpus.yaml:788-800`), así que el evento prohibido es un error
  real del bot, no un artefacto del arnés.

## Tasks

- T1 → S2, S3 · RED: los tests del acuse y de los cuatro casos en que no debe disparar · `-`
- T2 → S2, S3 · GREEN: el detector determinista y su punto de enrutamiento · `-`
- T3 → S1-S4 · verificación y cierre del corte · `-`

## Log

L1 — pedido del owner, verbatim (pendiente 3 del handoff, más la decisión):

> 3. real-varias-reparaciones: G4 por unknown_intent en un «Eso!» después de un rechazo de alcance. Es
> del clasificador, no de la KB.

> vamos con el orden sugerido

L2 — diagnóstico read-only previo (agente explorador, 2026-11-25): el turno pasa por
`receive.is_confusion_only`, `is_social_only`, `is_greeting_only` y `closure_gate.is_farewell` sin
coincidir; el modelo devuelve `unknown`; `_RESCUE_RULES` no encuentra vocabulario de negocio; y
`_record_unknown_intent` (`app/chat/nodes/classify_intent.py:368`) registra el evento. «eso» fue
quitado a propósito de `CLOSING_TOKENS`, así que no es un cierre: es un acuse.

L3 — alcance: se implementa el camino determinista (F1), no la regla de prompt (F2) ni una regla
nueva en `_RESCUE_RULES` (F3): `_RESCUE_RULES` escanea todo el texto con `finditer`, así que una
regla `eso` rescataría también «eso no funciona, necesito una visita».

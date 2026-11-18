# La captura reconoce que el cliente pidió una evaluación y una cotización

Rama `fix/captura-evaluacion-cotizacion` · worktree `../lumat-agent-odd-evals-gates`

Es el residual 8 de #833, medido dos veces en su propio head (`113dc11b3`, corridas `gates-42-final` y
`gates-42-final2`, **41/42** las dos). El turno del cliente que pide «una nueva evaluación y cotización»
se lo come la captura: el bot sigue con su cuestionario y nunca nombra lo que le pidieron.

Riesgo: **medio**. Se toca el texto que el cliente lee en medio de la captura y una clave nueva de
`reply.texts`, que el panel expone y `validate_reply_texts` valida. No se toca la clasificación, ni
`respond`, ni la KB, ni el protocolo de emergencia.

## Specs

- **S1 — Una petición declarada se nombra una vez.** Cuando el cliente declara que quiere una evaluación,
  una revisión o una cotización —«me gustaría tener una nueva evaluación y cotización», verbatim del
  turno 2 de `real-maria-jesus-evaluacion-caldera`—, la primera respuesta posterior de la captura que no
  esté ya diciendo la ack de mantención contiene el texto configurado y la nombra. Se dice **una vez**:
  la marca de dicho (`_quote_acked`) impide repetirlo en cada pregunta de campo, igual que la ack de
  mantención. El orden entre las dos acks es preventiva → evaluación: la preventiva conserva el turno que
  ya tenía, y la de evaluación espera al siguiente en vez de reemplazarla.
- **S2 — Una pregunta de precio no es un pedido.** «¿Cuánto cuesta la evaluación?» pregunta, no pide: no
  dispara la ack, porque la respuesta de precio es de `respond` (`QUOTE_REQUIRED_REPLY`,
  `app/chat/nodes/respond.py:203`). Tampoco la dispara un rechazo ni la ausencia del presupuesto —«no
  necesito cotización», «no tengo presupuesto ahora»—, que dicen lo contrario de lo que la ack afirmaría.
  El filtro de preguntas es el mismo `_looks_like_question` que ya usa la detección preventiva, aplicado
  sólo al texto que no es pregunta.
- **S3 — El texto es configurable y no inventa slots.** Clave nueva `capture_quote_ack` en
  `REPLY_TEXT_DEFAULTS` con `frozenset()` de slots: el texto no depende de datos del caso, así que no
  agrega un `{{…}}` que algún call site no sepa llenar. `validate_reply_texts` la exige como toda clave,
  y `tests/unit/test_reply_texts.py` la lista en `EXPECTED_KEYS`.
- **S4 — Un fallo posterior no revierte la petición.** A diferencia de la ack de mantención, que cae
  cuando el cliente pasa a reportar una falla, la petición de evaluación **sobrevive** al síntoma: el
  cliente del escenario sigue queriendo la evaluación después de decir «ahora está en rojo otra vez».
  La ack de evaluación y la de mantención conviven, cada una dicha una vez.
- **S5 — Fuera de alcance.** No se toca el guard de gas, el alcance de artefactos excluidos, `respond`,
  la KB, la clasificación, ni ninguna expectativa del corpus. El gate G6 no se relaja: se cumple.

## Tasks

| ID | Qué | Specs | Commit |
|---|---|---|---|
| T1 | Pruebas de integración y de unidad sobre la ack: la declaración se nombra una vez y no se repite | S1, S4 | `fix(chat): acknowledge a request for an evaluation and a quote` |
| T2 | Detección y ack en `capture.py`, con el mismo patrón preventivo y sin caer ante un fallo | S1, S4 | junto a T1 |
| T3 | Texto configurable `capture_quote_ack` en `settings.py` y en el catálogo de `reply.texts` | S3 | junto a T1 |
| T4 | Control negativo de S2: ni la pregunta de precio ni el presupuesto ausente disparan la ack | S2 | junto a T1 |
| T5 | Re-medir el escenario y comprobar que no mueve otros | S5 | `docs(evals): …` |

## Evidencia

| Qué | Evidencia |
|---|---|
| T1–T4 | `00d870b41` — `fix(chat): acknowledge a request for an evaluation and a quote` |
| RED | `bash scripts/test.sh focused tests/integration/test_chat_harness.py` falla en las tres pruebas nuevas; `scripts/test.sh unit` falla en el catálogo de `reply.texts` |
| Mutación de los controles negativos | quitar el filtro de preguntas o el guard de presupuesto ausente hace fallar su prueba: no son vacuas |
| Antes del arreglo, con el defecto ya dentro | `captura-eval` (4/4 con gates, pero el turno 2 sólo pedía el equipo y la frase quedó marcada sin enviarse) |
| Después del arreglo, árbol sucio | `captura-eval-2` (1/1, la frase sale en el turno 5) |
| Después del arreglo, árbol limpio | `captura-eval-limpio`, sello `00d870b41`, **4/4, cero gates fallidos**, la ack en el turno 5 |

## Log

**L1 (pedido del owner, 2026-11-18, handoff).** Verbatim:

> «La captura que ignora «evaluación y cotización» (límite 8 de #833): mismo patrón que la ack de
> mantención, en app/chat/nodes/capture.py.»

**L2 (residual 8 de #833, verbatim del cuerpo de la PR).** Es la definición del defecto que esta feature
cierra:

> «**8. Capture does not acknowledge a request for an evaluation or a quote.** When the classifier routes
> the first turn to `capture`, the customer's "me gustaría tener una nueva evaluación y cotización" is
> never named: the bot goes straight to "¿Qué equipo es?" and "¿En qué comuna te encuentras?". Gate G6 of
> `real-maria-jesus-evaluacion-caldera` fails on the missing anchor in exactly those runs.»

**L3 (evidencia, 2026-11-18).** Corrida `gates-42-final2` (`odd/evals/conv-eval-gates-42-final2.md`),
sello `113dc11b3`, árbol limpio, **41/42**: el único fallo es G6 de
`real-maria-jesus-evaluacion-caldera` («ninguna respuesta contiene: evaluación, evaluacion, revis») y el
transcript muestra el turno 2 contestado con `¿En qué comuna te encuentras?`. El sidecar JSON de esa
corrida no guarda evidencia por turno (`evidence: {}`), así que la prueba es el transcript.

**L4 (decisión de diseño, 2026-11-18).** Se reusa el patrón preventivo (`_is_preventive_request` +
`capture_preventive_ack` + dedup por texto renderizado) en vez de inventar un mecanismo nuevo, y la ack
de evaluación **no** se retira cuando aparece una falla: esa caída existe en la preventiva porque el
cliente que pasa a reportar un problema ya cambió de pedido, y acá no cambia.

**L6 (defecto propio encontrado por la medición, no por el test, 2026-11-18).** La primera versión
marcaba `_quote_acked` apenas calculaba el texto, aunque la ack preventiva se llevara ese turno: la
frase nunca salía del proceso. El test de integración no lo veía porque, en su flujo, la ack
preventiva ya estaba dicha cuando llegaba la declaración. Lo mostró la base: en la conversación `299`
de la corrida `captura-eval`, `_quote_acked` estaba escrito y ningún mensaje saliente contenía la
frase. El arreglo separa la decisión en `_pick_ack`, que marca sólo el texto que se devuelve, y
`tests/unit/test_capture_quote_ack.py` la fija sin base ni modelo. La re-medición (`captura-eval-2`)
muestra la frase en el turno 5: «Entiendo, quieres una nueva evaluación con cotización. ¿En qué comuna
te encuentras?».

**L7 (medición de cierre, 2026-11-18).** `captura-eval-limpio` sobre `00d870b41`, árbol limpio: los
cuatro escenarios que tocan evaluación o cotización pasan, cero gates fallidos. La frase se lee, no
sólo se marca: «Entiendo, quieres una nueva evaluación con cotización. ¿En qué comuna te encuentras?».
El escenario semilla también pasaba antes del arreglo, pero por el «revisar» del turno 1 y no por
nombrar el pedido: el pase viejo era varianza de ruteo, el de ahora es la conducta que la spec pide.

**L5 (defecto del instrumento encontrado al medir, 2026-11-18).** `scripts/conv_eval.py --reset` revienta
con `psycopg.errors.FeatureNotSupported: cannot truncate a table referenced in a foreign key constraint`:
`_RESET_TABLES` (`scripts/conv_eval.py:1158`) no incluye `commitments`, que referencia `messages`. No se
arregla acá; la corrida del titular se hizo sin `--reset`, como las anteriores.

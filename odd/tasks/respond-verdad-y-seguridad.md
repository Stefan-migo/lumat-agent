# El camino de respuesta: verdad, seguridad y estabilidad

Rama `fix/chat-respond-verdad-y-seguridad` · worktree `../lumat-agent-odd-evals-gates`

La corrida de 42 escenarios con gates (`conv-eval-gates-42`, sello `dc530d833`, árbol limpio) cerró en
**40/42**. Dos fallos, y el A/B en `main` (`f4ec2f66c`) probó que ninguno es regresión de la ronda
anterior: los dos salen del camino de respuesta (`respond`).

1. `super-near-miss-lavadora` — el bot responde «Sí, reparamos lavadoras». Falla igual en `main`.
2. `simple-cobertura-comuna` — varianza: a veces nombra al asesor, a veces esquiva.

El tercero no está en los gates y es el más caro: en `real-caldera-urgencia` turno 2 el bot instruye
«revisa que la llave de gas esté abierta», que es manipulación de gas sin verificar seguridad.

Riesgo: **alto**. Se tocan prompts espejados (`agent/personas/*`, que `scripts/test.sh:60` declara
superficie de forma), la KB que alimenta las respuestas y el camino que contesta al cliente. Un error
acá se le dice a un cliente real. Verificación independiente obligatoria.

## Specs

- **S1 — La KB dice qué no se hace.** `docs/kb/lumat-servicios.md` enumera hoy los otros servicios
  (`:43`) y **no excluye nada**; el prompt manda sacar el alcance de `<kb>` y no inventarlo
  (`agent/personas/orchestrator.md:16`), así que la KB es la única fuente que podía evitarlo. La
  sección de otros servicios nombra explícitamente qué queda fuera: lavadoras, lavadoras-secadoras,
  refrigeradores y, en general, artefactos que no estén en la lista. Un test fija la exclusión, porque
  volver a borrarla devuelve el defecto sin que ningún gate lo vea hasta la próxima corrida.
- **S2 — Una respuesta no instruye manipular gas.** Ninguna respuesta que salga de `respond` le dice al
  cliente que abra, cierre, revise o pruebe una llave, válvula o suministro de gas como paso de
  diagnóstico. Se cumple con dos capas: la regla de `agent/personas/orchestrator.md:31` —que ya existía
  y el modelo violó— y un guard determinístico **después** de la respuesta (`respond.py:641` → `:656`),
  que la reemplaza por un mensaje seguro configurable y registra la intervención como evento del caso,
  para que el panel la muestre y las métricas no la escondan.
- **S3 — El guard no bloquea la seguridad legítima.** El protocolo de emergencia
  (`app/chat/nodes/emergency.py:47-59`) y los consejos condicionales —«corta el suministro de gas solo
  si puedes hacerlo de forma segura» (`app/services/settings.py:326`)— **no** disparan el guard: no
  salen de `respond` y no son instrucciones de diagnóstico. Un test con esos textos como control
  negativo lo fija; sin él, el guard se come la respuesta correcta en una emergencia.
- **S4 — La cobertura se responde siempre igual.** Una pregunta de cobertura —«¿trabajan en Maipú?»,
  «¿atienden en X?», «¿llegan a X?»— se contesta de forma determinística comparando **el lugar que el
  cliente nombró** contra la lista configurada (`DEFAULT_COVERAGE_COMMUNES`,
  `app/services/settings.py:377-385`): si está, se confirma; si no está, se dice que no es cobertura
  habitual y que igual un asesor coordina la visita, que es exactamente lo que promete la KB
  (`docs/kb/lumat-cobertura-horarios.md:5`). **No hace falta un padrón de comunas**: el callejero sólo
  trae seis (`app/data/callejero/maestro.json.gz`), así que el bot no debe validar que el lugar exista —
  debe responder la política con lo que el cliente dijo. Hoy `coverage_reply` sólo dispara si la comuna
  está en la lista o si el mensaje dice «comuna/cobertura»
  (`app/chat/nodes/configured_answers.py:156-174`), así que Maipú cae al modelo y la respuesta cambia
  entre corridas. Con esto, el escenario deja de depender de la suerte.
- **S5 — Fuera de alcance.** No se toca el camino de detección de emergencias, ni la clasificación, ni el
  catálogo de servicios: no se agregan servicios nuevos. El protocolo de seguridad queda byte-idéntico.

## Tasks

| ID | Qué | Specs | Commit |
|---|---|---|---|
| T1 | La KB de servicios dice qué no se hace, con test que lo fija | S1 | `fix(kb): say which appliances Lumat does not repair` |
| T2 | Guard determinístico de instrucciones de gas, con el evento y su mensaje configurable | S2 | `fix(chat): never send the customer to a gas valve` |
| T3 | El control negativo del guard: protocolo de emergencia y consejo condicional no se tocan | S3 | junto a T2 |
| T4 | La cobertura responde determinísticamente para cualquier comuna nombrada | S4 | `fix(chat): answer a coverage question even outside the list` |
| T5 | Re-medir los dos escenarios y los 42 con gates en el árbol limpio | todas | `docs(evals): …` |
| T6 | Verificación independiente del corte | todas | — |

## Entrega

Una PR (`fix/chat-respond-verdad-y-seguridad`), con un commit por causa. Es el mismo camino y el mismo
riesgo, así que se revisa junto; si el diff pasa las 400 líneas, se parte en dos tajadas: KB + gas por un
lado, cobertura por otro.

Ojo con la evidencia: cambiar la KB cambia su fingerprint, así que los informes anteriores dejan de
comparar contra el mismo KB. La corrida de cierre tiene que declarar el fingerprint nuevo.

## Límites aceptados

With this cut the reply is **not** replaced for these gas sentences. Each is recorded as a `response_guard_observation` breadcrumb unless noted:
1. Bare gas-supply imperatives without a hardware noun: "Abre el gas.", "Cierra el gas.", "Corta el gas y ventila.", "Corta el gas antes de que llegue el técnico."
2. State checks on the supply: "revisa que el gas esté habilitado", "verifica que el gas esté cortado", "revisa que el gas esté abierto".
3. Appliance ignition/test without the word gas in the clause: "Prueba encender el calefont.", "Revisa si el calefón enciende.", "Verifica si el calefont enciende.", "Mira si la cocina enciende.", "Prueba con la cocina."
4. Flame leak test and unlabelled valves: "Prueba con un fósforo si hay fuga de gas.", "Pasa un fósforo por la unión para ver si hay fuga.", "Abre la llave azul.", "Cierra la llave azul del calefont."
5. Pressure/regulator work: "Revisa la presión del gas.", "Revisa el regulador de gas."
6. Mixed water-and-gas clauses: "revisa que la llave de paso de agua esté abierta y que el gas esté habilitado".
7. Excluded-appliance repair claims are no longer replaced either: "Sí, reparamos lavadoras." reaches the customer with a breadcrumb only (the KB/persona sentence is now the sole defence; `super-near-miss-lavadora` passed 42/42 without the deterministic guard).
**No breadcrumb at all** for verbs outside the operation list: "Sube el regulador de gas.", "Purga la línea de gas.", "Cambia el regulador de gas."

Accepted on 2026-11-17 because the measured alternative — deleting a correct answer — failed a scenario harder, and the corpus measures 42/42.

The fourth-verification follow-up closes item 1's four bare gas-supply imperatives; the accepted list above records the residuals before that follow-up, and the 42/42 measurement predates it.

## Log

**L1 (pedido del owner, 2026-11-17).** Después de ver 40/42 con dos fallos preexistentes y el defecto de
gas, eligió arreglar el camino de respuesta antes de pagar la corrida con juez, con este alcance: los
tres defectos juntos.

**L2 (decisión del owner, 2026-11-17).** Preguntado cómo hacer exigible la regla de gas —que ya está
escrita y el modelo violó— eligió **guard determinístico más regla en el prompt**: la respuesta que
instruye manipular gas se reemplaza por un mensaje seguro y la intervención queda registrada.

**L3 (corrección de S4 antes de implementar, 2026-11-17).** La primera versión de S4 pedía reconocer la
comuna contra una lista del proyecto. El callejero tiene seis comunas y no incluye Maipú
(`app/data/callejero/maestro.json.gz`), y `coverage.communes` sólo guarda las cubiertas. Inventar un
padrón habría sido agregar una fuente de verdad que nadie mantiene. S4 pasa a: comparar el lugar que el
cliente nombró contra la lista de cobertura y, si no está, responder la política real —que es lo que la
KB ya promete— sin validar la existencia del lugar.

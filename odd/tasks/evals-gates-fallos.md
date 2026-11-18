# Los seis escenarios que reprueban gates

Rama `odd/evals-gates` · worktree `../lumat-agent-odd-evals-gates`

El corpus conversacional (`scripts/conv_eval_corpus.yaml`, 42 escenarios) cierra en **35/42** gates.
De los siete fallos del informe sellado en `69d9a12b7`, uno (`simple-dia-especifico`) ya se arregló en
PR #829. Quedan seis, que no comparten causa: son tres familias de defecto y una expectativa de corpus
mal calibrada.

Riesgo: **medio**, pero no uniforme. La captura decide qué se le pregunta al cliente en producción y
dos de estos casos meten al bot en un bucle de preguntas repetidas; el resto son clasificación y
eventos. Sin migraciones, sin cambios de contrato público.

## Specs

Cada spec cita el texto del cliente y la salida observada **verbatim**, del informe
`odd/evals/conv-eval-nojudge-main-conversaciones.md` (sello `69d9a12b7`).

- **S1 — Una mantención declarada no se pierde.** Ante el turno
  `Mantencion\nEsta funcionando bien la calefacción.\nQuiero mantencion`, alguna respuesta de la
  conversación menciona la mantención o el equipo (`mantenci`, `caldera`; gate G6 de
  `real-mantencion-caldera`). Hoy el bot contesta `¿En qué comuna te encuentras?` y el motivo declarado
  no aparece nunca.
- **S2 — La mantención pedida se nombra, y no se repite en cada pregunta.** La primera respuesta de la
  captura nombra el servicio que el cliente pidió (mantención de la caldera, del calefont, de la
  calefacción). La pregunta de captura puede repetirse —`MAX_ASKS_PER_FIELD = 2` es diseño
  (`app/chat/nodes/capture.py:83`)—, pero la ack no se repite palabra por palabra en cada campo, y un
  fallo reportado después la retira: un cliente que pasa de «quiero mantención» a «ahora no calienta»
  no puede seguir leyendo que quiere una mantención.
- **S3 — Una propuesta de horario no termina en un callejón sin salida.** Ante `es factible que pases
  tipo 14 horas?` (`real-dato-mas-pregunta`), el bot no responde `No tienes visitas próximas para
  reagendar.` Ese texto no sale de una tool: es `manage_no_visits` (`app/services/settings.py:132`),
  emitido por `_start_offer` cuando la consulta de visitas vuelve vacía (`app/chat/nodes/manage.py:55-75`),
  y `manage` sólo corre para `cancelar_visita`/`reagendar_visita`
  (`app/chat/nodes/orchestrate.py:102-121`). Un cliente sin visitas agendadas recibe ese callejón dos
  veces y su pregunta se pierde. El `unknown_intent` que el gate prohibía **no** entra en esta spec: lo
  escribe el turno 1 del propio guion (L7).
- **S4 — Un turno de media no es un fallo de comprensión (el defecto es del instrumento).** El turno
  `<video omitido>` de `real-claudio-caldera-valvula` no puede registrar `unknown_intent` (gate G4).
  El cerebro ya cumple: un mensaje de media con texto vacío no llega a clasificar
  (`app/chat/nodes/classify_intent.py:254-256`) y se acusa recibo con `EVIDENCE_ACK`
  (`app/chat/nodes/receive.py:29`, `:207-209`). Lo que miente es el corpus: `chat_harness.run_turn`
  persiste **todos** los turnos como `MessageType.TEXT` (`scripts/chat_harness.py:130-135`), así que
  `<video omitido>` llega como texto literal, `is_media_evidence` da `False`
  (`app/chat/nodes/handoff_gate.py:155-161`) y el turno clasifica. El arreglo es que el instrumento
  pueda enviar un turno de media, no relajar el gate.
- **S5 — Un dato rechazado se marca saltado.** Ante `no te voy a dar mi correo, con el telefono basta`
  (`complejo-no-quiere-email`), el correo queda como campo saltado y el flujo continúa. **Esto ya
  funciona y no se toca:** la frase está en `_SKIP_WORDS` (`app/chat/nodes/capture.py:120`) y en
  `_REFUSAL_FIELDS` (`:127-129`), y `capture()` la aplica en `:631-643`. La spec queda como invariante
  con su test: si mañana alguien rompe el rechazo, la prueba falla.
- **S6 — Un día declarado se registra.** Ante `si, cualquier dia despues de las 6`, la disponibilidad
  declarada se guarda como dato del caso. Hoy el turno se descarta y el bot vuelve a pedir la dirección
  que ya venía pidiendo: bucle.
- **S7 — Una pregunta de periodicidad es una consulta, no un valor (decisión del owner, L7).**
  `Corresponde hacerla??\nEs cada 6 meses??` (`real-precio-mantencion-ciclo`) se clasifica `consulta`,
  que es lo que la propia definición del clasificador le asigna («procedimientos, plazos […] mantención»,
  `agent/personas/classify.md:1`) y lo que el bot ya hace. `valores` es «precios y tarifas» y esa
  pregunta no lo es. El gate G2 se corrigió en el corpus; no se toca el clasificador.
- **S8 — `complejo-dos-temas` deja de exigir derivación (decisión del owner, L2).** La consulta de
  precio (`hola, cuanto cuesta el lavado de red?`) y la de garantía (`y eso cuanto de garantia tiene?`)
  se responden de la KB y el bot **puede** quedarse en `bot`. La expectativa pasa a `state_any:
  [bot, human]` sin `causes_required`. El gate que queda es `must_include_any` de garantía y los hard
  fails del escenario.
- **S9 — Fuera de alcance: el turno 2 de `real-caldera-urgencia`.** `revisa que la llave de gas esté
  abierta` es manipulación de gas sin verificar seguridad, es del camino `respond` y **no** se toca acá.
  Tampoco se toca el camino de emergencia, el borde humano ni el audio (S1-S10 de
  `emergencia-turno-siguiente.md`).
- **S10 — El instrumento no se ablanda.** Ningún gate se relaja por conveniencia: cada spec de arriba
  cambia comportamiento, salvo S8, que cambia una expectativa que el resto del corpus contradice
  (`real-precio-mantencion-ciclo` tiene como hard fail «Derivar sin intentar responder la consulta
  general»).

## Tasks

| ID | Qué | Specs | Entrega |
|---|---|---|---|
| T1 | `complejo-dos-temas` deja de exigir `human` + `persona`, con la razón escrita en el corpus | S8, S10 | PR 0 ✓ |
| T2 | El instrumento sabe mandar un turno de media: `msg_type` por turno en el corpus, el harness y el evaluador | S4 | PR 0 ✓ |
| T3 | Tres expectativas que el corpus contradecía: `consulta` en periodicidad, sin `unknown_intent` de fragmento, sin derivación forzada | S3, S5, S7 | PR 0 |
| T4 | La mantención declarada se reconoce y la respuesta la nombra; no se repite la pregunta sin nombrarla | S1, S2 | PR A |
| T5 | Una propuesta de horario no termina en `manage_no_visits`: si no hay visitas, deriva con causa | S3 | PR A |
| T6 | La pregunta de periodicidad se clasifica como valores | S7 | **dropped** — la expectativa estaba mal, no el bot |
| T7 | Re-medir los cuatro que quedan con gates en el árbol limpio, y anotar sello y resultado | todas | cierre |
| T8 | Verificación independiente del corte | todas | cierre |

## Entrega

Una PR por familia de causa, más una PR 0 para el instrumento:

| PR | Qué revisa el humano | Rama |
|---|---|---|
| 0 · instrumento | las líneas de `conv_eval_corpus.yaml` que mentían, el `msg_type` por turno del harness y por qué cada expectativa corregida contradicía al resto del corpus | `test/evals-instrumento-honesto` |
| A · chat | los dos defectos de producto: la mantención que se reconoce y no se nombra, y el callejón de `manage` cuando el cliente no tiene visitas | `fix/chat-mantencion-y-agenda-sin-visitas` |

Cada PR se mide con los escenarios que toca, más un barrido de gates del corpus completo al cerrar la
última, para no mover ningún escenario que no era el objetivo.

## Evidencia

| Task | Commit |
|---|---|
| T1 | `test(evals): stop demanding a handoff on a price question` |
| T2 | `test(evals): let a scenario send a media turn` |

## Log

**L1 (pedido del owner, 2026-11-17).** Continuación del handoff de la ronda anterior, verbatim:

> «Los 6 escenarios que fallan gates (el trabajo pendiente real) […] unknown_intent prohibido:
> real-claudio-caldera-valvula, real-dato-mas-pregunta […] Derivación que no ocurre: complejo-dos-temas,
> complejo-no-quiere-email […] Contenido faltante: real-mantencion-caldera,
> real-precio-mantencion-ciclo»

**L2 (decisión del owner, 2026-11-17).** Preguntado qué hacer con `complejo-dos-temas`, que exige
`human` + `persona` después de una consulta de precio y garantía que el bot respondió bien de la KB,
eligió: **corregir la expectativa del corpus**, con esta razón escrita en el corpus: «la consulta se
responde de la KB; derivar sin intentar responder es hard fail en real-precio-mantencion-ciclo. La
expectativa anterior contradecía esa regla».

**L3 (decisión del owner, 2026-11-17).** Forma de entrega elegida: **una PR por grupo de causa** — captura,
eventos, clasificación — cada una con su corrida de gates de los escenarios que toca.

**L4 (consentimiento del owner, 2026-11-17).** Autorizó crear el worktree `odd/evals-gates` →
`../lumat-agent-odd-evals-gates` para este trabajo.

**L5 (corrección al handoff, 2026-11-17).** El handoff hablaba de 7 escenarios; el informe sellado en
`69d9a12b7` lista siete, y uno ya se arregló en PR #829 (`simple-dia-especifico`, fixture de dirección
real, medido 1/1 en el commit `de6642f85`). El pendiente son seis y hay que re-medir para confirmarlo
antes de dar por buena la lista.

**L6 (mapa del código antes de escribir specs, 2026-11-17).** La exploración con evidencia `path:line`
cambió dos diagnósticos del handoff y ajustó un tercero:

1. **`real-claudio-caldera-valvula` no es un defecto del bot, es del instrumento (S4).** El cerebro ya
   trata bien un mensaje de media: sin texto no clasifica y sólo acusa recibo. El corpus manda
   `<video omitido>` como texto porque el harness persiste todo como `TEXT`. Meter el evento
   `unknown_intent` en el camino de media sería arreglar el síntoma en el lugar equivocado.
2. **`complejo-no-quiere-email` ya marca el correo como saltado (S5).** La frase del rechazo está en
   `_SKIP_WORDS` y en `_REFUSAL_FIELDS` desde CM-2. El fallo real es que la disponibilidad del último
   turno se pierde y la dirección se pide dos veces; la derivación que el escenario espera existe, pero
   llega en la tercera reiteración, un turno después de donde el escenario termina.
3. **`real-dato-mas-pregunta` no es una tool (S3): es el nodo `manage`.** La frase sale de
   `manage_no_visits` cuando no hay visitas próximas, y `manage` sólo corre si el clasificador dijo
   `reagendar_visita`. Queda por determinar, con la base a mano, **en qué turno** se registró el
   `unknown_intent` que el gate prohíbe: el informe no lo dice por turno.

Efecto sobre el plan: PR 0 deja de ser «sólo la expectativa de `complejo-dos-temas`» y pasa a incluir
el turno de media del harness. PR B pierde el arreglo de media y se queda con la agenda.

**L7 (evidencia en la base y decisiones del owner, 2026-11-17).** La corrida `gates-uno`
(`odd/evals/conv-eval-gates-uno.md`, sello `d17974f4f`, árbol limpio) dejó **3 de 7**. Cayeron
`complejo-dos-temas` (la expectativa corregida en T1), `simple-dia-especifico` (PR #829) y
`real-claudio-caldera-valvula` (el turno de media de T2). Quedaron cuatro, y la base abierta por
conversación mostró que **tres de los cuatro no eran defectos del bot**:

| Escenario | Lo que dijo la base |
|---|---|
| `real-mantencion-caldera` | el caso es `mantención de calefacción`; el bot lo sabe y contesta sólo `¿En qué comuna te encuentras?`. **Defecto real.** |
| `real-dato-mas-pregunta` | `unknown_intent` en el **turno 1** (`18:30 comienzo con los chicos`, fragmento huérfano del guion); después dos `reagendar_visita` → `manage` → `No tienes visitas próximas para reagendar.` **El defecto real es el callejón; el evento es del corpus.** |
| `real-precio-mantencion-ciclo` | `consulta` + `kb_retrieved`: la etiqueta que su propia definición asigna. **Expectativa.** |
| `complejo-no-quiere-email` | cuatro turnos, todos `solicitar_visita`, correo saltado correctamente; la dirección se pide **una** vez y el guion termina ahí. **Expectativa.** |

Decisiones del owner, las tres por la opción de corregir la expectativa:

1. `real-precio-mantencion-ciclo`: `intent_expected` pasa de `[valores]` a `[consulta]`.
2. `real-dato-mas-pregunta`: se retira `events_forbidden: [unknown_intent]`; quedan los hard fails.
3. `complejo-no-quiere-email`: `state_any: [bot, human]` y se retira `causes_required`.

Con el corpus corregido, de los cuatro quedan **dos defectos reales** (T4 y T5) y un escenario que
pasa por construcción (`real-precio-mantencion-ciclo`). La lista de «seis escenarios que fallan gates»
era, en realidad, dos defectos del bot y cinco problemas del instrumento.

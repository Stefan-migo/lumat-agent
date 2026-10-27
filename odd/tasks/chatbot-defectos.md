# ODD — defectos del bot (chatbot-defectos)

Los seis escenarios del corpus conversacional que **nunca pasan** en el árbol publicado (`main` = `9337731a`,
trío `after-682`: 7, 7 y 4 de 14). El instrumento ya no está en discusión: L7 de `odd/tasks/conv-eval-corpus.md`
dejó la evidencia y el orden. Esta feature arregla el bot.

## Specs

Los `S#` citan **textual** la falla que reportó el juez en `odd/evals/conv-eval-after-682-{1,2,3}.md`, más el
ancla de código donde se produce. Un `S#` es el criterio con el que se juzga si el arreglo sirvió: si el texto
se puede verificar contra el reporte, no es una paráfrasis mía.

### S1 — la emergencia termina en `human` y no registra el evento `escalation`

> `G3 · events_required`: «nunca se registró: escalation» — falla 3 de 3 corridas.

`app/chat/nodes/emergency.py:69-83` cambia el estado a `HUMAN` (`:58-64`), marca el caso
(`emergency/escalado/escalated_at`, `:68-76`) y escribe el evento **`emergency`/`strong_hit`** (`:77-83`), más
auditoría y notificación. El único emisor de `escalation` es `app/chat/nodes/handoff.py:124-128`, y `handoff`
**nunca** está en este camino (`app/chat/graph.py:335`: `emergency → END`). Consecuencia: el caso más grave del
producto es invisible para `app/services/analytics.py:94-107` y para el panel.

El evento debe emitirse con la misma forma que produce `handoff` —reusando el helper de
`app/services/realtime.py:36-48`— junto al marcado del caso, no en reemplazo de él.

### S2 — cuatro escenarios responden `kb_miss` cuando la respuesta está en la KB

> `G9 · kb_answered`: «la respuesta estaba en la KB y el bot respondió con la oferta de kb_miss (producción no
> registra evento en ese camino)» — aparece en `simple-cobertura-comuna`, `simple-horario-sabado` (a3),
> `complejo-dos-temas` y `complejo-fuera-de-cobertura-insiste`.

Decisión en `app/chat/nodes/respond.py:336-343`, alimentada por `respond.py:150-176` (`top_k=5`,
`min_sim=0.50`, `audience=CUSTOMER`, `global_only=True`) → `app/services/kb.py:388-431`
(`distance <= 1 - min_sim`). La consulta es el texto crudo del turno; el fallback por `service` sólo se agrega
si `intent not in (None, "unknown")` (`respond.py:126-131`), y una pregunta corta con saludo
("hola, ustedes trabajan en maipu?") no tiene `service` al que caer.

**Restricción que manda, y que prohíbe el atajo**: `odd/tasks/kb-retrieval-calibration.md:165-190` midió que el
top-1 de las consultas respondibles va de **0.3626 a 0.8277**, que el mejor absoluto fue **0.4752** y que
consultas irrelevantes llegan hasta **0.6976** por solapamiento estructural. El `0.50` en producción **cae
adentro** de la distribución respondible. Por lo tanto bajar `min_sim` no es un arreglo: es cambiar un
falso negativo por falsos positivos. El arreglo es de **forma de la regla** (margen relativo entre top-1 y
top-2, o una segunda consulta construida desde intención + tópico), y no puede romper
`super-near-miss-lavadora`, que hoy pasa 3 de 3.

Parte del defecto, no un extra: el camino de `kb_miss` blando **no registra ningún evento**, así que ni el
panel ni la telemetría pueden ver cuántas veces el bot dijo "no sé" sobre algo que sí sabía.

### S3 — la despedida se contesta con otra pregunta comercial

> Hard fail del juez: «Respondió la despedida («eso era todo») con una nueva pregunta comercial («¿En qué más te
> puedo ayudar?»).»

`app/chat/nodes/closure_gate.py:29` reconoce sólo `_CLOSING_PHRASES = ("eso fue todo",)`; los tokens de
`CLOSING_TOKENS` (`:19-28`) incluyen `eso/todo` pero **no** `era`, así que "eso era todo" no entra. El texto
sale de `messages.smalltalk` (`app/chat/nodes/respond.py:295-298`, `app/services/settings.py:248`). Además
`closure_gate.py:68-69` devuelve `{}` siempre que hay un campo pendiente, de modo que **una despedida en medio
de una captura no puede cerrar nunca**.

Es la dimensión `conversational` (1.86), la peor y la más estable de las seis: el bot responde, no conversa.

### S4 — la captura pregunta antes de responder, y vuelve a preguntar lo ya aclarado

> Hard fail del juez: «Pide datos (nombre y diagnóstico) antes de responder lo que el cliente preguntó
> —mantención de calefont en Ñuñoa: valor y coordinación— y vuelve a preguntar algo que el cliente ya había
> aclarado al decir que quería una mantención.»

`capture` se despacha antes de cualquier respuesta (`app/chat/nodes/orchestrate.py:38`,
`app/chat/graph.py:319-329`), así que el turno 1 pregunta en vez de cotizar. "Diagnóstico" es el campo
`failure` (`app/chat/nodes/capture.py:60`, etiqueta "Problema" `:92`). Una intención preventiva lo saltea por
palabras clave (`capture.py:437-461`), pero el campo queda sin valor, se pregunta en el turno 1 y otra vez en
el 2 (`MAX_ASKS_PER_FIELD`, `:75`), y al tercero deriva `campo_sin_respuesta` (`:545-560`, `:634-640`). Eso es
la "vuelta a preguntar". `app/chat/phrasing.py` sólo reescribe la misma plantilla (modo `plantilla` por
default), no cambia el orden.

**Cuidado con el alcance**: este escenario pasó de 0 de 3 a **2 de 3** después de #682/#683. Lo que se toca es
el residuo, y no puede tirar abajo las dos corridas que hoy pasan.

### S5 — la corrección del equipo se ignora y la cobertura no se evalúa antes de derivar

> `G10 · causes_required`: «ninguna derivación esperada (esperaba cobertura); se registró:
> handoff:campo_sin_respuesta» · `G6 · must_include_any`: «ninguna respuesta contiene: caldera» · Hard fail del
> juez: «Quedarse con el primer equipo mencionado e ignorar la corrección: tras "no era calefont, es una
> caldera" repitió la misma pregunta genérica sin reconocer el cambio de equipo ni la comuna Providencia.»

`equipment_type` **sí** se sobrescribe por turno (`capture.py:423-426`), pero el campo libre `equipment` nunca
(`_merge_extracted` `capture.py:344-403`, guarda en `:352-353`), y `case.service` se reescribe cada turno
(`classify_intent.py:157-169`). La respuesta del turno de corrección sale de `_reask_pending`, que **nunca
aplica la etiqueta** (sólo `_ask_next` lo hace, `capture.py:652-654`). Y `_out_of_coverage` (`:561-570`) se
evalúa únicamente desde `_ask_next` (`:617-623`), mientras la derivación por `campo_sin_respuesta` ocurre
antes (`:548-550`) — aunque Providencia está fuera de `DEFAULT_COVERAGE_COMMUNES`
(`app/services/settings.py:349-357`).

### S6 — DECISIÓN DE PRODUCTO ABIERTA: "no te voy a dar mi correo" no tiene causa propia

> `G10 · causes_required`: «ninguna derivación esperada (esperaba booking_unavailable, persona); se registró:
> handoff:campo_sin_respuesta, handoff:campo_sin_respuesta»

Hecho que el código deja ver: **ninguna causa existente significa "el cliente rechazó un dato"**.

- `campo_sin_respuesta` = un campo se preguntó `MAX_ASKS_PER_FIELD` (2) veces sin respuesta aceptable
  (`capture.py:545-550`, `:634-640`).
- `booking_unavailable` = la agenda no pudo cubrir la visita (`app/chat/nodes/booking.py:108`, `:131`); es
  inalcanzable acá porque el booking nunca corre.
- `persona` = el cliente pidió una persona explícitamente (`handoff_gate.py:99-100`, `orchestrate.py:82-83`).
- `consent_declined` existe, pero **sólo** para el paso de consentimiento (`capture.py:471-484`).

Un rechazo explícito cae hoy en "campo sin respuesta" porque `_SKIP_WORDS` (`capture.py:100-112`) no contempla
"no te voy a dar". La consecuencia no es cosmética: el panel y las métricas leen "el cliente no contestó" donde
pasó "el cliente dijo que no", que son dos problemas comerciales distintos.

Hay tres caminos y ninguno se puede elegir desde el código: **(a)** agregar una causa propia
(`campo_rechazado`) y permitir que el agendamiento siga sin ese dato; **(b)** tratar el rechazo como `is_skip`
y hacer el correo opcional en el flujo de booking; **(c)** aceptar que el bot está bien y que lo que está mal
es la expectativa del corpus. La spec queda abierta y **no se convierte en tarea** hasta que el owner elija.

## Tasks

Orden por valor/riesgo, el que dejó L7. Cada tarea se verifica con **su escenario del corpus**
(`--only <id>`, segundos, no el trío) más el test enfocado; el trío de tres corridas se reserva para el cierre
de la feature, donde `full` y `shape` también son obligatorios.

| ID | Spec | Qué | Verificación |
|---|---|---|---|
| T1 | S1 | Emitir `escalation` en `emergency()` reusando el helper de `realtime` | `--only super-emergencia-gas` (G3 verde) + test de integración |
| T2 | S2 | Diagnosticar las 4 consultas (similitud observada, no la del documento) y después cambiar la forma de la regla | `--only` de los 4 escenarios + `super-near-miss-lavadora` sin regresión |
| T3 | S3 | Cerrar la despedida: frases de `closure_gate` y si puede dispararse con captura pendiente | `--only simple-despedida` + test de `closure_gate` |
| T4 | S4 | Responder antes de la primera pregunta y no preguntar dos veces un campo que la intención preventiva ya salteó | `--only complejo-agendar-calefont` en 3 corridas (hoy 2 de 3) |
| T5 | S5 | Evaluar cobertura antes de derivar y llevar el equipo capturado al texto de re-pregunta | `--only super-burst-contradiccion` |
| T6 | S6 | **Bloqueada**: espera la decisión de producto | — |

Un commit por tarea, con su test. T1 es la más chica y la más grave: una emisión de evento.

## Log

### L1 — pedido original, verbatim

> «handoff/chatbot-defectos continuamos desde aca. dame un overview antes de continuar. necesito que me
> expliques todo lo que encontro el evaluador del chatbot. /home/stefan/repos/lumat-agent-odd-chatbot-conv-eval
> por que sigue abierto este worktree? pense que estaba todo mergeado al main. necesito que me digas donde ver
> todas las evaluaciones que hizo ayer el evaluador. luego explicame que es lo que deberiamos hacer para
> continuar»

### L2 — el precio de la mantención no es un defecto (medido, no asumido)

Cuatro observaciones por `scripts/chat_harness.py` con teléfonos nuevos: `$50.000` las cuatro veces. El cálculo
es determinista (`settings.tarifa_vigente` → octubre → `mantencion_calefont` 50.000) y **la elección de fila la
hace el LLM**, que recibe el bloque `<tarifario>` con cuatro líneas y `Visita técnica $30.000` como señuelo. El
`$30.000` histórico era eso, no una tarifa mal cargada. Arreglarlo de verdad no es prompt engineering: es que el
nodo de precio resuelva el servicio y emita la cifra. Queda **fuera de esta feature** como deuda de
arquitectura, no como bug.

### L3 — el instrumento queda cerrado (`main` = `9337731a`)

Trío `after-682` sobre el árbol publicado: 7, 7, 4 → mediana 7 de 14, con sello limpio, 14 de 14 escenarios
medidos y fingerprints de corpus y KB idénticos al trío anterior. `agendar-calefont` pasó de 0 a 2 de 3: **la
captura de #682/#683 funcionó donde se la apuntó**. `no-quiere-email` cambió de modo de falla. `emergencia-gas`
no se movió. Evidencia en PR #690 y en L7 de `odd/tasks/conv-eval-corpus.md`.

### L4 — worktree y Graph Check

Feature abierta en `../lumat-agent-odd-chatbot-defectos` (rama `odd/chatbot-defectos`, base `9337731a`, base de
test derivada en el puerto 5907), con consentimiento explícito del owner por feature.

Graph Check: `graphify query` corrido sobre las cuatro áreas (emergencia, retrieval/`kb_miss`, cierre, captura),
nodos consultados `emergency()`, `events.py`, `record_audit()`, `closure_gate()`, `capture()`, `_ask_next()`,
`services/settings.py` y `chat/graph.py`. El grafo está **desactualizado** (construido desde `456a0294`, HEAD
`9337731a`): el refresh `graphify . --update` corresponde al cierre de la sesión, no a cada tarea.

### L5 — T1 cerrada: la emergencia ya registra su escalamiento (`a6e0d921`)

`record_activity(..., "escalation", cause="emergency:strong_hit", actor="system")` dentro de `emergency()`, junto
al marcado del caso que ya existía. El evento anterior (`emergency`/`strong_hit`) y las banderas del caso **no**
se reemplazan: se agrega el que faltaba.

Dos correcciones sobre lo que entregó el worker, y el porqué:

1. **El `cause` pasó de `emergency_strong_hit` a `emergency:strong_hit`.** `handoff` escribe
   `handoff:<razón>` y `app/services/analytics.py:101` filtra por esa forma (`cause == "handoff:kb_miss"`), así
   que un nombre sin origen habría sido una segunda convención en el mismo campo. El `actor="system"` se
   mantuvo: es el que este nodo ya usa dos líneas más arriba en `set_conversation_state`.
2. **`app/chat/graph.py:31` afirmaba que `handoff` "owns every escalation".** Con el strong hit emitiendo el
   suyo, la frase quedó falsa; ahora dice cuál se detiene en `emergency`. Es documentación que el cambio
   invalidaba, no un extra.

Verificación: `bash scripts/test.sh db tests/integration/test_emergency.py tests/integration/test_handoff.py`
→ **82 passed**; `scripts/conv_eval.py --only super-emergencia-gas --no-judge --reset` → **1/1 escenarios pasan,
sin gates fallando** (antes: 0/1 por G3). El test vive en `test_strong_hit_mid_capture_interrupts`, junto a la
aserción del evento `emergency`, así que también cubre la interrupción a mitad de captura. El RED se observó
antes de implementar (`assert any(e.event == "escalation" ...)` → `assert False`).

### L6 — T2a: el umbral está descartado por medición, no por opinión

Similitud real (`app/services/kb.py:retrieve`, `top_k=5`, `min_sim=0.0`, KB sembrada con los 4 documentos
customer, fingerprint `91ca087a1130`), sobre las consultas de los escenarios que fallan **más el control que no
debe matchear**:

| Consulta | top-1 | top-2 | margen | ¿debería matchear? |
|---|---|---|---|---|
| `hola, ustedes trabajan en maipu?` | **0.4033** | 0.3302 | 0.073 | sí |
| `necesito una visita, el calefont no calienta. vivo en ñuñoa y solo puedo un sabado` | 0.2866 | 0.2254 | 0.061 | sí |
| `carlos. pero dime altiro si atienden sabado, eso es lo que necesito saber` | 0.1298 | 0.1033 | 0.027 | sí |
| `y eso cuanto de garantia tiene?` | **0.4498** | 0.3768 | 0.073 | sí |
| `hola, necesito mantencion de caldera, estoy en temuquito` | 0.3491 | 0.3418 | 0.007 | sí |
| **`hola, arreglan lavadoras? se me inundo el lavadero` (control)** | **0.4026** | 0.3404 | 0.062 | **no** |

**Bajar `min_sim` no es un arreglo y ahora está probado**: el control que hoy *no* matchea (`0.4026 < 0.50`, y por
eso `super-near-miss-lavadora` pasa 3 de 3) puntúa **más alto que tres de las cuatro consultas que sí deberían
matchear**. Un umbral que deje pasar "trabajan en maipú?" deja pasar "arreglan lavadoras?", que es exactamente el
escenario que demuestra que el bot no se inventa servicios. El margen entre top-1 y top-2 tampoco separa: el
del control (0.062) cae en el mismo rango que el de dos consultas respondibles.

La causa de fondo no es el umbral sino **la construcción de la consulta**: el turno crudo se compara contra 22
chunks largos (4 documentos), y una pregunta corta —o una que sólo tiene sentido con el turno anterior, como
"y eso cuanto de garantia tiene?"— queda diluida. La señal que sí existe en el sistema es la **intención ya
clasificada**: `respond.py:126-131` sólo agrega el fallback por `service` cuando `intent not in (None,
"unknown")`, y los documentos de la KB ya están separados por tema (cobertura y horarios, garantías y pagos,
identidad, servicios). Enrutar por intención a documento deja de ser un concurso de similitud.

**Consecuencia sobre T2**: deja de ser "cambiar la forma de la regla" y pasa a ser una decisión de diseño con
alcance transversal — el retrieval alimenta todos los turnos del cliente, no sólo estos cuatro escenarios. No se
implementa hasta elegir el camino, y T2b queda bloqueada igual que T6.

### L7 — T3 cerrada (`312293ca`) y la trampa de entorno que casi la mide mal

**T3.** El mensaje real no era "eso era todo" sino **"dale, muchas gracias, eso era todo"**, y el bot contestaba
"Con gusto. ¿En qué más te puedo ayudar?". Fallaban dos cosas: `_CLOSING_PHRASES` sólo conocía "eso fue todo", y
aun matcheando la frase, `is_farewell` exigía que **todos** los tokens restantes fueran de cierre — mientras
`dale`, `muchas` y `gracias` fueron sacados de `CLOSING_TOKENS` a propósito en S3 (la cortesía pertenece al
clasificador). Resultado: una despedida explícita envuelta en cortesía no podía cerrar nunca.

Frases agregadas ("eso era todo", "eso es todo", "eso seria todo", "nada mas") y un set separado
`_COURTESY_TOKENS` que **sólo** se consulta cuando una frase de cierre matcheó. Así la cortesía sola no cierra
("gracias" sigue sin cerrar) y el contenido que sigue a la frase tampoco ("eso era todo lo que necesitaba saber
del precio" queda abierto). Después: `> *bot:* ¡Gracias por escribirnos! Que tengas buen día.` · juez **3.83**,
sin hard fail, gates limpios. Antes: 0/1 con hard fail.

Queda abierto a propósito: `closure_gate` devuelve `{}` cuando hay `_pending`, así que una despedida a mitad de
captura no cierra. Es una decisión de comportamiento, no un descuido.

**La trampa de entorno, y es la más peligrosa de la sesión.** La primera verificación de T3 dio 0/1 con
`Aviso de horario configurado.` en **todos** los turnos, incluida la pregunta del precio. No era el bot: la base
de test del worktree nuevo tenía cuatro filas en `settings` —`hours.schedule` con una ventana de **00:00 a
00:01**, `hours.timezone`, y los textos de fixture "Despedida configurada." / "Aviso de horario configurado."—
que había dejado el test `test_out_of_hours_and_farewell.py` que corrí dos pasos antes.

`--reset` vacía 24 tablas de **estado de conversación**, y `settings` no está entre ellas. La receta documentada
advierte de re-sembrar la KB después de `pytest` (porque `kb_documents` sí se trunca), pero **no dice nada de
`settings`**: cualquiera que corra el corpus después de una suite mide un bot configurado por un test. La base de
`main` tenía cero filas (defaults, abierto); la del worktree nuevo, una ventana cerrada.

Dos consecuencias:

1. **Antes de citar una corrida hay que revisar los fingerprints del sello *y* el estado de `settings`,** igual
   que se revisa la KB. Un run con `árbol sucio: no` y fingerprints iguales todavía puede estar midiendo un bot
   configurado por un test.
2. **Es un follow-up del instrumento**, no de esta feature: `conv_eval.py` debería rechazar (o resetear) un
   `settings` que no coincida con los defaults antes de medir. No se arregla acá.

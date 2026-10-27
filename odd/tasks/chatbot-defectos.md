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

**Decisión de producto (L11): ruteo por tema.** El bot busca primero **dentro del documento del tema** al que
pertenece la pregunta (cobertura y horarios, garantías y pagos, servicios, quiénes somos), y el parecido deja de
ser el único criterio. El tema sale de un **mapa determinista pregunta→tema**, medido contra los 4 escenarios; un
campo nuevo del clasificador (`agent/personas/*`, shape surface) sólo si el mapa no alcanza. La regla no puede
aflojar `super-near-miss-lavadora`: "arreglan lavadoras" tiene que seguir sin encontrar nada, y eso es parte de la
verificación, no una nota al pie.

Por qué el ruteo y no una consulta mejor armada: `turn_queries` ya intenta texto crudo y después el `service`
clasificado (`respond.py:104-140`), y las cuatro consultas siguen fallando porque el problema no es el texto de
la consulta sino que el puntaje corta dentro de la distribución respondible.

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

Cerrado en T5a (`c29f844c`, la cobertura decide antes de derivar) y T5b (`c879438c`, un solo renderizado para los
dos caminos de captura): el escenario pasó de `{G10, G6}` a `{G6}` y la causa registrada es `handoff:cobertura`.
Lo que queda es G6.

**Decisión vigente (L14, reemplaza el momento de respuesta propuesto en L11–L12):** ante la pregunta
«¿Elegís 1, 2 o 3?», el owner eligió «si las 2»: **«Responder antes de transferir»**. El bot reconoce el equipo
corregido e informa el precio publicado aplicable al servicio solicitado **antes** de transferir al asesor. Si
falta un precio publicado o el servicio es ambiguo, aclara que requiere cotización: reconocer «caldera» no
permite asumir reparación o mantención. No inventa precio, fecha ni disponibilidad.

La respuesta que transfiere incluye esa información y aclara que un asesor coordina. Después de transferir,
se conserva el silencio del bot en conversaciones `HUMAN`/`CLOSED`, sin excepciones ni respuestas automáticas
que interfieran con la persona. El texto de cobertura reconoce el equipo y mantiene respaldo si falta ese dato;
los textos personalizados existentes deben seguir siendo válidos. La frase no se repite porque el bot ya no
interviene después de transferir. El requisito previo «No puede ser silencio» se retira: confundía el evaluador
directo del cerebro con el canal real. No se modifica el corpus en T5c; si contradice esta política, su resultado
se reporta como limitación del instrumento, no se altera el producto para hacerlo pasar.

### S6 — «no te voy a dar mi correo» se registra como campo sin respuesta

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

Los tres caminos eran: **(a)** agregar una causa propia (`campo_rechazado`) y permitir que el agendamiento siga
sin ese dato; **(b)** tratar el rechazo como `is_skip` y que el correo no bloquee; **(c)** aceptar que el bot
está bien y que lo que está mal es la expectativa del corpus.

**Decisión de producto (L11): (b), con el correo todavía en la lista.** El correo se sigue preguntando a todos
—la regla comercial no cambia para el cliente que sí lo da—, pero un rechazo explícito se reconoce como
**saltar el campo**: el campo queda «sin dato», no se vuelve a preguntar, el flujo continúa y la derivación, si
ocurre, lleva su causa real (`booking_unavailable`, `persona`). No se agrega una causa nueva, y el corpus no se
toca.

**Consecuencia aceptada y registrada**: el panel y las métricas siguen sin distinguir «dijo que no» de «no
contestó» en la causa; el rechazo queda visible en el hilo del caso (campo sin dato), no en el agregado. Era el
costo de (b) sobre (a), elegido a conciencia.

## Tasks

Orden por valor/riesgo, el que dejó L7. Cada tarea se verifica con **su escenario del corpus**
(`--only <id>`, segundos, no el trío) más el test enfocado; el trío de tres corridas se reserva para el cierre
de la feature, donde `full` y `shape` también son obligatorios.

| ID | Spec | Qué | Verificación |
|---|---|---|---|
| T1 | S1 | Emitir `escalation` en `emergency()` reusando el helper de `realtime` | `--only super-emergencia-gas` (G3 verde) + test de integración |
| T2 | S2 | Diagnosticar las 4 consultas (similitud observada, no la del documento) y después cambiar la forma de la regla | `--only` de los 4 escenarios + `super-near-miss-lavadora` sin regresión |
| T2b | S2 | **Delivered · backend closure green (L40)** · Ruteo por tema: mapa determinista pregunta→tema y búsqueda acotada al documento del tema, con respaldo al conjunto completo | `--only` de los 4 escenarios + `super-near-miss-lavadora` sin regresión + test unitario del mapa |
| T3 | S3 | Cerrar la despedida: frases de `closure_gate` y si puede dispararse con captura pendiente | `--only simple-despedida` + test de `closure_gate` |
| T4 | S4 | Responder antes de la primera pregunta y no preguntar dos veces un campo que la intención preventiva ya salteó | `--only complejo-agendar-calefont` en 3 corridas (hoy 2 de 3) |
| T5 | S5 | Evaluar cobertura antes de derivar y llevar el equipo capturado al texto de re-pregunta | `--only super-burst-contradiccion` |
| T5c | S5 | **Code delivered locally · manual verification passed (L22–L24)**: equipment/legacy-slot `5c0d5e3a`, tariff/quotation/channel tests `66021c4d`; owner-authorized manual checks passed, NOT independent approval. Real-model proof remains deferred. Full real-model evaluation remains deferred to feature closure | Prior integration 79, slots 22, `quick` and `full` exit 0; previous verifier emitted NO verdict; no real-classifier proof; see L15–L18 |
| T6 | S6 | **Code locally delivered · manual verification accepted (L37)** · Rechazo explícito a un dato = saltar el campo; el correo sigue en la lista y no bloquea el agendamiento | `--only complejo-no-quiere-email` + test de rechazo explícito en `test_chat_capture.py` |

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

### L8 — T5: primer intento revertido, y el diagnóstico corregido

Se delegó T5 y volvió a medias: código sin test verde. **Revertido sin commitear** (`git checkout` de los dos
archivos). Lo que dejó fue útil, igual.

**Por qué se revirtió.** El worker reportó que su test de cobertura **pasaba antes de implementar**. Un test que
no falla antes no demuestra el defecto, y un parche sobre esa base es especulación: después quedó con
`KeyError: '_pending'` en su propio setup y sin el texto del equipo.

**El diagnóstico corregido, y confirma el original por otra vía.** El transcript real (`after-682-3`) dice:

```
2. cliente  necesito arreglar un calefont
   bot      Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?
3. cliente  no era calefont, es una caldera, y estoy en providencia
   bot      Cuéntame qué pasa con el equipo: ¿no enciende, no calienta o muestra algún código de error?
4. cliente  cuanto sale y cuando pueden venir
   bot      Veo que esa pregunta no te acomoda. Un asesor de Lumat te contacta…
```

- La config **no** es la causa: `CONDUCT_DERIVACIONES = ("cobertura",)` (`app/services/settings.py:76`) y el
  default la incluye, así que la guarda `if COVERAGE_DERIVATION not in derivaciones` pasa.
- `_out_of_coverage` se consulta **sólo** desde `_ask_next` (`capture.py:614`). Mientras `failure` está
  pendiente el flujo va por `_reask_pending` (`:545-560`) y a la tercera deriva. O sea: **con un campo pendiente
  que llega a la derivación, la cobertura es estructuralmente inalcanzable.** El test del worker pasaba porque
  armaba un estado donde `_ask_next` sí se alcanzaba; no reproducía el camino.
- El worker buscó la corrección del equipo en `equipment_type` y no apareció por una razón distinta a la que
  asumimos: `_merge_extracted` (`capture.py:354`) hace `if not value or captured.get(field): continue`, es decir
  **nunca sobrescribe un campo ya capturado**. En el turno 2 el equipo quedó como calefont, y la corrección del
  turno 3 se descarta. Eso explica G6 (ningún mensaje dice "caldera") mejor que el renderizado de la pregunta.

**Qué necesita T5 para hacerse bien** — dos arreglos, no uno, y tests que reproduzcan el camino con campo
pendiente:

1. Evaluar la cobertura **antes** de la rama de derivación de `_reask_pending` (la dirección del worker era
   correcta; su test no).
2. Permitir que una **corrección explícita** sobrescriba un campo ya capturado, sin abrir la puerta a la
   corrupción por prosa que la guarda de `:356` protege. Es la parte delicada y merece su propio análisis.

**Corte de slice**: la rama queda en **363 líneas autoradas, 6 commits**, con T1 y T3 cerradas y verificadas
contra el corpus. Es un corte de PR limpio; T5, T2b y T6 siguen abiertas y T5 necesita su propia unidad.

### L9 — T5a cerrada (`c29f844c`) y por qué tres intentos fallaron en el mismo punto

**El mecanismo, medido y no inferido.** Corrida instrumentada de `super-burst-contradiccion`, mirando la base
después:

```
captured_data: {"comuna": "Providencia", "equipment": "calefont",
                "equipment_type": "caldera",
                "_asked": {"failure": 2}, "_pending": ["failure"]}
events:        state_change bot->human: handoff:campo_sin_respuesta
               escalation               handoff:campo_sin_respuesta
```

Tres cosas quedaron probadas:

1. **La comuna sí se captura.** "y estoy en providencia" llega a `captured_data`. La extracción **no** es el
   defecto: mi sospecha inicial era falsa en esa parte.
2. **`equipment_type` sí se corrige** a `caldera`. El que queda obsoleto es el campo libre `equipment`
   ("calefont"). Eso es T5b.
3. **La derivación ignora la cobertura**: `campo_sin_respuesta` con la comuna fuera de cobertura. `_out_of_coverage`
   se consultaba sólo desde `_ask_next`, y con un campo pendiente el flujo va por `_reask_pending` y deriva, así
   que la regla era **estructuralmente inalcanzable** en ese camino.

**Por qué los tres intentos fallaron, y la lección.** Los tres tests pasaban antes de implementar, o sea no
demostraban nada. Las dos razones:

- Sembrar `_pending` / `_asked` en `captured_data` desde el test y correr el grafo **no reproduce el camino**:
  termina en `_ask_next`, donde la cobertura sí se evalúa, y el test pasa por la razón equivocada.
- Con el clasificador mockeado (`mock_openai_chat`) **tampoco**: la extracción real de "providencia" y la
  corrección del equipo no ocurren con un doble.

El test que funciona construye el estado que la corrida dejó en la base y llama `_reask_pending` **directo**. RED
observado: `assert 'campo_sin_respuesta' == 'cobertura'`.

**Resultado**: 32 tests verdes en `test_chat_capture.py` (incluido el nuevo) y 40 en `test_handoff.py`; en el
escenario, los gates pasaron de `{G10, G6}` a **`{G6}`** y la causa registrada es `handoff:cobertura`. **G10
queda arreglado; G6 sigue fallando a propósito** porque el texto de la re-pregunta todavía no nombra el equipo
corregido.

**Notas de entorno para la próxima sesión, caras de redescubrir:**

- Los tests van por **`bash scripts/test.sh db …`**, nunca por `uv run pytest` directo: el script es quien exporta
  `TEST_POSTGRES_PASSWORD`, y sin él `migrate.sh` falla con "permission denied to alter role".
- Un volumen nuevo necesita **una** pasada manual de `db/migrate.sh` con `DATABASE_URL=$TEST_ADMIN_DB_URL`, o el
  primer `pytest` muere en la migración.
- La suite vacía `kb_documents` **y deja filas en `settings`**. Antes de cualquier corrida: re-sembrar la KB y
  borrar `settings`. Las dos cosas, no una (L7).

**Corte de slice**: 456 líneas, 8 commits. El PR #695 cubre T1+T3; T5a ya está en la rama y entra en el próximo
slice junto con T5b.

### L10 — T5 cerrada en su código (`c879438c`), y el escenario cambió de pregunta

Con T5a y T5b dentro, `super-burst-contradiccion` ya no repite la pregunta genérica. La conversación real ahora:

```
2. cliente  necesito arreglar un calefont
   bot      Entiendo, es un problema con tu calefont. Cuéntame qué pasa con el equipo: ...
3. cliente  no era calefont, es una caldera, y estoy en providencia
   bot      Todavía no tenemos visitas técnicas en Providencia, un asesor de Lumat se contactará
            contigo para ayudarte a la brevedad.
4. cliente  cuanto sale y cuando pueden venir
   bot      Todavía no tenemos visitas técnicas en Providencia, un asesor de Lumat se contactará
            contigo para ayudarte a la brevedad.
```

El label del equipo ya aparece (turno 2) y la cobertura ya decide (turno 3), que era el objetivo. Pero **G6 sigue
fallando, y por una razón nueva**: ninguna respuesta dice "caldera" porque la derivación por cobertura se adelanta
y no vuelve a hablar del equipo. También se repite la misma respuesta en los turnos 3 y 4.

Eso **no es un bug que yo deba cerrar solo**. Son dos preguntas de producto:

1. ¿La respuesta de derivación por cobertura debe reconocer el equipo que el cliente corrigió, o alcanza con
   derivar?
2. Si la conversación ya derivó, ¿el turno siguiente debe repetir la misma respuesta textual?

Las dos cambian lo que el cliente lee y lo que el corpus espera. Quedan como pregunta abierta, igual que S6, y
**no** se resuelven cambiando el corpus a conveniencia del bot.

Nota sobre el duplicado: aparecieron **dos** divergencias entre `_ask_next` y `_reask_pending` (la regla de
cobertura y el label del equipo). La segunda no se copió: se unificó en `_render_capture_question`, porque el
defecto es la duplicación, no cada omisión por separado.

### L11 — las tres decisiones de producto, tomadas en `rapso-session`

Sesión: `.rapsodia-code/sessions/archived/2026-10-27-chatbot-defectos-decisiones/` (registro completo, más Engram).
El owner eligió sobre tres explicaciones en simple, con ejemplo de lo que ve el cliente y el costo de cada
opción. **Ninguna de las tres cambia el corpus**: las tres se arreglan en código.

- **D1 — retrieval.** Eligió: «(a) Buscar dentro del documento que corresponde». El tema sale primero de un mapa
  determinista pregunta→tema; un campo nuevo del clasificador sólo si el mapa no alcanza, porque `consulta`
  cubre cobertura, horarios, servicios y plazos en una sola etiqueta. Guardia: `super-near-miss-lavadora` sigue
  sin encontrar nada. → S2, T2b.
- **D2 — derivación por cobertura.** Eligió: «(a)+(b) Las dos cosas»: la derivación **nombra el equipo**
  corregido y la frase **no se repite** en los turnos siguientes. No puede ser silencio: `G8 reply_present` exige
  respuesta a cada turno. → S5, T5c.
- **D3 — rechazo de un dato.** Eligió: «(b) Saltar el campo y correo opcional», y precisó la regla comercial:
  «Sigue en la lista, rechazo no bloquea». O sea: el correo se sigue preguntando a todos, un rechazo explícito
  se trata como saltar el campo y el flujo continúa. Sin causa nueva, y con la consecuencia aceptada: el panel
  no distingue «dijo que no» de «no contestó» en el agregado. → S6, T6.

### L12 — precisión del owner y arranque de T5c

Pedido verbatim: «perfecto merge y limpieza. y luego continuamos con lo que sigue. ii ademas respodner el precio de la caldera.»

#697 y #698 mergeados (`82e311c6`, `3fa72711`), con ambos CI verdes; ramas de entrega eliminadas.
T5c arranca en `odd/chatbot-defectos-t5c` desde `3fa72711`. El primer worker no escribió nada:
el grafo estaba desactualizado y su superficie de edición no autorizaba regenerarlo. El parent ejecutó
`graphify update .`: exit 0, 22.852 nodos, 40.976 aristas y 1.527 comunidades. Advertencias:
57 archivos SQL omitidos por dependencia `tree_sitter_sql` ausente, cinco JSON sin nodos; no se instaló nada.
Consulta `capture handoff derivation_reply tariff`: nodos `capture()`, `_reask_pending()`, `_ask_next()`,
`handoff()`, `derivation_reply()`, `get_reply_texts()`; aristas consultadas por `graphify path capture handoff`:
no encontró camino dirigido (el despacho se revisa en el grafo conversacional real).

No hay prueba todavía de ausencia de credenciales: buscar `OPENAI_API_KEY` no demuestra qué proveedor usa
el proyecto. El worker debe identificar la configuración real sin imprimir secretos antes de declarar el
corpus disponible o bloqueado. No se elimina `settings` si contiene configuración necesaria para el modelo.

Risk: item 3 (contrato compartido de textos y slots; conservar textos personalizados existentes).
Requiere verificación independiente después de la implementación. Suite `full` requerida por el merge de
`origin/main` en la rama de decisiones; el CI sobre `bd8754f5` pasó antes del merge de #698.

### L13 — bloqueo de producto: el bot no responde tras transferir a una persona

El segundo worker no modificó código ni ejecutó RED/GREEN. El parent verificó:
`app/webhook/ingest.py:396-402` conserva el mensaje entrante pero no ejecuta el bot cuando la conversación
está `HUMAN` o `CLOSED`. `handoff.py` cambia a `HUMAN` al derivar por cobertura. El evaluador llama al
cerebro directamente y deja el webhook fuera de alcance (`scripts/conv_eval.py:8`, `:1312`); por tanto, el
texto repetido en su turno 4 no demuestra qué recibe un cliente real después de derivar. La premisa previa
sobre ese turno en producción era incorrecta.

Pendiente decisión del owner: mantener silencio tras la transferencia, cambiar el momento de transferencia,
o autorizar una excepción acotada. No debilitar el control para satisfacer el evaluador. La ampliación necesaria
a `tests/unit/test_reply_texts.py` es un ajuste de superficie de ingeniería que resuelve el parent, no otra
pregunta de producto.

### L14 — el owner elige informar antes de transferir

Respuesta verbatim: «si las 2».

Opción elegida presentada: «2. Responder antes de transferir» — «El bot informa el precio publicado que
corresponda —o aclara que requiere cotización— y después pasa al asesor para coordinar.»
La recomendación fue resolver la información disponible antes de entregar la conversación y después dejar
al asesor a cargo. S5 reemplaza la exigencia de respuesta automática posterior a la transferencia. No se
modifica el control `HUMAN`/`CLOSED` de `app/webhook/ingest.py`.

El parent amplía la superficie necesaria a `tests/unit/test_reply_texts.py` y
`tests/integration/test_webhook_ingest.py` para verificar slots y silencio por el canal público. No requiere
otra elección del owner. Graph Check: `handoff() --calls [EXTRACTED]--> derivation_reply()` (1 salto), y nodos
`tarifa_vigente()`, `get_reply_texts()`; grafo actualizado en esta sesión. T5c se reabre para implementación.

### L15 — T5c parcial: precio antes de transferir, sin prueba del corpus

**S5 implementado.** La respuesta de cobertura incluye el equipo corregido (`equipment_type` antes que
`equipment`, y «equipo» como respaldo), luego consulta sólo una tarifa vigente cuando `case.service` coincide
con una clave o etiqueta de servicio publicada. Si el servicio no se identifica o no tiene precio vigente,
dice que requiere cotización; en ambos casos indica que un asesor coordinará y que no puede confirmar fecha ni
hora. El texto de cobertura permite el slot opcional `{{equipo}}`; el texto personalizado antiguo que sólo
contiene `{{comuna}}` sigue siendo válido. La transferencia a `HUMAN` y el silencio posterior no se cambiaron.

**RED/GREEN deterministas observados.** Antes del cambio de slots,
`bash scripts/test.sh focused tests/unit/test_reply_texts.py` falló porque esperaba `{"comuna", "equipo"}`
y sólo estaba permitido `{"comuna"}`. Antes de completar la respuesta, la integración enfocada registró seis
fallas: faltaban equipo y respaldo, tres servicios no identificados no indicaban cotización y el texto legacy
no quedaba preservado. Tras implementar, `bash scripts/test.sh db tests/integration/test_handoff.py tests/integration/test_webhook_ingest.py`
terminó con **79 tests pasados**. Advertencia real: `RuntimeWarning: coroutine '_publish_all' was never awaited`
en `test_startup_sweep_reprocesses_received` (`_pytest/stash.py:108`).
`bash scripts/test.sh focused tests/unit/test_reply_texts.py` terminó con **22 tests pasados**.

El primer `bash scripts/test.sh quick` falló únicamente por dos pins de copy anteriores en
`tests/unit/test_handoff_replies.py`: `test_the_five_reasons_ship_the_approved_wording` y
`test_each_derivation_reason_renders_its_own_text[cobertura]`. Con autorización explícita se actualizó sólo
la expectativa del copy de cobertura y el renderizado del respaldo `equipo`; se conservaron las expectativas
para los otros motivos, la comuna ausente y el copy custom legacy. La única corrida de `quick` después de esa
corrección terminó con **exit 0**, llegó a **100%** y no emitió advertencias. El runner no mostró un conteo
agregado de tests.

**Prueba de canal:** `test_coverage_handoff_followup_stays_silent_at_process_message_boundary` ejercita
`ingest.process_message`; pasa el test de integración y comprueba persistencia del mensaje, sin llamada al grafo
ni envío saliente. No se alteró `app/webhook/ingest.py` ni se debilitó la guarda `HUMAN`/`CLOSED`.

**Corpus pendiente, no inferido.** No se ejecutó `scripts/conv_eval.py` ni se midió un transcript con el
clasificador real; los tests de handoff usan estado clasificado construido directamente. La configuración
observada es `deepseek`, sin clave en el entorno y sin fila coincidente de `PanelSecret` en la base de test; no
se imprimieron secretos. Por eso T5c queda **partial**, no cerrada. No se modificó `scripts/conv_eval_corpus.yaml`.

**Graph Check de esta tarea:** consultados `capture()`, `handoff()`, `derivation_reply()`, `get_reply_texts()` y
nodos de settings/tarifas; `graphify path "handoff()" "derivation_reply()"` devolvió
`handoff() --calls [EXTRACTED]--> derivation_reply()` (1 salto). Leído `graphify-out/GRAPH_REPORT.md`
(22.852 nodos, 40.976 aristas, 1.527 comunidades; grafo construido desde `bd8754f5`). No se refrescó el grafo.

### L16 — verificación del parent: suite verde y dos pruebas faltantes

`git diff --check`: exit 0. `bash scripts/test.sh shape`: exit 0, sin superficies de shape.
Native ASSESS: riesgo nativo medium, elevado a high por item 3 (contrato compartido de textos editables),
independentVerifier requerido; reviewDue false (`under_budget`), por lo que no se inicia review nativa.
Verificador independiente `mvqzuyqp-5-5etq`: falló con `assistant reported an error`, sin verdict ni evidencia
admitida. No se reintenta ni se reemplaza por una revisión del propio autor.

Suite completa del parent: `bash scripts/test.sh full`, job-6: **exit 0**, 5 min 50 s, llegó a 100%; sin conteo
agregado en la salida final. Advertencias observadas: coroutine `_publish_all` sin await en
`test_startup_sweep_reprocesses_received`; cambio de pooling CLS a mean del modelo FastEmbed en
`test_project_slug_is_normalized_and_unique`. No son fallos de test y no se corrigieron fuera de alcance.

Corpus con clasificador real no disponible por credenciales ausentes. T5c queda **blocked**, sin commit ni
publicación nuevos. Needs owner decision: aportar configuración para la prueba real y revisión independiente
por una persona, o aceptar explícitamente continuar con esas dos pruebas faltantes. No se declara S5
verificado completo ni se prosigue a T2b/T6 ocultando el bloqueo.

### L17 — orden acordado y cierre explícito de conversación

El owner aceptó el orden propuesto: «perfecto seguiremos con ese orden.» Revisión independiente de T5c ahora;
después T2b y T6 con pruebas enfocadas; evaluación conversacional completa con el modelo real al terminar los
cambios. Esto reemplaza la propuesta de tratar revisión y corpus como una aceptación conjunta de faltantes:
se puede diferir la evaluación completa, pero no afirmar que ya se probó el clasificador ni que la revisión
independiente fallida aprobó el código.

Pedido de cierre verbatim: «perfecto seguiremos con ese orden. pero primero necesito que cerremos esta conversacion. necesito que cerremos aqui. guarda la memoria y pasame el handoff para continuar desde aqui con un nuevo chat.»

Pausa por pedido explícito del owner: no seguir implementando, no commit, push, PR ni más verificaciones en
esta conversación. Handoff: `odd/handoffs/chatbot-defectos-t5c-continuacion.md`. Worktree
`/home/stefan/repos/lumat-agent-odd-chatbot-defectos`, rama `odd/chatbot-defectos-t5c`, HEAD `3fa72711`.
T5c conserva cambios locales; los siguientes cambios de código T2b/T6 todavía no empezaron.
Graph Check de cierre: `handoff() --calls [EXTRACTED]--> derivation_reply()` (1 salto). El grafo ya se actualizó
una vez durante esta sesión; no se repite la regeneración por cada edición de documentación.

### L18 — resume reconciliation and independent review route

Owner request verbatim:

```text
Continuamos chatbot-defectos en el worktree
   /home/stefan/repos/lumat-agent-odd-chatbot-defectos,
   rama odd/chatbot-defectos-t5c.

   Leé odd/handoffs/chatbot-defectos-t5c-continuacion.md y
   odd/tasks/chatbot-defectos.md (hasta ## Log, después L9–L17).
   Recuperá la memoria odd/chatbot-defectos/tasks y reconciliá
   el diff local sin descartar ni rehacer los cambios.

   T5c ya está implementado, sin commit. Los tests enfocados,
   quick y la suite completa pasaron. Su revisión independiente
   falló sin emitir resultado.

   El orden acordado es:
   1. Resolver la revisión independiente de T5c.
   2. Implementar T2b: búsqueda en los documentos por tema.
   3. Implementar T6: continuar sin correo ante rechazo explícito.
   4. Hacer la evaluación conversacional completa con el modelo
      real al terminar los cambios de código.

   Para T5c, el bot informa el precio publicado aplicable o la
   necesidad de cotización ANTES de transferir al asesor.
   Después de transferir queda en silencio. No confundir el
   precio de reparación con el de mantención.

   No se ejecutó el corpus con el clasificador real: faltan
   credenciales del proveedor configurado. No lo cuentes como
   prueba aprobada ni como una renuncia a evaluarlo al final.
```

Recovered observation 6865 (`odd/chatbot-defectos/tasks`): its full feature document matched the local file exactly before this entry.
Confirmed branch `odd/chatbot-defectos-t5c`, HEAD `3fa72711d76fa6f15afe508b6d6f8a4e5d000cd2`.
Preserved all seven modified tracked files and the untracked continuation handoff; no source edits, resets, commits or publication.
Resume snapshot: tracked diff +414/-21; `git diff --check` exit 0. Prior green tests remain historical evidence, not newly executed checks.
Source/test diff matches the handoff: corrected equipment, optional legacy-safe slot, explicit current service tariff or quotation, unchanged HUMAN/CLOSED guard, public ingest silence assertion.
Graph consulted: `handoff()`, `derivation_reply()`, `get_reply_texts()`, `tarifa_vigente()`; extracted one-hop `handoff() → derivation_reply()`.
Read report summary/community hubs (22,852 nodes, 40,976 edges, 1,527 communities; provenance bd8754f5); no graph regeneration.
Independent verifier role is advertised with read/grep/find/bash, but the failed prior invocation still has NO verdict.
Per L16/handoff no automatic retry: awaiting owner's explicit choice of one new bounded verifier invocation or human review. No substitute native review or author's self-review.
T2b and T6 remain ordered next; complete real-model evaluation remains required at the end, with configured-provider credentials still missing as last observed.

### L19 — explicit authorization for one new bounded verifier invocation

Owner selected «Autorizar un nuevo intento acotado (recomendado)» (token `authorize_one_new_t5c_verifier_attempt`).
Presented consequences: «Una nueva ejecución del verificador independiente sobre T5c y S5, con pruebas enfocadas; sin repetir full ni ejecutar el corpus real. Si vuelve a fallar sin resultado, se detiene.»
Route: delegated `gentle-ai-verify`, required by Risk: item 3 (shared owner-editable reply contract). Prior failed invocation remains without a verdict; this is the one explicitly authorized new invocation, not an automatic retry.
Scope: T5c/S5 and affected existing reply contracts only; baseline `3fa72711d76fa6f15afe508b6d6f8a4e5d000cd2`. No full-suite rerun, source edits, commits, publication or real-model corpus run in this verification.

### L20 — authorized verifier failed without a result; stop at missing proof

Task `mvr1ke6f-1-pmyb` (`gentle-ai-verify`) failed with exact result `Subagent gentle-ai-verify failed: assistant reported an error`. Read the delivered result once: no verdict, findings, command results or test evidence were returned. This is unavailable proof, not a rejected implementation and not an approval. No third invocation, alternative review ceremony or author self-review substitutes for it.

Owner follow-up verbatim: «Review the delivered subagent output and continue.» Reviewed the output; continuation reaches the previously agreed stop condition: «Si vuelve a fallar sin resultado, se detiene.»

T5c remains blocked pending an independent human review against S5 and affected existing reply contracts. T2b and T6 remain pending in the agreed order. Complete real-model evaluation remains required after code changes, with credentials still missing as last observed. No tests, full suite or corpus were run by the parent in this continuation; `git diff --check` exit 0. Existing source/test modifications and untracked handoff remain preserved; no commit or publication.

Needs your decision: arrange independent human review and provide its result, or explicitly revise the independent-review prerequisite. No prerequisite is waived by silence or by the agent failure.

### L21 — owner authorizes manual verification instead of Gentle AI reviewers

Owner request verbatim: «puedes hacer una verificacion manual. sin utilizar las herramientas de gentle ai? solo para estar seguro del proceoso y continuar?» Follow-up verbatim: «continue».
Parent explained this is a manual code review and focused functional verification, NOT independent review. Owner's explicit request revises the review-route prerequisite from L20 for this unit; the failed independent runs still have no verdict. No Gentle AI review/lifecycle tools or new subagents are used for this manual verification.
Route: inline manual review of actual T5c source/test diff and focused test wrapper commands. Preserve local code, no reimplementation. Final real-model evaluation remains required after T2b/T6.
Progress: inspected handoff(), derivation_reply(), current tariff helpers, reply validation, public process_message HUMAN/CLOSED guard and focused test assertions. Graph query consulted handoff(), derivation_reply(), tarifa_vigente(); extracted handoff() → derivation_reply() edge. Graph report summary/community hubs read; no refresh.
`bash scripts/test.sh focused tests/unit/test_reply_texts.py tests/unit/test_handoff_replies.py tests/unit/test_tarifa_vigente.py`: exit 0, reached 100%, no stdout aggregate count or stderr warning. Test DB target validated without printing credentials: localhost:5907/lumat reachable. Focused integration and direct manual/differential probes still pending; do not mark T5c verified yet.

### L22 — manual verification passed; preserve missing real-model proof

Owner-authorized parent verification found no blocker in the implemented T5c behavior. This is NOT independent approval: both independent verifier invocations failed without verdicts.

Observed checks:
- `bash scripts/test.sh focused tests/unit/test_reply_texts.py tests/unit/test_handoff_replies.py tests/unit/test_tarifa_vigente.py`: exit 0, reached 100%, no warning.
- `env -u DATABASE_URL -u TEST_ADMIN_DB_URL -u TEST_DB_PORT -u TEST_DB_PROJECT bash scripts/test.sh db tests/integration/test_handoff.py tests/integration/test_webhook_ingest.py`: job-1 exit 0, 79 cases, reached 100%. Existing warning: `RuntimeWarning: coroutine '_publish_all' was never awaited` in `test_startup_sweep_reprocesses_received`.
- Initial ephemeral differential probe: exit 1 BEFORE behavior; application import lacked six dummy Settings variables outside pytest. No product failure or RED claimed. One correction supplied the same dummy import requirements as `tests/conftest.py`, with a deliberately unreachable DB URL and no provider/DB calls.
- Corrected differential/manual command: exit 0. Compared baseline `3fa72711d76fa6f15afe508b6d6f8a4e5d000cd2` source copies in a temporary ignored project directory against current source in separate Python subprocesses: 16 existing render paths, identical stdout, empty stderr, exit 0 for both. Includes existing derivation reasons, legacy custom coverage text and missing-commune fallback. Scratch copies automatically removed.
- Supplemental isolated helper probes: corrected caldera wins stale calefont; unknown/blank/missing equipment falls back safely; exact service key, accented label and uppercase unaccented label select the injected published 123456 tariff and format `$123.456`; repair, ambiguous service, missing service and absent current tariff return quotation without a currency amount. These helper probes do NOT prove live classifier behavior.
- Source review confirms published tariff resolution uses configured timezone/current date and existing tarifa_vigente; process_message keeps the unchanged HUMAN/CLOSED early return. Integration proves HUMAN state/event and inbound history without graph invocation or outbound delivery.
- `git diff --check`: exit 0. `bash scripts/test.sh shape`: exit 0, no shape surfaces touched. No new full/quick run; historical green evidence from L15/L16 retained.

Delivery split (engineering, not a product change): T5c equipment/optional-slot compatibility with its unit tests in one commit (<=5 files including this task record); tariff/quotation before handoff with its integration/channel tests and handoff note in a second commit. Stage only the relevant handoff.py hunk for the first unit; never restore, discard or rewrite working source to achieve the split. Record commit identities after observing successful commits. No push, PR or merge authorized here. The overall feature and real-model evaluation remain open; T2b then T6 are next.

### L23 — cohesive local delivery

Equipment/legacy-slot compatibility committed as `5c0d5e3a` (5 files, +266/-19). Only the equipment rendering hunk was staged from handoff.py; working source was preserved. First staged whitespace check caught an extra blank line at the end of this task document (exit 2); removed that trailing blank line, subsequent staged and working `git diff --check` both exit 0. No test or behavior was changed by the whitespace correction.
Second unit contains the existing verified tariff/quotation logic, integration handoff tests, public ingest silence test and historical handoff note. Successfully committed as `66021c4d` (5 files, +325/-2). Native review was not run: owner requested the manual route without Gentle AI review tools (L21); no native approval is claimed.
Memory mirror full content submitted successfully; large observation readback is truncated by the memory tool, so a full exact readback cannot be claimed. Local feature file remains the full authoritative record.

### L24 — start T2b after T5c manual verification and local delivery

T5c source/tests preserved in `5c0d5e3a` and `66021c4d`; post-commit worktree was clean and `git diff --check` exit 0. No push/PR/merge. Both independent review attempts remain without verdict; manual route explicitly authorized in L21 and observed checks in L22 satisfy the chosen continuation prerequisite, not the final real-model proof.
T2b/S2 route: bounded delegated writer because the runtime explicitly signaled the parent context backstop; this is the next several-step unit. Scope: deterministic question→topic routing and topic-document retrieval with safe global fallback, no threshold-only fix; preserve the washing-machine negative control and existing retrieval audience/global/project guards. Parent owns this log and subsequent reconciliation. T6 remains next, final complete actual-model evaluation remains required after code changes.
The owner's request to avoid Gentle AI tools applied to the manual T5c verification; no native review or reviewer was used for that verification. T2b is implementation, not another T5c review invocation.

### L25 — T2b needs one additional event-helper edit surface

Worker `mvr248gk-2-u037` returned `interaction_required`; no files changed and no RED/GREEN/tests run. Parent spot-check confirmed `app/services/realtime.py`: `ACTIVITY_EVENTS` only includes `classified`, `kb_retrieved`, `escalation`; `record_activity()` validates that vocabulary and stages realtime publication, while `activity_events()` filters reconnect-safe history using it. A direct ConversationEvent write would bypass the existing helper. Working status remains only the parent's task-document update; `git diff --check` exit 0.

Worker's complete blocking choice envelope (closed single-select, choose one):
- Question: Approve adding `app/services/realtime.py` to the allowed edit surfaces, or defer the soft `kb_miss` event requirement and proceed with the currently authorized files?
- Reason: The required event helper rejects `kb_miss`, and implementing event persistence in `respond.py` would bypass its validation and realtime staging.
- Option 1: Approve the additional path `app/services/realtime.py`.
- Option 2: Defer the soft `kb_miss` event criterion; keep the original allowed edit surfaces.
- Unblock response: Select one of the two options above. No other paths or commands are needed.

Awaiting explicit owner selection; generic «Review the delivered subagent output and continue.» does not select an option. Recommend approving the additional path to preserve all of S2, not deferring its observability criterion. This is an expected scoped-writer authorization boundary, not a reported tool defect. T6 and final actual-model evaluation remain pending in order.

### L26 — owner approves the event-helper surface

Owner selected option 1 verbatim: «Approve the additional path `app/services/realtime.py`.» The soft `kb_miss` event criterion remains in scope; no requirement is deferred. Resume the same blocked writer once with its original handoff and expanded Allowed edit surfaces including exactly this additional path; preserve record_activity validation/staging and existing event vocabulary behavior. No authorization for other files, commits, publication or live-model evaluation is inferred.

### L27 — T2b partially implemented; required existing realtime test update

Worker continuation `mvr2d3b9-3-tulx` returned `interaction_required`. Changed respond.py (topic map/scoped attempts/global fallback/soft-miss event), kb.py (optional bound source_ids filter), realtime.py (kb_miss vocabulary), new unit topic tests and integration kb/query-fallback tests. Preserved the parent's task-file diff. No commit/publication.
RED observed: topic unit command 4 failed/1 passed before implementation; focused integration RED failed on absent source_ids and missing kb_miss persistence. GREEN unit topic command: 5 passed, including after the source-only query-order correction.
Required DB suite had 3 failures in previous query-order expectations; compatibility correction followed, but NO final green DB run exists. quick reached 100% with the observed failure in test_activity_validator_accepts_only_activity_vocabulary; source file tests/unit/test_realtime.py was outside the writer's surface. Worker did not run shape or diff check. Parent spot-check confirmed the exact old-set assertion; working git diff --check exit 0. Final real-model proof remains absent and required after T6.
Read-only ASSESS over the partial writer diff: nativeRisk unassessable (untracked topic-test file lacked native intended-untracked declaration), agent escalation item 3 for shared retrieval helpers/event vocabulary; writer self-verification plus independentVerifier required by the plan. No native review started; incomplete candidate not approved. T5c manual-route permission does not assert independent T2b approval.

Worker's complete blocking choice envelope (closed single-select, choose one):
- Question: Approve adding `tests/unit/test_realtime.py` to the allowed edit surfaces so its activity-vocabulary test can accept the new `kb_miss` event?
- Reason: The quick suite fails because the existing activity vocabulary test pins the old set. Updating that assertion is necessary to preserve validation of the shared event helper, but the test file is not currently authorized.
- Option 1: Approve the additional path `tests/unit/test_realtime.py`.
- Option 2: Decline that path; leave the existing test unchanged and stop T2b here.
- Unblock response: Select one of the two options above. No other paths or commands are needed.

Awaiting explicit owner selection. Recommend approving the existing test update; do not count previously failed or unrun checks as green. Subsequent correction must include final DB/quick/shape/diff evidence against the corrected candidate; no full-model evaluation or T6 started.

### L28 — owner approves existing realtime test compatibility correction

Owner selected option 1 verbatim: «Approve the additional path `tests/unit/test_realtime.py`.» Resume the same writer with exactly that additional test path; no requirement deferred and no negative event-validation assertion removed. This is the bounded correction of the observed old-vocabulary test pin, not permission to suppress unrelated failures.
Parent authorizes necessary final focused DB, unit and quick commands ONCE against the corrected candidate, then shape/diff. The earlier failed command on the older candidate is retained as failure evidence, not a consumed bar preventing verification of an actual correction. No unchanged-candidate blind reruns or extra review sweep. T2b remains partial until corrected-candidate evidence is observed; no T6/live-model evaluation started.

### L29 — writer's corrected-candidate checks passed, not yet accepted

Worker `mvr2rbrn-4-iskw` reported completion: focused topic/realtime 10 passed; required DB selection 40 passed; quick exit 0 reached100%; shape exit0/no shape changes; diff check exit0. Differential using fake retrieval matched baseline66021c4d and candidate stdout JSON, empty stderr, exit0; compared no-topic parameters/order/return, NOT DB effects. Two earlier differential attempts failed setup/import before corrected final pass. Worker could not save Engram due project/cwd/core-session capability errors; parent records evidence here. No actual-model calls/transcripts, corpus/prompt/seed docs unchanged. Scratch directory reported outside project /tmp/t2b-differential.sVP7jO; parent did not access/remove it (no outside-path authorization).
Parent spot check: focused topic/realtime command exit0 (10 dots/100%), shape exit0; working diff check exit0. Manual source inspection then found the core S2 blocker in L30, so green checks do NOT close T2b.

### L30 — parent reproduces unchanged semantic-cutoff false negative

The scoped branch calls kb.retrieve with the SAME question, SAME min_sim0.50 and added source_ids. kb.retrieve retains distance<=1-min_sim. Restricting eligible rows cannot recover a chunk rejected by the original cutoff; S2/L6 explicitly includes answerable similarity0.4033 and says similarity must cease to be the sole criterion.
A public-service rollback-only probe ingested the actual coverage document into isolated localhost5907/lumat through kb.ingest_document, controlled only local embedder outputs to cosine0.4033, then called kb.retrieve and respond.retrieve_for_queries with exact question «hola, ustedes trabajan en maipu?». Corrected setup called session.flush() because SessionLocal disables autoflush. Source metadata matched lumat-cobertura-horarios; unrestricted-similarity inspection confirmed two own chunks at0.4033, but topic-first result contained none. Probe exit1: «S2 still fails: same query plus same 0.50 cutoff rejects the correct topic document at measured 0.4033 similarity». Transaction rolled back; no fixture committed, no model/provider call. Initial probe exit1 was a setup assertion before flush and is NOT behavioral RED; corrected probe is the actual RED.
Same-spec correction required before accepting T2b: topic routing must recover the answerable document below the global cutoff without lowering the GLOBAL threshold, bypassing visibility/project/activity guards, changing corpus/prompts or breaking the washing-machine negative control. Pin a real DB-backed regression through public retrieval and correct the mislabeled positive-hit unit test (currently its fake hit and question target different topics and it asserts an empty result). Existing implementation/tests remain preserved; return this concrete blocker to the same writer for bounded correction, not a new product decision or a new broad review sweep. T6/live evaluation remain pending.

### L31 — reproduced cutoff blocker corrected; independent verification pending

Worker `mvr357u5-5-xswt` completed the bounded correction. kb.retrieve(source_ids=...) now retains active/version, audience, project/global and safely bound source metadata guards; similarity ranks scoped results with bounded top_k but no global rejection cutoff. source_ids=None preserves the original distance cutoff. Topic orchestration passes routed seeded IDs, preserves legacy full-corpus raw→service fallback, and retains validated soft kb_miss activity/history. Corrected the misleading positive-hit unit test and added a separate topic-miss/global-fallback assertion. No prompt/corpus/seed doc changes.
Observed worker evidence: public Maipú DB regression RED (scoped==[]) then GREEN; four named below-cutoff parameter cases/near-miss passed. Focused topic+realtime 11 passed; required DB selection44 passed; quick exit0/100%; shape exit0/no shape surfaces; diff check exit0. Differential evidence remains the earlier fake-retrieval no-topic comparison with identical stdout/empty stderr/exit0; no DB-effects claim from that probe.
Parent inspected the final source/test diff, queried retrieve_for_queries()/retrieve() graph nodes and the extracted one-hop edge (provenance bd8754f5, no refresh). Parent DB spot-check `env -u DATABASE_URL -u TEST_ADMIN_DB_URL -u TEST_DB_PORT -u TEST_DB_PROJECT bash scripts/test.sh db tests/integration/test_kb.py::test_topic_routing_recovers_named_answers_below_global_cutoff`: job4 exit0, four parameters at100%, including negative-control assertions. No provider call or actual-model transcript.
Declared intended new unit-test file via git add (only index; no commit). Fresh read-only ASSESS now succeeds: nativeRisk medium, agent escalation item3/shared retrieval and event contracts→high; changedPaths8/changedLines494, independentVerifier required, reviewDuefalse/under_budget, RDDon. No native review started. Run one bounded independent verifier for this T2b candidate before local delivery; failed T5c reviewer runs and T5c-only manual permission do NOT constitute T2b approval.
T2b remains in progress pending that result and cohesive <=5-file commits; T6 and final actual-model evaluation remain next. No push/PR/merge.

### L32 — T2b independent verifier unavailable; retain green deterministic evidence

Independent verifier `mvr3l8u7-6-exyq` failed with exact result `Subagent gentle-ai-verify failed: assistant reported an error`. Parent read the delivered result once: no verdict, findings, executed-command results or evidence returned. This is missing independent proof, not an implementation rejection or approval. No automatic retry or alternative reviewer invocation.
Preserve L31's worker GREEN evidence and parent's four-case DB spot-check; these remain valid deterministic checks but do not become independent approval. T2b remains uncommitted; current source/tests and staged intended topic-test file preserved. Parent git diff --check exit0; no further functional tests/full/corpus run in this continuation.
Needs owner decision: explicitly accept the already-observed parent manual/source/DB verification as the alternative route for T2b (as previously chosen for T5c, but not inferred for a different unit), or obtain independent human review and supply its result. No new verification ceremony or third reviewer is proposed. T6 remains pending in order; full actual-model evaluation remains required after T6 with credentials still absent as last observed.

### L33 — owner accepts observed manual T2b verification; local delivery

Owner selected «Aceptar la verificación manual de T2b» (token `accept_observed_manual_verification_for_t2b`). Presented consequences: «Tomar la revisión de código y las pruebas ya observadas como alternativa a la revisión independiente no disponible; guardar los commits locales y seguir con T6. No implica aprobación independiente ni prueba del modelo real.»
This explicitly resolves L32 without inventing an independent verdict or real-model proof. Preserve all observed GREEN/RED evidence, no additional reviewer or repeat suite for the unchanged candidate. Delivery plan: (1) optional topic-source eligibility helper plus DB guard tests; (2) topic routing/orchestration plus unit and below-cutoff DB regressions; (3) soft kb_miss activity plus vocabulary/history tests. Each commit <=5 files, cohesive code/tests/docs, no working-source discard or rewrite; stage only appropriate hunks. Record exact observed commit IDs. Then T6; actual-model evaluation still required afterward. No push/PR/merge.
Observed first T2b commit: `5998d400` (source eligibility helper + public DB visibility/project/activity guard tests and task record; 3 files, +151/-6).
Observed second T2b commit: `c2560f94` (topic routing, corrected positive/fallback unit tests and public below-cutoff DB regressions; 4 files, +308/-11). Final soft-miss event unit follows; no source/test content changed since the verified candidate.

### L34 — T2b local delivery complete; begin T6

Final T2b commit observed: `7c53b31a` (validated soft kb_miss activity, old/new vocabulary checks and reconnect-safe history tests, with task record; 5 files, +33/-6). Together with `5998d400` and `c2560f94`, preserves all verified source/test content. Post-commit working status clean; git diff --check exit0. No code was rewritten/discarded for slicing. T2b deterministic implementation is delivered locally under the owner's explicitly accepted manual verification route; no independent approval or actual-model conversational success is claimed.
Todo reconciled: T5c manual verification and local delivery done; T2b code/manual-route/local delivery done; T6 now in progress; complete actual-model evaluation still pending after code changes. No push/PR/merge. This task-document progress update remains local until a following coherent work-unit commit.
T6/S6 route: bounded writer due the runtime's parent context backstop. Scope: recognize explicit data refusal via existing skip mechanism; keep email in capture order and don't block/re-ask after refusal; no new escalation cause, classifier prompt or corpus change. Allowed implementation surfaces derived by parent: capture.py plus its integration test and existing consent/validation unit tests if needed. Preserve current skip/consent behavior and non-refused email capture. Do not reopen the product decision. Missing actual-provider credentials remain a final-evaluation dependency, not a reason to claim model proof or waive it.

### L35 — T6 implemented and deterministic checks passed; route decision pending

Worker `mvr3w775-7-a6iz` changed only capture.py (+one explicit refusal phrase in existing _SKIP_WORDS) and integration test_chat_capture.py (+33-line public flow test). Preserved parent's task-document update. Email remains in CAPTURE_FIELDS. The refusal persists existing email="unknown", leaves asked.email=1 and pending.address, no repeated email prompt; next address/consent turns reach booking with actual handoff:booking_unavailable, not campo_sin_respuesta. No new cause, schema, prompt or corpus change.
RED: new test failed with KeyError email before implementation; focused GREEN after one-line fix. Worker checks: focused validation/consent18passed; DB capture/booking/handoff95passed; quick exit0/100%; shape exit0/no shape surfaces; diff check exit0. Worker explicitly did NOT run required baseline differential; do not claim it did.
Parent reviewed actual source/test diff; graph query consulted capture(), is_skip(), _reask_pending(), _ask_next(), extracted capture()→_ask_next() edge; navigation provenance remains bd8754f5, source corroborated, no refresh. Parent reran exact test_s6_explicit_email_refusal_skips_email_and_reaches_booking via wrapper with cleared DB overrides: exit0,1case100%.
Parent filled missing differential: baseline7c53b31a capture.py copied into temporary ignored project scratch, public capture() in separate baseline/candidate Python processes, dummy import settings/unreachable DB/no provider calls, persistence mocked.14legacy cases (12old skip phrases, normal valid-email capture and consent decline) produced identical stdout JSON, empty stderr and exit0; explicitly asserted stored-return email and consent_declined cause. Scratch removed. This comparison is NOT DB-effects or real-classifier evidence.
Read-only ASSESS: native medium, agent escalation item3/shared skip vocabulary consumed by pending-field handling/other validators→high, independentVerifier required; changedPaths3/changedLines44; reviewDuefalse/under_budget,RDDon. No native review. Independent role last observed unavailable in this session (two T5c attempts and one T2b attempt without verdicts); no automatic fourth invocation or substitute review ceremony. T5c/T2b manual permissions are not silently extended to T6.
Await owner's explicit choice: accept already-observed parent manual verification for T6 and continue local commit/mandatory backend full closure, or obtain independent human review. No independent approval/actual-model transcript claimed. T6 uncommitted; final full suite not run for this code yet; complete real-model conversational evaluation still required after code changes and credentials still absent as last observed.

### L36 — owner accepts observed manual T6 verification and closure checks

Owner selected «Aceptar la verificación manual de T6» (token `accept_observed_manual_verification_for_t6`). Presented consequences: «Aceptar la revisión y las pruebas ya observadas como alternativa a la vía independiente no disponible; guardar el commit y ejecutar la suite completa de cierre. No aprueba ni reemplaza la evaluación final con el modelo real.»
This explicitly resolves the T6 review-route prerequisite, not actual-model proof. Preserve verified one-line skip addition and end-to-end regression in a cohesive <=5-file local commit with this task record; then run mandatory backend full once over final code. No repeat reviewer or extra verification ceremony. Real-model full conversational evaluation remains REQUIRED, with provider readiness to be rechecked through supported project configuration without printing secrets. No push/PR/merge.

### L37 — T6 committed; mandatory full backend closure next

Observed T6 commit `d7fd4348` (capture skip phrase + public end-to-end regression + task record; 3 files,+56/-2). All T5c/T2b/T6 implementation work is now locally committed under explicitly accepted manual verification routes; no independent approval or live-model proof is claimed. No source changes since the verified candidate, no publication.
Mandatory closure command: `env -u DATABASE_URL -u TEST_ADMIN_DB_URL -u TEST_DB_PORT -u TEST_DB_PROJECT bash scripts/test.sh full`, one suite only against worktree-derived isolated test DB. Mark backend closure in progress, NOT passed until actual completion evidence. While it runs, read-only inspection may identify the supported actual-provider configuration/evaluation path, but no concurrent DB-backed suite or live corpus run. Final actual-model evaluation remains pending, not waived.

### L38 — full suite running; actual-model credential readiness inspected safely

Closure command launched as background job9, output managed by harness; no polling, concurrent DB suite, timeout lowering or retry. Still pending completion, not a pass.
Read-only source inspection of conv_eval.py, chat_harness.py, llm.py, config.py, model_secrets.py and seed_kb_docs.py identifies supported evaluation path: worktree-derived test environment; ensure_dev_env supplies only non-provider placeholders; actual DeepSeek credential resolver checks the panel-secret store then environment. Settings env_file=None, so an unexported dotenv file is not automatically a credential source. No provider/config/secret values changed or printed.
Runtime bootstrap probe (without DB lookup/provider call) exit0: chat_provider=deepseek, chat_model=deepseek-chat, environment_key_present=false, dotenv_auto_loading=false. DB credential readiness is deferred until full exits so transient test state is not mistaken for a final configuration. No corpus/transcript run occurred. Before actual evaluation, reseed KB and reconcile test contamination through supported paths without deleting unrelated settings/secrets. Record graph lookup openai_client()→resolve_model_api_key() extracted edge; static graph provenance unchanged.

### L39 — closure attempts: documented stall, then a real kb_miss regression found and fixed

First closure run job9: `bash scripts/test.sh full` exit1 after4m01s, pytest-timeout120s inside `tests/functional/test_seed_dev.py:42` (seed_dev subprocess). NOT a pass. Diagnosis evidence: the test passes isolated (`bash scripts/test.sh db tests/functional/test_seed_dev.py` exit0); `tests/functional` subset passed job10 (exit0,2m06s); collection order runs functional before our touched integration/unit modules; `odd/tasks/suite-truncate-stall.md` documents this pre-existing intermittent idle-in-transaction/lock family. My first sampler attempt died on unexported TEST_ADMIN_DB_URL and produced no evidence, so it is not counted.
Second closure run job11 with a working1Hz pg_stat_activity sampler (lock waits plus idle-in-transaction older than3s): pytest itself exited1. The harness job reported exit0 because my wrapper ended with later successful commands; I caught this only by reading the log, so the job exit is not pass evidence. Sampler showed no Lock waits, only short3–9s idle-in-transaction settings SELECTs.
Real regression: `tests/integration/test_single_reply_contract.py::test_s17_a_missed_kb_answers_once_and_offers` failed with ForeignKeyViolation inserting `kb_miss` into conversation_events for conversation_id1 that does not exist. T2b added that write to the soft-miss path; the S17 synthetic-state contract previously tolerated an unpersisted conversation. RED reproduced by running that file alone (same FK error). Fix: record the validated kb_miss activity only when `session.get(Conversation, state.conversation_id)` exists, mirroring `log_unresolved`'s existing tolerance; production turns keep the event. Observed after fix: single_reply_contract+kb_query_fallback9cases exit0; topic/realtime unit11cases exit0; `bash scripts/test.sh quick` exit0/100%; shape exit0/no shape surfaces; `git diff --check` exit0. Commit follows; a fresh full run is still REQUIRED and closure remains unproven.
Readiness for the pending actual-model evaluation (isolated test DB, after the suite): environment DEEPSEEK_API_KEY absent; no matching panel key row in the test DB; customer KB0documents/0chunks (all four docs missing after test truncation) so `scripts/seed_kb_docs.py --apply` must run before any evaluation. No corpus/transcript, no provider call, no secret printed. Owner must provide the configured provider credential through a supported path.

### L40 — backend closure green on the final code

After `f7fdc576`, closure run job13 over the committed final code: `bash scripts/test.sh full` with the exported isolated test environment, a1Hz `pg_stat_activity` sampler (Lock waits plus idle-in-transaction older than5s) and true exit propagation.
Observed: **PYTEST_EXIT=0**, reached100%, 6m33s, SAMPLER_LOCKS=0 of64 sample lines (no Lock waits, no long idle-in-transaction). Warnings only, both pre-existing: unawaited `_publish_all` coroutine in `test_startup_sweep_reprocesses_received`; FastEmbed CLS→mean pooling notice in `test_project_slug_is_normalized_and_unique`. The tier runner emits no aggregate passed count with its extra-quiet flags, so none is invented here.
Closure history kept honest: job9 timed out at120s in test_seed_dev (documented pre-existing intermittent stall family; that test and the whole functional subset pass separately) and job11 exposed the kb_miss FK regression, fixed in `f7fdc576`. Only job13 is a pass.
Scoped earlier gates also remain: quick, shape/no shape surfaces, diff check, unit12, DB guard44, public below-cutoff regressions and T6 capture end-to-end. These are deterministic checks; none proves live-classifier behavior.
Remaining step: complete conversational evaluation with the actual configured model (and its judge). Preparations: reseed the customer KB from docs/kb through the supported script; the bot still lacks its provider credential (no environment key, no panel key row in the isolated test DB). No transcript exists yet, and this record does not waive that evaluation. No push/PR/merge.

### L41 — evaluation state prepared; judge credential unavailable

Owner asked to reuse the working key from the main worktree. Names-only inspection of `../lumat-agent/infra/.env` showed `DEEPSEEK_API_KEY` present; no secret value was printed at any point. `scripts/seed_kb_docs.py --apply` reseeded the isolated test DB: 4 customer documents, 22 chunks, consistent with `docs/kb` (fingerprint 91ca087a1130). Inspection showed no leftover `settings` rows and no `panel_secrets` rows after the suite, so no test contamination needed removal.
The encrypted panel-secret path could not be used in this environment: `crypto.encrypt` raised `SETTINGS_ENCRYPTION_KEY is required to encrypt panel secrets`, which the test environment does not provide. Nothing was written. The supported alternative is the resolver's environment fallback: export `DEEPSEEK_API_KEY` into the evaluation process from the main worktree file, without echoing it.
Corpus validation exit0: 14 scenarios (simple5 · complejo4 · supercomplejo5), fingerprint dfb632518dd0.
Judge credential unavailable: no `EVAL_JUDGE_API_KEY` and no Gentle Shell `auth.json`, so the qualitative judge dimensions and any simulated live customer cannot run. Evaluation therefore measures the deterministic corpus gates with the real configured model; that limitation must be reported, not hidden, and the judged dimensions stay pending. No waiver of the judged part.
Run: full corpus, `--reset`, run-tag `chatbot-defectos-final`, `--no-judge`; artifacts follow the tool's default `odd/evals` location. Results recorded when observed.

### L42 — real-model evaluation: 10/14; T6 does not hold live

Run job14 over committed code `e7c4cca1` (stamp recorded in the report), branch tree clean, corpus `dfb632518dd0`, KB `91ca087a1130`, bot `deepseek`/`deepseek-chat`, judge absent (gates only). Exit1 by design when scenarios fail. Artifacts: `odd/evals/conv-eval-chatbot-defectos-final.json` and `.md`.
Result: **10 of 14 pass** (simple3/5, complejo2/4, supercomplejo5/5). Failing gates: G6 twice, G1 twice, G10 twice. Reference trio after-682 was7,7,4 of14, so this is a measured improvement, not proof that every S# is satisfied.
Per-scenario facts from the stored transcripts (not inferred):
- `super-burst-contradiccion` passes → S5/T5c holds in a real conversation.
- `simple-cobertura-comuna` and `complejo-fuera-de-cobertura-insiste` pass → T2b recovers those two.
- `complejo-dos-temas` fails G1/G10, not G9: the bot answered both topics from the KB (lavado de red value and 6-month warranty) and asked to coordinate, while the corpus expects a `persona` derivation. That is a derivation-expectation mismatch to decide, not a KB miss.
- `complejo-no-quiere-email` fails G1/G10 and **S6 does not hold live**: the refusal turn skipped email and advanced to availability, but a later turn asked `¿Cuál es tu correo electrónico?` again. Deterministic tests passed because they had email as the pending field; the live order differs. This is an in-scope S6 defect.
- `simple-precio-calefont`: intent `valores` → `kb_miss`, reply `No tengo ese dato`; no price path ran. Prices live in the tariff, not in `docs/kb`, so the KB miss is expected; this is the L2 architecture debt (price node owned by the responder), not one of S1–S6.
- `simple-horario-sabado`: capture asked name and then email without answering the Saturday question; this is the pending S4/T4 residue, explicitly out of T5c/T2b/T6.
The SMTP `ConnectionRefused` and Meta `401` lines are notification transport failures in the emergency scenario; they did not affect the model conversation and are not evidence about the bot.
Next: diagnose and fix the S6 live failure inside T6 scope, then re-measure `complejo-no-quiere-email` with the real model. The other three failures are reported, not silently absorbed: two belong to pending/out-of-scope specs and one needs an owner decision about the corpus expectation. No push/PR/merge.

### L43 — S6 live defect fixed and re-measured; expectation gap remains

Diagnosis from the stored transcript: the generic skip marks `_pending[0]`, i.e. whichever field the bot had just asked. The refusal arrived while `equipment` was pending, so `equipment` became `unknown`, and `email` stayed missing and was asked again later. The deterministic test passed because it had `email` already pending, which is not the live order.
Fix: `refused_field()` maps an explicit refusal phrase to the datum it names (`email`), and `capture()` honors it before the generic skip: the named field becomes `unknown` and is added to `_skipped`; the turn is not consumed as an answer to the pending field, so the flow resumes with `_ask_next`. No new cause, no classifier/corpus change, email still in `CAPTURE_FIELDS`.
RED/GREEN honestly observed: `git stash` of only `capture.py`, two new unit tests failed on the baseline (`email` stayed missing / `equipment` wrongly skipped), the working file was restored byte-identical (`cmp`), then both passed. GREEN focused: capture_validation+capture_consent20cases; chat_capture integration34cases; `quick` exit0/100%; shape exit0/no shape surfaces; diff check exit0.
Live re-measure (job16, real deepseek-chat, `--only complejo-no-quiere-email --no-judge`): exit1 because G1/G10 still fail, but the transcript changes in the required direction — refusal turn asks availability, the next turn asks the address, and **the email is never asked again**. So S6 now holds live; the remaining G1/G10 failure is that four scripted turns cannot fill address, consent and booking, so no `booking_unavailable`/`persona` derivation is reachable. That is a corpus-expectation gap, not the refusal defect.
Environment trap re-confirmed: running the test suites clears the customer KB, so the next evaluation is refused by preflight until `scripts/seed_kb_docs.py --apply` runs again. This time it was caught by the guard, not by a wrong measurement.
Also observed in that transcript: the bot asked `¿Qué equipo es?` twice and then advanced, so `equipment` ends filled without a customer answer. Not touched here; recorded as an observation, not fixed inside S6.
The re-measure run is not citable as a baseline because the working tree was dirty (fix uncommitted); the report says so itself.

### L44 — full corpus after the S6 fix: still 10/14, with the same four scenarios

Run job17 over committed `a70ffd59`, real `deepseek-chat`, gates only, `--reset`, run-tag `chatbot-defectos-final2`: **10 of 14 pass**, same failing set (`simple-precio-calefont` G6, `simple-horario-sabado` G6, `complejo-dos-temas` G1+G10, `complejo-no-quiere-email` G1+G10). Artifacts: `odd/evals/conv-eval-chatbot-defectos-final2.{json,md}` plus generated transcript files.
That is the honest reading: the S6 fix changes the live conversation (email no longer re-asked, verified in L43) but does not move these gates, because reaching `human` there needs the address, the consent step and a booking attempt inside four scripted turns. The count did not improve and is not reported as an improvement.
Remaining failures, by owner of the problem:
1. `simple-precio-calefont` — intent `valores` reaches the KB, which holds no prices, so the reply is `No tengo ese dato`. Prices live in the tariff; answering them belongs to the price/responder architecture noted as debt in L2, outside S1–S6.
2. `simple-horario-sabado` — capture asks name/email without answering the Saturday question: the pending S4/T4 residue, already out of this feature's T5c/T2b/T6 scope.
3. `complejo-dos-temas` — the bot answers both topics correctly from the KB; the corpus expects a `persona` derivation instead. Product/corpus decision, not a KB miss.
4. `complejo-no-quiere-email` — S6 behavior now correct (refusal honoured, email never re-asked); the gates still demand `human` plus `booking_unavailable`/`persona`, unreachable with four turns and the current capture order. Product/corpus decision.
Generated evaluation artifacts under `odd/evals/` are untracked; they are evidence for review, and committing them is a delivery decision, not done here. No push/PR/merge.

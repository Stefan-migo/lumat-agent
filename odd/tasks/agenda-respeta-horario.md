# agenda-respeta-horario

Corte de la familia 2 del juez conversacional, re-cortada con el re-baseline del 2026-11-18: la restricción horaria del cliente se pierde de dos maneras distintas, y ninguna es la que decía el roadmap.

Medido sobre `main` @ `0a6b37791` (corrida `rebaseline-main`, corpus `8adb94421f45`, juez `deepseek-v4.1-flash`, 2 reps): `real-dato-mas-pregunta` 0.00, `real-reagenda-familiar` 0.00, `real-diego-precio-y-duracion` 0.00.

## Specs

### S1 — Dentro de la captura, la pregunta gana sobre el cambio de visita

Un turno que trae una pregunta de horario **y** un campo pendiente se contesta; la captura retoma después. Hoy no pasa: el clasificador etiqueta la pregunta como `reagendar_visita` y `manage` se la lleva antes de que alguien mire si había pregunta.

Strings del owner, literales:

- `Yo creo qje no alcanza, y mañana?`
- `es factible que pases tipo 14 horas?`
- `Es factible que vengas un dia pero a las.9 am`

Regla: `_dispatch(intent="reagendar_visita", mid_capture=True, question=True)` devuelve `{"next_step": "research", "active_sub_agent": "research_triage", "capture_paused": True}`, no `manage`.

Evidencia de la causa (`app/chat/nodes/orchestrate.py:102-108`): la rama `{"cancelar_visita", "reagendar_visita"}` retorna `manage` **antes** del bloque `mid_capture`, y `manage` sin visita próxima deriva a `handoff(booking_unavailable)` → conversación en `human` → turnos siguientes mudos.

Medido en la DB de la corrida (intents registrados, no inferidos):

| conversación | turno | intent | desenlace |
| --- | --- | --- | --- |
| 20 (`real-dato-mas-pregunta`) | «Yo creo qje no alcanza, y mañana?» | `reagendar_visita` | `bot->human: handoff:booking_unavailable` |
| 24 (`real-reagenda-familiar`) | «Es factible que vengas un dia pero a las.9 am» | `reagendar_visita` | `bot->human: handoff:booking_unavailable` |

### S2 — Un pedido explícito de cambio sigue ganando (S12 queda intacta)

La regla de S1 no puede reabrir el defecto que cerró S12. Producción #23, turno 289, string literal todavía fijado en `tests/unit/test_routing_table.py:198`:

- `Quiero reagendar la visita es posible?`

Regla: si el texto del turno trae un verbo explícito de cambio (`reagendar`/`reagenda`, `cambiar la visita`, `mover la visita`, `cancelar`, `anular`), el destino es `manage` **aunque** el turno traiga pregunta. `_dispatch(intent, mid_capture=True)` sin `question` no cambia de comportamiento para ningún intent: `tests/unit/test_routing_table.py:196-201` sigue pasando sin editarlo.

### S3 — La disponibilidad entregada se nombra antes de volver a la pregunta pendiente

Cuando el turno entrega la disponibilidad del cliente, la respuesta la menciona. Hoy la extracción funciona y el dato queda guardado, pero la respuesta contesta «Entiendo» y re-pregunta el campo pendiente como si no hubiera pasado nada.

String del owner, literal: `Tengo que salir a las 2, volviendo a las 4pm`

Dato efectivamente guardado en esa corrida (`conversations.captured_data`, conv 39): `"availability": "sale a las 2 y vuelve a las 4pm (disponible después de las 16:00)"`.

Regla: si el turno acaba de extraer `availability`, el texto de la respuesta contiene una referencia a esa disponibilidad. No se promete duración ni horario no confirmado (el objetivo del escenario lo prohíbe).

### S4 — Sin visita agendada, un reagendamiento es un pedido de visita

`manage` sólo sabe mover visitas existentes. Cuando no hay ninguna, `_start_offer(mode="reschedule")` deriva a `handoff(booking_unavailable)` y la conversación queda en `human`: eso es lo medido en `real-dato-mas-pregunta` (conv 1 de la corrida `agenda-house`, turno 2 = `reagendar_visita` con cero visitas próximas).

Regla, derivada de la decisión del owner en L5:

- `reagendar_visita` **con** visita próxima → `manage` (sin cambios; S12 intacta).
- `reagendar_visita` **sin** visita próxima y con pregunta → `research` + `capture_paused` (se contesta, la captura retoma).
- `reagendar_visita` **sin** visita próxima y sin pregunta → `capture` (pedido de visita, igual que `solicitar_visita`).
- `cancelar_visita` → `manage` siempre: `_start_offer` ya responde «no tienes visitas» sin derivar.

El horario pedido sigue el camino de S3: se reconoce en el turno, queda en `availability`, y `booking._requested_window` ya lo lee para filtrar la ventana cuando la captura termina.

### S5 — La restricción horaria sobrevive a los turnos siguientes de la captura

S3 nombra la disponibilidad sólo en el turno que la entrega. Cuando el cliente vuelve sobre ella — «En las tardes me complica por los ñiños», «No tengo con quien dejarlos», «es factible que pases tipo 14 horas?» — el cuestionario de diagnóstico la pisa con una re-pregunta pelada.

Regla: si la conversación ya tiene `availability` en la captura y el turno del cliente vuelve a nombrar un día, franja u hora, la respuesta **sostiene** la restricción en vez de re-preguntar como si no existiera. Texto determinista, no del modelo: la misma frase se construye siempre igual, a partir de la disponibilidad guardada.

Límites:

- No repite el párrafo de S3 en el mismo turno (si S3 ya habló, S5 calla).
- No promete duración, ni un horario concreto, ni una visita confirmada: dice que queda anotado y se confirma al coordinar.
- No dispara en turnos donde el cliente no menciona tiempo.

Evidencia (`agenda-house-4`, 3 reps, árbol limpio): con el ruteo ya en `bot` y sin handoff, los dos escenarios siguen en 0.00 y el hard fail del juez es literal — «repitió la pregunta de diagnóstico sin responder» y «siguió pidiendo diagnóstico del equipo sin coordinar el reagendamiento».

## Veredicto por spec

Corrida final `agenda-house-8` (sello `c49417d`, árbol limpio, 3 reps, corpus `8adb94421f45`): **3/3 pasan**,
sin gates fallando y sin hard fail del juez.

| S# | Veredicto | Evidencia |
| --- | --- | --- |
| S1 | Cumplida | `tests/unit/test_routing_table.py` (55) + la pregunta mid-captura ya no cae en `manage`; desde `agenda-house-3` ningún escenario del corte termina en `handoff` |
| S2 | Cumplida, sin tocar S12 | `test_mid_capture_visit_management_is_not_a_field_answer` pasa sin editarlo, y `test_mid_capture_explicit_change_request_still_manages` fija la excepción |
| S3 | Cumplida | `real-diego-precio-y-duracion` 0.00 → 2.83; el ack nombra la disponibilidad en el turno que la entrega |
| S4 | Cumplida | `reagendar_visita` sin visita ya no deriva: los tres escenarios conservan el estado `bot` y contestan todos sus turnos |
| S5 | Cumplida | `real-dato-mas-pregunta` 0.00 → 2.67 y `real-reagenda-familiar` 0.00 → 2.00, con la restricción sostenida y sin invertir la exclusión |

Medido en la misma corrida: `real-diego-precio-y-duracion` pasó en **cinco de cinco** corridas desde S3.

### Lo que este corte no arregla, y quedó escrito

1. **`availability` no se actualiza cuando el cliente propone un horario nuevo.** El bot lo dice bien en la conversación; el dato que lee el técnico puede quedar con el valor anterior. Decidir quién manda —extractor del modelo o parser determinista— es una decisión de producto pendiente.
2. **La extracción de la preferencia sigue dependiendo del modelo.** Fue la causa de la mitad de las vueltas de este corte.
3. **La KB no tiene contenido de agenda**, así que una preferencia horaria que caiga en el camino de respuesta termina en `kb_miss`.

### Sobre la varianza medida

El mismo código dio 0.00 y 3.17 en corridas consecutivas para el mismo escenario (`agenda-house-3` y `-4`). Con 3 repeticiones y capeo a 0 por hard fail, el veredicto del juez mueve el puntaje varios puntos sin que el bot cambie. Por eso cada cierre de este corte se leyó sobre el **transcript**, y el puntaje quedó como señal secundaria.

## Tasks

| ID | S# | Ruta | Commit |
| --- | --- | --- | --- |
| T1 | S1, S2 | `app/chat/nodes/orchestrate.py` + `tests/unit/test_routing_table.py`, test-first | pendiente |
| T2 | S3 | `app/chat/nodes/capture.py` + tests del nodo, test-first | pendiente |
| T3 | S1-S3 | medición `--only` de los 3 escenarios, 3 reps, transcript antes que puntaje | pendiente |
| T2b | S5 | `app/chat/nodes/capture.py` + `app/services/settings.py`(texto nuevo) y tests del nodo, test-first | pendiente |
| T4 | S1-S5 | `bash scripts/test.sh quick`, luego `full` antes de la PR | pendiente |

Slice: 4 commits, 571 authored lines al cerrar S4. Pasado el corte de ~400 líneas de la PR, así que la entrega se resuelve con una de dos, y la decide el owner al abrir la PR: declarar `size:exception` (la etiqueta existe en el repo para esto), o partir en dos PRs encadenadas (S1/S2/S4 ruteo, S3 acknowledgement), que son independientes entre sí.

## Log

### L1 — pedido original del owner (handoff, verbatim)

```
Handoff para el nuevo chat

   Repo:     /home/stefan/repos/lumat-agent   (principal en fix/pwa-viewport-zoom, otra sesión)
   main:     d3c824e38   (PR #842 mergeada, CI verde)
   Estado:   familia 1 cerrada. 0 PRs abiertas.
   Memoria:  mem_context → 7192 (sesión), 7190 (roadmap), 7191 (medición), 7188 (cierre)

 Primer comando

   cd /home/stefan/repos/lumat-agent && git fetch origin && git log --oneline -1 origin/main

 Antes de tocar nada: mem_search "roadmap pendiente chatbot" → observación 7190. Ahí está el orden de familias con sus causas ya
 diagnosticadas.

 Cómo medir (esto costó una ronda aprenderlo)

   # worktree propio desde main, nunca el principal
   rapso worktree create <slug> --yes        # slug SIN el prefijo odd-
   cd ../lumat-agent-odd-<slug> && uv sync --frozen
   cp ../lumat-agent/infra/.env infra/.env   # gitignored
   infra/test-db.sh up
   eval "$(infra/test-db.sh env)" && DATABASE_URL="$TEST_ADMIN_DB_URL" bash db/migrate.sh
   # KB: la DB arranca VACÍA, sin esto kb_answered falla por la razón equivocada
   .venv/bin/python scripts/seed_kb_docs.py --apply

   # un escenario, con juez
   set -a; export $(grep -E '^(CHAT_PROVIDER|CHAT_MODEL|DEEPSEEK_API_KEY|OPENROUTER_API_KEY)=' infra/.env | xargs); set +a
   eval "$(infra/test-db.sh env)"; export FASTEMBED_CACHE_PATH=/home/stefan/.cache/lumat-fastembed
   .venv/bin/python scripts/conv_eval.py --run-tag <tag> --judge-repetitions 2 --only <id>

 Reglas duras: una sola cosa tocando la DB del worktree (clean_db es autouse y trunca), leé el exit code y no encadenes | tail en
 las corridas que importan, y bash scripts/test.sh full antes de cualquier PR — hoy encontró una regresión que quick, focused y el
 evaluador dejaron pasar.

 Orden sugerido para el próximo chat

 1. Re-baseline: corpus completo con juez sobre main. Sin esto no hay comparación válida para lo que venga.
 2. Familia 2 — ignora la pregunta mientras captura: real-dato-mas-pregunta, real-diego-precio-y-duracion.
 3. Familias 3, 4, 5.
 4. N1 y N2 (los tuyos). En N2, primero la aserción: simple-horario-sabado sacó 3.33 con el defecto presente.
 5. Corpus completo otra vez → gate de la segunda capa.

 Lo que no hay que repetir

 - Un guard que reemplaza respuestas tiene que ser negación-consciente y estar acotado a lo que se midió. f9e29596b ya lo tenía
   escrito y lo repetí igual.
 - must_not_include del corpus es ciego a la negación: para «no trabajamos con X» hace falta must_not_affirm (G11, ya existe).
 - agent/personas/orchestrator.md y prompts.FALLBACKS van byte-idénticos; hay un test que lo fija.
 - El tamaño de la PR se declara con size:exception; el repo tiene esa etiqueta para eso.
```

### L2 — decisión del owner sobre la colisión con S12

Opción elegida, verbatim: «La pregunta gana: research primero, manage después» — con la aclaración de que el riesgo declarado en la opción («puede reabrir el defecto #23 que S12 cerró») se cubre con S2: el verbo explícito de cambio sigue ganando.

### L3 — decisión del owner sobre la medición

Opción elegida, verbatim: «3 reps y transcripts como evidencia primaria». El puntaje del juez queda como señal; la atribución se hace leyendo el diálogo.

### L4 — evidencia del re-baseline (2026-11-18)

`main` @ `0a6b37791`, corrida `rebaseline-main`, 36/42, árbol limpio, KB sellada, cero fallos de corrida. Corpus sólo cambió `must_not_affirm` en dos escenarios respecto del baseline viejo, así que la comparación es válida.

Dos «regresiones» del re-baseline, desarmadas por transcript:

- `real-reagenda-familiar` 2.67 → 0.00 con **diálogo byte-idéntico** al de la corrida vieja: es ruido del juez sobre una respuesta determinista, no una regresión. Este corte la arregla por S1.
- `real-reclamo-real-si-deriva` 2.25 → 0.00 con cambio real de diálogo: el bot ofrece el catálogo completo a un cliente que acaba de cortar la relación. Regresión candidata de la lista cerrada de la KB que agregó familia 1. Fuera de alcance acá; se reproduce aparte.
- `super-enojo-reclamo` 0.00 → 2.92 **sin arreglo**: el transcript conserva el defecto textual de familia 4 («la mantención es preventiva… se evalúa y se presupuesta aparte»). Familia 4 sigue abierta.

### L5 — decisión del owner: el horario pedido no se ofrece antes de terminar la captura

Opción elegida, verbatim: «Terminar la captura y recién ahí ofrecer horarios». Descartadas: ofrecer slots en el turno sin datos para asignar técnico, y dejar que el bot siga contestando después del handoff.

### L6 — la medición que obligó a agregar S4 (corrida `agenda-house`, 3 reps)

`real-diego-precio-y-duracion` 0.00 → **2.67**: S3 funciona, la restricción se nombra.

S1/S2 no se activaron, y el guard estaba en la condición equivocada: en los dos escenarios restantes el turno crítico llega **sin campo pendiente**, así que `mid_capture` es `False` y el bloque nunca se evaluó. Conv 1 (`real-dato-mas-pregunta`, turno 2 `reagendar_visita`, cero visitas) fue a `manage` → `booking_unavailable` → `human` → mudo. Conv 2 (`real-reagenda-familiar`) entró a captura normal, el ack de S3 nombró las 9 am, y después el bot se fue al cuestionario de diagnóstico y abandonó el pedido — el hard fail textual del juez.

De ahí S4: sin visita, un reagendamiento no puede ir a `manage`, porque `manage` no tiene nada que mover.

### L7 — por qué hay una S5 (corrida `agenda-house-4`)

El ruteo ya está: los dos escenarios terminan en `bot`, sin handoff y con la restricción nombrada en el turno que la entrega. Siguen en 0.00 porque el turno siguiente la pierde. Tres corridas consecutivas mostraron además que el clasificador oscila entre `solicitar_visita` y `reagendar_visita` para la misma frase, y que el camino de respuesta del modelo es inestable (misma frase: respuesta buena en `agenda-house-2`, `kb_miss` en `agenda-house-3`). Por eso S5 es determinista y vive en la captura: no depende del label ni del modelo.

### L8 — medición final y cierre de familia 2

`agenda-house-8` (3 reps, árbol limpio, sello `c49417d`): 3/3, sin hard fail. Transcripts revisados turno por turno:

- `real-dato-mas-pregunta` turno 3: «Sobre tu horario: las 14:00 en adelante. Queda anotada y la confirmamos al coordinar la visita.» — nombra la hora propuesta y no promete.
- `real-reagenda-familiar` turno 3: «Sobre tu horario: 9:00 am.» ante «En las tardes me complica» — ya no convierte una exclusión en preferencia.

Ocho corridas intermedias (`agenda-house` a `-7`) quedan como registro de iteración; sólo la final se commitea como evidencia.

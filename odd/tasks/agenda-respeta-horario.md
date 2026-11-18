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

## Tasks

| ID | S# | Ruta | Commit |
| --- | --- | --- | --- |
| T1 | S1, S2 | `app/chat/nodes/orchestrate.py` + `tests/unit/test_routing_table.py`, test-first | pendiente |
| T2 | S3 | `app/chat/nodes/capture.py` + tests del nodo, test-first | pendiente |
| T3 | S1-S3 | medición `--only` de los 3 escenarios, 3 reps, transcript antes que puntaje | pendiente |
| T4 | S1-S3 | `bash scripts/test.sh quick`, luego `full` antes de la PR | pendiente |

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

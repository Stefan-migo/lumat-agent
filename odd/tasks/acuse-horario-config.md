# acuse-horario-config — el acuse no clava fecha y el sello dice con qué redacción midió

Corte en dos commits sobre el programa del chatbot: el instrumento declara la redacción de captura que
midió (producción corre `llm`), y el acuse de horario deja de afirmar una fecha que el juez lee como
promesa. Nace del handoff posterior a #880, pendientes 1 (diagnóstico de configuración) y 2 (acuse).

## Specs

S1. «El acuse del capture afirma una fecha («Sobre tu horario: el sábado 28/11») y el juez lo lee como
promesa. Misma clase de defecto que arreglamos, en otro nodo (capture.py).»

S2. «Confirmar la config de producción (`chat.conduct`, `settings` en general) — barato, y decide si el
pendiente 3 es bot o instrumento.»

S3. «ok vamos con 1 y 2. juntos.»

## Tasks

- T1 → S2 · arnés: el sello de la corrida declara `chat.conduct`/`redaccion` · `1369380e2` ✅
- T2 → S1 · `capture`: el acuse nombra día, franja u hora, nunca una fecha · `e0ece6c92` ✅
- T3 → S3 · verificación (`focused` + `quick`) y cierre del corte · último commit

## Log

L1 — pedido del owner, verbatim: «ok vamos con 1 y 2. juntos.»

L2 — evidencia del pendiente 1 (2026-11-24, `ssh deploy@agente.lumat.cl`,
`select key, left(value::text,220) from settings order by key` sobre `lumat-db-1`): producción tiene
`chat.conduct = {"orden": ["failure", "equipment", "comuna", "availability", "name", "email", "address"],
"redaccion": "llm", "derivaciones": ["cobertura"], "max_preguntas_por_mensaje": 1}`. También
`hours.schedule` días 1–7 00:00–23:59, `hours.timezone` `America/Santiago`, `hours.closure_enabled` false
—la misma ventana que el arnés siembra—, `coverage.communes` con 7 comunas y `reply.texts` con textos
propios del owner.

Consecuencia medida: el pendiente 3 (`¿name?`, `¿equipment?` al cliente) **no** es artefacto del
instrumento, es defecto de producto. La ruta es única: `phrasing.phrase` reescribe sólo cuando
`conduct.redaccion == "llm"`, y `phrasing.rewrite` (`app/chat/phrasing.py:161`) manda al modelo
`Campos pendientes: ['name']` con el identificador interno, mientras `validate` (`phrasing.py:99`) sólo
compara el conteo de `?` y los guardas de números/fechas/correo. Producción está en esa ruta desde que el
owner encendió la redacción con modelo.

L3 — decisión de alcance de T1: el arnés **declara**, no controla. `HARNESS_SETTINGS` siembra únicamente
`hours.schedule`/`hours.timezone`/`hours.closure_enabled` porque es la configuración que el corpus prueba
de forma determinista; sembrar `chat.conduct` cambiaría el texto que el cliente lee en todo el corpus y no
es lo que este corte mide. Lo que hoy falta es honestidad del informe: el sello dice la ventana pero no la
redacción, así que una corrida con `llm` y otra con `plantilla` producen textos distintos bajo sellos
idénticos.

L4 — fuera de alcance, medido: el hueco de `validate`/`rewrite` que deja caer `¿name?` es el pendiente 3 y
va en su propio corte (con test de que un identificador de campo no puede ser una reescritura válida). El
acuse de `capture_availability_ack` (S3 de `agenda-respeta-horario`) interpola el valor que escribió el
cliente, no una fecha del parser, y no cambia acá.

L5 — restricción de no regresión: los acuses existentes son contrato medido. `tests/integration/test_chat_capture.py`
fija cinco veces «queda anotada» y una vez «14:00» en el hold; el G6 de `simple-horario-sabado` acepta
`sabado`, `sábado`, `asesor`, `coordina`. El cambio de T2 tiene que conservar día y hora y sacar sólo la
fecha.

L6 — RED y GREEN observados (worktree `../lumat-agent-odd-acuse-horario-config`, base `e6bd0d6c1`):

- T1 RED: `test_render_markdown_declares_the_capture_redaction_the_run_measured`,
  `test_conduct_fingerprint_moves_only_when_the_conduct_moves` y
  `test_the_capture_conduct_is_read_from_the_database_the_run_uses` fallan con `AttributeError: module
  'conv_eval' has no attribute 'measured_conduct'` / `'conduct_fingerprint'`. GREEN con las tres suites
  del evaluador: **162 passed** (`test_conv_eval.py`, `test_conv_eval_settings.py`,
  `test_conv_eval_agenda.py`).
- T2 RED: `TypeError: window_label() got an unexpected keyword argument 'with_date'`. GREEN con
  `test_slot_window.py`, `test_chat_capture.py`, `test_capture_phrasing.py` y
  `test_agenda_respeta_horario.py`: **121 passed**.
- El hold medido ahora dice «Sobre tu horario: el sábado. Queda anotada y la confirmamos al coordinar la
  visita.» — conserva el día que el cliente nombró, pierde la fecha.

L7 — verificación en el worktree (`odd/acuse-horario-config`, base `e6bd0d6c1`):

- `bash scripts/test.sh quick` → **EXIT 0**, 100 % de la barra.
- `bash scripts/test.sh full` (primera corrida) → **rojo por el stall preexistente**, no por el corte:
  `pytest-timeout` a 120 s dentro de `tests/functional/test_seed_dev.py:42` (`subprocess.run` del seed).
  Es la familia documentada en `odd/tasks/suite-truncate-stall.md` y ya registrada con la misma línea en
  `odd/tasks/artifact-outputs.md:256`, `odd/tasks/chatbot-defectos.md:769` y
  `odd/handoffs/chatbot-fase-3-ficha-de-caso.md:83`. Prueba de que no es del diff: aislado pasa
  (`uv run pytest tests/functional/test_seed_dev.py -q` → 1 passed), el diff no toca `db/`, `scripts/`
  ni `app/panel/`, y no quedaron `seed_dev.py` huérfanos (0 procesos) ni conexiones colgadas (1 en
  `pg_stat_activity`) antes del re-run.
- `bash scripts/test.sh full --deselect tests/functional/test_seed_dev.py::test_dev_seed_populates_dashboard_and_composer`
  (el deselect que el repo documenta para tener señal) → **EXIT 0**, 10 m 54 s, 100 % de la barra, sin
  fallos. La corrida completa autoritativa sigue siendo la de CI en el PR, que trae su propio Postgres.

L8 — lo que este corte deja abierto, a propósito:

- **Pendiente 3 (`¿name?`, `¿equipment?`)**: es defecto de producción (`redaccion: llm` medido), y su
  arreglo es en `phrasing.rewrite`/`phrasing.validate`, no acá.
- **Continuidad del arnés**: `chat.conduct` queda *declarado* y no sembrado. Una base de evaluación sin
  fila mide `plantilla`; el informe ahora lo dice, pero la decisión de sembrarlo sigue abierta.
- **Medición**: el efecto del acuse nuevo sobre el juez (`simple-horario-sabado`) sólo se ve con una
  corrida nueva del corpus, que queda para cuando se decida re-baselinear.

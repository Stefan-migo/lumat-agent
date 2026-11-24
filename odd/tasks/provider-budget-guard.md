# provider-budget-guard

El turno del panel muere a los ~3 min cuando una llamada al proveedor tarda o se reintenta, porque el
presupuesto del cliente LLM (timeout × intentos) coincide con el guard de la base y un nodo espera al
proveedor con la transacción del turno abierta. Medido en producción (hilo 63, 2026-11-24): 3 turnos
fallidos, 7 de 27 turnos del panel caídos ese día. Riesgo: alto por alcance compartido — toca bordes de
transacción del grafo, el cliente LLM y el camino de fallo, que usan todos los turnos; sin migraciones.

## Specs

**S1 — Ningún nodo espera al proveedor con la transacción del turno abierta.**
`plan_llm`, `repair_plan`, el responder (`execute` con `on_token`) y el verificador de efectos
(`verify_effects`, cuyas dos llamadas al modelo se hacen a través de `verification.run_verification`)
liberan la transacción con el trabajo ya hecho **inmediatamente antes** de cada llamada al proveedor,
incluida la segunda llamada del planner (el repair) y la que sigue a cada tool de sólo lectura que
despacha el verificador. Precedente textual en el repo: `_generate_thread_title` llama `release_transaction(session)`
justo antes de `client.chat.completions.create` (`app/services/agent_chat.py:307`). Excepción explícita,
la misma de `pool-safety` S2: el turno que reanuda una escritura aprobada mantiene su única transacción y
no libera nada, porque un commit a mitad dejaría una aprobación consumida con la escritura sin aplicar
(`test_resume_path_never_commits_or_publishes_mid_execution` es el contrato que debe seguir pasando).

**S2 — El presupuesto total del cliente LLM queda por debajo del guard de la base.**
`(1 + LLM_MAX_RETRIES) × LLM_TIMEOUT_SECONDS` es **menor** que el `idle_in_transaction_session_timeout`
de `db/migrations/070_session_safety.sql` (180 s), con margen declarado, y el cliente lo aplica con
`max_retries` explícito en vez del default del SDK (2, que da exactamente 180 s con timeout de 60 s). Un
test deriva la desigualdad de las constantes y del valor que fija la migración, no de números literales
repetidos.

**S3 — Un turno que se cae deja la razón registrada.**
Cuando el turno termina en fallo, `assistant_state.live.reason` y una fila
`audit_log(action="internal_chat.run_failed")` guardan la clase de la excepción y un mensaje acotado
(nunca contenido de operador ni payloads); el texto que ve el operador **no cambia**
(`"El agente no pudo procesar este mensaje. Reinténtalo."`, contrato de `pool-safety` S4). Además
`_releasing` deja una línea de log con el nombre del nodo y sus milisegundos cuando el nodo supera el
umbral, para atribuir el próximo atasco sin leer tracebacks de SQLAlchemy.

**S4 — Sin regresión en los caminos que ya funcionan.**
Turno aprobado: sigue sin commitear a mitad. Turno normal: persiste la respuesta y el costo. Turno
cancelado: termina `cancelled`. Aprobación parkeada: termina `approval_pending`. Fallo con la base
muerta: sigue terminando `failed` con el copy exacto y el hilo reintentable. Los tests de esos caminos
existen y deben pasar sin cambios.

## Tasks

| ID | Spec | Route | Commit |
| --- | --- | --- | --- |
| T1 | S1 | backend · `release_transaction` antes de cada `chat.completions.create` en `nodes.py` | `ba918dad7` |
| T2 | S2 | backend · `LLM_TIMEOUT_SECONDS` / `LLM_MAX_RETRIES` + `max_retries` explícito en `llm.py` | `f0abaa7af` |
| T3 | S3 | backend · `live.reason` + `internal_chat.run_failed` + log de nodo lento | `d0b3c867e` |
| T4 | S4 | verificación · barrido de regresión y `scripts/test.sh full` | sin commit propio (evidencia en L4) |

## Log

**L1 — pedido del owner (2026-11-24), verbatim:**

> vamos en el orden recomendado

**L2 — qué significa ese orden (decisión del owner sobre la propuesta del orquestador del mismo día).**
El orden recomendado fue: (1) este corte —presupuestos que colisionan: liberar la transacción antes de
cada llamada al proveedor, acotar el cliente por debajo del guard, y que el fallo diga la razón—;
(2) el paso 2 de `planner-presupuesto` (instrumentar `assistant.evidence_truncated`); (3) el paso 3 sólo
con el dato del paso 2. Este documento es el corte (1).

**L3 — diagnóstico medido (2026-11-24, read-only sobre producción, `v2026.11.17`):**
- Hilo 63 (`test-del-agente`), 3 turnos fallidos: 321 «Si» 10:03:57→10:07:02, 322 «Si»
  10:43:48→10:46:52, 323 «Que pasó puedes averiguar?» 10:47:09→10:50:16. Siempre ~3:05.
- Los tres con la misma firma en el log del contenedor:
  `psycopg.errors.IdleInTransactionSessionTimeout` → `app/chat/assistant/graph.py:109 wrapped` →
  `app/db.py:60 release_transaction` → `commit`; y después `PendingRollbackError` en el camino de fallo.
- `current_setting('idle_in_transaction_session_timeout')` en producción = `3min`; `statement_timeout` y
  `lock_timeout` = 0.
- `LLM_TIMEOUT_SECONDS = 60.0` (`app/services/llm.py:19`) y el cliente OpenAI reintenta 2 veces por
  default ⇒ 60 × 3 = 180 s = exactamente el guard. Los dos números viven en módulos distintos y nadie
  los había atado.
- En la imagen desplegada, `release_transaction` aparece **0 veces** dentro de `nodes.py`: sólo en el
  borde de nodo (`graph.py:104`). Un nodo que escribe y después vuelve a llamar al proveedor
  (`plan_llm` registra uso y, si el plan vino mal, hace el repair call) deja la transacción abierta
  durante esa espera.
- Frecuencia: 7 de 27 turnos del panel fallaron el 2026-11-24; 9 de 41 el 2026-11-21; 2 de 11 el
  2026-11-18. Es una familia, no un incidente aislado.
- El proveedor estaba sano al medir: `deepseek-chat` respondió en 2,3 s desde el contenedor.
- El camino de fallo **funcionó**: el hilo quedó reintentable, el panel siguió respondiendo 200 y no se
  repitió el incidente de pool del 2026-11-21.

**L4 — lo que salió distinto al plan (2026-11-24):**
- **S1 y S2 tuvieron RED real**: el test nuevo falló 5 veces antes de implementar, con los mensajes
  `planner provider call began with an open transaction`, `responder provider call began with an open
  transaction`, `LLM_MAX_RETRIES` inexistente y el `max_retries` ausente. **S3 no tuvo RED previo**: se
  implementó antes del test y se registra así, no como test-first. El RED de S3 que sí existe es el de las
  dos regresiones que introdujo su primera versión (abajo).
- **La auditoría nueva rompía el camino de fallo**, que es justo lo que `pool-safety` S4 prohíbe:
  `test_failed_run_recovers_when_audit_write_raises_operational_error` agotaba los 3 intentos de
  recuperación cuando `record_audit` lanzaba `OperationalError`, y el mensaje del operador quedaba sin
  marcar `failed`. Corregido escribiendo la fila dentro de un `session.begin_nested()` (SAVEPOINT) con
  degradación a log; test derivado: `test_failed_orphan_survives_a_rejected_audit_write`. El mismo cambio
  destapó `test_reap_stale_run_fails_an_orphaned_run_once_it_stops_advancing` (stub de sesión sin
  `begin_nested`), corregido en el stub del test nuevo, no en el código.
- **S2 se resolvió bajando reintentos, no el timeout**: `LLM_TIMEOUT_SECONDS` queda en 60 s y
  `LLM_MAX_RETRIES = 1` ⇒ 120 s contra los 180 s del guard, con 60 s de margen. Bajar el timeout habría
  cortado llamadas legítimamente lentas con prompts de ~12.000 tokens. El test deriva el límite leyendo el
  valor de `db/migrations/070_session_safety.sql` en vez de repetir el número.
- **Consecuencia compartida declarada**: el mismo `openai_client` sirve al flujo de WhatsApp, así que la
  ventana de recuperación ante un 5xx/429 transitorio baja de 3 intentos a 2 allí también. Se verificó con
  los 204 tests unitarios de la familia `llm`/`whatsapp`/`chat` sin tocarlos (verdes).
- **El Graph Check bloqueó una vez**, y no por el código: `graphify-out/` es gitignored y vive sólo en el
  worktree principal. Las consultas obligatorias se corrieron allí, y su resultado es evidencia del defecto:
  `graphify path _planner_call release_transaction` y `graphify path _record_usage release_transaction`
  devuelven **no directed path**, mientras `_generate_thread_title` sí tiene la arista que lo arregló.
- **Evidencia de verificación** (worktree `odd/provider-budget-guard`, base `14b297daa`):
  `tests/integration/test_assistant_chat.py` **81 passed**; foco planner/tool-loop/guardrails/proyecto
  **147 passed**; familia `llm`/`whatsapp`/`chat` **204 passed**;
  `test_resume_path_never_commits_or_publishes_mid_execution` **1 passed** (el turno aprobado conserva su
  transacción única); `bash scripts/test.sh full` **exit 0, 0 FAILED/ERROR, progreso 100%, 10m48s**.
- **Trampa pagada de nuevo**: una corrida anterior de `full` leyó `FULL_EXIT=0` que era el status de `tail`,
  no el de pytest. El cierre se hizo con el log en archivo aparte y el exit real. En esa corrida previa
  apareció el timeout de 120 s de `tests/functional/test_seed_dev.py`, que **no** reapareció en la corrida
  verde: es la familia intermitente ya documentada en `odd/tasks/chatbot-defectos.md` y
  `odd/tasks/suite-truncate-stall.md`, no un efecto de este corte.


**L5 — hallazgos de la verificación independiente y su resolución (2026-11-24).**
El verifier corrió con sondas propias (`/tmp`, fuera del repo) y no aceptó los tests del worker como
evidencia. Veredicto inicial: **S1 PASS, S2 PASS, S4 PASS, S3 FAIL**, más dos advisories.

- **S3 FAIL (blocker, corregido en `28140eb9f`)**: `_run_agent_turn_session` se tragaba la excepción en su
  propio `except`, así que `run_agent_turn` —único llamador de `_record_failed_run`— nunca corría y
  `live.reason` quedaba vacío en el camino ordinario. El verifier lo reprodujo con `run_assistant`
  lanzando `RuntimeError` sobre la base real: `live.reason: None`, `run_failed rows: 0`. Es decir, el
  caso que S3 existe para explicar (un error de proveedor común) era justamente el que no dejaba rastro;
  el camino que sí lo dejaba era el de la base muerta. Ahora el `except` del turno guarda la razón y una
  fila, con el helper de SAVEPOINT. Test: `test_a_failed_turn_records_its_reason_and_one_audit_row`.
- **Advisory corregido — cuarto llamador al proveedor**: `verification.run_verification` llamaba al modelo
  con la transacción del turno abierta (`nodes.py:1278`, nodo `verify_effects`, que corre en todo turno
  que exija verificación). Es la misma colisión, fuera de la enumeración original de S1, que se enmienda
  arriba. Test: `test_verification_releases_transaction_before_each_verifier_call`.
- **Advisory corregido — redacción incompleta**: `_failed_run_reason` dejaba pasar texto del operador
  cuando llegaba escapado por `repr`. Ahora redacta las variantes cruda, `repr`, `json.dumps` y
  `unicode_escape`. Test: `test_failed_run_reason_redacts_repr_escaped_operator_content`.
- **Pin extra derivado del verifier**: el test de S2 ahora exige `LLM_MAX_RETRIES != openai.DEFAULT_MAX_RETRIES`,
  para que el default del SDK (2, que da 180 s exactos) no vuelva a entrar sin que un test lo note.
- **Lo que el verifier confirmó con sondas propias**: orden `write → COMMIT → PROVIDER(in_tx=False)` en los
  tres sitios originales; `resume` con `PROVIDER(in_tx=True)` y **cero** commits; `(1+1)×60 = 120 s < 180 s`
  con 60 s de margen y `max_retries=1` efectivamente pasado; copia al operador byte-idéntica en 17 chequeos
  sobre base real; `OpenAI(` existe sólo en `app/services/llm.py`, o sea que el flujo de WhatsApp comparte
  el cliente y **ningún test fijaba el conteo viejo**.
- **Gates tras la corrección**: `tests/integration/test_assistant_chat.py` **82 passed**; foco (planner,
  tool-loop, guardrails, write-chain y probes de recovery) **161 passed**; familia `llm`/`whatsapp`/`chat`/
  `verification` **235 passed**; `bash scripts/test.sh full` **exit 0, 0 FAILED/ERROR, progreso 100%**.

**L6 — veredicto final de la re-verificación independiente (2026-11-24).**
El mismo verifier re-corrió sus propias sondas sobre `28140eb9f` y dio **S1 PASS · S2 PASS · S3 PASS ·
S4 PASS**. El blocker de S3 quedó resuelto por el código que ejecutó, no por el test nuevo: con
`run_assistant` lanzando `RuntimeError("provider timed out after 120s")` sobre la base real, obtuvo
`live.reason = "RuntimeError: provider timed out after 120s"`, **1** fila `internal_chat.run_failed`, la
copia al operador byte-idéntica y `_record_failed_run: 0 call(s)` — o sea, la razón sale del `except` del
turno, que era justamente el camino que reportó roto. Sondas del delta: `verify_effects` con una tool
despachada da `COMMIT → PROVIDER-1(False) → write:tool → COMMIT → PROVIDER-2(False)`, y con `resume=True`
`PROVIDER(in_tx=True)` sin un solo commit. `run_verification` tiene un único llamador (`nodes.py:1294`), así
que la enumeración enmendada de S1 queda completa para el grafo.

**Advisory aceptada (no se corrige, por decisión):** si la escritura de `internal_chat.run_failed` se
rechaza **una vez** dentro del SAVEPOINT del propio turno, esa fila se pierde; la razón en
`assistant_state.live.reason`, la terminalización y la copia al operador se mantienen. Es exactamente lo que
S3 promete ("la razón queda registrada"; la fila es el registro contable) y la alternativa —dejar que el
fallo del SAVEPOINT suba para reintentar por `_record_failed_run`— reabriría el riesgo de romper la
terminalización, que es lo que `pool-safety` S4 prohíbe. Un doble rechazo simétrico no duplica filas.

**Transparencia del verifier:** su primer intento sobre `tests/integration/test_assistant_chat.py` devolvió
82 errores por correr en paralelo con otra sesión de pytest sobre la misma base de prueba
(`psycopg.errors.InternalError: tuple concurrently updated`); la corrida secuencial dio 82 passed. No es
defecto del código y refuerza la regla del repo: una suite por worktree a la vez.

**Estado final de la unidad:** 7 commits sobre `14b297daa` (`ba918dad7`, `f0abaa7af`, `d0b3c867e`,
`24e77f61f`, `28140eb9f`, `a960a49cf`, este cierre), 617 líneas, 6 archivos. Gates de cierre:
integración 82 passed, foco 161 passed, familia compartida 235 passed, `scripts/test.sh full` exit 0 con
0 FAILED/ERROR. Push, PR y deploy son decisión del owner.

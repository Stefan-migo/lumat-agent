# panel-turn-tool-transaction

El turno del panel muere a los ~3 min cuando un **tool** hace I/O externo con la transacción del
turno abierta: PostgreSQL corta la conexión por `idle_in_transaction_session_timeout` (180 s) y el
turno recién se entera en el siguiente borde de nodo, donde el `INSERT` de auditoría levanta
`PendingRollbackError` y el operador sólo ve la copia genérica. Riesgo: alto por alcance compartido
—toca el despacho de tools, que usan todos los turnos, y el camino de fallo— sin migraciones.

## Specs

**S1 — Ningún tool espera I/O externo con la transacción del turno abierta.**
Un tool clasificado como I/O externo suelta la transacción del turno inmediatamente antes de esa
espera: `chatbot.simulate` y `chatbot.eval_regression` (recorren el grafo del chatbot y el juez, con
llamadas al proveedor durante minutos), `web.search` y `web.fetch` (terceros) y `kb.retrieve` (no hace
red: el embedder es local, fastembed/ONNX, 384d; se marca porque su carga en frío no está acotada).
La clasificación vive en el registro (`ToolDefinition.external_io`) y `execute` libera antes de
despachar un tool marcado; los tools que además usan la sesión del turno *después* de leer
(`chatbot.simulate`) sueltan también en su propio borde interno, porque un release previo al despacho
no cubre la espera que ocurre después de sus primeras lecturas.

**S2 — La medición queda fijada como test, no como recuerdo.**
Con `idle_in_transaction_session_timeout` comprimido a 8 s en la base derivada del worktree y un tool
que lee y **después** espera 14 s, el turno termina `processed`. Hoy ese test es RED: el turno muere
con `psycopg.errors.IdleInTransactionSessionTimeout` → `PendingRollbackError`, la firma medida en
producción el 2026-11-27 (hilo 65, mensaje 333, 03:42:12 → 03:45:24). El test no deja el guard
comprimido: lo restaura en `finally`.

**S3 — El próximo atasco se atribuye solo, sin tracebacks de SQLAlchemy.**
Cada despacho de tool deja una fila `audit_log(action="internal_chat.execution_started")` con
`run_id`, `tool` y `arguments_sha256` **antes** de ejecutar, aparte de la fila
`internal_chat.execution` que ya se escribe al terminar. Es la fila que hoy falta cuando el turno
muere y la única forma de saber qué tool colgó el turno: en producción no hay una sola línea
`WARNING` en tres días, así que el log `Slow assistant node` de `provider-budget-guard` S3 no es
observable. El texto que ve el operador no cambia: `"El agente no pudo procesar este mensaje. Reinténtalo."`

**S4 — Sin regresión en los caminos que ya funcionan.**
El turno que reanuda una escritura aprobada sigue sin commitear a mitad
(`test_resume_path_never_commits_or_publishes_mid_execution` pasa sin cambios), el planner/repair/
responder/verificador siguen liberando antes de cada llamada al proveedor, y `chatbot.simulate` deja
de commitear la sesión del turno: corre en su propia sesión, que es lo que su contrato de aislamiento
ya decía.

## Tasks

| ID | Spec | Route | Commit |
| --- | --- | --- | --- |
| T1 | S2 | test · `tests/integration/test_assistant_tool_transaction.py` + `test_assistant_simulation_session.py` | `7ebaacd57`, `7157477cf` |
| T2 | S1 | backend · `external_io` en `ToolDefinition` + release en `execute` | `7ebaacd57` |
| T3 | S1 | backend · `chatbot.simulate` en sesión propia (deja de commitear la del turno) | `7157477cf` |
| T4 | S3 | backend · `internal_chat.execution_started` al despachar un tool marcado | `7ebaacd57` |
| T5 | S4 | verificación · focused + `quick` + `full` | sin commit propio (evidencia en L7) |

## Log

**L1 — pedido del owner (2026-11-27), verbatim:**

> hey chat. necesito que entres al vps y revises las ultimas conversaciones con el asistente lumat. esta teniendo errores para evaluar la ultimas tools que faltan en la investigacion. revisa el artifact del proyecto test del asistente. del usuario Stefan. ahi es donde esta el asistete lumat ha estado registrando testeando los tools. dame un overview antes de continuar

**L2 — decisión del owner (2026-11-27).** Sobre el overview, eligió pinear el timeout de los 3 min
antes de destrabar el testing de las 4 tools restantes, y después autorizó el fix completo: S1 + S2 +
la instrumentación que reemplaza el log invisible. Worktree `../lumat-agent-odd-panel-turn-tool-transaction`,
rama `odd/panel-turn-tool-transaction`, creado con `rapso worktree create` tras ese consentimiento.

**L3 — diagnóstico medido (2026-11-27, read-only sobre producción `v2026.11.22` + reproducción local).**
- Turnos fallidos con la misma duración constante: mensaje 333 (hilo 65) 03:42:12.75 → 03:45:24.78
  (192 s), mensaje 330 (hilo 64) 23:32:50 → 23:35:52 (182 s), hilos 63 del 2026-11-24 a ~3:05.
- Firma en el contenedor: `psycopg.errors.IdleInTransactionSessionTimeout` →
  `app/chat/assistant/graph.py:115 wrapped` → `app/db.py:60 release_transaction` → `commit` → flush →
  `INSERT INTO audit_log (... action='internal_chat.execution' ...)` → `PendingRollbackError`.
  `current_setting('idle_in_transaction_session_timeout')` en producción = `3min`.
- El corte `provider-budget-guard` sí está desplegado (5 `_release_before_provider_call` en
  `nodes.py`, `LLM_MAX_RETRIES = 1` ⇒ 120 s < 180 s) y no alcanza: la espera que rompe el turno no es
  la del proveedor del planner, es la de un tool.
- En el turno `d3623e08` (hilo 65) el último `internal_chat.execution` auditado es
  `assistant.capabilities` a las 03:42:17.956; el fallo se registra 187 s después y la fila pendiente
  del flush fallido es un `internal_chat.execution` **con `arguments_sha256`** (182 chars): un tool
  que corrió y nunca se commiteó. El rollback borró cuál era.
- Reproducción local (guard comprimido a 8 s, turno real por `submit_message`): planner que espera
  14 s → turno `processed` en 14.2 s (la liberación funciona); tool que espera 14 s **antes** de su
  trabajo de base → sano (`session.in_transaction()` es `False` al despachar); tool que lee y
  **después** espera 14 s → `IdleInTransactionSessionTimeout` → `PendingRollbackError`. La última es
  la firma de producción.
- En producción **no hay una sola línea `WARNING` en tres días**: el log de nodo lento del corte
  anterior nunca llega al contenedor.
- `app/services/kb.py:10` aclara que los embeddings son locales (`fastembed`/ONNX, 384d, sin API):
  `kb.retrieve` no hace red, así que el I/O externo que puede colgar un turno son
  `chatbot.simulate`, `chatbot.eval_regression`, `web.search` y `web.fetch`.

**L4 — dos ítems del registro de testing que quedaron viejos** (no son de este corte, no se tocan acá):
`chatbot.eval_regression` ya tiene baseline en la imagen (`/app/odd/evals/conv-eval-baseline.json`,
23 639 B, 2026-11-23 20:40, resuelto por `app/services/chat_regression.py:38`), y `conversations.search`
es un límite de contrato real: `app/services/conversations.py:42` filtra por nombre de cliente,
teléfono y `summary`, nunca por el texto de los mensajes.

**L5 — lo que salió distinto al plan (2026-11-27).**
- **El worker delegado no pudo verificar nada**: el worktree recién creado no tiene `.venv` ni
  `infra/.env` (ambos ignorados por git), así que `scripts/test.sh db` y `quick` morían antes de
  pytest. `rapso worktree provision` no los trae; se resolvió con `cp ../lumat-agent/infra/.env
  infra/.env` + `uv sync --frozen` + `infra/test-db.sh up` (este worktree deriva el puerto 6060).
- **El test que traía el worker no podía ponerse verde**: usaba `customers.list`, un tool que no está
  marcado, así que el release previo al despacho no aplica; además creaba el `User` con `role="admin"`
  (str) en la misma sesión, y `_run_agent_turn_session` lee `user.role.value` → `AttributeError`.
  Reescrito con la forma medida.
- **El end-to-end con guard comprimido no es honesto y no se escribió**: a los 14 s de espera el guard
  mata también la sesión de la simulación, así que "turno processed" no distingue el fix del defecto.
  La invariante quedó fijada en los dos seams que sí la deciden: release en el despacho (sesión espía,
  con el control de un tool no marcado) y `simulate` corriendo en sesión propia.
- **La trampa que pagó la suite**: pasar `simulate` a sesión propia **perdía las respuestas**, porque
  el `with SessionLocal()` de salida cierra y descarta lo no commiteado; lo detectó
  `test_simulation_writes_no_domain_event_or_active_conversation` (`assert outbound` vacío). Se corrigió
  con un `commit()` explícito antes de devolver, no relajando el test. Es exactamente el caso de "código
  compartido que otro camino ya usa" y quedó pinneado por ese test existente.
- **RED real observado por reversión**: con `git stash push -- app/` los 6 tests nuevos fallan; con el
  cambio vuelven verdes. El RED no se observó antes de escribir el código (el worker no tenía entorno),
  y se registra así, no como test-first.

**L6 — el contrato que el cambio rompió, y cómo se reacotó (2026-11-27).**
- La primera corrida de `scripts/test.sh full` salió roja y el job la reportó verde: el comando
  medía el exit del `echo` final, no el de pytest. El log tenía `FULL_EXIT=1`. Misma trampa que el
  cierre del corte `provider-budget-guard`, en espejo.
- El fallo real: `test_execution_audits_before_evidence`
  (`tests/integration/test_assistant_harness_guardrails.py:100`) fija el orden `["handler", "audit"]`,
  o sea **ninguna auditoría antes del handler** para un tool barato. Grabar
  `internal_chat.execution_started` para todos los tools lo rompía (`['audit','handler','audit']`).
- Decisión: la fila de arranque se graba **sólo para los tools marcados `external_io`**, que es donde
  una espera larga es posible y donde la atribución compra algo. Los otros ~40 conservan su única fila
  de ejecución completada, y el contrato existente queda intacto en vez de reescrito.
- S3 se asertó a nivel de nodo (sesión espía: `add(execution_started)` → `commit` → handler), no
  end-to-end: los tools marcados que podrían llevar esa aserción piden aprobación del owner, y montar
  el flujo de aprobación para probar una fila de auditoría cuesta más de lo que mide.

**L7 — evidencia de verificación (worktree `odd/panel-turn-tool-transaction`, 2026-11-27).**
- RED por reversión (`git stash push -- app/`): 4 de los 5 tests de los dos archivos nuevos fallan —
  clasificación, release en el despacho y las dos de simulación. El control (`customers.list`, no
  marcado) pasa en ambos sentidos, que es lo que debe hacer.
- GREEN focalizado: `test_assistant_tool_transaction.py` + `test_assistant_simulation_session.py` +
  `test_assistant_harness_guardrails.py` → **34 passed in 2.90s**.
- Familia asistente (chat, write chain y sus probes, simulate, eval_regression, chat_simulation,
  guardrails): **147 passed**.
- `bash scripts/test.sh quick` → verde (T0 + T1).
- `bash scripts/test.sh full` → **exit 0**, progreso 100% sin fallos ni errores (12m 13s). Corrido con
  el exit real del job, porque `addopts = "-q"` más el `-q` del tier dejan la corrida en `-qq` y no
  imprime el resumen: la evidencia es el exit y el 100% sin `F`/`E`.
- `bash scripts/test.sh shape` → "no shape surface touched", los tiers dirigidos alcanzaban; `full` se
  corrió igual por ser cierre de feature.

# ODD: asistente-guardrails

**Branch**: `odd/asistente-guardrails` · **Worktree**: `../lumat-agent-odd-asistente-guardrails`
**Base**: `9d7a6f8e` (= `main`) · **Status**: in progress

## Objective

Un plan bien intencionado del asistente del panel no puede destruir el turno por un argumento
fuera de rango, y ningún techo puede quedar invisible para quien tiene que respetarlo.

## Specs

- **S1** (diagnóstico medido, no normativo) El mensaje exacto
  `No pude planificar esa solicitud de forma segura. Inténtalo nuevamente.` del hilo 49 de
  producción (`2026-11-16`, proyecto `test-del-agente`) provino de `stage=guardrails`,
  `reason=unsafe_plan`, `whitelisted: true`, `arguments_valid: false`, sobre el plan
  `{"kind":"tool","tool":"read_project_file","arguments":{"file_id":3,"limit":6000}}`.
  El techo real de una página es `3890` y vivía solo en un `field_validator`, así que el
  *JSON Schema* que lee el planificador publicaba `{"type":"integer","minimum":1}` sin
  `maximum` y sin `default`.

- **S2** El schema que recibe el planificador para `limit` de `read_project_file` publica el
  techo y el valor por defecto (`maximum` y `default`), derivados de **una sola** constante.

- **S3** Un `limit` mayor que el techo se **acota** al techo y el turno ejecuta; `read_project_file`
  deja de poder rechazar un plan por pedir una página más grande que la que existe.

- **S4** Un plan que falla guardrails recibe **un** turno de reparación acotado, con el error de
  validación devuelto al planificador. Si el segundo plan es válido, el turno ejecuta. Si vuelve a
  fallar, el turno termina con el mismo texto exacto
  `No pude planificar esa solicitud de forma segura. Inténtalo nuevamente.`

- **S5** El acotado no relaja ninguna frontera: no amplía el catálogo ni los permisos, no toca
  herramientas de escritura, y todo plan cuyos argumentos ya estaban dentro de rango se comporta
  exactamente igual que antes. Un límite semántico (cuántas filas pediste) sigue rechazándose; solo
  se acota el techo de página de un lector paginado.

- **S6** La guía operativa del asistente dice el techo y que se acota (`agent/skills/assistant/tools.md`).

- **S7** Fuera de alcance: los otros contratos validados en `field_validator` y no publicados
  (celdas de `PdfTable`, extensión de `project_file.save`, `filename` de `artifact.pdf`,
  `skill.propose`). Quedan registrados como la misma clase de defecto y se arreglan en otra unidad.

## Tasks

| ID | Specs | Route | Commit |
|---|---|---|---|
| T1 | S2 | inline — `app/chat/assistant/budgets.py` + `Field(le=)` en `ProjectReadFileArgs` | `b9bcac74` |
| T2 | S3 | inline — acotado antes de validar, con test del techo publicado | `b9bcac74` |
| T3 | S4, S5 | inline — nodo `repair_plan` + ruteo acotado en el grafo | `b9bcac74` |
| T4 | S6 | inline — skill `tools.md` | commit de docs de esta ficha |
| T5 | S1-S7 | inline — verificación por spec y cierre | ver `## Verification` |

## Verification

- `bash scripts/test.sh quick` → verde (gate T0 + unit T1).
- `bash scripts/test.sh db tests/integration/test_assistant_harness_production.py tests/integration/test_assistant_harness_guardrails.py tests/integration/test_assistant_chat.py`
  → verde, 108 tests.
- `bash scripts/test.sh shape main` → `shape: no shape surface touched -> targeted tiers are safe`.
- `bash scripts/test.sh full` (con `FASTEMBED_CACHE_PATH` y redirigido a archivo, nunca por un pipe):
  `pytest_exit=0`, progreso hasta `[100%]`, cero líneas `FAILED`/`ERROR`, 10m56s sobre el árbol
  commiteado. **Nota de instrumentación**: `pyproject.toml` fija `addopts = "-q"` y el tier `full`
  agrega otro `-q`, o sea `-qq`, que imprime los puntos y las advertencias pero **suprime la línea
  final de conteo**. La evidencia válida es el código de salida más la ausencia de `FAILED`/`ERROR`;
  no hay que confundir “no hay resumen” con “no corrió”.
- Verificación independiente (`gentle-ai-verify`, read-only) sobre `git diff 9d7a6f8e..HEAD`:
  resultado en el cierre de la sesión; el plan de `gentle-ai review assess` con el ítem 2 escalado
  exigió verificador separado.

## Log

- **L1** (2026-11-16, pedido del owner, verbatim):
  > hey chat mira lo que pasa con el asistente lumat ahora cuando le hablo : '/home/stefan/repos/LumatData/Herramientas-verificadas-y-funcionales.md'  puedes investigar por que no funciona el asistente?

- **L2** (2026-11-16, autorización de lectura): el owner autoriza lectura read-only de producción.
  Evidencia recogida por SSH como `deploy` sobre `179.199.148.175`:
  `internal_chat_threads.assistant_state->'planner'` del hilo 49 y `->'guardrails'`.
  `printenv` dentro de `lumat-api-1`: `ASSISTANT_CHAT_PROVIDER=deepseek`,
  `ASSISTANT_CHAT_MODEL=deepseek-chat`.

- **L3** (2026-11-16, medición que descarta las otras hipótesis): dentro de `infra-api-1`
  (mismo árbol que `main`, versión `2026.11.9`) se corrió `plan_llm` real con los dos mensajes del
  hilo: `deepseek-flash` 3/3 válidos y `deepseek-chat` 3/3 válidos, 38 tools, guardrails `execute`.
  O sea: ni el código ni el modelo ni la API key estaban roto — el contrato estaba mudo.

- **L4** (2026-11-16, decisiones del owner, verbatim de la opción elegida):
  1. Techo invisible → **«Las dos»**: publicar el tope en el schema y acotar como red de seguridad.
  2. Plan bien intencionado que falla guardrails → **«Turno de reparación ante unsafe_plan»**.
  3. Trabajo de código → **«Sí, worktree ODD y rama odd/ (recomendado)»**.

- **L5** (2026-11-16, decisión de alcance del acotado, con derecho a veto del owner): el acotado se
  aplica al techo de página de `read_project_file` y no a todo límite numérico. Motivo: un `limit`
  de listado es semántico (cuántas filas pediste) y existe un test de integración que fija su
  rechazo — `tests/integration/test_assistant_chat.py::test_a_boundary_rejected_plan_does_not_reach_the_responder`
  con `customers.search limit=999`. Ese caso queda cubierto por el turno de reparación de T3, no por
  el acotado. Si el owner prefiere acotar todo límite numérico, S3 y T2 se reabren.

- **L6** (2026-11-16, corrección de dos tests que fijaban el comportamiento viejo, autorizada por S3 y S4):
  1. `tests/unit/test_assistant_tools.py::test_read_project_file_page_is_bounded_and_keeps_cursor_before_text`
     pasa a `..._page_is_clamped_and_keeps_cursor_before_text`: `page_limit + 1` ya no lanza
     `ValidationError`, se acota a `page_limit`. Conserva el default, el `next_offset` y el orden
     cursor-antes-que-texto.
  2. `tests/integration/test_assistant_harness_production.py::test_malformed_or_unwhitelisted_production_plan_falls_back_without_execution`
     pasa a `..._falls_back_after_one_repair`: la cuenta de llamadas al proveedor va de 2 a 3
     (planificador, reparación, título del hilo) y el segundo turno se afirma como turno de
     planificador —misma persona, `<available_tools>` presente, el rechazo `whitelisted=false` y el
     plan anterior en el mensaje final—. El texto visible no cambia.
  Motivo: los dos tests afirmaban exactamente lo que la decisión del owner cambia. Ningún otro test
  existente se tocó.

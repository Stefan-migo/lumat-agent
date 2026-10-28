# ODD — asistente-herramientas

Worktree: `/home/stefan/repos/lumat-agent-odd-asistente-herramientas` · rama `odd/asistente-herramientas` · base `4352f018`
Objetivo: el asistente ejecuta las herramientas que declara, encadenadas en el mismo turno; y tres correcciones de la interfaz del hilo.

## Specs

### Ejecución real de herramientas

- **S1** Un pedido de datos operativos (listar clientes, buscar un cliente, ver su historial y sus citas) ejecuta las herramientas en **ese mismo turno**, encadenadas, sin pedir aprobación cuando son de lectura. Cita (L1): *"el agente no puede cumplir con mi solicitud. no peude ejecutar multiples tools. la verdad que el agente es inservible aun"*.
- **S2** El planificador **no ofrece ni acepta** `kind: "delegate"`, y el grafo del asistente no tiene span delegado: todo pedido va por el loop de herramientas (decisión del owner, L2).
- **S3** Un turno cuyo pedido necesita datos y que termina **sin ejecutar ninguna herramienta** deja registrada la causa en `internal_chat_threads.assistant_state`, en una clave persistida legible: qué tools se ejecutaron (nombre y estado) y, si no hubo ninguna, por qué.
- **S4** La respuesta del asistente no puede afirmar que no puede ejecutar herramientas cuando el turno sí tenía catálogo disponible. Cita textual que **no** debe volver a ocurrir (L1): *"en esta respuesta no puedo ejecutar nada — las herramientas del panel están declaradas, pero este turno es solo texto, así que no puedo listar clientes ni correr la cadena que pides ahora"*.
- **S5** Cuando la cadena de lecturas alcanza el tope de pasos, el turno lo declara en la evidencia registrada (`cap_reached`) en vez de cortar en silencio.

### Interfaz del hilo

- **S6** La conversación se mantiene enfocada en el último mensaje: al abrir un hilo, al llegar un mensaje nuevo y mientras se transmite la respuesta, la vista muestra el final. Cita (L1): *"el foco de la conversacion se tiene que mantener abajo. siempre mantener el final solo si el usuario quiere scrollear up para leer mensajes anteriors. pero el foco debe estar en el ultimo mensaje siempre."*
- **S7** Si el usuario scrollea hacia arriba para leer mensajes anteriores, la vista **no** lo arrastra al final mientras dura ese scroll; vuelve a seguir el final cuando el usuario vuelve al fondo. Cita (L1): *"solo si el usuario quiere scrollear up para leer mensajes anteriors"*.
- **S8** El menú de la pestaña del hilo ofrece **Exportar conversación** y descarga el hilo completo (todos los mensajes, no solo los 10 visibles) en Markdown. Cita (L1): *"deberiamos agregar una opcion para exportar la conversacion completa"*, sobre el menú *"Renombrar / Cerrar pestaña / Eliminar hilo"*.
- **S10** El loop de herramientas no gasta dos pasos en el **mismo** `(tool, arguments)`: si el plan siguiente repite exactamente el paso anterior, la cadena se detiene y la causa queda registrada (`repeated_tool_call`), en vez de consumir el tope repitiendo la misma lectura.
- **S11** Una lectura de listado puede **avanzar**: `customers.list`/`customers.search` aceptan un desplazamiento opcional, y el catálogo del planificador lo expone, para que "listar todos los clientes" no devuelva siempre la misma página y la cadena pueda pasar al siguiente paso.
- **S12** La actividad que muestra el panel refleja **cada** paso ejecutado, con el nombre de su herramienta; hoy `_execution_events` lee el `tool_result` singular y colapsa una cadena de 4 pasos en un evento con `tool: null`.
- **S9** El composer del asistente no muestra el chip `@ Agente · Próximamente`. Cita (L1): *"lo que dice en el chatbox del asistente lumat ... agente proximamente. debe ser removido. ya no va."*

## Tasks

| ID | Specs | Ruta | Commit |
|---|---|---|---|
| T1 ✅ | S2, S3, S4, S5 | inline (padre): retirar la capa `delegate` del planificador y del grafo, sacar la negación de capacidad del responder | 1 |
| T2 | S1 | inline: cadena real contra el modelo (heredoc, DB harness) + tope de pasos con evidencia | 1 |
| T3 ✅ | S6, S7, S9 | worker + cierre del padre: foco al último mensaje + retiro del chip | 2 |
| T4 ✅ | S8 | worker + cierre del padre: exportar conversación (endpoint + menú) | 3 |
| T5 ✅ | S10, S11, S12 | worker + padre: el loop avanza y se reporta honesto | 4 |
| T6 ✅ | S10, S11 | worker + padre: guarda normalizada por `args_model`, cue de paginación en la evidencia, tope 4→6 | 7 |

## Log

- **L1** (pedido del owner, verbatim):

  > ok cosas que le siguen faltando al asistente lumat:
  >
  > - el foco de la conversacion se tiene que mantener abajo. siempre mantener el final solo si el usuario quiere scrollear up para leer mensajes anteriors. pero el foco debe estar en el ultimo mensaje siempre.
  > - deberiamos agregar una opcion para exportar la conversacion completa: /tmp/gpBwU85D/pi-clipboard-8db6228a-a2b0-4437-afe6-b8f56b295ada.png en este dialog.
  > - lo que dice en el chatbox del asistente lumat /tmp/gpBwU85D/pi-clipboard-54632f37-014f-41e0-b902-11114830c273.png agente proximamente. debe ser removido. ya no va.
  > - mira esta conversacion: [hilo 82 del panel: overview de capacidades → pedido de lista de clientes + Marcela Fuentes + historial operativo → el asistente responde que "este turno es solo texto"]
  >
  > el agente no puede cumplir con mi solicitud. no peude ejecutar multiples tools. la verdad que el agente es inservible aun

- **L2** (decisiones del owner, verbatim): `1. ¿Qué hacemos con la capa delegate / sub-agente customer_records? — Retirarla del planificador (recomendado)`. `2. ¿Cómo arrancamos y con qué autorización de worktree? — Worktree nuevo, las 4 unidades (U1→U4)`.

- **L3** (diagnóstico del turno fallido, verificado en `infra-db-1`, hilo 82, run `efec344c55f44ddeb660dab21558796e`):
  - `planner`: `kind=delegate`, `sub_agent=customer_records`, `valid=true`. El planificador obedeció `agent/prompts/assistant_plan.md:21-23` ("For bounded operational customer-record gathering, use `kind: \"delegate\"`").
  - `guardrails`: `decision=delegate`, `scope_valid=true`, `whitelisted=true`.
  - Evento `tool`: `tool=null`, `status=completed` → el span delegado corrió **0 pasos**; `DELEGATION_SPAN_MAX_STEPS = 2` (nodes.py:44) y `_delegation_plan` usa `json.loads` crudo y cae a `bounded_fallback` sin registrar decisión ni excerpt: falla en silencio.
  - `tool_results` quedó solo con el `memory.read` del bootstrap (`code_initiated: true`) = la "Actividad del agente (1 paso)" del panel.
  - `respond_stream` recibe persona + skills y cero evidencia de tools → el modelo inventó "este turno es solo texto".
  - `ASSISTANT_STATE_KEYS` (state.py:12) no incluye `tool_results`/`tool_steps`/`evidence`: hoy **no hay forma persistida de saber qué tools corrió un turno**.
- **L4** (entorno): main `4352f018` = `origin/main`, árbol limpio, un worktree. Stack local arriba (`infra-api-1` :8000, `lumat-harness-api-1` :8001, `lumat-harness-db-1` :5433 con 0 hilos). Worktree nuevo sin `infra/.env` ni `.venv`.

- **L5** (causa raíz de S4, decisiva): la frase *"este turno es solo texto"* **no fue una alucinación del modelo**: `execute()` (`nodes.py`, rama respond) arma un `tool_statement` que, cuando `state["tool_result"]` es `None`, decía literalmente *"The listed tools are panel capabilities only. This reply cannot invoke them."* El modelo repitió la instrucción al usuario. Su origen legítimo es `odd/tasks/dsml-responder-guard.md` (evitar que el modelo emita markup DSML como texto); la negación de capacidad era un efecto colateral. Nuevo texto: deja la regla de markup y **prohíbe** afirmar que no puede usar las tools. Tests actualizados en `tests/unit/test_assistant_tool_loop.py` y `tests/integration/test_assistant_harness_guardrails.py`.
- **L6** (T1 ejecutado): `PlannerOutput.kind` ya no acepta `delegate`, `sub_agent` desaparece del modelo, `app/chat/assistant/delegation.py` se elimina, el grafo pierde `delegation_span`, `extension_hook_metadata()` reporta `panel_subagents: retired`, y `tests/unit/test_assistant_delegation.py` se retira con sus dos tests de integración. `bash scripts/test.sh quick` verde y `bash scripts/test.sh db tests/integration/test_assistant_chat.py tests/integration/test_assistant_harness_guardrails.py` verde. S3 queda anclado con una aserción sobre `assistant_state["tool_results"]` (nombre y estado por tool ejecutada).

- **L7** (corte de entrega, registrado a pedido del harness): el commit 1 (`8511187c`) son 1238 líneas autoradas, de las cuales **1117 son borrado** — la capa delegada, sus 495 líneas de tests y los dos tests de integración que la ejercitaban. Estrategia de entrega: **un PR único**, con el commit 1 como unidad de review autocontenida (retiro de una capa) y T3/T4 como commits aparte. No se apila: el riesgo de una capa retirada no se revisa mejor partido en dos.
- **L8** (T3, cerrado por el padre): el worker entregó el hook y el retiro del chip, pero sus tests eran **verdes por construcción**: el helper del test no conectaba `onScroll`, así que `fireEvent.scroll()` no hacía nada y "stops following after the user scrolls up" pasaba sin ejercitar la pausa. Además el archivo era `.ts` con JSX, así que ni siquiera compilaba. Y `followingRef` sobrevive al cambio de hilo: scrollear arriba en un hilo dejaba el hilo siguiente abierto arriba, que es exactamente lo que S6 prohíbe. Corregido: test renombrado a `.tsx`, `onScroll` conectado, y el hook recibe `resetKey` (el `threadId`) para volver a seguir al abrir otro hilo, con un test propio. Verificado: `npx vitest run src/components/domain/useStickToBottom.test.tsx src/components/pages/AgentChat.test.tsx` → 82 tests verdes; `npx tsc -b` → 0.

- **L9** (T2, verificación con el modelo real — veredicto **parcial**): `gentle-ai-verify` levantó el harness sirviendo **el árbol del worktree** y repitió el pedido real. Turno 1: `planner.failure.reason=empty_completion` del proveedor → fallback genérico (flake del modelo, no del código: un sondeo directo al proveedor devolvió contenido válido). Turno 2: **S4 cumplido** (la respuesta ya no niega capacidad), pero **S1 incumplido**: `planner.kind=tool`, `guardrails.decision=execute`, `tool_steps=4`, `cap_reached=true`, y las 4 ejecuciones son `customers.list(limit=20)` **idénticas**; ni `customers.search` ni `customers.operational_history` corrieron. La respuesta final pidió autorización para lecturas ("dame la luz verde para correr la búsqueda"), que S1 prohíbe.
  Causa habilitante medida: `SearchArgs` (`app/chat/assistant/tools/registry.py`) solo tiene `query` y `limit` — sin desplazamiento, "listar todos los clientes" (43 filas) no puede avanzar y el planificador repite la misma llamada hasta el tope.
  Advisories reproducidos: `_execution_events` (`app/services/agent_chat.py:648`) lee el `tool_result` singular y reporta `tool: null` para una cadena de 4 pasos (es la misma forma que produjo el "Actividad del agente (1 paso)" del hilo 82); `record_llm_cost` deduplica por `call_key`, así que las llamadas repetidas del planificador no se ven en `cost_calls`.
  Modelo usado: `deepseek-flash` (barato) — un turno de dos se cayó por el proveedor.

- **L10** (decisión del padre sobre el conflicto que reportó T5): el grafo es `plan_llm → guardrails → execute_tool → tool_loop_head → plan_llm`, así que `tool_loop_head` **no ve el plan siguiente** — la guarda de repetición solo puede vivir en `guardrails`, que sí ve el plan nuevo y los `tool_results` previos. Cuando S10 choca con dos tests existentes (`test_cap_refuses_the_step_after_the_budget`, `test_s7_surplus_plans_do_not_extend_a_read_only_chain`) que usaban **llamadas idénticas** como fixture cómodo para probar el tope, **gana S10**: esos tests se reescriben con argumentos **distintos** por paso, de modo que sigan probando el tope (que sigue vigente para cadenas que avanzan) sin contradecir la regla nueva. No se debilita ninguna aserción: el tope se sigue midiendo.

- **L11** (gates medidos, con código de salida real): `bash scripts/test.sh unit` → **0**; `bash scripts/test.sh db tests/integration/test_assistant_chat.py tests/integration/test_assistant_harness_guardrails.py` → **0**; gate del panel completo (`npm run build` → `npm test`, porque el cambio toca `web/`) → **0**, `✓ built in 7.76s` y **116 archivos / 1342 tests** verdes. `bash scripts/test.sh full` corriendo al cierre de esta entrada, solo y sin otro suite Python al lado.

- **L12** (`bash scripts/test.sh full` en rojo, **ambiental y preexistente**): la corrida terminó con `Timeout` en `tests/functional/test_seed_dev.py::test_dev_seed_populates_dashboard_and_composer`. Aislado, el mismo test falla por otra razón que no toca el diff: `db/migrate.sh` devuelve `Only roles with the CREATEROLE attribute and the ADMIN option on role "app" may alter this role`. Prueba de que es del entorno y **no** de este trabajo: el mismo test, aislado, falla idéntico en el worktree principal intacto (`45bf8d55`, release v2026.10.8) contra *su* base de test (puerto 5986). Este branch no toca `db/` ni `scripts/` (`git log origin/main..HEAD -- db/ scripts/` vacío). Queda como defecto de entorno registrado, no como regresión; el suite completo corre limpio en CI, que tiene su propio Postgres.
- **L13**: `main` avanzó a `45bf8d55` (release `v2026.10.8`) mientras este trabajo estaba en curso; la base del branch es `4352f018`. No hay cambios ajenos en las superficies tocadas, así que la entrega requiere traer `origin/main` al branch (obligatorio por `strict: true`) y volver a correr los checks enfocados sobre el árbol combinado.

- **L14** (S1 **cumplido**, medido con el modelo de producción): mismo pedido, `deepseek-chat` (hilo 6 del harness): `tool_steps=3`, `cap_reached=false`, `execution_stall=null`, y **tres herramientas distintas** ejecutadas y completadas — `customers.list{limit:20}` → `customers.search{"Marcela Fuentes"}` → `customers.operational_history{customer_id:1}`. Respuesta decisiva: *"Listo, hice los tres pasos."*; el cierre ofrece trabajo **adicional**, no permiso para las lecturas pedidas, que ya habían corrido. `type=tool` events con nombre por paso (S12 intacto).
  **Corrección de premisa**: el fallo de L9 era **del código, no del modelo**. El control con `deepseek-flash` sobre el mismo árbol también avanzó (4 pasos, luego de paginar 0/20/40) y tampoco pidió permiso. Lo que faltaba era offset, tope 5+ y el cue de paginación.
  **Corrección de entorno (para `docs/ops.md` y memoria)**: fijar **solo** `CHAT_MODEL` **no** cambia el modelo del asistente; el asistente lee `assistant_chat_model`, que viene de `ASSISTANT_CHAT_MODEL` (`infra/docker-compose.yml` lo reenvía). Sin eso, cualquier medición local del asistente mide otro modelo que el elegido.
  **Caveat honesto**: la corrida usó el árbol **sin commitear** (esta ronda de T6). El commit siguiente lo fija, y el probe de integración `test_a_paged_read_chain_advances_instead_of_stalling_as_a_repeat` ancla de forma determinista que paginar es progreso y no la repetición que la guarda detiene.
- **L15** (tope de pasos 4 → 6): justificado por la forma medida del pedido real — tres páginas de 43 clientes, la búsqueda por nombre y el historial operativo son cinco pasos. El `cap_reached` se sigue reportando cuando se alcanza.

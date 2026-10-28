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
- **S9** El composer del asistente no muestra el chip `@ Agente · Próximamente`. Cita (L1): *"lo que dice en el chatbox del asistente lumat ... agente proximamente. debe ser removido. ya no va."*

## Tasks

| ID | Specs | Ruta | Commit |
|---|---|---|---|
| T1 ✅ | S2, S3, S4, S5 | inline (padre): retirar la capa `delegate` del planificador y del grafo, sacar la negación de capacidad del responder | 1 |
| T2 | S1 | inline: cadena real contra el modelo (heredoc, DB harness) + tope de pasos con evidencia | 1 |
| T3 | S6, S7, S9 | worker: foco al último mensaje + retiro del chip | 2 |
| T4 | S8 | worker: exportar conversación (endpoint + menú) | 3 |

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

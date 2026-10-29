# ODD: asistente-memoria-captura

**Branch**: `odd/asistente-memoria-captura` · **Worktree**: `../lumat-agent-odd-asistente-memoria-captura` · **Base**: `23d1d29f` (= `main` al arrancar, 2026-10-29)
**Status**: planning — frente 1 de 2. El frente 2 (eje `user` cross-project) va en su propio worktree/PR (`asistente-memoria-usuario`); el diseño aprobado está en Engram obs 6959.
**Constraints**: MEM-7 (`openspec/specs/memory/spec.md:142` — no escribir cada mensaje); MEM-3 (la captura no inyecta contexto, escribe en el storage); `cost_allowed=False` ⇒ no se captura; el nodo nunca rompe el turno ni el stream de respuesta (degrada como `write_recap`); dedup por `normalized_hash` y `judge_memory_relations` ya existen, no se reimplementan; `producer=AGENT`, `origin_thread_id` obligatorio (MEM-9).
**Source**: conversación 2026-10-29 (decisiones en `## Log`) + verificación de código (`tukulpan.py`, `assistant/nodes.py`, `assistant/graph.py`, `tools/registry.py`, `agent_chat.py`, Engram `internal/store/store.go:11346-11420`).

## Specs

**S1 — Captura autónoma.** El asistente guarda memorias relevantes sin que el usuario se lo pida.
> "necesito que el agente logre guardar memorias relevantes autonomamente"

**S2 — El disparador no es el usuario.** Ningún requisito de que la persona diga "guardá esto".
> "la idea aqui es que el usuario no le tenga que decir cuando guardar la memoria"

**S3 — Disparadores acotados.** La captura corre por turnos, por resultado durable y por inactividad; no en cada turno.
> "que genere summarys cada cierto tiempo? cuando exista algo relevante? cada ciertos turnos?"

Decidido por el owner (2026-10-29): "podrian ser 1 y 2. turnos + tool, y worker por inactividad".

**S4 — Un hilo que existió deja rastro.** Un hilo con varios turnos produce al menos una memoria resumen, aunque nadie lo cierre.
> "si una conversacion ya tiene varios turnos quizas. hacer un resumen para saber que existio ese hilo.?"

**S5 — Captura determinística.** El "cuándo" lo decide el código; el modelo solo aporta el contenido, bajo schema estricto.
> "con esa captura de memorias deterministicas."

## Tasks

- [ ] **T1 — Gate determinístico de captura.** `app/chat/assistant/memory_capture.py`: `thread_turn_index()`, `capture_budget_exhausted()`, `should_capture()` → `CaptureDecision(reason)` con `turnos | durable_write | compaction`, o `None`. Puro respecto del turno: lee DB sólo para conteos. Tests: `tests/unit/test_assistant_memory_capture.py`. Route: inline. Commit: —
- [ ] **T2 — Extractor con schema estricto.** `extract_candidates()` reusa el seam pagado `_planner_call(messages, state, "memory_capture")` (registra costo) con el prompt nuevo `agent/prompts/assistant_memory_capture.md`; devuelve 0..3 candidatos validados (mismas reglas que `MemoryWriteArgs`: `topic_key ^agent:`, `tipo` en los 4, `contenido` ≤2000). Tests: RED con JSON inválido, lista vacía y candidato fuera de schema. Route: inline. Commit: —
- [ ] **T3 — Nodo `memory_capture` en el grafo.** Entre `evidence` y `END`; escribe por `tukulpan.upsert(producer=AGENT, origin_thread_id=…)`; `try/except` → evidencia degradada, nunca excepción. Aristas: `evidence → memory_capture → END`. Tests: `tests/unit/test_assistant_tool_loop.py` (una captura por turno elegible, cero con costo bloqueado, cero sin candidatos), `tests/unit/test_cortex_session_loop.py` (aristas). Route: inline. Commit: —
- [ ] **T4 — Worker por inactividad.** `sweep_idle_threads()` en el mismo módulo; llamado desde `app/ops/worker.py::run_cycle` (el cron `*/5` ya existe, sin cambio de infra). Idempotente por `topic_key` derivado de `(thread_id, last_message_id)`; acotado por lote. Tests: `tests/integration/test_memory_capture_sweep.py` (un hilo inactivo captura una vez, dos ticks no duplican). Route: inline. Commit: —
- [ ] **T5 — Protocolo.** Persona + skill `memoria-tukulpan` + `assistant_plan.md`: checklist enumerado al estilo Engram y la aclaración de que `memory.write` no pide aprobación y se encadena con `follow_up`. Tests: `tests/unit/test_assistant_prompt_contract.py`. Route: inline. Commit: —
- [ ] **T6 — Spec MEM-13.** `openspec/specs/memory/spec.md`: requerimiento de captura determinística con escenarios (gate, schema, costo bloqueado, idempotencia, no-inyección). Tests: `tests/spec/test_memory_spec.py`. Route: inline. Commit: —
- [ ] **T7 — Verificación y commits.** `bash scripts/test.sh quick` por paso; `full` al cierre del feature; commits por unidad (sin atribución IA). Route: inline. Commit: —

## Log

**L1** (2026-10-29, pedido original verbatim):
> por ahora me interesa la memoria del asistente lmat. la de chatbot al parece esta funcioando bien.
>
> pero la del asistente lumat si me interesaria abrir esos dos frentes principales.
>
> - que el agente escriba memorias autonomamente. si una conversacion ya tiene varios turnos quizas. hacer un resumen para saber que existio ese hilo.?
>
> o algo asi? no se cuando . pero necesito que el agente logre guardar memorias relevantes autonomamente. no se si el skill de tukulpan esta correcto. pero si la idea aqui es que el usuario no le tenga que decir cuando guardar la memoria. que genere summarys cada cierto tiempo? cuando exista algo relevante? cada ciertos turnos? no se como proceder realmente. esta memoria esta basada en engram de gentleman programming. pueder revisar el repositorio de engram para evaluar ideas. de como proceder. con esa captura de memorias deterministicas.
>
> - la segunda es el scope de memoria del usuario. tien que dar la sensacion de que el asistente lumat sabe del usuario. y puede obtener informacion a traves de todos los proeyectos es posible? pero esta informacion si tiene que estar filtrada solo para el usuario. no se pueden filtrar informacion entre usuarios.

**L2 — Decisiones del owner** (2026-10-29, verbatim de su respuesta):
- Captura: "Gate en código + extracción con LLM".
- Disparadores: "podrian ser 1 y 2. turnos + tool, y worker por inactividad".
- Eje usuario: "Eje user nuevo, atado al autenticado" (frente 2, otro worktree).
- Auditoría: "Sí, lista y borrar en el workspace" (frente 2).
- Arranque: "Sí: frente 1 en worktree, PR separado".

**L3 — Evidencia de investigación (Engram).** El mecanismo copiable es el reparto: el runtime dispara y extrae, el modelo solo produce texto. `internal/store/store.go:11346-11420` (`ExtractLearnings`): regex de `## Key Learnings` / `## Aprendizajes Clave`, ítems numerados o bullet, mínimo 20 caracteres y 4 palabras, dedup por hash normalizado. Hooks: session-end siempre escribe summary; subagent-stop siempre parsea. Lumat no tiene ninguno de los dos; su único write automático es el recap a 4k tokens, que es un volcado literal (`app/services/agent_chat.py:104-140`), no un resumen.

**L4 — Evidencia de código (señales ya disponibles).** `ToolDefinition.write` (`tools/registry.py:801`) da el gate por resultado durable sin tabla nueva; `state["compaction"]` y `state["cost_mode"]` ya viajan en el turno; `_planner_call` (`assistant/nodes.py:344`) ya registra costo por `call_key`, así que el extractor no abre un segundo camino de facturación. `create_thread`/`run_assistant` no tienen contador de turnos: se cuenta contra `internal_chat_messages` (índice `thread_id, created_at, id`).

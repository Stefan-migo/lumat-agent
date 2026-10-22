# HANDOFF — Asistente Lumat: rapso sessions pendientes (planning + configuración)

**Fecha**: 2026-10-13. **Estado**: hilo "asistente lumat" con 2 rapso sessions pendientes. En este chat se cerraron 2 sesiones (persona/prompts y memoria Tukulpan), ambas con handoff a ODD.

## Estado actual

- `main` = `63fde6d9`.
- `ready-for-odd/`: `2026-09-24-harness-audit-y-cobertura-panel`, `2026-10-05-asistente-lumat-workspace-multiagente`, `2026-10-13-asistente-lumat-ejecucion-y-prompt`, `2026-10-13-asistente-lumat-memoria-tukulpan`.
- **Handoffs ODD pendientes** (chats aparte): `odd/handoffs/asistente-lumat-persona-prompt.md` y `odd/handoffs/asistente-lumat-memoria-tukulpan.md`. **Coordinan**: ambos tocan `agent/personas/assistant.md`.
- **Memorias del hilo** (Engram, project `lumat-agent`): `assistant-lumat/architecture-gaps` (6391), `.../followup-tool-execution-prompt` (6392), `.../backlog-memory-tukulpan` (6393), `.../backlog-planning-sessions` (6394), `.../backlog-kb-independence` (6395), `.../backlog-configuration-layer` (6396).

## Sesión A — Sesiones de planificación (obs 6394)

**Problema**: hoy las sesiones de planificación solo activan/desactivan un estado; son inservibles.

**Forma deseada (owner)**: guiada —
1. hacer consultas al usuario,
2. guardar **memoria estructurada**,
3. guardar **decisiones**,
4. cerrar con un **artifact: reporte de la sesión**.

**Prior art que NO hay que re-litigar** (sesión `2026-10-05-asistente-lumat-workspace-multiagente`, 18 decisiones):
- **D2**: planning simplificado, CONSERVA un artifact reporte final.
- **D16**: modo planning = read-only para el negocio (reusa el tier gate).
- **D18**: reporte de planning = memoria Tukulpan (`scope=agent`) como fuente de verdad + preview markdown.
- **D6**: handoff Cortex→SDB opcional, no obligatorio.
- Task docs: `odd/tasks/asistente-planning.md`, `odd/tasks/asistente-sdb.md`.
- **Handoff previo (leerlo)**: `handoff/asistente-after-slice-3` (Engram obs 5811) — "continuar con Slice 4 (planning)".

**Objetivo**: abrir rapso session, verificar el estado real (¿qué de D2/D6/D16/D18 está implementado?), y decidir el rediseño guiado.

## Sesión B — Capa de configuración / tools default-on (obs 6396)

**Problema**: las 7 tools opt-in arrancan vacías (`ToolPolicy.opt_in_enabled` default `[]`, `app/services/project_config.py:15-16`). El owner quiere que (a) se **guarde la opción** (si se activan todas, queda guardado), o (b) todas arranquen **activadas por defecto**.

**Estado verificado**: la persistencia **ya existe** por-tool, por proyecto (`Project.config`) y con override por hilo (`InternalChatThread.assistant_state`), GET/PUT/DELETE en `/chat/threads/{id}/tool-policy`. **Falta solo el DEFAULT.**

**Decisión pendiente**: prender las **7** opt-in (incluye `project.create/rename/archive/merge`, que **mutan datos**) o solo las **seguras** (`web.search`, `web.fetch`, `automation.create_rule`).

**Prior art**: **D7** (tiers de riesgo), **D10/D11/D12** (global = seguridad + baseline; proyecto aditivo; proyecto vacío hereda global). Task doc: `odd/tasks/asistente-workspace-config.md`.

**Insight del owner (rector)**: más que tools nuevas, falta una **capa de configuración** que moldee al asistente.

## Cómo abrir una rapso session

Skill **rapso-session** (`/rapso-session`):
1. **session-init**: detectar tema; **chequear resume** en `.rapsodia-code/sessions/open/` + Engram; crear `.rapsodia-code/sessions/open/YYYY-MM-DD-<slug>/session.md`; `mem_save` init (`cortex-session/<slug>/init`).
2. **discuss**: capturar decisiones/riesgos en session.md + Engram — **un `topic_key` por item** (`cortex-session/<slug>/decision/<topic>`); no batchear; nunca reusar un slug para otra decisión.
3. **session-close**: consolidar → `report.md` → preguntar explícitamente si cierra con handoff ODD → mover a `ready-for-odd/` (con handoff) o `archived/` (sin) → `mem_save` report (`cortex-session/<slug>`) + `mem_session_summary`.

**Disciplina transversal**: verificar con código antes de diseñar; no re-litigar decisiones cerradas; chat en español rioplatense, artefactos en inglés; el AGENTE Lumat responde en **español chileno de Santiago**.

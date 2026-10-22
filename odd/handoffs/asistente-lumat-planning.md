# HANDOFF — Asistente Lumat: ODD de sesiones de planificación guiadas

**Fecha**: 2026-10-13. **Estado**: handoff pendiente en `.rapsodia-code/sessions/ready-for-odd/2026-10-13-asistente-lumat-planning/`. Nada implementado todavía.

## Qué construir (Feature)

Rediseñar las **Sesiones de planificación** del asistente como un **brainstorming guiado** por un agente-facilitador:

1. **Hilo propio** por sesión (D8).
2. El agente **abre/cierra** la sesión por **orden explícita** del usuario (tools), además del botón; al cerrar **ofrece** cerrar con artifact + handoff (D3).
3. Conversa **libre** con **checklist mínima** (objetivo, decisiones, riesgos, próximos pasos) que gatea el cierre (D7).
4. **Captura explícita con confirmación**: `planning.record_decision` / `planning.record_note` (D5).
5. Si toca Lumat, **lee el estado** con tools; la ejecución se declara en el handoff, no se ejecuta (D4, D16).
6. **Reporte sustantivo** (no topic-only) en memoria Tukulpan `agent` + preview markdown (D2/D18).
7. **Handoff a SDB** condicional: solo si es de Lumat y hay acción concreta, confirmado por el usuario (D6).

## Por qué

Diagnóstico verificado (obs 6437): el modo planning read-only (D16) y el borrado del clasificador heurístico **ya están implementados**. Lo que falta es la **sesión guiada** y la **sustancia del reporte**. Hoy el cierre escribe solo JSON con el topic (`app/panel/api/routes/chat.py:349-352`) — la queja del owner ("solo activa/desactiva un estado") es exacta.

## Fuente (leer PRIMERO)

- `.rapsodia-code/sessions/ready-for-odd/2026-10-13-asistente-lumat-planning/report.md` — resumen + ODD readiness + scope.
- `.rapsodia-code/sessions/ready-for-odd/2026-10-13-asistente-lumat-planning/session.md` — 8 decisiones (D1-D8) + risks.
- Engram: `cortex-session/2026-10-13-asistente-lumat-planning/init` (6436); `.../decision/*` (6438, 6442, 6443, 6444, 6446, 6447, 6448, 6451); `.../finding/current-planning-state` (6437).
- Prior art a **NO re-litigar**: sesión `2026-10-05-asistente-lumat-workspace-multiagente` (D2/D6/D16/D18); handoff obs 5811.

## Archivos a explorar/tocar

- `app/chat/assistant/nodes.py` — effective tools / tier gate (D16).
- `app/panel/api/routes/chat.py` — open/list/detail/close/reopen + `sdb_requested`.
- `app/services/tukulpan.py` — `write_agent_report`.
- `app/services/agent_chat.py` — `_run_sdb_tasks`, escritura del reporte.
- `app/models.py` — `InternalChatThread.current_plan`.
- `agent/registry.yaml` — `cortex_session` (reemplazar por las tools nuevas).
- `web/src/components/pages/AgentChat.tsx`, `PlanningSessions.tsx` — toggle + lista.

## Criterio de aceptación observable

- El usuario pide por chat "abrimos sesión de planificación con `<tema>`" → se crea la sesión en un hilo propio.
- El agente pregunta y captura decisiones/notas **con confirmación**.
- El agente **no** ejecuta tools de negocio (read-only).
- El agente **no** ofrece cerrar hasta cubrir la checklist mínima.
- Al cerrar: reporte **sustantivo** en memoria `agent` + preview markdown.
- Handoff a SDB **solo** si es de Lumat y hay acción concreta, confirmado por el usuario.

## Coordinación

- **Feature A (persona act-first)**: toca `agent/personas/assistant.md`. El **overlay de modo planning** no debe pelear con la persona global.
- **Slice 5** (SDB = loop + verify, D14/D15): el handoff a SDB depende de su forma final.

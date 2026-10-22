# HANDOFF — Asistente Lumat: ODD de la capa de configuración (y tools default-on)

**Fecha**: 2026-10-13. **Estado**: handoff pendiente en `.rapsodia-code/sessions/ready-for-odd/2026-10-13-asistente-lumat-config-layer/`. Nada implementado todavía.

## Qué construir (Feature)

Una **capa de configuración** que modele al asistente, estructurada como **config por proyecto extendida**:

1. **Default**: las **7 tools opt-in** arrancan activadas por defecto (`project_config.py:15-16`), con el tier gate siguiendo aplicando a las destructivas (D1).
2. **Modelo**: extender `ProjectConfig` con **7 dimensiones** (D2/D3): personalidad/tono, formato de respuesta, comportamiento de memoria, relación con la KB, skills del proyecto, agentes configurables, sesiones de planning. Global = baseline/seguridad; proyecto aditivo (D10).
3. **Fundación primero** (D4): modelo + **arreglar los 3 bugs de wiring UI** + agentes visibles/editables.
4. **Skills globales nuevas** (D5): `planning`, `tools`, `kb`.

## Por qué

El owner: *"más que tools nuevas, falta una capa de configuración que moldee al asistente"* (obs 6396). Verificado (obs 6456/6463): la capa actual es solo `instructions` + `tool_policy` + `skills`; el catálogo de skills del asistente tiene **1 sola skill**; los agentes están **hardcodeados**; y hay **3 bugs de wiring UI** (obs 6391).

## Fuente (leer PRIMERO)

- `.rapsodia-code/sessions/ready-for-odd/2026-10-13-asistente-lumat-config-layer/report.md` — resumen + ODD readiness + slices.
- `.rapsodia-code/sessions/ready-for-odd/2026-10-13-asistente-lumat-config-layer/session.md` — 5 decisiones (D1-D5) + risks.
- Engram: `cortex-session/2026-10-13-asistente-lumat-config-layer/init` (6455); `.../decision/*` (6459/6460/6461/6462/6466); `.../finding/current-config-state` (6456), `.../finding/skills-catalog` (6463).
- Prior art a **NO re-litigar**: D10/D11/D12 (obs 5694/5695/5697); "skills por sección, no agentes por sección" (obs 5687); evaluación base (obs 6391).

## Archivos a explorar/tocar

- `app/services/project_config.py` — `ToolPolicy` (default), `ProjectConfig`, `resolve_effective_config`.
- `app/chat/assistant/tools/registry.py` — tiers (`:698-734`).
- `app/panel/api/routes/chat.py` (`:105-142`), `app/panel/api/routes/projects.py` (`:80-95`).
- `app/services/skills.py`, `agent/registry.yaml` (`:61-64`), `agent/skills/assistant/`.
- `app/chat/assistant/nodes.py` (`:521-544`, `:594-597`).
- `web/src/components/pages/` — `AgentChat.tsx`, `AssistantWorkspace.tsx`, `Settings.tsx`, `ProjectsPage.tsx`.

## Criterio de aceptación observable

- Las 7 opt-in arrancan activas por defecto (el tier gate sigue aplicando a las destructivas).
- `ProjectConfig` expone las 7 dimensiones.
- Los 3 bugs de wiring UI resueltos: "Capacidades" con datos, "Recursos del proyecto" real, "Hilos por proyecto" disponible.
- Los agentes se ven y se editan.
- Las 3 skills globales (`planning`/`tools`/`kb`) son cargables por el planner.

## Coordinación

- **Sesión A (planning)**: el skill `planning` depende del diseño de la Sesión A (`odd/handoffs/asistente-lumat-planning.md`).
- **Feature A (persona act-first)**: ya mergeada (PR #579). "Act-first" es persona; el skill `tools` complementa con "qué tool para qué".

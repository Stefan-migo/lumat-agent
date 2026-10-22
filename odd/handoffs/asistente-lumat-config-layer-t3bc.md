# HANDOFF — asistente-lumat-config-layer → T3b + T3c (chat nuevo)

**Fecha**: 2026-10-14. **Estado**: T0–T3a hechos y committeados. T3b y T3c pendientes.

## Locator (leer PRIMERO)

- **Feature doc (fuente de verdad)**: `odd/tasks/asistente-lumat-config-layer.md` — leer hasta
  `## Log`. Ahí están Specs S1–S9, Tasks T0–T9 y el Log L1–L17 con toda la evidencia.
- **Worktree**: `/home/stefan/repos/lumat-agent-odd-asistente-lumat-config-layer`
- **Branch**: `odd/asistente-lumat-config-layer` · **Base**: `143ced8b` (= `origin/main` al crear)
- **Mirror Engram**: topic `odd/asistente-lumat-config-layer/tasks` (obs 6612).

## Estado actual

| Task | Estado | Commits |
| --- | --- | --- |
| T0 feature doc | done | 05b46b91 |
| T1 default-on 7 opt-in | done | 49227b57 |
| T2 sidebar Capacidades | done | fd5e39e2 |
| T3a Recursos selector + persistencia | done | b1313675 (backend), b1f670c0 (frontend) |
| **T3b pinned resources in context** | **PENDING** | — |
| **T3c planning.read_report tool** | **PENDING** | — |
| T4–T9 | pending | — |

RDD assess acumulado (`--base-ref 143ced8b --committed-only`): risk `medium`,
`review_due=false` (`under_budget`, 788 líneas). Frontera pendiente en el slice.

## Qué construir (T3b + T3c)

Diseño cerrado (S3, L16): fijar un recurso **marca** (ya hecho en T3a) y el contenido se lee
**on demand con tools** — nunca se inyecta completo cada turno.

### T3b — pinned resources in context
1. Exponer los recursos fijados como **referencia compacta** en el contexto del turno, para
   que el planner sepa que existen. Sugerido: un bloque `<pinned_resources>` con
   nombre/id/slug (no contenido) armado en `assemble_context` o en el armado del prompt
   (`app/chat/assistant/nodes.py`, `app/services/agent_chat.py`).
2. **Archivos fijados** → el agente los lee con `read_project_file` (ya existe; S6/T6 le
   agregará `offset`/`limit`).
3. **Habilidades fijadas** → declararlas para el responder (reusa `_skill_context` /
   `state.guardrails.skills` en `nodes.py`).
4. **Sesiones fijadas** → leer el reporte con la tool nueva (T3c).

### T3c — tool `planning.read_report`
1. Nueva tool `planning.read_report` en `app/chat/assistant/tools/registry.py`
   (`ToolDefinition`, `read_only=True`, `tier="default"`), args `{slug}`.
2. Handler: hallar la sesión por slug y leer su reporte. Hoy `_planning_thread` vive en el
   route layer (`app/panel/api/routes/chat.py:145`) y el reporte se lee con
   `tukulpan.get_by_key` (`_planning_report`, `chat.py:150`). Conviene mover/extraer un helper
   a `app/services/planning.py` y reusarlo.
3. Agregar a `agent/registry.yaml` (assistant `tools_whitelist`), a `ROLE_TOOL_ALLOWLIST`
   (ADMIN/OPERADOR, como el resto de `planning.*`), y a `DEFAULT_TOOLS` en
   `tests/unit/test_tool_tiers.py`.

## Env del worktree (ya provisionado en esta sesión)

- `.venv` sincronizado (`uv sync`) y `media/` creado.
- DB de test aislada: `bash infra/test-db.sh up` (puerto derivado = **6376**).
  `infra/.env` ya copiado desde el worktree primario.
- `web/node_modules` instalado (`npm install`).
- **Antes de pytest**: `eval "$(bash infra/test-db.sh env)"` (si no, el admin URL cae al
  usuario `app` y falla auth).

## Comandos

- Backend: `uv run --no-sync pytest tests/ -q` (suite completa ≈ 2171 tests).
- Frontend: `npm test` en `web/` (≈1192 tests). **Ojo**: en esta máquina la suite completa
  crasheó una vez por memoria baja → usar `npx vitest run --maxWorkers=2` si pasa.
- Build: `npm run build` en `web/` (tsc -b + vite).
- RDD: `gentle-ai review mode status` (está **on** global). Assess por commit:
  `gentle-ai review assess --cwd <worktree> --agent opencode --base-ref 143ced8b --committed-only --json`.

## Reglas

- Chat en Rioplatense; **artefactos/código/commits/docs en inglés**; sin `Co-Authored-By`.
- ODD: TDD (RED→GREEN) cuando hay test determinista; un work unit = un commit (≤5 archivos);
  actualizar el feature doc + mirror después de cada task.
- Slices pequeños: T3b y T3c son separables; T3c es autocontenido (tool + whitelist + tests).
- No tocar `ProjectConfig` para las 7 dimensiones (non-goal) ni los bugs de UI de
  `odd/panel-visual-alignment` (otro agente).

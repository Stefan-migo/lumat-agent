# HANDOFF — Asistente Lumat: ODD de persona/prompts (act-first)

**Fecha**: 2026-10-13. **Estado**: handoff pendiente en `.rapsodia-code/sessions/ready-for-odd/2026-10-13-asistente-lumat-ejecucion-y-prompt/`. Nada implementado todavía.

## Qué construir (Feature A)

Reescribir la **persona + prompts** del asistente del panel para que:
1. **Ejecute tools** en vez de pedir permiso o presentar un plan y esperar.
2. Trate la **KB como fuente opcional** (no como bloqueo/dependencia).
3. Tenga **personalidad y formato**: español chileno de Santiago, cálido pero conciso (~5–8 líneas; listas/tablas solo para enumerar).

## Por qué

Diagnóstico **H3 verificado**: el agente NO tiene un bug de ejecución — **nunca emite el tool call**. La causa es el prompt KB-céntrico (`agent/personas/assistant.md:1`: *"answer only from `<kb>`; if absent or insufficient, do not synthesize facts"*) y que ningún prompt le dice ACTUAR (`assistant_plan.md:14-18` permite `kind:"respond"` sin tool).

## Fuente (leer PRIMERO)

- `.rapsodia-code/sessions/ready-for-odd/2026-10-13-asistente-lumat-ejecucion-y-prompt/report.md` — resumen + ODD readiness.
- `.rapsodia-code/sessions/ready-for-odd/2026-10-13-asistente-lumat-ejecucion-y-prompt/session.md` — **diseño v1 completo** de la persona (sección "Diseño de la nueva persona + prompts").
- Engram: `cortex-session/2026-10-13-asistente-lumat-ejecucion-y-prompt` (obs 6405, report), `.../design/persona-prompt-v1` (obs 6402, diseño), `.../finding/h3-kb-centric-prompt` (obs 6398, diagnóstico).

## Archivos a tocar

- `agent/personas/assistant.md` — reemplazo (secciones Environment / How you act / Knowledge and evidence / Memory / Skills / Personality and format / Safety).
- `agent/prompts/assistant_plan.md` — delta: preferir `kind:"tool"` cuando el pedido necesita datos o acción.
- `agent/prompts/assistant_respond.md` — delta: quitar el gate KB; responder de tool results + `<kb>`; si `<kb>` vacío, seguir con evidencia de tools.

## Criterio de aceptación observable

- Reproducir el caso de producción (pedido de datos con `<kb>` vacío): el agente **ejecuta tools**, no pide permiso ni devuelve un plan.
- `<kb>` vacío **no** bloquea la respuesta.
- Respuesta concisa, en español chileno de Santiago.
- Suite del harness verde: `tests/integration/test_assistant_harness_*.py`.

## Cómo (ODD)

1. Crear worktree desde `main` (`63fde6d9`): `rapso worktree create asistente-lumat-persona-prompt` → rama `odd/asistente-lumat-persona-prompt`.
2. Crear `odd/tasks/asistente-lumat-persona-prompt.md` desde el reporte (commit en la rama, fuera de bloques `gentle-ai`).
3. Implementar con **Graph Check** + commits atómicos (Conventional Commits, sin atribución IA).
4. Verificar con los tests del harness; correr `gentle-ai review assess` sobre el commit (RDD).
5. Al crear el task doc, mover la sesión de `ready-for-odd/` → `archived/` (consumir el inbox).

## Restricciones

- Respetar **D10/D11/D12** (global = seguridad + baseline; proyecto aditivo; proyecto vacío hereda el global).
- **NO** tocar la ejecución de tools (no hay bug).
- **NO** incluir la Feature B (uploader KB) acá: va por el track `asistente-agentes-proyecto` (A3.5). Ver `handoff/asistente-agentes-proyecto-a35`.

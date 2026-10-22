# HANDOFF — asistente-lumat-config-layer → T8 (chat nuevo)

**Fecha**: 2026-10-15. **Estado**: T0–T7 hechos y **mergeados a `main`**. T8–T9 pendientes.

## Locator (leer PRIMERO)

- **Feature doc (fuente de verdad)**: `odd/tasks/asistente-lumat-config-layer.md` — ya en `main`.
  Leer hasta `## Log`. Ahí están Specs S1–S9, Tasks T0–T9 y el Log L1–L25 con toda la evidencia.
- **Base**: `main` @ `43237341` (merge de #623; incluye #621 T5, #622 T6, #623 T7).
- **Mirror Engram**: topic `odd/asistente-lumat-config-layer/tasks` (última revisión = post-T7).
- **Nuevo worktree**: con consentimiento explícito del owner,
  `rapso worktree create asistente-lumat-config-layer-t8 --yes`
  → `/home/stefan/repos/lumat-agent-odd-asistente-lumat-config-layer-t8`, branch `odd/asistente-lumat-config-layer-t8`.

## Estado

- **T0–T4** mergeados antes (PRs #616/#617/#618).
- **T5** (multimodal tool results, S5) → PR **#621** MERGEADO.
- **T6** (partial reads offset/limit, S6) → PR **#622** MERGEADO.
- **T7** (docx/xlsx/md attachments, S7) → PR **#623** MERGEADO.
- **T8–T9** pendientes. PRs del workstream **panel-tecnico** (#607/#615/#619/#620) siguen abiertos: **NO son de este ODD**, no tocarlos.

## T8 — Three global skills (S8)

Owner decision **D5**: adoptar `planning`, `tools` y `kb` como **skills globales** del asistente;
`lumat-concept` queda diferido. Hoy el asistente tiene **una sola skill**
(`agent/skills/assistant/memoria-tukulpan.md`, declarada en `agent/registry.yaml` bajo `assistant.skills`).
Las tres skills deben ser **cargables por el planner**.

Cómo funciona (verificado):
- `app/services/skills.py`: `global_skill_index(config)` lee `config.skills` (las de `assistant.skills`)
  y devuelve `SkillDefinition(name, description, scope="global", path)`; `load_skill_body(defn)` lee
  `agent/<path>` (`_AGENT_DIR / defn.path`). Los cuerpos viven en `agent/skills/assistant/*.md`.
- `nodes.py`: `_effective_skill_index` (= `global_skill_index`), `_validated_skills` (valida declaradas
  + pinned contra el índice) y `_skill_context` (carga los cuerpos en el responder).
- El planner ve el índice de skills (`available_skills` en `plan_llm`) y puede declararlas en el plan
  (`PlannerOutput.skills`); el nodo guardrails/responder las resuelve.

Piezas probables a tocar: 3 archivos markdown nuevos
(`agent/skills/assistant/planning.md`, `tools.md`, `kb.md`) + declararlas en `agent/registry.yaml`
(`assistant.skills` con `name`/`description`/`path`). Ojo: agregar skills cambia el catálogo que ve el
planner → puede afectar el hash congelado de `tests/unit/test_assistant_delegation.py` (recalcular si
el hash incluye las skills; verificar qué serializa `_planner_tool_catalog` — a T7 sólo incluía tools,
no skills, así que probablemente NO cambia; confirmar con el test). Cerrar el diseño/contenido de cada
skill con el owner antes de escribir (TDD).

## T9 — TecnicoLumat agent (S9, pendiente)

Owner verbatim: *"si que tambien entre. en el mismo odd."* Requiere: un binding rol→agente
(`tecnico` → TecnicoLumat), la declaración del agente (persona/tools/skills/memoria_scope) y una
política KB/memoria para el rol técnico (`kb.retrieve` hoy está denegado a `tecnico`,
`registry.py` `ROLE_TOOL_ALLOWLIST`). Hoy hay un único `assistant` y `actor_role` sólo filtra tools.

## Env del worktree nuevo

- `.venv` sincronizado (`uv sync`) y `media/` creado.
- DB de test aislada: `bash infra/test-db.sh up` (**el puerto deriva del slug**; ej. T5=6266, T6=6116,
  T7=6011; el `env` te lo dice). `infra/.env` copiado desde el worktree primario.
- Frontend: `npm install` en `web/` (el worktree nuevo NO trae `node_modules`).
- **Antes de pytest**: `eval "$(bash infra/test-db.sh env)"`.

## Comandos

- Backend: `uv run --no-sync pytest tests/ -q` (suite completa).
- Frontend: `cd web && npx vitest run --maxWorkers=2` (la suite completa puede crashear por memoria).
- Build: `cd web && npm run build` (tsc -b + vite).
- RDD: `gentle-ai review mode status` (on global). Assess por commit:
  `gentle-ai review assess --cwd <worktree> --agent opencode --base-ref <sha> --committed-only --json`.

## Reglas y gotchas

- Chat en Rioplatense; **artefactos/código/commits/docs en inglés**; sin `Co-Authored-By`.
- ODD: TDD (RED→GREEN) cuando hay test determinista; un work unit = un commit (≤5 archivos);
  actualizar el feature doc + mirror después de cada task.
- **`main` tiene branch protection**: `strict:true` (la rama debe contener el head de `main` antes de
  mergear → sincronizar `origin/main`), checks requeridos **`test` + `panel`**, y **review requerido**.
  El owner mergea sus PRs con `gh pr merge <n> --merge --admin`.
- **Slides encadenados**: T5/T6/T7 se entregaron como PRs apilados (`~t5` ← `~t6` ← `~t7`). Para
  mergear en orden: retargetear la base a `main` (`gh pr edit <n> --base main`), `git merge origin/main`
  en la rama, push, esperar CI, mergear. `rapso worktree cleanup <slug> --remote` limpia worktree +
  ramas (local y remota). Cerrar la DB de test con `bash infra/test-db.sh down` ANTES de borrar el worktree.
- **CI**: `.github/workflows/tests.yml` (pytest + npm ci/build/test). GitGuardian NO es requerido
  (falsos positivos por fixtures `password="..."` en tests).
- `graphify` es un gate obligatorio: si `graphify-out` está stale, `graphify . --update` antes de codear.

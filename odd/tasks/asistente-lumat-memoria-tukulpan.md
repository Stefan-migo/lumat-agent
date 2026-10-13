# ODD: asistente-lumat-memoria-tukulpan

**Branch**: `odd/asistente-lumat-memoria-tukulpan`
**Worktree**: `../lumat-agent-odd-asistente-lumat-memoria-tukulpan`
**Base**: `3475bba7` (= `origin/main` at branch time; el handoff citaba `8a946821`, `origin/main` avanzó con el PR #580 de panel-design-details durante el recon)
**Status**: in progress — slice 1: T1 y T2 hechos; T8a pendiente. Review RDD (lineage `review-8f7d2ae49bc9cb9e`) **approved + acknowledged** (`authority: burned`); 2 findings advisory no bloqueantes registrados abajo.
**Source**: `odd/handoffs/asistente-lumat-memoria-tukulpan.md` (Engram obs 6428) + `.rapsodia-code/sessions/ready-for-odd/2026-10-13-asistente-lumat-memoria-tukulpan/{report.md,session.md}` (Engram obs 6412/6414/6417/6419/6420) + hallazgos verificados 2026-10-13 (Engram obs 6457).

## Objective

Darle al asistente del panel un **comportamiento de memoria Tukulpan** que funcione: (a) cargar **siempre** la skill `memoria-tukulpan`, (b) hacer un **read determinista acotado** al inicio del turno — `pin` → `handoff` → recientes, hilo + `agent:{proyecto}` — entrando **como tool-result**, y (c) que el agente pueda **marcar handoffs** en `memory.write` cuando deja un punto de continuación.

## Problem (verified, not inferred)

El gap no es del subsistema Tukulpan (construido y auditado): es que **nadie le pide usar la memoria**.

- `assemble_context` (`app/services/agent_chat.py:190-259`) carga historial + adjuntos + identidad; **no** lee memoria.
- El único cue de memoria vive en `_context_text` (`nodes.py:199-221`) y aparece **solo tras compactación**.
- El planner sólo llama `memory.*` si el prompt lo empuja; `assistant_plan.md` describe los ejes pero no instruye consultar.
- La skill `memoria-tukulpan` se carga **solo si el planner la declara** (`nodes.py:584-621`); no hay force-load.

## Reconciliation with prior art (CRITICAL — verificado)

### D4 — el pull-only se eligió a propósito

`odd/tasks/remove-panel-memory-push.md` removió el push "todas las filas cada turno" por el blast radius (*"Safe autonomy and full pull are the same decision"*). ⟹ El determinístico **DEBE** ir por el **tool-result slot**, nunca por contexto inyectado.

### MEM-3 — el read determinista NO puede inyectar filas (BLOQUEANTE)

`openspec/specs/memory/spec.md` (MEM-3, normativo):

> Panel context assembly MUST NOT invoke it or automatically load memory rows; memory reads MUST occur through explicit `memory.read` tool calls

Scenario *Explicit search only*: en `assemble_context()` sin `memory.read` → ninguna fila entra al contexto del panel.

⟹ **La única forma que satisface MEM-3 y D4 a la vez**: el **loop emite un `memory.read` iniciado por código** al inicio del turno, y su resultado entra como **tool-result**. El "cuándo" (sólo si hay memoria; digest acotado) queda en **código**. El spec (T8) debe **clarificar** que un `memory.read` iniciado por código cuenta como el "explicit memory.read tool call" de MEM-3.

### Capas — dónde viaja cada instrucción

- El **body** de una skill llega **solo al responder** (`_responder_system_prompt` → `_skill_context`, `nodes.py:600-621`, usado en `:1064`). El responder es **text-only** (`:1042-1047`).
- El **planner** (`plan_llm`, `:446-460`) **no ve bodies**; su user prompt lleva `{{available_skills}}` = solo `{name, description}` (`:453-457`).
- El planner **sí** ve el **schema de argumentos** de cada tool vía `_planner_tool_catalog` (`:314-337`).
- ⟹ El `handoff` de `memory.write` llega al planner **por el schema**; el **"cuándo marcarlo" va en el `description=` del campo**, NO en el body de la skill.
- ⟹ Force-load de la skill toca **solo** el responder. **NO** dar el body al planner: rompe **D8** (*"only declared skills are loaded"*, `assistant_plan.md:11`) y suma tokens por turno sin ganancia.

## Constraints (preservar)

- **D4**: el determinístico va por tool-result, nunca por contexto inyectado.
- **MEM-3**: `assemble_context` NO carga filas; el read ocurre como `memory.read`.
- **Contratos fijados por tests** de la persona (`agent/personas/assistant.md`): identidad `You are the Lumat internal executive operator` (`:1`); línea de aprobación de escritura con `ask for approval before any write operation` (minúscula), `already authorized and runs without asking`, `Every other write still needs approval`, los 4 nombres del allowlist (`:35`); cita de `web.fetch` + `the URL that evidence reports after redirects` **en una sola línea**.
- **D8**: la selección de skills por el planner sigue igual para las demás skills; `memoria-tukulpan` pasa a siempre-on.
- **No** re-litigar el storage Tukulpan (auditado/cerrado, `odd/tasks/tukulpan-memory-closure.md`).

## Plan (tasks) — strict TDD (RED → GREEN → REFACTOR)

Runner: `uv run pytest tests/`.

- [x] **T1 — Schema `Memory.handoff` + migración.**
  `handoff: bool` (Boolean, default `False`) en `app/models.py:521-592`; migración `db/migrations/050_memory_handoff.sql` (convención `<num>_<desc>.sql`; la última es `049`). No crea tabla → `EXPECTED_TABLES` (`tests/integration/test_migrations.py:39`) no cambia.
  Tests: `tests/unit/test_memory_model.py` (columna + default), `tests/integration/test_migrations.py` (migración aplica).
  Route: **delegated** (writer). Trigger: writer trigger (schema + migración son una unidad no trivial).

- [ ] **T2 — Arg `handoff` en `memory.write`.**
  `handoff: bool = Field(default=False, description="...")` en `MemoryWriteArgs` (`registry.py:159-166`); el `description` documenta el **cuándo** (viaja al planner por el schema). Persistir: propagar `handoff` por `tukulpan.upsert` (`app/services/tukulpan.py:323-383`, `_upsert_resolved:223-320`, junto a `pin` en `:266-285`/`:308-318`).
  Tests: `tests/unit/test_memory_tool_axes.py`, `tests/unit/test_assistant_tools.py`.
  Route: delegated (misma unidad que T1).

- [ ] **T3 — `handoff` en el read + orden determinista.**
  Incluir `handoff` en la proyección de `_read_memory` (`registry.py:375-411`) y ordenar `pin` → `handoff` → recientes preservando el interleave de ejes que exige MEM-3; digest ≤ 500 chars (`MEMORY_READ_DIGEST_CONTENT_LIMIT`, `registry.py:37-39`).
  Tests: `tests/unit/test_memory_tool_axes.py`.
  Route: delegated.

- [ ] **T4 — Read determinista al inicio (código → `memory.read` → tool-result).**
  Nuevo nodo/step en el grafo entre `assemble_context` y `plan_llm` (`graph.py:86-89`; hoy `START → assemble_context → panel_cost_gate → plan_llm`) que **emite un `memory.read` iniciado por código** cuando hay memoria (exists check barato) y coloca el resultado en `state["tool_results"]` (init `[]` en `graph.py:109-129`). **No** tocar `assemble_context` (MEM-3).
  Tests: `tests/unit/test_assistant_tool_loop.py`, `tests/unit/test_assistant_harness.py`.
  Route: delegated. **Unidad más riesgosa** — es el corazón del feature.

- [ ] **T5 — Forzar `memoria-tukulpan` siempre-on (responder).**
  Inyectar la skill incondicionalmente en `_skill_context`/`_responder_system_prompt` (`nodes.py:600-621`). Solo responder.
  Tests: `tests/unit/test_assistant_prompt_contract.py`.
  Route: delegated.

- [ ] **T6 — Documentar `handoff` en la skill.**
  `agent/skills/assistant/memoria-tukulpan.md`: agregar `handoff` al shape JSON de `memory.write` + el **cuándo** marcarlo (punto de continuación / orden de tareas e hilos).
  Route: **inline** (un archivo Markdown, ya entendido).

- [ ] **T7 — Persona: cuándo marcar handoff.**
  `agent/personas/assistant.md` sección Memory (`:19-21`): una línea sobre marcar handoff. **Preservar** los contratos fijados por tests.
  Route: inline (una línea, ya entendida).

- [ ] **T8a — Spec MEM-12 (`handoff`).**
  `openspec/specs/memory/spec.md`: **requirement nuevo MEM-12** para el flag `handoff` (escribe, se lee, prioriza) con escenarios Given/When/Then.
  Tests: `tests/spec/test_memory_spec.py`.
  Route: inline (spec redactado desde el mapa ya verificado). Va con **slice 1**.

- [ ] **T8b — Spec MEM-3 (clarificación del read iniciado por código).**
  `openspec/specs/memory/spec.md`: clarificar MEM-3 — un `memory.read` **iniciado por código** al inicio del turno satisface "explicit `memory.read` tool call", y `assemble_context` sigue **sin** cargar filas; agregar escenario para el orden `pin` → `handoff` → recientes con digest acotado.
  Tests: `tests/spec/test_memory_spec.py`.
  Route: inline. Va con **slice 2**.

- [ ] **T9 — Commits atómicos** (Conventional Commits, sin atribución IA).

## Verification

- `uv run pytest tests/` — suite completa (strict TDD).
- Foco: `uv run pytest tests/unit/test_memory_model.py tests/unit/test_memory_tool_axes.py tests/unit/test_tukulpan.py tests/unit/test_assistant_tools.py tests/unit/test_assistant_tool_loop.py tests/unit/test_assistant_prompt_contract.py tests/unit/test_assistant_harness.py tests/spec/test_memory_spec.py tests/integration/test_migrations.py -q`.
- `uv run pytest tests/` completo (integration/functional) con DB (`eval "$(bash infra/test-db.sh env)"`).
- **No** relajar `tests/unit/test_assistant_grounding_gate.py`.
- RDD: `gentle-ai review assess --cwd <wt> --base-ref 3475bba7 --committed-only --json` tras cada commit de work-unit.

## Acceptance criteria (observable)

1. Al inicio de un turno con memoria existente, el agente recibe un **digest acotado** de memoria **vía tool-result** (no inyectado como contexto).
2. La skill `memoria-tukulpan` se carga **siempre** en el responder.
3. `memory.write` acepta `handoff` (visible al planner por el schema) y el agente lo marca al dejar un punto de continuación.
4. El determinístico ordena `pin` → `handoff` → recientes, incluyendo el eje `agent:{proyecto}`.
5. `assemble_context` sigue **sin** cargar filas (MEM-3 intacto) y specs MEM verdes.

## Delivery

- Forecast (authored lines, +y−): T1 ~40, T2 ~50, T3 ~40, T4 ~80, T5 ~20, T6 ~20, T7 ~10, T8 ~60, tests ~200 → **~520 líneas** > 400.
- **Estrategia de entrega** (decidida por el owner 2026-10-13): **chained PRs**, cadena **`stacked-to-main`** (cada PR mergea a `main` en orden).
- **Slices** (cada uno ≤ ~400 líneas; las slices se apilan: la rama de la slice N+1 nace de la slice N y su PR apunta a `main` — se retargetea al mergear la anterior):

| Slice | Tareas | Tema | Forecast |
|-------|--------|------|----------|
| **S1** | T1, T2, T8a + tests | Flag `handoff` end-to-end (schema + write + spec MEM-12) | ~190 |
| **S2** | T3, T4, T8b + tests | Read determinista + orden `pin`→`handoff`→recientes + clarificación MEM-3 | ~250 |
| **S3** | T5, T6, T7 + tests | Skill `memoria-tukulpan` siempre-on + docs + persona | ~120 |

- **RDD**: `gentle-ai review assess --cwd <wt> --base-ref <slice-base> --committed-only --json` tras cada commit de work-unit; el boundary avanza al git-sha revisado.
- **Push / PR / merge**: decisión del owner (el ODD autoriza los commits de work-unit en la rama, no el push/PR).

## Review findings (advisory, non-blocking) — lineage review-8f7d2ae49bc9cb9e

Review RDD aprobada (`approved` + `acknowledged`, authority burned) sobre el candidato `3475bba7..HEAD` (10 archivos, 190 líneas). Ningún finding abrió corrección.

- **R4-001 (resilience, WARNING)** — `app/services/tukulpan.py:317`. Un `upsert` de una memoria existente que **omite** `handoff` resetea el flag a `false`, borrando un marcador de continuación pendiente. *Nota*: espeja la semántica de `pin` (que ya se comporta así), así que puede ser por diseño — **decisión pendiente** (arreglar o documentar como consistente con `pin`).
- **R2-001 (readability, WARNING)** — `odd/tasks/...:47-50`. La cabecera decía "planned" mientras T1 ya figuraba hecho. **Corregido** en este commit (Status ahora refleja el slice en progreso).

## Evidence log

- **T1** — commit `ff88eb1b` `feat(memory): add the Memory.handoff flag with its migration` (`app/models.py`, `db/migrations/050_memory_handoff.sql`, `tests/unit/test_memory_model.py`, `tests/integration/test_migrations.py`).
  - Graph (consultado): nodos `Memory` (`app/models.py:521`), `models.py`, `tukulpan.py`, `memory.py`, `MemoryRelation`; `GRAPH_REPORT.md` (hubs `models.py`/`tukulpan.py`). `graphify path "Memory" "tukulpan.py"` sin path dirigido.
  - `uv run pytest tests/unit/test_memory_model.py -q` → **passed** (2).
  - `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/integration/test_migrations.py -q` → **35 passed**. El writer la reportó `partial` por DB caída; el orquestador levantó la DB (`bash infra/test-db.sh up`) y la corrió → verde. `EXPECTED_TABLES` sin cambios.
  - Ponytail: sin hallazgos.

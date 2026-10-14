# ODD: asistente-lumat-memoria-tukulpan

**Branch**: `odd/asistente-lumat-memoria-tukulpan-s3` (slice 3; slices 1 y 2 merged en `main`)
**Worktree**: `../lumat-agent-odd-asistente-lumat-memoria-tukulpan-s3`
**Base**: `c388fa02` (= `main` al arrancar slice 3)
**Status**: slice 1 **completo** (T1, T2, T8a, + fix R4-001) y **MERGED** en `main` (PR #586, `main` = `0299d8e1`); review RDD `approved + acknowledged` (`authority: burned`). Slice 2 **completo** (T3, T4, T8b) en `odd/asistente-lumat-memoria-tukulpan-s2`: 3 commits (`88f914c9`, `7d089c1d`, `24a1dc0f`), 8 paths / 217 líneas, `uv run pytest tests/` → **1974 passed**. RDD assess post-slice: `medium`, `review_due=false` (`under_budget`) → sin review. Slice 3 **completo** (T5, T6, T7) en `odd/asistente-lumat-memoria-tukulpan-s3` (base `c388fa02`): 2 commits (`ebb08b30`, `d00e8eed`), 5 paths / 101 líneas; suite completa verde (ver Evidence log slice 3). RDD assess acumulado: `medium`, `review_due=false` (`under_budget`) → sin review.
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
  `handoff: bool` (Boolean, default `False`) en `app/models.py:521-592`; migración `db/migrations/052_memory_handoff.sql` (convención `<num>_<desc>.sql`; `main` tomó `050` y luego `051` durante el vuelo → renumerada dos veces desde `050`). No crea tabla → `EXPECTED_TABLES` (`tests/integration/test_migrations.py:39`) no cambia.
  Tests: `tests/unit/test_memory_model.py` (columna + default), `tests/integration/test_migrations.py` (migración aplica).
  Route: **delegated** (writer). Trigger: writer trigger (schema + migración son una unidad no trivial).

- [x] **T2 — Arg `handoff` en `memory.write`.**
  `handoff: bool = Field(default=False, description="...")` en `MemoryWriteArgs` (`registry.py:159-166`); el `description` documenta el **cuándo** (viaja al planner por el schema). Persistir: propagar `handoff` por `tukulpan.upsert` (`app/services/tukulpan.py:323-383`, `_upsert_resolved:223-320`, junto a `pin` en `:266-285`/`:308-318`).
  Tests: `tests/unit/test_memory_tool_axes.py`, `tests/unit/test_assistant_tools.py`.
  Route: delegated (misma unidad que T1).

- [x] **T3 — `handoff` en el read + orden determinista.**
  Incluir `handoff` en la proyección de `_read_memory` (`registry.py:375-411`) y ordenar `pin` → `handoff` → recientes preservando el interleave de ejes que exige MEM-3; digest ≤ 500 chars (`MEMORY_READ_DIGEST_CONTENT_LIMIT`, `registry.py:37-39`).
  Tests: `tests/unit/test_memory_tool_axes.py`.
  Route: delegated.

- [x] **T4 — Read determinista al inicio (código → `memory.read` → tool-result).**
  Nuevo nodo/step en el grafo entre `assemble_context` y `plan_llm` (`graph.py:86-89`; hoy `START → assemble_context → panel_cost_gate → plan_llm`) que **emite un `memory.read` iniciado por código** cuando hay memoria (exists check barato) y coloca el resultado en `state["tool_results"]` (init `[]` en `graph.py:109-129`). **No** tocar `assemble_context` (MEM-3).
  Tests: `tests/unit/test_assistant_tool_loop.py`, `tests/unit/test_assistant_harness.py`.
  Route: delegated. **Unidad más riesgosa** — es el corazón del feature.

- [x] **T5 — Forzar `memoria-tukulpan` siempre-on (responder).**
  Inyectar la skill incondicionalmente en `_skill_context` (`nodes.py:627-643`; solo lo usa `_responder_system_prompt`, `:645`). Constante `ALWAYS_ON_RESPONDER_SKILLS = ("memoria-tukulpan",)`; los nombres declarados se preservan y el always-on se agrega al final, deduplicado. Solo responder; el planner sigue viendo solo `{name, description}` (D8).
  Tests: `tests/unit/test_assistant_planner.py` (4 nuevos, incluye guard D8). El handoff citaba `test_assistant_prompt_contract.py`; ese archivo es de contrato de texto de prompts, el comportamiento vive en `test_assistant_planner.py`.
  Route: **inline** (cambio único entendido: una función + tests; sin unidad paralela ni backstop de contexto → writer trigger no dispara. El plan lo marcaba delegated sin trigger nombrado).

- [x] **T6 — Documentar `handoff` en la skill.**
  `agent/skills/assistant/memoria-tukulpan.md`: `handoff` agregado al shape JSON de `memory.write` + párrafo del **cuándo** (continuation point / orden de tareas e hilos), consistente con el `description` del arg en `registry.py`.
  Tests: `tests/unit/test_assistant_prompt_contract.py::test_memory_skill_documents_the_handoff_marker`.
  Route: **inline**.

- [x] **T7 — Persona: cuándo marcar handoff.**
  `agent/personas/assistant.md` sección Memory: una línea sobre marcar `handoff` en un write que deja un continuation point. Contratos de persona preservados (identidad, línea de aprobación, cita `web.fetch`).
  Tests: `tests/unit/test_assistant_prompt_contract.py::test_persona_tells_when_to_mark_handoff`.
  Route: **inline**.

- [x] **T8a — Spec MEM-12 (`handoff`).**
  `openspec/specs/memory/spec.md`: **requirement nuevo MEM-12** para el flag `handoff` (escribe, se lee, prioriza) con escenarios Given/When/Then.
  Tests: `tests/spec/test_memory_spec.py`.
  Route: inline (spec redactado desde el mapa ya verificado). Va con **slice 1**.

- [x] **T8b — Spec MEM-3 (clarificación del read iniciado por código).**
  `openspec/specs/memory/spec.md`: clarificar MEM-3 — un `memory.read` **iniciado por código** al inicio del turno satisface "explicit `memory.read` tool call", y `assemble_context` sigue **sin** cargar filas; agregar escenario para el orden `pin` → `handoff` → recientes con digest acotado.
  Tests: `tests/spec/test_memory_spec.py`.
  Route: inline. Va con **slice 2**.

- [x] **T9 — Commits atómicos** (Conventional Commits, sin atribución IA). Slice 3: `ebb08b30` (T5), `d00e8eed` (T6+T7).

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
- **Push / PR / merge**: decisión del owner (el ODD autoriza los commits de work-unit en la rama, no el push/PR). **Slice 3: PR #590** (base `main`, label `type:feature`). `origin/main` avanzó a `d650b8f2` tras el branch (`c388fa02`): el pre-merge integration debe integrar el head actual de `main` y re-verificar.

## Review findings (advisory, non-blocking) — lineage review-8f7d2ae49bc9cb9e

Review RDD aprobada (`approved` + `acknowledged`, authority burned) sobre el candidato `3475bba7..HEAD` (10 archivos, 190 líneas). Ningún finding abrió corrección.

- **R4-001 (resilience, WARNING)** — `app/services/tukulpan.py:317`. Un `upsert` de una memoria existente que **omite** `handoff` resetea el flag a `false`, borrando un marcador de continuación pendiente. **ARREGLADO** en slice 1: `upsert(handoff: bool | None = None)` + sólo sobrescribe si viene explícito (`57a67a7c`). `pin` se dejó intacto (scoped al finding).
- **R2-001 (readability, WARNING)** — `odd/tasks/...:47-50`. La cabecera decía "planned" mientras T1 ya figuraba hecho. **Corregido** en este commit (Status ahora refleja el slice en progreso).

## Gatekeeper slice 2 (corrección aplicada por el orquestador)

- **Debilitamiento de assertions en T4** — el writer de T4 cambió dos assertions existentes de `tests/unit/test_assistant_tool_loop.py` de lista exacta (`handler_calls == [...]`) a `.count(...) == 1`, para acomodar el `memory.read` que ahora emite el bootstrap. Eso oculta regresiones. **Restaurado** a listas exactas: sin session → `["customers.search"]`; con session → `["memory.read", "customers.search"]`. Sin debilitar nada.
- **Contrato de aristas del grafo** — `tests/unit/test_cortex_session_loop.py` fijaba `panel_cost_gate → plan_llm`; actualizado al nuevo contrato `panel_cost_gate → memory_bootstrap → plan_llm` (misma fuerza, topología nueva).
- El writer de T4 corrió sólo 2 archivos; estas dos regresiones sólo aparecieron al correr `tests/unit` y `tests/` completos. Ningún finding abrió corrección RDD (assess `under_budget`).

## Evidence log

- **T1** — commit `ff88eb1b` `feat(memory): add the Memory.handoff flag with its migration` (`app/models.py`, `db/migrations/050_memory_handoff.sql` → renumerada dos veces al integrar `main` (#582 tomó `050`, #584 tomó `051`) → `052_memory_handoff.sql`, `tests/unit/test_memory_model.py`, `tests/integration/test_migrations.py`).
  - Graph (consultado): nodos `Memory` (`app/models.py:521`), `models.py`, `tukulpan.py`, `memory.py`, `MemoryRelation`; `GRAPH_REPORT.md` (hubs `models.py`/`tukulpan.py`). `graphify path "Memory" "tukulpan.py"` sin path dirigido.
  - `uv run pytest tests/unit/test_memory_model.py -q` → **passed** (2).
  - `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/integration/test_migrations.py -q` → **35 passed**. El writer la reportó `partial` por DB caída; el orquestador levantó la DB (`bash infra/test-db.sh up`) y la corrió → verde. `EXPECTED_TABLES` sin cambios.
  - Ponytail: sin hallazgos.

- **T2** — commit `534babaa` `feat(assistant): persist handoff from memory.write` (`app/chat/assistant/tools/registry.py`, `app/services/tukulpan.py`, `tests/unit/test_memory_tool_axes.py`, `tests/unit/test_assistant_tools.py`, `tests/unit/test_assistant_delegation.py`).
  - `handoff: bool` con `description` (viaja al planner por el schema). Persistido en insert y update de `_upsert_resolved`.
  - `tests/unit/{test_memory_tool_axes,test_assistant_tools,test_assistant_delegation}.py` → **verde** (spot check del orquestador). El 5º archivo es un **snapshot legítimo** del hash del catálogo del planner (cambió el schema), no un debilitamiento.
- **R4-001 fix** — commit `57a67a7c` `fix(memory): preserve handoff across repeat upserts` (`app/services/tukulpan.py`, `tests/unit/test_tukulpan.py`).
  - `upsert(handoff: bool | None = None)`; update sólo si `handoff is not None`; insert `bool(handoff)`. `tests/unit/test_tukulpan.py` → **verde**.
- **Slice 1 — review RDD** — lineage `review-8f7d2ae49bc9cb9e`: `approved` + `acknowledged` (`authority: burned`). Consent relayado y otorgado por el owner. 0 bloqueantes, 2 advisory (R4-001 arreglado, R2-001 corregido en `13d9e054`).
- **Slice 1 — re-assess post-fix** — `gentle-ai review assess --base-ref 534babaa --committed-only` → `risk: medium`, `changed_lines: 42`, `review_due: false` (`under_budget`).
- **T8a** — commit `035cdf63` `docs(spec): add the MEM-12 handoff marker requirement with its spec scenarios` (`openspec/specs/memory/spec.md`, `tests/spec/test_memory_spec.py`).
  - `uv run pytest tests/spec/test_memory_spec.py -k mem12 -q` → **2 passed**.

## Evidence log — slice 2 (`odd/asistente-lumat-memoria-tukulpan-s2`, base `0299d8e1`)

- **T3** — commit `88f914c9` `feat(memory): expose handoff in own-memory reads and order by pin, handoff, recency` (`app/chat/assistant/tools/registry.py`, `tests/unit/test_memory_tool_axes.py`).
  - Graph (consultado): `_read_memory()`, `registry.py`, `Memory`, `list_for_entity()`; `GRAPH_REPORT.md` hubs `registry.py`/`tukulpan.py`.
  - Orden estable **por eje** (`pin` → `handoff` → `updated_at.desc()`) antes del interleave (`zip_longest`) y del límite; `handoff` agregado a la proyección de scope `own`; digest de 500 chars intacto.
  - `uv run pytest tests/unit/test_memory_tool_axes.py tests/unit/test_assistant_tools.py -q` → **121 passed**.

- **T4** — commit `7d089c1d` `feat(assistant): emit a code-initiated memory.read as prior tool evidence` (`app/chat/assistant/graph.py`, `app/chat/assistant/nodes.py`, `tests/unit/test_assistant_tool_loop.py`, `tests/unit/test_cortex_session_loop.py`).
  - Nodo `memory_bootstrap` entre `panel_cost_gate` y `plan_llm`: corre **una vez** por turno, **no** corre con costo bloqueado (`evidence`) ni al re-entrar por `tool_loop_head`. Reusa `execute_tool("memory.read", {"scope": "own", "limit": 3})` y **sólo** agrega el entry a `tool_results` si hay filas; fail-safe ante `ToolValidationError`/`ToolExecutionError`/session o thread ausentes. **No** toca `assemble_context`, **no** incrementa `tool_steps`, **no** setea `tool_result` singular, **no** inyecta contexto. El planner lo ve vía `_render_tool_evidence` → `_planner_context_text` (marcado `code_initiated: true`).
  - `uv run pytest tests/unit/test_assistant_tool_loop.py tests/unit/test_assistant_harness.py -q` → **43 passed** (reporte del writer); corregido por el orquestador (ver Gatekeeper) → `uv run pytest tests/unit -q` **verde**.

- **T8b** — commit `24a1dc0f` `docs(spec): clarify the code-initiated own read and its pin-handoff-recency order` (`openspec/specs/memory/spec.md`, `tests/spec/test_memory_spec.py`).
  - MEM-3: un `memory.read` iniciado por el runtime al inicio del turno (entregado como tool-result, nunca inyectado) **satisface** el "explicit `memory.read` tool call"; `assemble_context` sigue sin cargar filas. Se agrega el orden por eje `pin` → `handoff` → recientes y 3 escenarios (code-initiated startup read, no-memory-no-read, own read order + bounded digest).
  - `uv run pytest tests/spec/test_memory_spec.py -q` → **36 passed**, incluye `test_mem3_own_read_orders_each_axis_by_pin_handoff_then_recency`.

- **Slice 2 — verificación de registro** — `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/ -p no:cacheprovider` → **1974 passed**, 2 warnings, EXIT=0.
  - Gotcha: la DB de test (tmpfs) arranca virgen; el rol `app` lo crea `db/migrate.sh` vía el fixture `migrated_db`. La primera corrida falló con `password authentication failed for user "app"` por una carrera de arranque del contenedor, no por el cambio.
- **Slice 2 — RDD** — `gentle-ai review assess --base-ref 0299d8e1 --committed-only` → `risk: medium`, `changed_paths: 8`, `changed_lines: 217`, `review_due: false` (`under_budget`). Sin review.

## Evidence log — slice 3 (`odd/asistente-lumat-memoria-tukulpan-s3`, base `c388fa02`)

- **T5** — commit `ebb08b30` `feat(assistant): always load the memoria-tukulpan skill for the responder` (`app/chat/assistant/nodes.py`, `tests/unit/test_assistant_planner.py`).
  - Graph (consultado): `guardrails()`, `_skill_context`/`_responder_system_prompt`, `global_skill_index`, `load_skill_body`, `plan_llm`; comunidades `guardrails`/`nodes.py`.
  - RED observado: `test_skill_context_injects_always_on_memory_skill_without_declared_skills` y `..._alongside_declared` fallan (2) con el código previo. GREEN: `tests/unit/test_assistant_planner.py` verde.
  - El test `test_skill_context_is_empty_without_validated_skills` cambió de contrato (ya no es vacío sin declaradas: ahora inyecta el always-on); reemplazado por 4 tests que preservan/refuerzan la intención, incluido el guard D8 (el planner nunca recibe el body).
  - `ALWAYS_ON_RESPONDER_SKILLS` se agrega a los declarados, deduplicado; si la skill no está en el index efectivo se omite (respeta override/borrado).

- **T6 + T7** — commit `d00e8eed` `docs(assistant): document the handoff marker in the memory skill and persona` (`agent/skills/assistant/memoria-tukulpan.md`, `agent/personas/assistant.md`, `tests/unit/test_assistant_prompt_contract.py`).
  - RED observado en ambos tests de contrato antes de documentar; GREEN tras editar skill y persona. Contratos de persona intactos (tests existentes verdes).

- **Slice 3 — suite completa** — `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/` → **1978 passed**, 1 failed.
  - El único fallo: `tests/integration/test_time_triggers.py::test_worker_processes_daily_summary_for_admin` (`assert run_cycle() == 1` → `0`). **No-causal**: el archivo del test y `app/ops/` están byte-idénticos al baseline `c388fa02`; el diff de slice 3 solo toca `nodes.py` + tests. Reproducción: pasa 4/4 en aislamiento y `tests/integration` completo (780 passed) → flake de **borde de minuto** (`run_cycle()` usa su propio `datetime.now()`; si el minuto cambia entre el `now` del test y el del worker, el trigger no queda `due`). Advisory pre-existente, no blocker de slice 3.
  - Gotcha heredado confirmado: los tests de `tests/unit` que tocan DB fallan si se corre `tests/unit` solo (el rol `app` lo crea `migrated_db` al correr integration primero); correr la suite completa en un proceso.

- **Slice 3 — RDD** — `gentle-ai review assess --base-ref c388fa02 --committed-only` (acumulado, 2 commits) → `risk: medium`, `changed_paths: 5`, `changed_lines: 101`, `review_due: false` (`under_budget`). Sin review.

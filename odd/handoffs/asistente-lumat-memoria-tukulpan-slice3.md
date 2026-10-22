# HANDOFF — Asistente Lumat: memoria Tukulpan — **slice 3** (skill siempre-on + docs)

**Fecha**: 2026-10-13 (post-merge de slice 2). **Estado**: slices 1 y 2 **MERGED**; slice 3 pendiente, nada implementado.

## Contexto (leer primero)

- **Slice 1 merged**: PR **#586**, `handoff` end-to-end (schema + write + spec MEM-12). Commit de merge `0299d8e1`.
- **Slice 2 merged**: PR **#587**, read determinista end-to-end (`memory_bootstrap` + orden `pin`→`handoff`→recientes + spec MEM-3). Commit de merge **`c388fa02`** (`main` = `c388fa02`).
- **Task doc (en `main`)**: `odd/tasks/asistente-lumat-memoria-tukulpan.md` — plan completo, constraints, slices, evidence log de 1 y 2, y la sección "Gatekeeper slice 2". **Leerlo antes de arrancar.**
- **Graphify**: `main` = `c388fa02`; el grafo se refrescó sobre `0299d8e1` (slice 2 lo consultó). Correr `graphify query` sobre el área antes de tocar código; refrescar (`graphify . --update`) una vez al cerrar la sesión.
- **Engram**: topic `odd/asistente-lumat-memoria-tukulpan` (obs 6521) y `odd/asistente-lumat-memoria-tukulpan/pr-587` (obs 6526); handoff previo obs 6428.

## Qué ya está hecho (slices 1 y 2, en `main`)

| ID | Qué | Estado |
|----|-----|--------|
| T1 | `Memory.handoff` + migración `db/migrations/052_memory_handoff.sql` | ✅ en main |
| T2 | `handoff` en `MemoryWriteArgs` (con `description` que viaja al planner por el schema) + persistencia en `tukulpan.upsert` | ✅ en main |
| T8a | Spec `MEM-12` (marcador handoff) + scenarios | ✅ en main |
| R4-001 | `upsert(handoff: bool \| None = None)` preserva el marcador | ✅ en main |
| T3 | `handoff` en la proyección de `_read_memory` + orden por eje `pin`→`handoff`→recientes | ✅ en main |
| T4 | Nodo `memory_bootstrap` (`panel_cost_gate` → `memory_bootstrap` → `plan_llm`) que emite un `memory.read` iniciado por código y lo entrega por `tool_results` | ✅ en main |
| T8b | Spec MEM-3 clarificado (read iniciado por código satisface MEM-3) + escenarios | ✅ en main |

## Qué falta: slice 3 (~120 líneas)

- **T5 — Forzar `memoria-tukulpan` siempre-on (responder).**
  Inyectar la skill **incondicionalmente** en `_skill_context` / `_responder_system_prompt` (`app/chat/assistant/nodes.py:600-621`, usado en `:1064`). **Solo el responder.**
  Tests: `tests/unit/test_assistant_prompt_contract.py`.
  Route: **delegated** (writer).

- **T6 — Documentar `handoff` en la skill.**
  `agent/skills/assistant/memoria-tukulpan.md`: agregar `handoff` al shape JSON de `memory.write` + el **cuándo** marcarlo (punto de continuación / orden de tareas e hilos).
  Route: **inline** (un archivo Markdown, ya entendido).

- **T7 — Persona: cuándo marcar handoff.**
  `agent/personas/assistant.md`, sección Memory (`:19-21`): una línea sobre marcar handoff. **Preservar** los contratos fijados por tests.
  Route: inline (una línea, ya entendida).

- **T9 — Commits atómicos** (Conventional Commits, sin atribución IA).

## Restricciones que NO se pueden violar

- **D8 (normativo)**: la selección de skills por el planner sigue igual para las demás skills; `memoria-tukulpan` pasa a siempre-on **solo en el responder**. `assistant_plan.md:11` dice *"only declared skills are loaded"*. **NO** le des el body de la skill al planner.
- **Capas**: el **body** de una skill llega **solo al responder** (`nodes.py:600-621`, usado en `:1064`); el **planner** solo ve `{name, description}` del index (`:453-457`). No metas reglas en el body esperando que el planner las lea.
- **Persona — contratos fijados por tests** (`agent/personas/assistant.md`): identidad `You are the Lumat internal executive operator` (`:1`); línea de aprobación de escritura con `ask for approval before any write operation` (minúscula), `already authorized and runs without asking`, `Every other write still needs approval`, los 4 nombres del allowlist (`:35`); cita de `web.fetch` + `the URL that evidence reports after redirects` **en una sola línea**. **No tocar** salvo agregar la línea nueva.
- **No** re-litigar el storage Tukulpan (auditado/cerrado, `odd/tasks/tukulpan-memory-closure.md`).

## Cómo (ODD, stacked-to-main)

1. Worktree desde `main` (**`c388fa02`**): `rapso worktree create asistente-lumat-memoria-tukulpan-s3` → rama `odd/asistente-lumat-memoria-tukulpan-s3`.
2. Copiar `infra/.env` al worktree (`cp ../lumat-agent/infra/.env infra/.env`) — **nunca sourcearlo**, envenena `DATABASE_URL`.
3. Implementar con **Graph Check** + **strict TDD** (`uv run pytest tests/`) + commits atómicos.
4. `git fetch origin main` justo antes de mergear; si `main` avanzó, integrar y re-verificar.

## Gotchas verificados (heredar)

1. **Gatekeeper — correr SIEMPRE la suite completa** (`uv run pytest tests/`), no solo los archivos que toca el writer. En slice 2 el writer debilitó dos assertions existentes (lista exacta → `.count()`) y rompió el contrato de aristas del grafo en `test_cortex_session_loop.py`; ambas se detectaron recién con `tests/unit` y `tests/` completos. **Nunca cerrar con el parcial del writer.**
2. **RDD / review**: la sesión de opencode debe correr **DENTRO del worktree**, o el transporte de reviewers falla (`opencode_review_transport_binding_invalid`). `gentle-ai review status` sin `--cwd` debe correr con process cwd = worktree.
3. **DB de test — carrera de arranque**: el contenedor `db-test` es efímero (tmpfs). El rol `app` lo crea `db/migrate.sh` vía el fixture `migrated_db`. Si la primera corrida falla con `password authentication failed for user "app"`, es carrera, no el cambio: re-correr. `bash infra/test-db.sh up` / `down`; siempre `eval "$(bash infra/test-db.sh env)"`.
4. **Migraciones — carrera de números**: `052` ya está tomado. Slice 3 **no** debería necesitar migración; si aparece una, verificar el próximo libre justo antes de crearla.
5. **Hash del catálogo del planner** en `tests/unit/test_assistant_delegation.py`: si cambia el schema de tools, recomputar el SHA (es snapshot legítimo, no debilitar). Slice 3 **no** debería tocar el schema de tools → no debería cambiar.
6. **`web/node_modules` no existe en worktree nuevo**: `cd web && npm ci` antes de correr el frontend. El build (`npm run build`, único type-check real vía `tsc -b`) y `npm test` solo hacen falta en el **pre-merge integration**.
7. **Pre-merge integration (AGENTS.md)**: antes de mergear, integrar el head de `main` y correr sobre el árbol mergeado: `uv run pytest tests/` + `cd web && npm test` + `cd web && npm run build`. **Report-only, fail-closed**: el merge lo decide el owner.
8. **GitGuardian**: en slice 2 quedó **verde**. (En slice 1 era rojo por falso positivo pre-existente; ya no aplica.) Los checks que importan: `test` y `panel`.
9. **Convención de PR del repo**: no hay `.github/PULL_REQUEST_TEMPLATE.md` ni enforcement de issues/type-labels. Estilo = Summary + tabla de cambios + test plan + Notes + label `type:feature` (como #586/#587). Branches `odd/*`.
10. **Evidencia slice 2 (referencia)**: backend `1974 passed`; frontend `1174 passed`; `npm run build` EXIT=0; RDD `medium`, 217 líneas, `under_budget`.

## Criterio de aceptación de slice 3

1. La skill `memoria-tukulpan` se carga **siempre** en el responder (aunque el planner no la declare).
2. El planner **sigue** viendo solo `{name, description}` (D8 intacto) — no recibe el body.
3. `agent/skills/assistant/memoria-tukulpan.md` documenta `handoff` (shape + cuándo).
4. La persona menciona cuándo marcar handoff, **sin** romper los contratos fijados por tests.
5. `tests/unit/test_assistant_prompt_contract.py` verde y suite completa (`uv run pytest tests/`) verde.
6. RDD assess sobre `--base-ref c388fa02 --committed-only` tras cada commit de work-unit; boundary avanza al sha revisado.

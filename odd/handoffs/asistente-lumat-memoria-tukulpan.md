# HANDOFF — Asistente Lumat: memoria Tukulpan — **slice 2** (read determinista)

**Fecha**: 2026-10-13 (post-merge de slice 1). **Estado**: slice 1 **MERGED**; slice 2 pendiente, nada implementado.

## Contexto (leer primero)

- **Slice 1 (flag `handoff`) ya está en `main`**: PR **#586**, merge commit **`0299d8e1`** (`main` = `0299d8e1`).
- **Task doc (en `main`)**: `odd/tasks/asistente-lumat-memoria-tukulpan.md` — tiene el plan completo, constraints, slices y evidence log. **Leerlo antes de arrancar.**
- **Fuente original**: `odd/handoffs/` anteriores + Engram (obs 6428 handoff, 6457/6473/6486/6493/6504).
- **Graphify**: `main` está en `0299d8e1` y el grafo fue refrescado sobre ese estado (`graphify-out/graph.json` + `GRAPH_REPORT.md`, 9533 nodos). Correr `graphify query` sobre el área antes de tocar código.

## Qué ya está hecho (slice 1)

| ID | Qué | Estado |
|----|-----|--------|
| T1 | `Memory.handoff` + migración (`db/migrations/052_memory_handoff.sql`) | ✅ en main |
| T2 | `handoff` en `MemoryWriteArgs` (con `description` que viaja al planner por el schema) + persistencia en `tukulpan.upsert` | ✅ en main |
| T8a | Spec `MEM-12` (marcador handoff) + scenarios | ✅ en main |
| R4-001 | `upsert(handoff: bool \| None = None)` — el marcador **sobrevive** re-escrituras que lo omiten | ✅ en main |

## Qué falta: slice 2

- **T3** — `handoff` en la proyección de `_read_memory` (`app/chat/assistant/tools/registry.py:375-411`) + orden **`pin` → `handoff` → recientes**, preservando el interleave de ejes que exige MEM-3; digest ≤ 500 chars (`MEMORY_READ_DIGEST_CONTENT_LIMIT`).
- **T4** — ⚠️ **el más riesgoso**: el **read determinista iniciado por código**. Un nodo/steps en el grafo entre `assemble_context` y `plan_llm` (`app/chat/assistant/graph.py:86-89`) que emite un **`memory.read` iniciado por código** cuando hay memoria y pone el resultado en `state["tool_results"]` (init `[]` en `graph.py:109-129`). **NO tocar `assemble_context`.**
- **T8b** — clarificar `MEM-3` en `openspec/specs/memory/spec.md`: un `memory.read` iniciado por código al inicio del turno **satisface** "explicit `memory.read` tool call"; `assemble_context` sigue sin cargar filas; escenario del orden nuevo.

Después: **slice 3** (T5 skill `memoria-tukulpan` siempre-on en el responder, T6 doc de la skill, T7 línea en la persona).

## Restricciones que NO se pueden violar

- **MEM-3 (normativo)**: *"Panel context assembly MUST NOT invoke it or automatically load memory rows; memory reads MUST occur through explicit `memory.read` tool calls"*. ⟹ el determinístico **jamás** inyecta filas en `assemble_context`; va **como tool-result**.
- **D4**: el determinístico va por tool-result, nunca por contexto inyectado.
- **Capas**: el **body** de una skill llega **solo al responder** (`nodes.py:600-621`, usado en `:1064`); el **planner** solo ve `{name, description}` del index (`:453-457`) pero **sí** ve el **schema de argumentos** (`_planner_tool_catalog`, `:314-337`). No metas reglas en el body de la skill esperando que el planner las lea.
- **D8**: no le des el body de la skill al planner.

## Cómo (ODD, stacked-to-main)

1. Worktree desde `main` (`0299d8e1`): `rapso worktree create asistente-lumat-memoria-tukulpan-s2` → rama `odd/asistente-lumat-memoria-tukulpan-s2`.
2. Copiar `infra/.env` al worktree (`cp ../lumat-agent/infra/.env infra/.env`) — **nunca sourcearlo**, envenena `DATABASE_URL`.
3. Implementar con **Graph Check** + **strict TDD** (`uv run pytest tests/`) + commits atómicos.

## Gotchas verificados (heredar)

1. **RDD / review (CRÍTICO)** — el transporte de reviewers de opencode falla si la sesión **no** corre en el worktree: `opencode_review_transport_binding_invalid: Task repository context does not match the repository`. La review #1 de slice 1 funcionó; la #2 falló por esto. **Corré la sesión DENTRO del worktree.**
2. `gentle-ai review status` sin `--cwd` **debe** correr con process cwd = worktree, o falla con *"lineage held by a different worktree"*.
3. **Migraciones — carrera de números**: `main` tomó `050` y `051` mientras slice 1 volaba (tu migración terminó siendo `052`). **Verificá el próximo número libre** justo antes de crear cualquier migración.
4. **DB de test persistente**: si renombrás una migración ya aplicada, `migrate.sh` la re-aplica → `psycopg.errors.DuplicateColumn`. Fix: `bash infra/test-db.sh down && bash infra/test-db.sh up`.
5. **Merge semántico**: `tests/unit/test_assistant_delegation.py` fija el **SHA-256 del catálogo del planner**. Si cambia el schema de tools (o integrás `main` con un tool nuevo), el hash queda inválido → recomputarlo. Un merge textual limpio **no** garantiza que el hash sirva.
6. **Integración pre-merge (AGENTS.md)**: antes de mergear, integrar el head de `main`, y correr **backend** (`uv run pytest tests/`) + **frontend** (`cd web && npm test`) + **`cd web && npm run build`** (es el único type-check del repo) sobre el árbol mergeado. Vitest verde **no** prueba que type-checkee.
7. **GitGuardian** es rojo por un **falso positivo pre-existente en `main`** (`tests/functional/test_api_kb_settings.py`, `password="op-pass"`, de #582). No es tuyo; los checks `test` y `panel` son los que importan.
8. `vitest` no está en el worktree nuevo: `cd web && npm ci` antes de correr el frontend.

## Criterio de aceptación de slice 2

1. Al inicio de un turno con memoria existente, el agente recibe un **digest acotado** vía **tool-result** (no inyectado).
2. `assemble_context` sigue **sin** cargar filas (MEM-3 intacto).
3. El determinístico ordena `pin` → `handoff` → recientes, incluyendo el eje `agent:{proyecto}`.
4. Specs MEM y suites verdes (strict TDD: `uv run pytest tests/`).

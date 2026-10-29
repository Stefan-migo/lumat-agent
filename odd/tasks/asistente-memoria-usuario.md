# ODD: asistente-memoria-usuario

**Branch**: `odd/asistente-memoria-usuario` · **Worktree**: `../lumat-agent-odd-asistente-memoria-usuario` · **Base**: `24b60d77` (= `main` al arrancar, 2026-10-29)
**Status**: planning — frente 2 de 2. El frente 1 (`asistente-memoria-captura`, MEM-13) está mergeado en `main` (#736, #737).
**Constraints**: el eje `user` es **cross-project por construcción** (`proyecto='default'`, sin filtro de proyecto en la lectura); el aislamiento es por **usuario autenticado** (`state["user_id"]`), **nunca** por `authorization.owner_id` (dueño del proyecto); el modelo nunca manda `owner_id` ni `entity_id` (lo deriva el server); el proyecto General (`agent:default`) **no se toca** y sigue siendo memoria de equipo; MEM-3 sigue intacto (la lectura es por tool, no inyección); MEM-9/MEM-1 (dedup por hash, juicio de relaciones) aplican sin reimplementar.

## Specs

**S1 — El asistente sabe del usuario.** La memoria tiene que dar esa sensación, no solo recordar datos de negocio.
> "tien que dar la sensacion de que el asistente lumat sabe del usuario."

**S2 — Acceso a través de todos los proyectos.** Un hecho sobre la persona se puede obtener desde cualquier proyecto.
> "y puede obtener informacion a traves de todos los proeyectos es posible?"

**S3 — Filtrado estricto por usuario.** Ninguna información de un usuario puede aparecer para otro.
> "pero esta informacion si tiene que estar filtrada solo para el usuario. no se pueden filtrar informacion entre usuarios."

**S4 — Auditoría.** El usuario puede ver y borrar lo que el asistente recuerda de él.
> Decisión del owner (2026-10-29): "Sí, lista y borrar en el workspace".

**S5 — General queda como memoria de equipo.** No se migran las filas existentes con `owner_id NULL`.
> Decisión del owner (2026-10-29): "General queda como memoria de equipo, sin cambios".

## Tasks

- [x] **T1 — Migración 059 + CHECK extendido.** `db/migrations/059_memory_user_scope.sql`: `CHECK ((visibility = 'global') = (scope IN ('agent','user')))`. `EXPECTED_TABLES` sin cambios. Tests: `tests/integration/test_migrations.py` (acepta user/global, acepta customer/thread, rechaza panel/global). Route: delegated. Commit: `703e9ca5`.
- [x] **T2 — Seam de servicio del eje user.** `tukulpan.user_memory_entity(owner_id)` → `f"user:{owner_id}"`; `visibility_target(visibility, *, thread_id, proyecto, owner_id=None)` con owner positivo obligatorio para el eje user. Tests: `tests/unit/test_tukulpan.py`. Route: delegated. Commit: `703e9ca5`.
- [x] **T3 — Tools.** `MemoryWriteArgs.visibility` suma `"user"`; `_write_memory` persiste `scope='user'` + `visibility='global'` + `proyecto='default'` + `owner_id` autenticado; `_read_memory`/`_search_memory` suman el eje user a `own` con `USER_AXIS_LIMIT = 2`. Tests: `tests/unit/test_memory_tool_axes.py`, `tests/unit/test_assistant_tools.py`. Route: delegated; corregido por el orquestador (ranking MEM-3). Commit: `452b446a`.
- [x] **T4 — Aislamiento entre usuarios.** `tests/integration/test_memory_user_axis.py`: memoria de A invisible para B, legible desde General y desde cualquier proyecto de A, y escritura sin usuario autenticado rechazada antes de persistir. Route: delegated. Commit: `452b446a`.
- [x] **T5 — Spec MEM-14 + protocolo.** `openspec/specs/memory/spec.md` + persona + skill. Tests: `tests/spec/test_memory_spec.py`, `tests/unit/test_assistant_prompt_contract.py` (50). Route: delegated; corregido por el orquestador (inversión `visibility`/`scope` + slicing). Commit: `23dce47a`.
- [ ] **T6 — API + UI de auditoría.** `GET`/`DELETE` de las **propias** memorias user (nunca de otro usuario, ni por id ajeno), y en el workspace del asistente la lista con borrar, siguiendo el patrón de `ClientMemories`. Tests: `tests/unit/test_panel_memory_routes.py`, `web/src/components/...`. Route: delegated. Commit: —
- [ ] **T7 — Verificación y commits.** Slice 1: `quick` verde y `full` en el corte (`452b446a`, 444 líneas). Slice 2: `full` + `npm run build` + `npm test` al cerrar. Route: inline. Commit: —

## Delivery

| Slice | Tareas | Tema | PR |
|---|---|---|---|
| **S1** | T1, T2, T3, T4, T5 | Backend completo del eje: migración, servicio, tools, aislamiento, spec | PR 1 (`main`) |
| **S2** | T6, T7 | API + UI de auditoría | PR 2 apilado sobre S1 |

Push, PR y merge son decisión del owner.

## Log

**L1** (2026-10-29, pedido original verbatim):
> la segunda es el scope de memoria del usuario. tien que dar la sensacion de que el asistente lumat sabe del usuario. y puede obtener informacion a traves de todos los proeyectos es posible? pero esta informacion si tiene que estar filtrada solo para el usuario. no se pueden filtrar informacion entre usuarios.

**L2 — Decisiones del owner** (2026-10-29): "Eje user nuevo, atado al autenticado"; "Sí, lista y borrar en el workspace"; "General queda como memoria de equipo, sin cambios"; "si vamos con frente 2" (consentimiento del worktree).

**L3 — Evidencia de código (estado al arrancar).**
- `db/migrations/030_memory_visibility_global.sql:21-23` fija `CHECK ((visibility = 'global') = (scope = 'agent'))`: un scope nuevo con visibilidad global es imposible sin migración.
- `app/chat/assistant/tools/registry.py` `_read_memory` (línea ~447) usa `memory_owner = authorization.owner_id` para proyectos con nombre y `None` para `default`; `_write_memory` (~542) persiste con `owner_id=None` en `default`. Por eso hoy admin y operador comparten la memoria general: el eje nuevo debe usar `state["user_id"]`, no el dueño del proyecto.
- `Memory` (`app/models.py`) ya tiene `owner_id`, `proyecto`, `scope`, `entity_id`, `topic_key` y la unique con `nulls not distinct`: **no hace falta columna nueva**, solo migrar el CHECK.
- `projects.agent_context()` filtra por `Project.owner_id`, así que hoy un proyecto pertenece a un solo dueño y `authorization.owner_id == user_id` en la práctica. El eje user **no se apoya** en esa coincidencia: la exige explícitamente.
- `memory_bootstrap` (`app/chat/assistant/nodes.py:472`) emite `memory.read` con `scope="own", limit=3`: el eje user entra por dentro de `own`, no por un nodo nuevo.

**L4 — Corte de slice 1.** T1-T5 cerradas en `452b446a` (444 líneas, 3 commits: `703e9ca5` migración+seam, `23dce47a` spec+protocolo, `452b446a` tools+aislamiento). `quick` verde. La slice 2 (T6/T7: API + UI de auditoría) va en su PR apilado.

**L5 — Defectos detectados por el orquestador en las entregas delegadas.**
1. **La migración rompía el eje `customer`.** La primera versión escribió `(visibility='thread' AND scope='panel') OR (visibility='global' AND scope IN ('agent','user'))`, que rechaza la memoria del bot de WhatsApp (`scope='customer'` + `visibility='thread'`): un `CheckViolation` en MEM-4/MEM-5. La forma correcta conserva el bicondicional original: `(visibility='global') = (scope IN ('agent','user'))`. Se agregó un test de regresión que fija que una fila customer/thread siga insertándose.
2. **El spec afirmaba una imposibilidad.** MEM-14 decía `visibility='user'` con `scope='global'`: el enum `memory_visibility` no tiene valor `user` y `global` no es un scope. Corregido a `scope='user'` con `visibility='global'`, y el test de spec que fijaba el error también.
3. **Slicing frágil del spec.** Los tests cortaban el documento y afirmaban `"### Requirement:" not in memXX`, lo que fijaba «este requirement es el último». Al agregar MEM-14, el test de MEM-13 del frente 1 falló. Ambos cortan ahora en el siguiente `### Requirement:` y afirman solo sobre su propia sección.
4. **`memory.search` rompía el ranking de MEM-3.** Interleavear por eje cuando existe el eje user altera el orden por score fusado que el spec exige. Corregido: unión de los tres ejes con el eje user acotado a `USER_AXIS_LIMIT` antes del `sort` por score.

**L6 — Limitación conocida (para T6).** `memory.update`/`memory.delete` siguen rechazando ids del eje user porque `_owned_agent_memory_or_raise` solo reconoce los ejes `panel` y `agent`. El agente corrige reescribiendo con el mismo `topic_key` (upsert). Ampliarlo toca la garantía de aislamiento, así que se dejó fuera de esta slice a propósito.

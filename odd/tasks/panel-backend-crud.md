# panel-backend-crud — CRUD de backend del panel (KB, usuarios, casos archivados)

Estado: en curso. Rama `odd/panel-backend-crud`, base `origin/main 3475bba7`.
Worktree: `/home/stefan/repos/lumat-agent-odd-panel-backend-crud`.
Origen: handoff `odd/handoffs/panel-backend-crud.md` (slices diferidos del PR #580).

## Objetivo
Cerrar los 3 CRUD de backend diferidos a propósito del slice frontend `panel-design-details`:
borrado real de documentos KB, borrado real de usuarios y archivado de casos cerrados. Un work
unit atómico por cambio, con verificación y commit Conventional sin atribución.

## Por qué
Son mutaciones destructivas sobre API + DB con FKs y riesgo de pérdida de datos en producción;
mezclarlas con pulido cosmético degradaba la review.

## Alcance
- Backend: `db/migrations/**`, `app/services/kb.py`, `app/panel/api/routes/kb.py`,
  `app/services/users.py`, `app/panel/api/routes/users.py`, `app/services/cases.py`,
  `app/panel/api/routes/cases.py`, `app/models.py`.
- Frontend: `web/src/api.ts`, `web/src/components/pages/KbDocumentDetail.tsx`,
  `web/src/components/pages/UserManagement.tsx`, `web/src/components/pages/ClientFicha.tsx` + tests.

## Restricciones
- El backend corre DESDE el worktree; un solo stack `infra` a la vez.
- **TDD estricto activo** (`openspec/config.yaml`: `testing.strict_tdd=true`). RED → GREEN → REFACTOR.
  Runner backend: `uv run pytest tests/`. Runner frontend: `cd web && npm test` (vitest run).
  Build/typecheck (incluye `tsc -b`): `cd web && npm run build`.
- Commit Conventional, **sin atribución de IA**.
- Integrar `origin/main` antes del PR; PR con CI verde (jobs `test` + `panel`).

## Decisiones cerradas
- **KB delete (opción A)**: el delete aplica a cualquier documento que el admin ya ve (todo el
  corpus — así lo sirve `GET /panel/api/kb`). Accountabilidad por confirmación explícita en UI +
  audit `kb.document_delete`. (Owner, 2026-10-13.)
- **Usuarios delete (opción A)**: delete real admin-only. Guardias: auto-borrado → 403; último
  admin activo → 409; usuario referenciado por FKs → 409 ("desactivá en su lugar"), vía violación
  de FK de Postgres (sin enumerar las 15 tablas, sin cascada silenciosa). Audit `user.delete`.
  (Owner, 2026-10-13.)

- **Casos archivar (opción A)**: soft-archive (columna `cases.archived_at`), restringido a casos
  **cerrados**, oculto por defecto de la ficha, con toggle **"Ver archivados"** y acción
  **desarchivar** (reversible). Audit `case.archived` / `case.unarchived`. (Owner, 2026-10-13.)

## Fuera de alcance / ítems separados
- **Múltiples casos abiertos por cliente**: NO forma parte de WU3 (el archive solo toca casos
  cerrados). Queda como ítem aparte a decidir.
- **Reabrir un caso archivado**: no se maneja en WU3 (queda archivado + abierto). Follow-up.

## Tareas (IDs estables)

### Work unit 1 — KB hard delete
- [x] **KB-1 — Migración cascade.** Nueva `db/migrations/050_kb_chunks_cascade.sql`: reemplazar la FK
  `kb_chunks_document_id_fkey` (hoy NO ACTION) por `ON DELETE CASCADE`, siguiendo el patrón de
  `047_appointment_calendar_sync_cascade.sql`. Rollback documentado en el archivo.
- [x] **KB-2 — Service.** `app/services/kb.py`: nueva `delete_document(session, doc_id, actor="system")`
  con audit `kb.document_delete` (before con title/version/active_version) + `session.delete(doc)`.
  Espejar el estilo de `disable_document` (ValueError si falta).
- [x] **KB-3 — Route.** `app/panel/api/routes/kb.py`: `DELETE /kb/{doc_id}` admin-only
  (`require_admin_json`), `_doc_or_404` primero. **Serializar el doc ANTES del commit** para evitar
  `ObjectDeletedError` (el row ya no existe tras el commit).
- [x] **KB-4 — Frontend API.** `web/src/api.ts`: `deleteKbDocument(id)` con `apiFetch(..., { method: 'DELETE' })`.
- [x] **KB-5 — UI.** `web/src/components/pages/KbDocumentDetail.tsx`: acción de borrado con
  confirmación fuerte inline (nombra el documento + "permanente"), reusando el patrón de
  disable/restore; al confirmar, navegar de vuelta a la lista.
- [x] **KB-6 — Tests.** `tests/integration/test_kb.py` (service: doc + chunks borrados),
  `tests/functional/test_api_kb_settings.py` (admin-only, 404, audit `kb.document_delete`, cascade de
  chunks), `web/src/components/pages/KbDocumentDetail.test.tsx`, `web/src/api.test.ts`.

### Work unit 2 — Usuarios delete
- [x] **USR-1 — Servicio.** `app/services/users.py`: `delete_user(session, user)` (`session.delete`) +
  helper `active_admin_count(session) -> int` (guardia de último admin activo).
- [x] **USR-2 — Route.** `app/panel/api/routes/users.py`: `DELETE /users/{user_id}` admin-only.
  `_get_user` (404) → auto-borrado 403 (espejo de `toggle-active`) → último admin activo 409 →
  audit `user.delete` (before=`to_admin_user_dict`) → `session.delete` → commit con
  `except IntegrityError: rollback + 409` (patrón ya presente en `routes/users.py:99-103`).
- [x] **USR-3 — Frontend API.** `web/src/api.ts`: `deleteUser(id)` (`method: 'DELETE'`).
- [x] **USR-4 — UI.** `web/src/components/pages/UserManagement.tsx`: acción de borrado en el menú
  desktop y en el action sheet mobile, con diálogo de confirmación fuerte (nombra el usuario +
  "permanente"); el self ya muestra "Acciones no disponibles". Superficie el 409 sin romper.
- [x] **USR-5 — Tests.** `tests/functional/test_api_users.py` (admin-only, 404, self 403, último
  admin 409, referenciado 409, éxito + audit `user.delete`; sumar la ruta al auth matrix),
  `web/src/components/pages/UserManagement.test.tsx` (confirmación + llamada + refresh + error 409),
  `web/src/api.test.ts`.

### Work unit 3 — Casos archivados
- [x] **CASE-1 — Migración.** `db/migrations/051_cases_archived_at.sql`:
  `ALTER TABLE cases ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;` (patrón de
  `033_customer_archived_at.sql`). Rollback documentado.
- [x] **CASE-2 — Serializer.** Exponer `archived_at` en el dict del caso (`to_case_dict`).
- [x] **CASE-3 — Servicio.** `app/services/cases.py`: `archive_case(session, case, actor)` (rechaza
  casos abiertos con `ValueError`) + `unarchive_case(...)`, con audit `case.archived` /
  `case.unarchived`. `app/services/customers.py`: `customer_history(..., include_archived_cases=False)`
  → filtra `Case.archived_at.is_(None)` por defecto.
- [x] **CASE-4 — Routes.** `app/panel/api/routes/cases.py`: `POST /cases/{id}/archive` (**409** si el
  caso está abierto) y `POST /cases/{id}/unarchive`, operator-only. `app/panel/api/routes/clients.py`:
  `GET /clients/{id}?include_archived_cases=` pasa el flag a `customer_history`.
- [x] **CASE-5 — Frontend API.** `web/src/api.ts`: `archiveCase(id)`, `unarchiveCase(id)`, y
  `getClientFicha(id, { includeArchivedCases })`.
- [x] **CASE-6 — UI.** `ClientFicha.tsx`: toggle **"Ver archivados"** en "Casos anteriores" (patrón de
  `ClientesList.tsx` "Mostrar archivados"), re-fetch con el flag; casos archivados con badge
  "Archivado" + acción "Desarchivar"; casos cerrados con acción "Archivar". Desktop + mobile.
- [x] **CASE-7 — Tests.** `tests/functional/test_api_cases.py` (archive/unarchive: operator-only,
  409 en abierto, audit `case.archived`/`case.unarchived`, exclusión/inclusión en la ficha),
  `web/src/components/pages/ClientFicha.test.tsx` (toggle + archivar/desarchivar), `web/src/api.test.ts`.

## Criterios de aceptación
- **(KB)** El delete borra el documento y sus chunks (cascade); 404 si no existe; solo admin;
  audit `kb.document_delete` con actor = username del admin.
- **(Usuarios)** Delete admin-only; 404 si no existe; 403 auto-borrado; 409 si es el último admin o
  si está referenciado por FKs (sin cascada); audit `user.delete`.
- **(Casos)** Archivar solo casos cerrados (409 si está abierto); reversible; oculto por defecto en la
  ficha y visible con `include_archived_cases`; audit `case.archived`/`case.unarchived`.

## Entrega
Presupuesto advisory ~400 líneas por work unit (no es cap duro). Estrategia: un work unit por commit;
PR(s) a decidir al cerrar el primer work unit. Si el acumulado supera ~400 líneas → chained PRs.

## Grafo (Graphify)
`graphify-out/GRAPH_REPORT.md` presente (build `38b9ed15`). Nodos: `KbList.tsx`, `services/kb.py`,
`record_audit()`. Refresh del grafo al cerrar la sesión.

## Verificación / evidencia
- KB-1..KB-6: `uv run pytest tests/integration/test_kb.py tests/functional/test_api_kb_settings.py -q` — 89 passed.
- Frontend: `cd web && npx vitest run src/components/pages/KbDocumentDetail.test.tsx src/api.test.ts` — 53 passed.
- Build/typecheck: `cd web && npm run build` — passed (`tsc -b` + Vite build; existing chunk-size warning).
- Constraint verified in PostgreSQL as `kb_chunks_document_id_fkey` before migration: `FOREIGN KEY (document_id) REFERENCES kb_documents(id) ON DELETE CASCADE` after applying migration.
- Commit del work unit: `73073e24` — `feat(kb): hard delete admin-visible documents` (10 archivos, +218/-9).
- Spot-check del padre (re-corrida independiente de la suite backend con la env de `test-db.sh`): 89 passed.
- RDD `review assess` (`--base-ref 3475bba7 --committed-only`): `risk: medium`, `review_due: false` (`under_budget`, 227 líneas < 400) → sin review aún; el boundary queda pendiente en el slice hasta que un commit posterior alcance el presupuesto.
- Nota de entorno: la DB de test se levanta con `bash infra/test-db.sh up` (puerto derivado 6026) y `eval "$(bash infra/test-db.sh env)"`; sin esa env `db/migrate.sh` apunta a un puerto muerto.
- RDD review del slice (lineage `review-bf916289a918a2f1`, 1 lente `review-reliability`, `approved`, authority **burned**): **1 hallazgo advisory no bloqueante** — **R3-001** (`web/src/components/pages/KbDocumentDetail.tsx:119`): tras borrar usa `window.history.back()`, que no garantiza volver a la lista si el detalle se abrió directo o el historial previo está fuera del panel (mismo patrón que el botón "Volver" ya existente). Trabajo posterior; NO re-corre la review sobre este candidato.

### WU2 — Usuarios delete
- Commit `2690c80e` `feat(users): hard delete with self/last-admin guards and FK conflict` (8 archivos).
- Backend: `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/functional/test_api_users.py -q` — 13 passed (spot-check del padre). Frontend vitest 61 passed. `npm run build` passed.
- RDD assess (base `3475bba7`, committed-only): medium, 422 líneas → `review_due: true` (`slice_budget_reached`) → review del slice KB+Usuarios.
- Nota: la guardia de último admin es redundante con la de auto-borrado (el admin que actúa es activo y se cuenta); se conserva como defensa en profundidad.

### WU3 — Casos archivados
- Commit `60e600ec` `feat(cases): soft-archive closed cases with ficha toggle` (14 archivos, +210/-23).
- Backend: `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/functional/test_api_cases.py -q` — 23 passed (spot-check del padre). Frontend vitest 94 passed. `npm run build` passed.
- RDD assess (base `2690c80e`, committed-only): medium, **234 líneas**, `review_due: false` (`under_budget`) → **sin review** para WU3; el native review solo se dispara al alcanzar ~400 líneas o riesgo alto.
- Desvío TDD declarado por el writer: el test de componente `ClientFicha` se agregó después de implementar la UI (no se observó RED); backend y contratos de API sí tuvieron RED observado.
- Aviso: la corrida de vitest imprimió warnings de React `act(...)` (no fallos). `ruff` no está instalado en el entorno → lint no ejecutado.

### Pre-merge integration check (rama apilada sobre `origin/main f03e6ad7`)
- Corrida completa sobre el stack (rama tope): backend **1962 passed / 0 failed** (247s), frontend **1174 passed** + `npm run build` OK.
- **Hallazgo del check** (los 3 fallos eran nuestros, tests desactualizados, NO bugs de producción): `tests/integration/test_migrations.py` exige la lista EXACTA de migraciones (faltaban 050 y 051) y dos asserts de shape exacto del dict de caso (`tests/functional/test_api_clients.py`, `tests/integration/test_customers.py`) no contemplaban `archived_at`. La verificación por work unit (solo archivos target) no los detectó.
- Corregidos: `test(migrations)`: 050 en la rama KB (PR1); `test(cases)`: 051 + `archived_at` en las dos asserts, en la rama de casos (PR3).
- PR1/PR2 re-verificados con la DB de test **reseteada** (`test-db.sh down/up`): la DB compartida conserva migraciones entre ramas → falso fallo. PR1 34/0, PR2 119/0.

### Entrega — chained PRs `stacked-to-main`
- Estrategia (owner): **(B) stacked-to-main**. 3 PRs, cada uno <400 líneas.
- PR1 `odd/panel-backend-crud-kb` (base `main`): KB delete — 231 líneas.
- PR2 `odd/panel-backend-crud-users` (base PR1): usuarios delete — 198 líneas.
- PR3 `odd/panel-backend-crud-cases` (base PR2): casos archivar — 250 líneas.
- Tras el merge del padre → retarget del hijo a `main`.

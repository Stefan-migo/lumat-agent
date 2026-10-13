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

## Decisiones abiertas (pendientes)
- **Usuarios**: ¿delete real con guardia de conflicto (409 FKs), o filtro "ocultar inactivos"?
- **Casos**: ¿archivar = ocultar de la ficha (reversible)? ¿archivados visibles en export/diálogo?
  ¿se permiten múltiples casos abiertos?

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
- [ ] **USR-*** — pendiente de decisión.

### Work unit 3 — Casos archivados
- [ ] **CASE-*** — pendiente de decisión.

## Criterios de aceptación
- **(KB)** El delete borra el documento y sus chunks (cascade); 404 si no existe; solo admin;
  audit `kb.document_delete` con actor = username del admin.

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

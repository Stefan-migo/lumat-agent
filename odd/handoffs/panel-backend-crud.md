# HANDOFF — CRUD de backend del panel (KB, usuarios, casos archivados)

Fecha: 2026-10-13. Estado: **sin empezar**. Origen: el slice frontend `panel-design-details`
(PR #580, mergeado en `main` = `3475bba7`). Estos 3 ítems se difirieron a propósito.

## Por qué van aparte del frontend
Son CRUD con **borrado real** (KB, usuarios) y archivo de casos: tocan API + DB, con FKs y
riesgo de pérdida de datos en producción. Mezclarlos con pulido cosmético degradaba la review.
`main` no tiene branch protection → la disciplina de review es evidencia, no enforcement.

---

## Setup de trabajo (¡ojo con el backend!)
- Crear worktree: `rapso worktree create <slug> --yes --root /home/stefan/repos/lumat-agent`
  (slug sugerido: `panel-backend-crud`). Base = `origin/main` actual.
- `rapso worktree provision <path>` **NO** copia `infra/.env` ni baja `web/node_modules`. A mano:
  `cp <main>/infra/.env infra/.env` y (si se toca frontend) `cd web && npm ci`.
- **Backend**: a diferencia del slice frontend, acá hay que correr el backend **desde el worktree**.
  `infra` es identidad compartida → **un solo stack a la vez**. Bajar el de main antes:
  `docker compose -p infra -f infra/docker-compose.yml down`. Luego levantar desde el worktree;
  el api bind-montea `..` y corre `--reload`.
- Tests backend: `uv run pytest` necesita la DB de test y `DEEPSEEK_API_KEY`
  (`docker compose -f infra/docker-compose.yml --profile test up -d db-test` o `eval "$(bash infra/test-db.sh env)"`).
- Graphify: grafo en `graphify-out/` (gitignored). Refrescar al cerrar la sesión (`graphify <root> --update`).
- Skills a cargar: `rapso-persona` (5-Step Gate) y `branch-pr` para el PR.
- CI: `.github/workflows/tests.yml` → jobs `test` (pytest + pgvector) y `panel` (npm ci + `tsc -b` + vitest).

---

## 1 · KB — hard delete real
- Hoy: `GET /panel/api/kb`, `POST /kb`, `POST /kb/{id}/edit|disable|enable|restore|visibility`.
  **No hay delete.**
- Modelo: `kb_documents` (id, project_id, title, format, content, version, active_version, active,
  visibility, provider, model, cost_meta, timestamps) + `kb_chunks` (id, document_id, version,
  chunk_index, content, source_meta, embedding `vector(384)`).
- **Bloqueo**: `kb_chunks.document_id → kb_documents.id` **sin `ON DELETE`** (default NO ACTION).
  Falta migración: `ON DELETE CASCADE` (o borrado transaccional de chunks antes del doc).
  Migraciones relevantes: `db/migrations/001_init.sql`, `008_local_embeddings.sql`,
  `027_kb_visibility.sql`, `041_kb_project_scope.sql`.
- No hay otras FKs entrantes (la recuperación es transitoria). Auditar con `app/services/audit.py`
  (guarda el id como string, no FK) → evento `kb.document_delete`.
- Backend: `app/panel/api/routes/kb.py` (`require_admin_json`), `app/services/kb.py`, serializers.
- UI: `web/src/components/pages/KbList.tsx` (DataTable desktop + lista mobile),
  `KbDocumentDetail.tsx`, wrappers en `web/src/api.ts`. Delete con confirmación explícita
  (nombra el documento + "permanente").
- Tests: `tests/integration/test_kb.py`, `tests/functional/test_api_kb_settings.py`,
  `web/src/components/pages/KbList.test.tsx`, `KbDocumentDetail.test.tsx`, `web/src/api.test.ts`.
- **Decisión abierta**: ¿delete para cualquier doc admin-visible, o solo si el proyecto es del admin?

## 2 · Usuarios — delete
- Hoy: `GET/POST /panel/api/users`, `GET/PATCH /users/{id}`,
  `POST /users/{id}/toggle-active|reset-password|unlock`. **No hay delete.**
  Soft-disable = `active`; la lista sigue mostrando inactivos (por eso se llenó de test users).
- Modelo `users`: id, username, password_hash, role, active, failed_logins, locked_until, email,
  name, phone, position. **Sin `created_at`.**
- **Bloqueo**: FKs restrictivas (NO ACTION) — `cases.responsible_id`, `conversations.responsible_id`,
  `messages.author_id`, `appointments.technician_id`, `technician_availability.technician_id`,
  `technician_weekly_schedule.technician_id`, `notification_operations.user_id`,
  `panel_notifications.user_id`, `push_subscriptions.user_id`, `internal_chat_threads.user_id`,
  `projects.owner_id`, `project_aliases.owner_id`, `memories.owner_id`, `project_files.owner_id`,
  `settings.updated_by`.
- Propuesta: `DELETE /panel/api/users/{id}` admin-only, con **bloqueo de auto-borrado y del último
  admin**, y si hay referencias → **409 conflict** ("desactivá en su lugar"). Nunca cascada silenciosa.
  Auditar el evento.
- Alternativa más chica si solo se busca que no aparezcan: filtro "ocultar inactivos" (no borra filas).
- Sesiones: la cookie firmada lleva `user_id`; tras borrar, el próximo request da 401 (o redirect a login).
- Frontend: `web/src/components/pages/UserManagement.tsx` (menú desktop + action sheet mobile), `web/src/api.ts`.
- Tests: `tests/functional/test_api_users.py`, `web/src/components/pages/UserManagement.test.tsx`, `web/src/api.test.ts`.

## 3 · Clientes — archivar/remover casos cerrados
- No existe endpoint. `cases` está referenciado por conversaciones/citas → **soft-archive**
  (nueva columna `archived_at` + migración), endpoint restringido a casos cerrados
  (`app/services/cases.py`: cerrado = `closed|cerrado|finalizado|cancelado`; `null` = abierto),
  y excluir archivados del historial de la ficha.
- Fuente del historial: `GET /panel/api/clients/{customer_id}?messages_limit=10` →
  `customers.customer_history(...)` (devuelve TODOS los casos, sin paginar server-side).
- UI: `web/src/components/pages/ClientFicha.tsx`, pestaña "Casos anteriores"
  (ya paginada client-side a 5 por PR #580).
- Tests: `tests/functional/test_api_cases.py`, `web/src/components/pages/ClientFicha.test.tsx`.
- **Decisiones abiertas**: ¿archivar = ocultar de la ficha (reversible)? ¿archivados visibles en
  export/diálogo de historial? ¿se permiten múltiples casos abiertos?

---

## Orden sugerido (work units)
1. **KB delete** (menor superficie, sin FKs entrantes): migración cascade + `DELETE` + auditoría + UI + tests.
2. **Usuarios delete** con guardia de conflicto (409) + self/last-admin + UI + tests.
3. **Casos archivados**: `archived_at` + endpoint + exclusión en la ficha + UI + tests.

## Criterios de aceptación / verificación
- Un work unit por cambio; commit Conventional **sin atribución de IA**.
- Frontend: `npx vitest run <archivos>` + `npm run build` (incluye `tsc -b`). Backend: `uv run pytest tests/`.
- Integrar `origin/main` en la rama antes del PR; PR con CI verde (`test` + `panel`).
- RDD: `gentle-ai review assess --cwd <worktree> --agent opencode --base-ref origin/main --committed-only --json`.
- Grafo: registrar los nodos consultados (`app/panel/api/routes/kb.py`, `app/services/kb.py`,
  `app/panel/api/routes/users.py`, `app/models.py`, `app/services/cases.py`, `KbList.tsx`,
  `KbDocumentDetail.tsx`, `UserManagement.tsx`, `ClientFicha.tsx`).

## Notas de contexto
- El frontend ya dejó `ConversationSummary` y la paginación de "Casos anteriores" (5/página) en `main`.
- Flake conocido: `web/src/components/pages/AgentChat.test.tsx` falla por timeout bajo carga paralela;
  pasa aislado (68/68). No confundir con regresión.
- `origin/main` avanzaba seguido durante el día (p. ej. #578, #579 mientras corría este slice):
  fetch + merge antes de pushear, siempre.

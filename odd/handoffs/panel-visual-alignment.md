# HANDOFF — panel-visual-alignment → continuar en T7 (frontend árbol de carpetas)

Fecha: 2026-10-14. Estado: **T6 backend listo y verificado; falta el frontend de carpetas/delete/KB.**
Worktree: `/home/stefan/repos/lumat-agent-odd-panel-visual-alignment` — branch `odd/panel-visual-alignment`
(base main `6d7988b2`). Task doc: `odd/tasks/panel-visual-alignment.md` (leer hasta `## Log`).
Ningún otro worktree toca `web/` (verificado).

## Qué está hecho

| T | Qué | Commits |
| --- | --- | --- |
| T1 | Chrome/tabla del header de proyecto (slot `titleIcon` aditivo en PageFrame/PageHeader) | `f194eef9`, `3ef51197`, `0417b401` |
| T1b | Header del **workspace embebido**: sin rail lima, sin botón, gap título→tabs (era el grid estirando) | `ef0a9524`, `a45f7280` |
| T2 | Tab Contexto: card Instrucciones (ícono+subtítulo+helper+footer) + 2 cards derecha | `31f11237`, `641c1606`, `f6c7877d` |
| T2c | Vínculo archivo↔KB (`kb_document_id`, migración 054 + backfill) + tabla unificada "En la KB" | `5c9d6606`, `de995673`, `36c03f34` |
| T6 | Backend carpetas: migración 055 + CRUD + upload-a-carpeta + delete archivo (cascada KB) + delete carpeta recursivo | `fcc54f61`, `f2fd0f28`, `f9698d69` |

Datos de dev en el stack: 3 archivos de proyecto, 0 carpetas, 4 docs KB.

## Qué falta (en orden sugerido)

- **T7 — frontend árbol de carpetas (S6).** `ProjectResources.tsx`: árbol con nodo raíz del proyecto,
  carpetas colapsables anidadas + filas de archivo (nombre, tamaño, badge "En la KB", descargar, eliminar);
  buscador `Buscar archivo o carpeta…`; `Subir archivo` apuntando a la carpeta seleccionada; footer
  `N archivos · M carpetas`; CRUD de carpetas (crear/renombrar/borrar). Ref: imagen 2 del owner.
- **T8 — delete + diálogos de confirmación** (ref imagen 3): ícono + título + close, la pregunta, card de
  preview (nombre/tamaño/estado), `Proyecto: <name>`, footer `Cancelar` + rojo. Para archivo de proyecto
  y para documento de KB.
- **T9 — card Conocimiento** según ref: buscador `Buscar documento…`, filas `FORMAT · vN` + badge Activo +
  trash, footer con conteo.
- **T3 (Agentes)**, **T4 (Skills)**, **T5 (Hilos)** — siguen pendientes del scope original.

## API ya disponible (verificada en vivo)

- `GET/POST/PATCH/DELETE /panel/api/projects/{slug}/folders` (create body `{name, parent_id?}`, rename `{name}`).
- `POST /panel/api/projects/{slug}/files` acepta `folder_id` (form).
- `DELETE /panel/api/projects/{slug}/files/{file_id}` → 204, borra bytes + fila + doc KB.
- `DELETE /panel/api/projects/{slug}/folders/{folder_id}` → 204, recursivo.
- `GET /panel/api/projects/{slug}/files` devuelve `folder_id` y `kb_document_id`.
- `DELETE /panel/api/kb/{doc_id}` (ya existía) para el doc de KB.

## Levantar el stack (ya está corriendo)

```bash
# API aislada (worktree) — project lumat-pva → api :8001, db :5433
cd /home/stefan/repos/lumat-agent-odd-panel-visual-alignment
docker compose -p lumat-pva -f infra/docker-compose.yml -f infra/docker-compose.harness.yml up -d
docker compose -p lumat-pva -f infra/docker-compose.yml -f infra/docker-compose.harness.yml restart api   # aplica migraciones nuevas
# Frontend :5173 → proxya a :8001
cd web && VITE_API_TARGET=http://localhost:8001 npm run dev
```

Panel: http://127.0.0.1:5173/panel/app/ — proyecto demo slug `test` (se abre como tab:
`/panel/app/chat?context=test`).

## Tests

- Frontend: `cd web && npm run build && npm test` (vitest). Ojo: `AgentChat > markdown snapshot stale`
  es **flaky** bajo carga; pasa aislado.
- Backend:
  ```bash
  cd /home/stefan/repos/lumat-agent-odd-panel-visual-alignment
  PYTHON=python3 ./infra/test-db.sh up          # DB de test del worktree en :6301
  export DATABASE_URL='postgresql+psycopg://app:app@localhost:6301/lumat' \
         TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:6301/lumat' \
         DEEPSEEK_API_KEY=test APP_DB_PASSWORD=app
  uv run pytest tests/integration/test_project_files.py -q
  ```

## Gotchas (ya resueltos, pero anotados)

- **Vite sirve transforms stale**: si un cambio no aparece, matar vite, `rm -rf web/node_modules/.vite` y
  reiniciar. Verificar con `curl .../panel/app/src/... | grep <algo>`.
- El bash tool mata procesos background no detachados → usar `setsid ... & disown`.
- El worktree venía con `.venv` y `media/` **root-owned y vacíos** (provision); se recrearon
  (`rm -rf .venv && uv sync`; `rm -rf media && mkdir media`).
- `web/scripts/capture-section.mjs` escribe SIEMPRE en `refs/current` del worktree **primario**.
- El header es compartido: usar props **aditivas** (no romper otras páginas).

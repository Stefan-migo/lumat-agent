# HANDOFF — panel-visual-alignment → continuar en T9 (card Conocimiento)

Fecha: 2026-10-14. Estado: **T7 + T10 + T11 + T12 listos y verificados (árbol de archivos completo). Falta T9 (card Conocimiento) y T8 (diálogo de delete de doc KB).**
Worktree: `/home/stefan/repos/lumat-agent-odd-panel-visual-alignment` — branch `odd/panel-visual-alignment`
(base main `6d7988b2`, HEAD `d6783729`). Task doc: `odd/tasks/panel-visual-alignment.md` (leer hasta `## Log`).
Ningún otro worktree toca `web/` (verificado en el handoff anterior).

## Qué está hecho

| T | Qué | Commits |
| --- | --- | --- |
| T1 | Chrome/tabla del header de proyecto (slot `titleIcon` aditivo) | `f194eef9`, `3ef51197` |
| T1b | Header del workspace embebido (sin rail, sin botón, gap título→tabs) | `ef0a9524` |
| T2 | Tab Contexto: card Instrucciones + 2 cards derecha | `31f11237`, `641c1606` |
| T2c | Vínculo archivo↔KB (`kb_document_id`, mig 054) + tabla unificada "En la KB" | `5c9d6606`, `de995673` |
| T6 | Backend carpetas: mig 055 + CRUD + upload-a-carpeta + delete archivo/carpeta | `fcc54f61`, `f2fd0f28` |
| T7 | **Frontend árbol de carpetas** (API client + tree UI) | `bb6b6a64`, `c0268a94` |
| T10 | **Endpoint mover archivo** (`PATCH .../files/{id}`) + drag & drop | `196ebd23`, `c366119d` |
| T11 | Root sin colapsar, toolbar `...`, diálogo de subida, layout, `...` sin fondo | `c366119d` |
| T12 | **Toast global**, fix z-index del menú, sacar destacador | `6b9af9b2`, `43340a03` |
| T12b | Fuente del toast = `--font-ui` (Inter) | `569921f1` |

## Qué falta (en orden sugerido)

- **T9 — card Conocimiento del proyecto (imagen 1, abajo).** Hoy usa `DataTable` genérico y **desborda** a
  ancho angosto (hay un wrapper `.projects-page__table-scroll` que lo contiene, pero hay que rediseñarlo).
  Según la referencia: subtítulo `Documentos de la base de conocimiento (RAG).`; buscador
  `Buscar documento…`; filas con ícono, título, `FORMAT · vN`, badge `Activo` y trash; footer con conteo
  (`2 documentos`) y la nota `Consulta aquí el formato, la versión y el estado de cada documento.`.
- **T8 — diálogo de delete de documento de KB** (imagen 2 derecha): ícono + título `Eliminar de la KB` +
  close, la pregunta, card de preview (título + `CSV · v1` + badge `Activo`), `Proyecto: <name>`, footer
  `Cancelar` + rojo `Eliminar de la KB`. El diálogo de **archivo** ya está hecho (imagen 2 izquierda) — reusar
  ese patrón. El endpoint ya existe: `DELETE /panel/api/kb/{doc_id}`.
- **T3 (Agentes)**, **T4 (Skills)**, **T5 (Hilos)** — pendientes del scope original (specs S3/S4/S5 en el
  task doc).

## API disponible (verificada)

- `GET/POST/PATCH/DELETE /panel/api/projects/{slug}/folders` (create `{name, parent_id?}`, rename `{name}`).
- `POST /panel/api/projects/{slug}/files` acepta `folder_id` (form).
- `PATCH /panel/api/projects/{slug}/files/{file_id}` con `{folder_id}` (null = raíz) → **mover**.
- `DELETE /panel/api/projects/{slug}/files/{file_id}` → 204 (bytes + fila + doc KB).
- `DELETE /panel/api/projects/{slug}/folders/{folder_id}` → 204, recursivo.
- `GET /panel/api/projects/{slug}/files` devuelve `folder_id` y `kb_document_id`.
- `DELETE /panel/api/kb/{doc_id}` para el doc de KB.

## Frontend — piezas nuevas a reusar

- **`ToastProvider` / `useToast`** (`web/src/components/primitives/Toast.tsx`): toast global abajo-derecha,
  auto-dismiss 5 s, apilable y cerrable. `useToast()` devuelve no-op si no hay provider. El feedback de
  acciones va por acá, **no** por banners inline.
- **`Select`** primitiva, **`Dialog`**, **`Menu`** (`trigger="icon"`), **`SearchInput`**, **`Badge`**,
  **`EmptyState`**, **`StateMessage`**.
- `ProjectResources.tsx` es el ejemplo del patrón: toolbar, árbol, diálogos (subir / crear-renombrar carpeta
  / confirmar delete), drag & drop, toasts.

## Levantar el stack

```bash
cd /home/stefan/repos/lumat-agent-odd-panel-visual-alignment
docker compose -p lumat-pva -f infra/docker-compose.yml -f infra/docker-compose.harness.yml up -d
docker compose -p lumat-pva -f infra/docker-compose.yml -f infra/docker-compose.harness.yml restart api
cd web && VITE_API_TARGET=http://localhost:8001 npm run dev
```

Panel: http://127.0.0.1:5173/panel/app/ — proyecto demo slug `test`, standalone `/panel/app/projects/test`.

## Tests

- Frontend: `cd web && npm run build && npm test` (vitest). Ojo: `AgentChat > markdown snapshot stale` es
  **flaky** bajo carga; pasa aislado. Suite actual: **1199 passed / 106 files**.
- Backend:
  ```bash
  cd /home/stefan/repos/lumat-agent-odd-panel-visual-alignment
  PYTHON=python3 ./infra/test-db.sh up
  export DATABASE_URL='postgresql+psycopg://app:app@localhost:6301/lumat' \
         TEST_ADMIN_DB_URL='postgresql://lumat:lumat@localhost:6301/lumat' \
         DEEPSEEK_API_KEY=test APP_DB_PASSWORD=app
  uv run pytest tests/integration/test_project_files.py tests/functional/test_api_project_files.py -q
  ```
  (pytest imprime poco con la config actual; usá `echo "exit=$?"` o corré un test puntual para ver el conteo.)

## Gotchas (varios ya resueltos, anotados para no regresar)

- **RDD está ON (global).** Después de cada work-unit commit: `gentle-ai review assess --cwd . --agent
  opencode --base-ref HEAD~N --committed-only --json`. Viene dando **medium / under_budget / review_due false**.
- **Vite sirve transforms stale**: si un cambio no aparece, matar vite, `rm -rf web/node_modules/.vite` y
  reiniciar. Verificar con `curl .../panel/src/components/... | grep <algo>`.
- El bash tool mata procesos background no detachados → `setsid ... & disown`.
- **`<dialog>` cerrado queda en el DOM.** Testing-library lo trata como **hidden** para `getByRole`
  (solo el abierto es consultable), pero **`getByText` SÍ matchea texto dentro de un dialog cerrado**
  (p. ej. los `<option>` del `Select`) → scopeá con `within(dialog)` o `container.querySelector`.
- **`...` sin fondo/borde es decisión global** (`.menu__trigger--icon` en `primitives.css`): no le devuelvas
  fondo ni borde.
- **`.menu__content` tiene `z-index: var(--z-modal)`**: sin eso, el popup pierde contra la fila raíz sticky
  (`z-index: 1`) y el primer ítem queda tapado.
- **`.btn` tiene `white-space: nowrap`** (global): los labels de botón no se parten.
- **El root del árbol NO es colapsable** (decisión del owner).
- `web/scripts/capture-section.mjs` escribe SIEMPRE en `refs/current` del worktree **primario**.
- Para screenshots ad-hoc: Playwright con `channel: "chrome"`, login leyendo `PANEL_ADMIN_USERNAME/PASSWORD`
  de `infra/.env` del worktree primario, y el script debe vivir dentro de `web/` (si no, no resuelve
  `@playwright/test`). Borrar el script temporal después.

## Key Learnings

1. El popup del `Menu` (Radix, portalado) no traía `z-index`, así que perdía contra cualquier hermano posicionado con `z-index` (la fila raíz sticky lo tapaba y ocultaba el primer ítem).
2. Un `<dialog>` cerrado sigue en el DOM: `getByRole` lo ignora por inaccesible, pero `getByText` sí matchea su contenido (los `<option>` de un `Select` colisionan).
3. El feedback de acciones debe ser un toast transitorio (abajo-derecha, auto-dismiss), no un banner inline permanente.
4. El toast heredaba la fuente del navegador; hay que setear `font-family: var(--font-ui)` explícitamente porque no existe una regla global de fuente en `body`.
5. Reusar `--z-modal` para el menú y sumar `--z-toast` para los toasts evita regresiones de stacking.

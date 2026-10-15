# panel-visual-alignment

Objective: redesign the project-detail tabs (Contexto, Agentes, Skills, Hilos) to match the owner's
reference images. Started frontend-only; the owner later authorized bounded backend additions (the
`kb_document_id` link and project-file folders). Branch `odd/panel-visual-alignment`.
Delivery: ask-on-risk. Runner: `npm test` (vitest) + `npm run build` (tsc -b + vite build).

Scope lock: agents stay fixed system roles. Hilos is wired to the existing endpoint. No palette/token
changes. One bounded backend addition was authorized later: `project_files.kb_document_id` (migration
054) to remove the files/knowledge duplication (see L8).

## Specs

S1 — Shared page chrome (refs 6-9).
The project-detail header adopts the reference shape: a leading folder icon tile, the project name as
the page title, the status badge beside the title, the purpose as subtitle, and `Abrir asistente` as
the primary action. No page-level breadcrumb: the shell top bar owns it. Reuse `PageFrame`/`PageHeader`;
any new slot is additive and must not change existing pages. Tab bar keeps its underline-active style.

S2 — Contexto tab (ref 6). Two-column layout.
Left card `Instrucciones del proyecto`: icon + title + subtitle `Define el contexto compartido por el
asistente.`; read-only `Nombre del proyecto` and `Propósito`; editable `Instrucciones del proyecto`
with placeholder `Describe cómo debe trabajar el asistente en este proyecto…`; helper `Estas
instrucciones forman parte del contexto del proyecto.`; footer action `Guardar cambios`.
Right column: `Archivos del proyecto` card — icon + title + count badge + `Subir archivo`; empty state
`Aún no hay archivos` / `Sube el primer documento de este proyecto.`; `Conocimiento del proyecto` card
— icon + title + count + `Subir archivo a la KB`; empty state `Sin documentos indexados` / `Los
archivos compatibles se indexan automáticamente.`; footer note `Los archivos del proyecto se comparten
como contexto; los adjuntos de un hilo permanecen en ese hilo.`
Behavior is already wired and must not change.

S3 — Agentes tab (ref 8).
Card `Agentes del proyecto` with subtitle `Roles disponibles para trabajar con el contexto del
proyecto.` Three role cards, each with a dark circular icon tile, name, role chip, and description:
- `Orquestador` · chip `Asistente del proyecto` · `Responde consultas y utiliza las herramientas
  disponibles según la solicitud.`
- `Verificador` · chip `Solo lectura` · `Contrasta criterios con evidencia y consulta herramientas de
  solo lectura.`
- `Explorador` · chip `Investigación` · `Investiga con las herramientas habilitadas para la
  delegación.`
Then `Última ejecución` card: subtitle `Estado registrado de la ejecución más reciente.`, status pill
(e.g. `Completada`) and timestamp. Read-only; agents remain fixed system roles.

S4 — Skills tab (ref 7).
Search field `Buscar habilidad por nombre o descripción…`. `Catálogo global` card with count badge +
`Habilidades globales de solo lectura.` and rows: icon tile, name, description, chips `Global` /
`Solo lectura`. `Habilidades del proyecto` card with count + `Agregar habilidad` action, dashed empty
state `Aún no hay habilidades en este proyecto` / `Agrega una habilidad para definir instrucciones
específicas.`, and a collapsible `Agregar habilidad` disclosure. Footer note `Las habilidades globales
se consultan; las del proyecto se gestionan aquí.` Existing add/edit/delete behavior preserved
(whole-array PATCH via `updateProjectConfig`).

S5 — Hilos tab, wired (ref 9).
Replace the hardcoded placeholder. List the project's chat threads via `GET
/panel/api/chat/threads?proyecto=<slug>`. When empty, show the reference empty-state visual (icon,
title, supporting copy, `Abrir historial` CTA, footer note). Assumption to confirm with the owner: the
empty-state copy reflects a real empty project (not "unavailable"), e.g. `Aún no hay hilos en este
proyecto`.

S6 — Project file folders + delete (backend feature; refs images 2-3). Owner-authorized.
- Data: a project-scoped `project_folders` table (`parent_id` for nesting) and `project_files.folder_id`.
- Folder CRUD: create (name + optional parent), rename, delete. Delete is recursive: it removes its
  files (and each file's linked KB document) and subfolders; the confirmation states the file count.
  Empty folders are allowed.
- Upload targets a folder (`folder_id`, optional → project root).
- File delete: `DELETE /panel/api/projects/{slug}/files/{file_id}` removes the stored bytes, the row and
  the linked KB document. KB documents are removed through the existing `DELETE /panel/api/kb/{id}`.
- Tree UI: a root project node with collapsible folders and file rows (name, size, `En la KB` badge,
  download, delete), a `Buscar archivo o carpeta…` search, a `Subir archivo` action, and a
  `N archivos · M carpetas` footer.
- Confirmation dialogs (ref image 3) for file delete and KB document delete: icon tile + title + close,
  the question, a preview card with name/size/state, `Proyecto: <name>`, footer `Cancelar` + red action.
- Knowledge card: `Buscar documento…`, rows with `FORMAT · vN` and an `Activo` badge, a delete action,
  and a document-count footer.

S6b — File manager completeness (ref: owner feedback 2026-10-14, see L13). Owner-authorized.
- The layout MUST NOT break at any width: the toolbar and card content wrap gracefully; no control is
  clipped and no text overflows its row.
- The folder tree scrolls vertically on its own when its content exceeds the visible height.
- The project node is the tree **root**: it is not collapsible and carries no twisty.
- A `⋯` action menu groups `Subir archivo` and `Crear carpeta`.
- Drag-and-drop moves a file into a folder (or back to the project root).
- The upload dialog states and lets the user pick the destination folder, and offers `Crear carpeta`
  inline.

S6c — Global design decision: every vertical `⋯` (icon) menu trigger has **no background and no
border** — just the vertical dots.

## Tasks

| ID | Spec | Route | Status | Evidence |
| --- | --- | --- | --- | --- |
| T1 shared chrome | S1 | inline | done | f194eef9 |
| T1b workspace header fixes | S1 | inline | done | ef0a9524 |
| T2 Contexto | S2 | inline | done | 641c1606 |
| T2c KB link + unified files list | S2 | inline | done | 5c9d6606, de995673 |
| T3 Agentes | S3 | inline | pending | — |
| T4 Skills | S4 | inline | pending | — |
| T5 Hilos wire | S5 | inline | pending | — |
| T6 backend project folders | S6 | inline | done | fcc54f61, f2fd0f28 |
| T7 files tree UI | S6 | inline | done | bb6b6a64, c0268a94 |
| T8 delete + confirm dialogs | S6 | inline | pending | — |
| T9 knowledge card layout | S6 | inline | pending | — |
| T10 move file endpoint + drag & drop | S6b | inline | done | 196ebd23 |
| T11 upload dialog + tree/root/toolbar revisions | S6b, S6c | inline | done | c366119d |

## Log

L1 (owner, verbatim): "ok quiero trabajar en estos tres paneles. ... Estas tabs no han sido disea;adas
y algunas no estan conectadas. hay que redise;ar completamente estas secciones estas son las
referencias para el dise;o ... necesito que adaptemos lo que tenemos. entiendo que la seccion agentes
deberia dar la posibilidad de crear un agente? o modificarlo? no estoy seguro. lo mismo con skills.
deberia haber una forma de agregar skills?"
L2 (owner): "vamos solo frontend." → agents stay fixed roles; no backend.
L3 (owner): "si hilos si entra hay que cablearlo." → Hilos is in scope and wired.
L4: T1 done (f194eef9). Added an additive `titleIcon` slot to shared `PageFrame`/`PageHeader`
(optional, no existing page changed); project detail now renders the folder tile + status badge beside
the title, purpose as subtitle. `npm run build` green; full vitest suite green (1182 passed; the two
`ProjectsPage` header assertions were updated to the new structure).
L5 (owner, verbatim): "vamos primero con el trabajo del 'workspace' - la linea vertical verde al lado
del titulo se va. - aqui hay que quitar el boton volver al asistente ya que como se abre en un tab no
es necesario. ya estamos en el asistente. - hay un espacio grande entre el titulo y los tabs hay que
fixearlo". Also: the reference breadcrumb and the "Abrir asistente" button must NOT be added.
L6: T1b done (ef0a9524). Embedded project detail (`projects-page--embedded`): removes the shared header
lime rail, renders no action button, and adds `align-content: start` so the frame grid's auto rows stop
stretching (the title bar was 132px tall for a 55px header). Title-to-tabs gap now ~16px. Full suite
green (1184).
L7: T2 done (31f11237 primitives + 641c1606 page). Contexto tab: left "Instrucciones del proyecto" card
(icon + subtitle + helper + save footer), right column split into "Archivos del proyecto" and
"Conocimiento del proyecto" cards with count badges, dashed empty states and a closing note. Additive
primitives: `Card.footer`, `EmptyState` icon/action/dashed variant. Verified by headless screenshot in
the workspace. `Abrir asistente`/breadcrumb intentionally omitted. Open item: the reference shows a
"Subir archivo a la KB" button on the knowledge card; no distinct backend action exists (project files
index automatically), so it was omitted pending the owner's call.
L8 (owner decision): after review, the owner chose option **B** — a unified project-file list with a KB
state, plus a bounded backend change. Findings that drove it: `POST /kb` already accepts `project_id`
(not exposed in the UI), and `ingest_project_file` auto-indexes a supported upload, so the same
document was listed twice. `to_doc_dict` did not expose the file link. Implemented in T2c: migration
054 adds `project_files.kb_document_id` (backfilled from chunk provenance), the serializer exposes it,
and the Contexto tab now shows one files table with an "En la KB" column while the knowledge card keeps
only documents added straight to the project KB (with its own `POST /kb` upload action).
L9 (owner): "carpetas reales (con backend)". Authorized a real folder feature (S6) instead of a flat
search list, plus the delete actions and confirmation dialogs of ref image 3. Defaults chosen by the
orchestrator unless the owner objects: deleting a project file also deletes the KB document it produced;
deleting a folder is recursive and its confirmation states the file count; empty folders are allowed.
L10: T6 done (fcc54f61 + f2fd0f28). Backend folders: migration 055 (`project_folders`,
`project_files.folder_id`), folder CRUD, upload-to-folder, file delete (removes the linked KB document)
and recursive folder delete. Verified live against the isolated stack (create/list/rename/upload/
delete/404) and by `tests/integration/test_project_files.py` (9 passed) plus
`tests/functional/test_api_project_files.py` + `test_api_projects.py` (18 passed). Note: the worktree's
provisioned root-owned `.venv` and `media/` were empty and blocked the test runner; recreated them
(`uv sync` + `mkdir media`).
L11 (owner): "ok cerramos aqui. guarda memoria. dame el handoff para continuar con T7 frontend en un
nuevo chat." Session closed after T6. Next: T7 (frontend folders tree). Handoff written to
`odd/handoffs/panel-visual-alignment.md` in the primary worktree.

L12: T7 done (bb6b6a64 API client + c0268a94 tree UI). Frontend folder tree in `ProjectResources.tsx`:
search toolbar + `Subir archivo` (targets the selected folder, root by default), a project-root node,
collapsible folders with recursive file counts, file rows (type icon, name, size, `En la KB` badge,
download, delete), folder create/rename/delete via a row `⋯` menu, and a `N archivos · M carpetas`
footer. Deletes go through a confirmation `Dialog`. New `ProjectFolder` type, `folder_id` on
`ProjectFile`, and API helpers in `api.ts`. `ProjectsPage` now passes `projectName`. Reference default
the owner did not spec: folder CRUD affordances = `Menu` kebab (root → `Nueva carpeta`; row →
`Nueva subcarpeta`/`Renombrar`/`Eliminar`). Verified: `npm run build` green, full vitest suite green
(1193 passed), and standalone screenshots of `/panel/app/projects/test` match reference image 1.
Note: file rows use a type icon, not image thumbnails (the list API serves no thumbnail). RDD assess:
medium, `under_budget`, no review due.

L13 (owner, verbatim): "actual [Image 1] . aun se sigue rompiedo el layout tenemos que asegurarnos que no
se rompa el layout. el arbol de carpetas no activa slider vertical para scroll.

ref card archivos de proyecto actual [Image 2] .
- debemos crear un boton mas "..." verticales. para agrupar tanto el boton subir archivo mas un boton
  para crear carpeta.
- la primera carpeta visible es la carpeta del propio proyecto pero no es necesario. hay que dejarlo
  como raiz. no es necesario hacer colapsable o expandible la carpeta del proyecto. ya estamos ahi.
- necesitamos drag and drop aqui. para mover archivos de carpeta.
- el dialog para subir un archivo se tiene que adaptar y tiene que mostrar un boton para crear carpeta y
  tambien especificar bien en que carpeta se va a subir el archivo.

- basicamente a este arbol de archivos debe tener todo para poder manejar los archivos correctamente.

esto es desicion de dise;o general. todos lso botones mas "..." verticales. deben estar sin bacground y
sin borde. solo los ... verticales."
→ Captured as S6b/S6c and tasks T10/T11.

L14: T10 + T11 done (196ebd23 backend move + c366119d frontend). Backend:
`PATCH /panel/api/projects/{slug}/files/{file_id}` with optional `folder_id` (null = root), service
`move_project_file` + audit; verified by 2 new tests (integration + functional). Frontend: root node is a
non-collapsible project root; the toolbar `⋯` groups `Subir archivo` + `Nueva carpeta`; the upload dialog
selects the destination folder and creates folders inline; drag & drop moves a file into a folder (or
back to the root) via the new endpoint; global decision — every vertical `⋯` trigger is borderless and
backgroundless; `.btn` labels no longer wrap; resource cards keep their grid track at any width and a
wide table scrolls instead of overflowing. Verified: `npm run build` green, full vitest suite green
(1196 passed), tree scroll measured live (`scrollHeight 1356 > clientHeight 350`, `overflow-y: auto`),
screenshots at 1440 and 1024 px match the requested layout. RDD assess: medium, `under_budget`, no review
due. Note: the visible `+ Subir archivo` button is kept alongside the `⋯` menu (which also lists `Subir
archivo`); flag to the owner whether to drop the duplicate.

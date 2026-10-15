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

S4 — Skills tab (owner images 2026-10-14). Owner-authorized bounded backend addition.
Search field `Buscar habilidad por nombre o descripción…`. `Catálogo global` card with count badge +
subtitle `Habilidades globales de solo lectura.` and rows: icon tile, name, description, chips `Global` /
`Solo lectura`. `Habilidades del proyecto` card with count + subtitle `Se guardan en la configuración de
este proyecto.` + `Agregar habilidad` action, dashed empty state `Aún no hay habilidades en este
proyecto` / `Agrega una habilidad para definir instrucciones específicas.`, and the `Agregar habilidad`
card action opens a dialog with the name, description and content form (editing reuses the same dialog).
Every row expands into a read-only `Contenido de la habilidad` / `Vista de
lectura` panel that renders the skill body as markdown; a project row also carries an `...` menu
(`Editar` / `Eliminar`). Footer note `Las habilidades globales se consultan; las del proyecto se
gestionan aquí.` Existing add/edit/delete behavior preserved (whole-array PATCH via
`updateProjectConfig`). Backend addition: `GET /panel/api/skills` now returns each global skill's
declared `body` (read through `load_skill_body`; an unreadable body degrades to `null` instead of
failing the catalog).

S5 — Hilos tab, wired (ref 9).
Replace the hardcoded placeholder. List the project's chat threads via `GET
/panel/api/chat/threads?proyecto=<slug>`. Populated state (ref 9 image 1): card
`Hilos del proyecto (N)` with subtitle `Conversaciones asociadas a <name>.`, a `Nuevo
hilo` header action, a `Buscar hilo…` search, a `Más recientes` sort, a flat
`Hilo / Última actividad / Acciones` table (icon tile + title + one-line preview +
`Hoy · HH:MM` + `Abrir hilo` + a `...` rename/delete menu) and a `N hilos` / `1 de 1`
footer. Empty state uses the reference visual with the real-empty copy the owner
confirmed in L24: icon, title `Aún no hay hilos en este proyecto`, the reference copy
and CTA `Abrir historial` plus the closing note. The reference's `No
disponible` copy is kept only for the denied/error state. Backend addition
(owner-authorized in L24): the thread summary now carries `preview`, a bounded
one-line snippet of the latest message.

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

S6d — Global design decision: action feedback is a **transient toast** anchored to a screen corner
(bottom-right) that auto-dismisses; never a permanent inline banner.

S6e — Embedded Contexto tab scroll (owner feedback 2026-10-14, see L20).
Inside the assistant workspace the project page fills its row and the active tab body scrolls
vertically **as a whole** (one scrollbar for the tab; the page header and the tab bar stay fixed), so a
tall Contexto tab is never clipped past the bottom of the workspace. The standalone page keeps
scrolling with the document.

## Tasks

| ID | Spec | Route | Status | Evidence |
| --- | --- | --- | --- | --- |
| T1 shared chrome | S1 | inline | done | f194eef9 |
| T1b workspace header fixes | S1 | inline | done | ef0a9524 |
| T2 Contexto | S2 | inline | done | 641c1606 |
| T2c KB link + unified files list | S2 | inline | done | 5c9d6606, de995673 |
| T3 Agentes | S3 | inline | done | b49d066e |
| T4 Skills | S4 | inline | done | 310d1f8a, 9435dcee |
| T5 Hilos wire | S5 | inline | done | 849aa8e2, 807c8a45 |
| T6 backend project folders | S6 | inline | done | fcc54f61, f2fd0f28 |
| T7 files tree UI | S6 | inline | done | bb6b6a64, c0268a94 |
| T8 delete + confirm dialogs | S6 | inline | done | c32accd5 |
| T9 knowledge card layout | S6 | inline | done | c32accd5 |
| T10 move file endpoint + drag & drop | S6b | inline | done | 196ebd23 |
| T11 upload dialog + tree/root/toolbar revisions | S6b, S6c | inline | done | c366119d |
| T12 toast + menu stacking + tree polish | S6b, S6c, S6d | inline | done | 6b9af9b2, 43340a03 |
| T13 embedded tab scroll | S6e | inline | done | 243447e9 |
| T14 mobile tabs bar + skills layout | S1, S4, S6b | inline | done | 62faed16, adb77b9c |

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

L15 (owner, verbatim): "ok mejor. pero aun un par de cosas: - [Image 1] actual. ese destacador. hay que
sacarlo o bien hay que cambiar el color pero se ve muy mal. - actual abriendo el boton mas[Image 2] , el
boton subir archivo esta fuera deberia estar dentro. ademas el "testproyect" tapa el dialog abierto. -
actual con toast [Image 3] . aqui el toast queda para siempre. no se va nunca. importante seria quizas
tambien cambio global. redise;ar el toast. que aparezca en una equina superior o inferior derecha. y que
se autooculte."

L16: T12 done (6b9af9b2 + 43340a03). (1) Removed the folder selection highlight and the selection concept
entirely (the upload dialog owns the destination). (2) `Subir archivo` moved inside the toolbar `⋯` menu;
fixed a real stacking bug — the portal `.menu__content` had no z-index and lost to the sticky root row
(`z-index: 1`), which hid the first menu item and let the root row paint over the menu; added
`z-index: var(--z-modal)`. (3) New global `ToastProvider`/`useToast` primitive: transient notifications
anchored bottom-right, auto-dismissing (5 s), stacking, closable; mounted around the app; the tree and
knowledge action feedback now use it instead of a permanent inline banner. Added `--z-toast`. Verified:
`npm run build` green, full vitest suite green (1199 passed), live checks (menu items both present, toast
appears and is gone after 5.2 s), screenshots in `/tmp/opencode/tree-shots3/`. RDD assess: medium,
`under_budget`, no review due.

L17 (owner, verbatim): "si ahora se ve correcto. el toast abajo esta correcto igual [Image 1] . pero la
fuente no es la correcta. debe ser la fuente que utilizamos en el dise;o lumat. cerramos con esa
correccion. guarda la memoria. dame el handoff para continuar con T9 en un nuevo chat"

L18: T12 follow-up done (569921f1). The toast inherited the browser default font; set
`font-family: var(--font-ui)` (Inter) on `.toast`, matching the rest of the panel. Build green, full
suite green (1199). Session closed. Next: T9 (knowledge card, ref image 1) then T8 (KB document delete
dialog, ref image 2 right). Handoff written to `odd/handoffs/panel-visual-alignment-t9.md` in the primary
worktree.

L19 (owner): "podemos hacer t9 y t8 en un solo workunit? ... asegurate agregar tambien los sliders
verticales para scroll de cada card y no romper el layout" — T8 and T9 shipped as **one work unit**
(`c32accd5`, "feat(panel): redesign the project knowledge card and add KB document delete"), as asked.
T9: the knowledge card drops the generic `DataTable` (the overflow source) for a row list matching the
reference — subtitle `Documentos de la base de conocimiento (RAG).`, a `Buscar documento…` toolbar with
the `Subir archivo a la KB` action, rows of icon + title + `FORMAT · vN` + `Activo` badge + trash, and a
footer note plus the `N documentos` count. T8: the `Eliminar de la KB` dialog reuses the file-delete
pattern (icon + title + question + preview card with `FORMAT · vN` + badge + `Proyecto: <name>` +
`Cancelar`/red confirm) and calls the existing `deleteKbDocument`. Scroll: the document list caps at
22rem and scrolls on its own, like the file tree, so each card keeps its grid track. Verified: `npm run
build` green, full vitest suite green (1201 passed, +2 tests), no horizontal overflow at 1440/1100/900
px, and the list scroll engages (clientHeight 352 / scrollHeight 1229, `overflow-y: auto`). RDD assess:
medium, `under_budget`, no review due.

L20 (owner, verbatim): "actual. [Image 1] . Se rompe el layout hacia el bottom. se alargan tanto las cards
que desaparecen por el bottom. hay que arreglar eso. insisto que necesitamos un slider vertical para hacer
scroll. puede ser un scroll por card individual o un slider global para toda la tab contexto. me parece
que tiene mas sentido esta." → Captured as S6e and T13. Root cause: the embedded page lived in
`.assistant-workspace__thread` (a full-height track) but `.assistant-workspace` has `overflow: hidden`,
and the frame only had `align-content: start` with no scroll region, so a Contexto tab taller than the
workspace was clipped with no scrollbar. Fix (243447e9, `ProjectsPage.css` only): the embedded frame is a
flex column with `min-height: 0`; `.page-frame__content` fills the remaining row; the `.tabs` panel gets
`flex: 1 1 auto; min-height: 0; overflow-y: auto` — one vertical scrollbar for the whole tab, with the
page header and tab bar fixed. The standalone page is untouched (it scrolls with the document via
`.panel-shell__content-area { min-height: 100dvh }`). Verified live in the embedded workspace
(`/panel/app/chat?context=test`) at 1440x820 and 1280x640: `.tabs__panel` overflows and scrolls
(clientHeight 498 / scrollHeight 958 and 318 / 1106, `overflow-y: auto`, `scrollTop` responsive), no
horizontal overflow. Build green; full suite green (1200 passed + the known flaky `AgentChat > markdown
snapshot stale`, which passes in isolation 68/68). The per-card caps from L13 (`.file-tree` and
`.project-knowledge__list`, 22rem) are kept, so a very long card still scrolls internally as well as the
tab; if the owner prefers a single scroll, drop those two `max-height` rules.

L21: T3 done (b49d066e). Agentes tab redesigned: `Card` "Agentes del proyecto" with the subtitle
`Roles disponibles para trabajar con el contexto del proyecto.` and three role cards (dark circular icon
tile — `Bot`/`ShieldCheck`/`Compass` by role key — + name + role chip + description), then a separate
`Última ejecución` card (`Estado registrado de la ejecución más reciente.`) with a status pill and
timestamp. The pill maps the recorded `latest_run.status` (`completed` → `Completada`, `executing`/
`responding`/`running`/`planned` → `En curso`/`Planificada`, `approval_pending` → `Pendiente de
aprobación`, `failed`/`error` → `Fallida`, `degraded` → `Degradada`; unknown falls back to the raw
value), so it reads as a recorded state, not a live feed. Data stays data-driven: `name`, `agent.role`
and `description` come from `GET /panel/api/projects/{slug}/agents`; the icon is the only UI-owned
affordance (roles are fixed system roles). Copy note flagged to the owner: the S3 reference chips were
`Asistente del proyecto` / `Solo lectura` / `Investigación`, while the backend returns `Asistente del
proyecto` / `Verificación independiente` / `Investigación de solo lectura` — the UI renders the backend
copy, so aligning to the reference means editing the endpoint (one place), and the old standalone
`Solo lectura` badge was folded into the role chip. Verified: focused 4/4, `npm run build` green, full
suite green (1202; two load-flaky tests, `AgentChat > markdown snapshot stale` and `ClientesList >
distinguishes a filtered-empty result…`, pass in isolation 110/110); live standalone (1440) and embedded
(1440) screenshots, 3 cards, dark tile `rgb(20,60,44)`, pill `Completada` + timestamp, no horizontal
overflow. RDD assess: medium, `under_budget`, no review due.

L22 (owner): T3 approved as-is ("esta bien como esta"), then "vamos a T4. aqui estan las referencias
para skills" with two reference images. Asked whether to include the reference's expandable read view,
which needs the global skill body; the owner chose **(a)**: full T4 including the expander and the small
backend addition. Done in two atomic commits — `310d1f8a` (backend + `GlobalSkill` type + backend test)
and `9435dcee` (component + CSS + `ProjectsPage` + frontend test). Backend: `GET /panel/api/skills`
returns `body` per global skill via `load_skill_body`, degrading to `null` on `SkillError` so a missing
file never breaks the catalog. Frontend: `ProjectSkills.tsx` rewritten — full-width search
(`Buscar habilidad por nombre o descripción…`), `Catálogo global` card (count badge, subtitle, rows with
icon tile + name + description + `Global`/`Solo lectura` chips), `Habilidades del proyecto` card (count
badge, subtitle `Se guardan en la configuración de este proyecto.`, `+ Agregar habilidad`, dashed empty
state, collapsible add/edit disclosure), a page footer note, and a per-row expander rendering the body
through the shared `Markdown` component (`.markdown` styles reused). The project row gained an `...`
menu (`Editar` / `Eliminar`) replacing the old inline buttons; the old `projectId` prop (only used in
the title) was dropped. Verified: frontend focused 4/4, backend `test_api_skills.py` + `test_skills.py`
9 passed, `npm run build` green, full frontend suite green (1204); live standalone capture shows the
empty-project state matching reference image 2 and the expanded global skill matching image 1 (real body
rendered from `agent/skills/assistant/memoria-tukulpan.md`, headings `Tukulpan memory` / `Axes and
ownership` / `Tool arguments` / `Gotchas`, content scroll clientHeight 288 / scrollHeight 1242), no
horizontal overflow. RDD assess: medium, `under_budget`, no review due.

L23 (owner, verbatim): "el boton agregar habilidad y el dropdown agregar habilidad. llevan donde mismo.
simplemente sacar el dropdown de la parte de abajo y dejar solo el boton agregar habilidad en el header
del card. luego crear un modal/dialog para agregar el nuevo skill" — done (7fd3e20b). Removed the
collapsible bottom `Agregar habilidad` disclosure (and its CSS) so the card has a single action, and
moved the add/edit form into a `Dialog` opened by the header button; the row `...` → `Editar` reuses the
same dialog (`Editar habilidad`). Actions are `Cancelar` + `Guardar habilidad`. Verified: focused 5/5,
`npm run build` green, full suite green (1205); live capture confirms one header button, no bottom
disclosure, and the dialog with title `Agregar habilidad`, the three fields and both actions. RDD
assess: medium, `under_budget`, no review due.

L24 (owner, verbatim, 2026-10-14): "ambas versiones empty y poblada de la referencia 9" → provided
ref 9 (populated + empty). Two decisions were confirmed before code: (1) the empty-state copy is
adapted to a real empty project — title `Aún no hay hilos en este proyecto` with the reference
copy/CTA/note, and the reference `No disponible` copy is kept only for the denied/error state;
(2) the per-row subtitle needs a bounded backend addition — a `preview` snippet of the latest
message. T5 done (849aa8e2 backend + 807c8a45 frontend). Backend:
`to_internal_chat_thread_summary_dict` now emits `preview` (whitespace-collapsed, with the
`**`/backtick emphasis markers stripped, capped at 140 chars with an ellipsis); verified by the
preview tests in `tests/integration/test_assistant_chat.py` (2 new). Frontend: new
`ProjectThreads.tsx` replaces the placeholder — populated table (search + `Más recientes` sort by
activity/title, client pagination, `Nuevo hilo` via `createChatThread` then open, per-row
`Abrir hilo` and a `...` rename/delete menu) plus the reference empty/unavailable states. The card
reacts to its own width through a container query, so the embedded assistant column stacks the row
(activity + actions below the title) instead of breaking it. `InternalChatThreadSummary` gained
`preview`; `formatThreadActivity` was added to `threadDateGroups.ts`; `ProjectsPage` gained
`onOpenThread`/`onOpenHistory`, wired from `AppShell`, `TechnicianShell` and the embedded
`AssistantWorkspace`. Verified: focused frontend 20/20, backend preview tests green, `npm run build`
green, full vitest suite 1211 passed (the 2 known load-flaky tests pass in isolation 110/110); live
standalone (1280) and embedded (1280, ~456px column) captures match reference image 1, no horizontal
overflow, and the embedded `.tabs__panel` stays `overflow-y: auto`. RDD assess: medium, `under_budget`,
no review due. Open item flagged to the owner: the real-empty state has no `Nuevo hilo` button (it
matches ref 9's empty layout); threads are created from the assistant workspace.

L25 (owner, verbatim, 2026-10-14): "un detalle en la version mobile. ref tab contexto version mobile
actual [Image 1] , se rompe el component de tabs. cuando se abre el tab contexto este tapa parcialmente,
casi completamente los tabs. en las otras no pasa. … ref skills mobile [Image 5] , puedes mejorar la
visualizacion de la skill el card muestra la descripcion y titulo muy colapsado hay que rediseñar el
layout para que se vea bien en mobile version." Also, per the owner: the real-empty Hilos state keeps no
`Nuevo hilo` button. → Captured as T14. Root cause of the tabs bug: `.tabs` is a column flexbox and, on
mobile, the `[role="tablist"]` gets `overflow-y: hidden`, which drops its automatic minimum size to 0 — so
under the tall Contexto panel it shrank (measured 20px) and the content painted over the labels;
Hilos/Agentes/Skills have shorter panels, hence no shrink. Fix (62faed16): `flex-shrink: 0` on
`.tabs [role="tablist"]` in `primitives.css` — a shared-primitive change (risk item 3). Skills fix: a
`@media (max-width: 39.99rem)` block wraps the chips row (`__meta`) onto its own line (the copy column went
25px → 262px) and a `.project-skills__project-card` modifier stacks the wide `Agregar habilidad` action so
the title fits on one line. Verified by an independent verifier against scratch copies (current vs baseline
`2ba5bd15`): both fixes confirmed, no regression across 11 tabbed routes, no blockers; one pre-existing
advisory (the primitive's mobile tab `min-height` stops at `39.99rem`, so bars are 34px at ≥640px).
Durable regression probes added as `web/playwright/panel-mobile-layout.spec.ts` (3/3 green on the fix,
2/3 red on the baseline), carried by `adb77b9c` together with the breakpoint alignment. `npm run build`
green; full vitest suite 1213 passed. RDD assess: medium, `under_budget`, no review due.

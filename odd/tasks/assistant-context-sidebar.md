# ODD — Assistant context sidebar, aligned to the owner's reference

Feature: rebuild the assistant context sidebar (`Detalle del hilo`) so it matches the owner's final
visual reference, `Lumat UI read-only skills and capabilities.png` (three columns: `01 · Elegir
proyecto`, `02 · Recursos del proyecto`, `03 · Capacidades`).
Branch `odd/assistant-context-sidebar`, worktree `../lumat-agent-odd-assistant-context-sidebar`.
Scope is the assistant **sidebar only** (owner decision, L2). Surface: `web/src/components/pages/
AssistantWorkspace.tsx` (`ThreadContextSections`, `ContextSection`) and `ProjectResourcesPanel.tsx`.

## Specs

S1 — The reference is the target for the whole sidebar, in its three states. Owner, verbatim (L1):
"ok esta es la referencia final. para mejorar. principalmente mejorar el selector de proectos del
menu proyectos, mejorar el ui/ux del menu recursos del proyecto. y todo los demas menues ajustarlos
a la referencia". "Los demás menús" means every section of this sidebar, not other panel pages.

S2 — **Project section** (`01 · Elegir proyecto`). Header row: folder icon, `Proyecto`, chevron.
Inside: a trigger showing folder icon + current project name + chevron; activating it opens a panel
with a search field (`Buscar proyecto…`), then the project list — folder icon + name per row, the
current one tinted and ending in a check. Below the list, the hint `El proyecto define el contexto
de este hilo.`. With no project selected the trigger and the list show `General / Sin proyecto`, and
the collapsed `Recursos del proyecto` row reads `Selecciona un proyecto para ver sus recursos.`.
Whether `General / Sin proyecto` is a selectable row that detaches the project, or only the rendered
value of "no project", is decided against the existing API contract in T2 and recorded in the Log —
no new backend behaviour.

S3 — **Section rows**, every one of them (icon, title, count, chevron, subtitle, summary as in the
reference): leading icon, title, optional count pill, optional lock glyph when the content is
read-only, chevron at the right (pointing right when collapsed, down when expanded), and a
one-line secondary text under the title: the section's own subtitle when expanded (`Documentos
compartidos del proyecto`, `Información que el asistente puede consultar`, `Skills disponibles · Solo
lectura`, `Los adjuntos y resultados pertenecen a este hilo.`) or its summary/empty copy when
collapsed (`4 archivos · 3 documentos · 2 habilidades`, `Aquí aparecerán los archivos generados.`).
Counts are neutral, never tones of success/danger. Disclosure keeps `aria-expanded` + `aria-controls`.

S4 — **Section order**, top to bottom, per the reference: `Proyecto`, `Recursos del proyecto`,
`Archivos del hilo`, `Artefactos del hilo`, `Capacidades del asistente`. Capacidades moves to the
end (today it sits third, `AssistantWorkspace.tsx:697-733`). Existing persisted expansion state
(`contextSections`) keeps working, and its defaults stay as shipped (`Proyecto` open, the rest
closed) — the reference itself shows `Recursos del proyecto` both open (column `02`) and closed
(column `01`), so no default is changed.

S5 — **Recursos del proyecto** (`02`) holds three cards, in this order, each with its own header
(count pill) and subtitle:
  1. `Archivos [N]` — `Documentos compartidos del proyecto`; a `Subir archivo` button plus a compact
     icon button for folder creation; then the tree: folders with disclosure chevron and their count,
     files with type icon and name, every row reachable and every file row carrying the `⋮` menu.
     Dropping onto a folder row targets that folder; dropping on the tree card targets the root.
  2. `Conocimiento [N]` + lock — `Información que el asistente puede consultar`; a row reading
     `N documentos disponibles` that opens the KB detail, and `Solo lectura` aligned at the right.
  3. `Habilidades [N]` — `Skills disponibles · Solo lectura`; one row per skill: sparkle icon, name,
     and a right-aligned `Global` or `Proyecto` badge. Read-only, no toggles.
  This is the standing owner decision already recorded in `odd/tasks/assistant-panel-frontend.md` L9
  ("los archivos del proyecto debe ser completo. crear carpetas, subir archivos…  los checkboxes se
  eliminan…  lo de la kb puede quedar como solo lectura en el sidebar menu"), restated as layout.

S6 — **Thread files and artifacts** cards. Each row: the file-type glyph in a tinted tile, the
filename, a meta line (`PNG · Adjunto a este hilo` for attachments, `PNG · Generado en este hilo`
for artifacts), and the `⋮` menu at the right (`Abrir` / `Descargar`). Artifacts empty state keeps
the copy `Aquí aparecerán los archivos generados.`; attachments keep `Aún no hay archivos adjuntos.`.

S7 — **Capacidades del asistente** is last and, expanded, shows a nested read-only card with two
rows: `Herramientas` + `N herramientas disponibles`, and `Base de conocimiento` + a dot and
`Disponible` / `No disponible`; the panel footer reads `Información de solo lectura.`. The existing
loading, error and no-data states stay (`StateMessage`), never a fabricated count.

S8 — **Design system compliance** (`web/DESIGN_SYSTEM.md`): reuse shipped primitives — `Popover`
(native popover API: top layer, Escape, focus return) for the project panel, `SearchInput` for the
search field, `Menu` for the `⋮` menus, `Icon`, `Badge`, `Dialog`, `StateMessage`. Semantic tokens
only: no raw hex and no magic spacing in component CSS (token guards). Controls keep the 40px minimum
height. Destructive folder deletion goes through `Dialog` naming the folder — the current
`window.confirm` at `ProjectResourcesPanel.tsx:55` goes away. Product copy is neutral Chilean
Spanish, never voseo.

S9 — **States**: the resources panel shows a loading state while it fetches (today it renders an
empty tree and fills in later) and an error state, both through `StateMessage`. Empty content inside a
card (no files, no documents, no skills) is a quiet muted line, not a `StateMessage` banner: an empty
card is routine information, and a tinted alert box for it shouted louder than the data. Icons use the
`Icon` primitive with `sm`/`md` scale; fixed lucide `size={14|15}` props are removed
(`ProjectResourcesPanel.tsx:65-79`).

S10 — **Mobile**: the same sections render in the thread-detail sheet (`mobile` variant of
`ThreadContextSections`); no fixed pixel widths, no hover-only affordance. Every action reachable by
touch, and the section rows keep 44px targets.

S11 — **Selected project, closer to the reference.** The owner's crop of the reference shows the
selected project as a tall, quiet field: the folder glyph at `md` scale, the project name reading as the
value, generous padding, a hairline border on a light surface, and the chevron at the far right. The
current trigger is smaller and plainer than that (owner: "el formato de como se muestra el proyecto
seleccionado se ve muy sencillo"). The collapsed `Proyecto` row keeps its summary line.

S12 — **Upload destination.** Today every upload lands in the root because the UI always sends
`folder_id: null` (`ProjectResourcesPanel.tsx`), even though `POST /projects/{slug}/files` accepts a
folder. The owner must be able to choose the folder a file goes into: each folder row offers `Subir
aquí`, the card header keeps `Subir archivo` for the root, and dropping OS files anywhere on the
Archivos card uploads to the root. Owner, verbatim: "no se puede seleccionar a que carpeta se sube el
archivo" and "tampoco se pueden subir archivos arrastrandolos directamente al menu recursos del
proyecto".

S13 — **Move files between folders by dragging** (owner: "tampoco esta el drag and drop para mover
archivos entre el worktree"). Dragging a file row onto a folder row moves that file into the folder;
dragging it onto the card's root area moves it back to the root. The backend already supports it:
`PATCH /projects/{slug}/files/{file_id}` with `FileMoveBody{folder_id}`. A drop of OS files and a drop
of a tree file must never be confused: the tree drag carries its own payload type.

S14 — **Drag from the sidebar into the chat** (owner definition, verbatim): "los archivos disponibles
en los menus del sidebar derecho. deben ser drag and drop para el chat del hilo. o sea el usuario puede
referenciar y cargar estos archivos al contexto cuando lo considere necesario. esto seria para: los
archivos del proyecto. archivos del hilo, artefactos del hilo". Project files attach to the thread
through the existing `application/x-lumat-project-file` payload and
`POST /chat/threads/{id}/attachments/from-project`. Thread files and artifacts are already thread
context and have no attach endpoint, so dropping one adds a **reference chip** to the message being
written (owner's choice on 2026-10-30: "Ficha de referencia en el compositor"); the reference is
visible in the sent message and can be removed before sending. No new backend behaviour.

## Tasks

T1 — DONE (`c694b8be`). Section shell per reference: `ContextSection` gains subtitle/summary/lock,
keeps disclosure semantics, and the order changes to S4. S3, S4. `AssistantWorkspace.tsx`,
`AssistantWorkspace.css`, `AssistantWorkspace.test.tsx`. 36/36 focused tests, `npm run build` clean.
T2 — DONE (`dac68d15`). Project picker: Popover + SearchInput + tinted selected row with check + hint
copy, and a locked variant for a thread that already has messages. S2, S8. `AssistantWorkspace.tsx`,
`AssistantWorkspace.css`, `AssistantWorkspace.test.tsx`. 38/38 focused tests, build clean.
T3 — DONE (`e1ca2b92`). Recursos del proyecto as three cards (Archivos / Conocimiento / Habilidades)
with the file `⋮` menu, named `Dialog`s for folder creation and deletion, `Icon` scale, the loading
state and the count summary. S5, S8, S9. `ProjectResourcesPanel.tsx`, `AssistantWorkspace.css`,
`AssistantWorkspace.test.tsx`. 40/40 focused tests, `tsc -b` clean.
T4 — DONE (`30c72997`, `dfd8ff6f`). Thread files, thread artifacts and capabilities cards per
reference, with the resources summary wired into the collapsed row. S6, S7.
`AssistantWorkspace.tsx`, `AssistantWorkspace.css`, `AssistantWorkspace.test.tsx` (plus the
capabilities copy assertions in `AgentChat.test.tsx`). 41/41 focused, 121/121 with AgentChat.
T5 — DONE (this commit). Verification and close. Evidence, all measured on this worktree:
`npx vitest run` → **118 files / 1357 tests, exit 0** (2 min 39 s, machine load ~4);
`npm run build` (`tsc -b` + `vite build`) → exit 0; rendered comparison against the reference through
a worktree Vite on `:5175` with a real login, at 1440px and 390px, including the mobile sheet — see L8
for the four defects that pass found. No Storybook story: this page has none today and the workspace
needs a mock harness its `stories/pages/_shared/mockData` does not provide, so the rendered captures
are the state-matrix evidence instead. A throwaway debug test that slipped into `dac68d15` is removed
in `dfd8ff6f`.

Slice boundary: 896 authored lines over 9 commits, past the ~400-line review slice. Per the owner's
standing decision recorded in `odd/tasks/assistant-panel-frontend.md` L10 — slices land as commits and
the PR opens when the assistant frontend is complete — the boundary is recorded here instead of
opening a PR mid-feature.

T6/T7 — DONE (`6a67a19d`). Project trigger presentation per the reference crop, the upload destination
(`Subir aquí` per folder, root upload from the card header, OS-file drops anywhere on the Archivos
card), and moving a file between folders by dragging its row. S11, S12, S13. `ProjectResourcesPanel.tsx`, `AssistantWorkspace.tsx`, `AssistantWorkspace.css`, tests. Commit
`feat(assistant): …`.
T7 — Move project files between folders by dragging a file row onto a folder row or the card root, via
`PATCH /projects/{slug}/files/{file_id}`. S13. `ProjectResourcesPanel.tsx`, `api.ts`,
`AssistantWorkspace.test.tsx`. Commit `feat(assistant): …`.
T8 — DONE (this commit). Reference chips: dragging a thread file or an artifact from the sidebar into the
composer adds a reference to the message being written, removable before sending and visible in the
sent text as `Referencia: <archivo>`. Rendered evidence: the chip, the folder menu with `Subir aquí`,
and a synthetic drop in a real browser.
`AgentChat.tsx`, `AssistantWorkspace.tsx`, `AssistantWorkspace.css`, tests. Commit
`feat(assistant): …`.

## Log

L1 — Owner request that opened this feature (verbatim), with the reference image attached
(`/home/stefan/Downloads/Lumat UI read-only skills and capabilities.png`):
"ok esta es la referencia final. para mejorar. principalmente mejorar el selector de proectos del
menu proyectos, mejorar el ui/ux del menu recursos del proyecto. y todo los demas menues ajustarlos
a la referencia"

L2 — Owner answered the scope question with "Sólo el sidebar del Asistente": the project selector in
`ProjectsPage` (the assistant's `Proyectos` tab), the mobile header picker and the `Cambiar` action
of the thread-detail sheet are **out of scope** for this feature. Also authorized the worktree
(`rapso worktree create assistant-context-sidebar --yes`).

L3 — Entry state measured, not assumed: `main` = `ac5822d1`, clean except an unrelated untracked
`odd/handoffs/chatbot-agenda-config-fuente.md`. Production still serves `v2026.10.13` (`5ec2573e`),
so the assistant frontend from `d9c1d43f` (PR #748) is in `main` but not deployed; the dev stack
(Vite `:5173` on `main`'s code, API `:8000`) is the review surface. The reference therefore has to be
compared against the dev stack, never against production.

L4 — Prior art read before touching the sidebar: `odd/tasks/asistente-side-menus.md` (single
`Contexto` tab, collapsible rows with icon/title/count/chevron, "Actividad" removed and its loss
accepted) and `odd/tasks/assistant-panel-frontend.md` (S1–S7, L7 counts hidden messages, L9 the
owner's resource-panel decision, L12 the checkboxes removed in favour of dragging into the chat).
This feature restyles and restructures; it does not reopen any of those decisions.

L5 — Two readings of the reference settled in T1, both recorded because the reference is a picture:
(1) the secondary line under a section title is the **subtitle while open** and the **summary or
empty copy while closed**, one line at a time, rendered as a sibling of the disclosure button so the
button's accessible name stays the bare title (`AssistantWorkspace.test.tsx` pins the exact name
`Proyecto`); (2) for `Archivos del hilo` the same sentence is passed as both subtitle and summary,
because the reference shows it whether the section is open or closed. T1 also removed the old
bottom-of-panel note and moved its sentence into that section's secondary line.

L6 — Measured before writing T3, because the reference shows `Global` and `Proyecto` skill badges:
`app/services/thread_resources.py:41` returns skills as `{name, description}` built from
`config.skills`, so every skill the endpoint lists is project scope. The `Proyecto` badge is real; a
`Global` badge would be invented, so it is not rendered and the reference's split waits for a backend
change (out of scope: this feature adds no backend behaviour). T3 also moves folder creation from the
always-visible "Nueva carpeta" input into a `Dialog`, because the reference shows a compact action in
the card header rather than a bare input in the middle of the tree.

L7 — The T3 worker stopped before editing because the worktree's `graphify-out/GRAPH_REPORT.md` was
built from an older commit than `HEAD`, and the project rule says to rebuild a stale graph first.
Resolved without a refresh, because two project facts override it: `graphify-out/` is gitignored and
local to whichever worktree holds it (the canonical graph is the main worktree's, which is where the
mandatory queries ran for this feature), and AGENTS.md schedules `graphify . --update` **once per work
session, at close — never after every batch or commit**. The consultations that satisfy the gate for
this feature are recorded here: `graphify query "assistant workspace sidebar sections project picker
resources"` (nodes `AssistantWorkspace.tsx`, `ProjectResources.tsx`, `Icon.tsx`, `Badge.tsx`,
`StateMessage.tsx`, `Button.tsx`, `api.ts`, `services/projects.py`, `assistantTabs.ts`) plus the
worker's own `graphify query "AssistantWorkspace"`. The graph refresh stays on the session-close list.

L8 — The rendered result was verified, not assumed. A second Vite (`:5175`) serving this worktree's own
code was started against the dev API, and a throwaway Playwright script logged in through
`POST /panel/api/login` and captured the context pane at 1440px, the open project picker, the collapsed
sections, 390px mobile, and the mobile sheet with its loading state. The screenshots are in
`/tmp/assistant-shots` and the script was deleted; nothing was added to the repository. Four defects
that no test caught came out of that pass and are fixed: (1) the project popover panel is 22rem wide in
the primitive and overflowed the pane, so the picker scopes it to `min(19rem, …)`; (2) empty cards
rendered a full `StateMessage` alert box, replaced by a muted line (S9 now says so); (3) the Archivos
card nested a dashed drop box inside the card, removed — the card is the root drop target; (4) the
Conocimiento card said `Solo lectura` twice and printed `0 documentos disponibles` next to `Sin
documentos disponibles`, so the count row only renders when there are documents. The mobile sheet
renders the same sections and showed the loading state, which is the S10 evidence.

L9 — Owner review of the implemented sidebar (verbatim):
"ok referencias cortaS:\n\n- menu proyecto.:\nes ok. cuando esta cerrado se ve asi: [captura], el
formato de como se muestra el proyecto seleccionado se ve muy sencillo en la referencia se ve asi:
[captura]\n\n- menu Recursos del proyecto:\n\nanda bastante bien. se pueden subir archivos y crear
carpetas. sin embargo. no se puede seleccionar a que carpeta se sube el archivo. \ntampoco esta el
drag and drop para mover archivos entre el worktree\ntampoco se pueden subir archivos arrastrandolos
directamente al menu recursos del proyecto.\n\n---\n\n 1. Arrastrar attachments del hilo al chat —
falta definir qué significa. significa eso. que los archivos disponibles en los menus del sidebar
derecho. deben ser drag and drop para el chat del hilo. o sea el usuario puede referenciar y cargar
estos archivos al contexto cuando lo considere necesario. tiene sentido? esto seria para: los
archivos del proyecto. archivos del hilo, artefactos del hilo. \n\nel resto esta bien."
This reopens nothing: T1-T5 stay done, and S11-S14 plus T6-T8 are added above.

L10 — Scope check before writing (measured in the backend, not assumed): B, C and D need no backend.
`POST /projects/{slug}/files` already accepts a folder, `PATCH /projects/{slug}/files/{file_id}` takes
`FileMoveBody{folder_id}` (`app/panel/api/routes/project_files.py:94-107`), and the chat already
handles `application/x-lumat-project-file` (`AgentChat.tsx:909-929`). `PATCH
/projects/{slug}/folders/{folder_id}` also renames folders, which the owner did not ask for and this
feature does not add.

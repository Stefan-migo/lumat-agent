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
empty tree and fills in later), plus empty, filtered-empty and error states via `StateMessage`. Icons
use the `Icon` primitive with `sm`/`md` scale; fixed lucide `size={14|15}` props are removed
(`ProjectResourcesPanel.tsx:65-79`).

S10 — **Mobile**: the same sections render in the thread-detail sheet (`mobile` variant of
`ThreadContextSections`); no fixed pixel widths, no hover-only affordance. Every action reachable by
touch, and the section rows keep 44px targets.

## Tasks

T1 — Section shell per reference: `ContextSection` gains subtitle/summary/lock, keeps disclosure
semantics, and the section order changes to S4. S3, S4. `AssistantWorkspace.tsx`,
`AssistantWorkspace.css`, `AssistantWorkspace.test.tsx`. Commit `refactor(assistant): …`.
T2 — Project picker: Popover + SearchInput + tinted selected row with check + hint copy. S2, S8.
`AssistantWorkspace.tsx`, `AssistantWorkspace.css`, `AssistantWorkspace.test.tsx`. Commit
`feat(assistant): …`.
T3 — Recursos del proyecto as three cards (Archivos / Conocimiento / Habilidades) with the `⋮` file
menu, `Dialog` confirmation, `Icon` scale and the loading state. S5, S8, S9.
`ProjectResourcesPanel.tsx`, `AssistantWorkspace.css`, `ProjectResourcesPanel.test.tsx`. Commit
`feat(assistant): …`.
T4 — Thread files, thread artifacts and capabilities cards per reference. S6, S7.
`AssistantWorkspace.tsx`, `AssistantWorkspace.css`, `AssistantWorkspace.test.tsx`. Commit
`feat(assistant): …`.
T5 — Verification and close: focused suites, `npm run build`, `npm test`, Storybook story, mobile
sweep, and the rendered comparison against the reference. S8, S10. Commit `test(assistant): …`.

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

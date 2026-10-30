# ODD — Assistant file viewer

Feature: open a file from the assistant context sidebar and read it **inside the panel**, with a real
preview per format, instead of forcing a download. Branch `odd/assistant-file-viewer`, worktree
`../lumat-agent-odd-assistant-file-viewer`. Frontend only: the content endpoints already exist.

## Specs

S1 — Owner request, verbatim (L1): "capacidad para ver archivos dentro el panel. o sea que los archivos
md se puedan renderizar y mostrar en un formato md preview. lo mismo con pdfs, htmls, etc. O sea
capacidad para abrir archivos en el panel mismo en multiples formatos." The owner then chose, on
2026-10-30: formats **md, txt, pdf, images, html, csv and xlsx**; surface **`Dialog` in the panel**, not
a route.

S2 — **Entry points**: every file row in the assistant context sidebar opens the viewer — project files
(`ProjectResourcesPanel`), thread files and thread artifacts (`ThreadContextSections`). Each row's `⋮`
offers `Abrir` as the primary action and keeps `Descargar`. Today a thread file opens a new tab and an
artifact downloads on click; both now open the viewer, and download stays one menu item away.

S3 — **Rendering per format**, decided by extension first and content type second:
- `.md` / `.markdown` → rendered markdown, same stack as the chat (`react-markdown` + `remark-gfm`).
- `.txt`, `.log`, `.json`, `.yaml` and other text → monospace block, no wrapping surprises.
- `.csv` / `.tsv` → a real table with a small in-house parser (no dependency); header row from the first
  record; horizontal scroll instead of squeezed columns.
- `.pdf` → the browser's own PDF viewer in an `iframe`; the file never enters memory as text.
- images (`png`, `jpg`, `jpeg`, `gif`, `webp`, `svg`) → `img` with `alt` = filename.
- `.html` / `.htm` → an `iframe` with a **restrictive `sandbox`** so no script can run; never
  `dangerouslySetInnerHTML`.
- anything else, including `.xlsx` (see S4) → an honest "no hay vista previa para este formato" message
  plus the download action.

S4 — **xlsx**: a spreadsheet preview needs a parser and this tree has none (`package.json` carries no
`xlsx`/`exceljs`). Adding one is a dependency decision for the owner, so this slice ships the honest
fallback from S3 rather than a silent gap or an unapproved dependency. If the owner approves a parser,
it lands as its own follow-up with its own review.

S5 — **Accessibility and states**: the viewer uses the `Dialog` primitive (focus trap, Escape, focus
restore) with the filename as the title. It covers loading (while text is fetched), error (fetch failed:
message plus download), and unsupported. Nothing autoplays.

S6 — **Security**: fetched text is rendered through React or the markdown component, never as raw HTML;
html previews are sandboxed with no permissions; a cross-origin or redirect response never reaches an
inline frame without the sandbox attribute.

S7 — **Design system**: `Dialog` primitive, semantic tokens only (no raw hex, no magic spacing), controls
keep the 40px minimum height, product copy in neutral Chilean Spanish.

## Tasks

T1 — DONE (`737c5477`). `FileViewer` component: extension-first format detection, per-format rendering,
loading/error/unsupported states, and an in-house RFC-4180 reader for delimited files.
`FileViewer.tsx` (+ `FileViewer.css`, + `FileViewer.test.tsx`, 10 tests). S3, S5, S6, S7.
T2 — DONE. The three row families open it and every `⋮` offers `Abrir`; thread files and artifacts now
open the viewer instead of a new tab / a download, and download moved one menu item away. S2.
`AssistantWorkspace.tsx`, `ProjectResourcesPanel.tsx`, `api.ts` (`assistantArtifactContentUrl`,
`projectFileContentUrl`), both test files. `AssistantWorkspace` stays at 42 tests.
T3 — DONE. Verification, all measured on this worktree: focused `FileViewer` 10/10 and
`AssistantWorkspace` 42/42; full `npx vitest run` **118 files / 1368 tests, exit 0**; `npm run build`
(`tsc -b` + `vite build`) exit 0; and a rendered capture of the markdown preview in Chrome against a
Vite of this worktree (`:5176`), showing headings, bold, inline code and a GFM table read from the real
file. xlsx keeps the S4 fallback.

## Log

L1 — Owner request that opened this feature (verbatim): "- capacidad para ver archivos dentro el panel.
o sea que los archivos md se puedan renderizar y mostrar en un formato md preview. lo mismo con pdfs,
htmls, etc. O sea capacidad para abrir archivos en el panel mismo en multiples formatos." It arrived
together with the artifact-revision request; that one is a separate feature and is not touched here.

L2 — Decisions taken by the owner on 2026-10-30 through the option picker: formats "md + txt + pdf",
"Sumar imagenes y html sandbox" and "Sumar csv y xlsx como tabla"; surface "Dialog en el panel
(recomendado)"; and a new worktree for this feature ("Worktree nuevo para el visor, versionado
despues"), which is this one.

L3 — Measured starting point: the three content endpoints already exist and are cookie-authenticated
same-origin, so the viewer needs no backend work — `/panel/api/projects/{slug}/files/{id}/download`,
`threadAttachmentContentUrl(threadId, attachmentId)` (`api.ts:385`), and
`/panel/api/chat/threads/{id}/artifacts/{id}/download` (`api.ts:376`). `react-markdown` and `remark-gfm`
are already dependencies because the chat renders with them.

L4 — Branch shape, decided when the first commit turned out to be built on `main`: the sidebar rows this
viewer wires into only exist on `odd/assistant-context-sidebar`, which is not merged. The viewer commit
was therefore cherry-picked onto `odd/assistant-file-viewer-stacked`, branching from that feature's tip
(`5da6065c`), so the stack reads `main → odd/assistant-context-sidebar → odd/assistant-file-viewer-stacked`.
The main-based `odd/assistant-file-viewer` branch is left as an unreferenced first attempt; it holds no
work the stacked branch lacks.

L5 — Behaviour changes worth naming, because they rewrite what the previous feature pinned: a thread file
and an artifact row used to open a new tab and download respectively; both now open the viewer, and the
download lives in the row menu. The two assertions that pinned the old roles were updated with a comment
that says why. The attachment row stopped being an anchor, which also removes the risk of a nested
interactive element inside a draggable row.

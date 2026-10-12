# asistente-side-menus

Feature id: `asistente-side-menus`
Branch: `odd/asistente-side-menus`
Worktree: `/home/stefan/repos/lumat-agent-odd-asistente-side-menus` (base `origin/main` `f0fbd103`, PR #562 merged)
Created: 2026-10-11

## Objective

Redesign the **right side menu** of the Asistente Lumat panel — the thread detail
panel (`<aside id="assistant-workspace-context">` in
`web/src/components/pages/AssistantWorkspace.tsx`) — to match the owner's visual
reference, and **ship it with a single "Contexto" tab** (the "Actividad" tab is
removed).

A later slice will cover the **left side menu**; it is out of scope here.

## Decisions taken by the owner

- Keep only the **Contexto** tab. Remove the **Actividad** tab from the panel,
  including its content ("Agentes del proyecto" + "Actividad del agente") and its
  tests. The loss of that view is explicitly accepted.

## Visual reference — target layout (top to bottom)

1. **Header**
   - Left: decorative panel icon (`PanelRight`) + title **"Detalle del hilo"**
     (bold), with a muted **subtitle = the active thread's title** (fallback
     `"Sin título"`) below it.
   - Right: the existing close/toggle control (`X` when open). Keep the current
     collapse/expand behaviour: collapsed = the 3.5rem rail with the `PanelRight`
     button; expanded = the full panel.
2. **Tab strip**: a single tab **"Contexto"** active, with the accent underline.
   Reuse the `Tabs` primitive with a one-item list so re-adding "Actividad" later
   is trivial.
3. **Contexto sections** — a vertical list of collapsible rows. Each row:
   **leading icon**, **title**, optional **count badge**, and a **chevron** at the
   right (points right when collapsed, down when expanded). Rows, in order:
   - **Proyecto** (`Folder`) — expanded by default. Inner box: folder icon +
     project name + status badge (existing `projectStatusLabel` /
     `projectStatusTone`) + purpose. No active project → the current empty state.
   - **Recursos del proyecto** (`Share2` / `Network`) — no count. Inner box:
     `Selección de recursos aún no disponible.` (honest placeholder — no backend).
   - **Capacidades del asistente** (`BrainCircuit`) — when capabilities exist show
     `N herramientas disponibles` + `Base de conocimientos: Disponible|No
     disponible`; otherwise the count badge reads **`Sin datos`** and the inner
     box reads `Sin información disponible.`
   - **Archivos del hilo** (`Paperclip`) — count = `attachments.length`.
     Empty → dashed inner box: paperclip + `Aún no hay archivos adjuntos.`
     With items → rows: file-type icon + filename + meta line (`PDF · Adjunto`) +
     an action button.
   - **Artefactos del hilo** (`FileText`) — count = `artifacts.length`.
     Rows: icon + filename + meta `Generado en este hilo` + **download** button
     (reuse the existing `downloadArtifact` handler incl. its busy/error states).
   - **Fuentes del hilo** (`Link`) — count = 0 today (no data). Inner box
     placeholder as today. (Future rows would be doc/web source rows + open
     button.)
4. **Footer note**: info icon + `Los adjuntos y resultados pertenecen a este hilo.`

File-type icons get a tone colour from existing tokens (`--danger` for PDF,
`--success` for spreadsheet/CSV, `--info`/`--corp-accent` for document/markdown,
neutral otherwise). Reuse `web/src/components/pages/assistantFileIcon.ts` for icon
selection — do not duplicate the mapping.

## Constraints

- **Do not regress `Settings`.** The shared `Accordion` primitive and
  `primitives.css` are used by Configuración. The reference row (icon-left,
  chevron-right, optional count) does not match the existing `Accordion`
  (chevron-left, mandatory count), so implement the row as a small local
  component in the page — or a new dedicated primitive if you judge it will be
  reused — but never by altering Settings' accordion look.
- Keep the panel collapse/expand behaviour and aria wiring working
  (`aria-controls`, `aria-expanded`, the `≤64rem` scrim).
- All new UI copy in **neutral Chilean Spanish**, matching the rest of the panel.
- Reuse existing primitives and tokens. **No new dependencies.**
- Update every test that asserts the removed Actividad tab.

## Dead code removed together with the tab

Removing the Actividad tab leaves these `AssistantWorkspace` props unused
(`tsconfig.json` sets `noUnusedLocals` + `noUnusedParameters`): `evidence`,
`plan`, `lifecycle`, `processing`.

- Remove them from the `AssistantWorkspace` signature.
- Remove them from the `<AssistantWorkspace>` call site in
  `web/src/components/pages/AgentChat.tsx` (~lines 843-846).
- In `AgentChat.tsx`, `activityEvidence` (~811) and `persistedActivity` (~806-810)
  become dead → remove them.
- `plan` and `evidence` **state** in `AgentChat.tsx` stay: they are used elsewhere
  (~927 and ~934). Do not remove them.

## Work units (one commit each, Conventional Commits, no AI attribution)

- **WU1** `refactor(assistant): drop the thread activity tab and its unused props`
  — `AssistantWorkspace.tsx`, `AgentChat.tsx`, `AssistantWorkspace.test.tsx`.
- **WU2** `feat(assistant): redesign the thread detail panel (Contexto)`
  — `AssistantWorkspace.tsx`, `AssistantWorkspace.css`, tests (and the local
  section component if extracted).

## Route

- **Delegated direct** — one writer (subagent) for both work units. Trigger:
  the write touches ≥2 non-trivial files (`AssistantWorkspace.tsx`, its CSS, the
  tests, `AgentChat.tsx`).

## Acceptance criteria

- The panel shows a single "Contexto" tab; no "Actividad" tab remains anywhere.
- The header reads "Detalle del hilo" with the thread-title subtitle.
- The six sections render as collapsible rows with icons, chevrons, and counts
  where applicable, and expand/collapse on click with correct a11y.
- Empty states and placeholders stay honest (no fabricated data).
- The footer note is present.
- No regression in the left pane, thread tabs, composer, or Settings.

## Checks (run from `web/`)

- `npx tsc -b --force --noEmit`
- `npx vitest run --no-file-parallelism`
- `npm run build`

## Notes / environment

- Graph `graphify-out/` is **stale** (built from `576b07ef`, HEAD is `f0fbd103`);
  refresh with `graphify <root> --update` once at session close, not per commit.
- Dev stack for this worktree: API `:8001`, db `:5433`, Vite `:5174`
  (`VITE_API_TARGET=http://localhost:8001`). The isolated DB starts empty; the
  owner will do the visual pass.

## Progress / Evidence — slice 1 (2026-10-11)

- **WU1** `a2c58ed5` — `refactor(assistant): drop the thread activity tab and its unused props`
- **WU2** `ec19f36b` — `feat(assistant): redesign the thread detail panel (Contexto)`
- **Task doc** `cde71155` — this file.
- **Checks** (from `web/`, observed):
  - `npx tsc -b --force --noEmit` → passed (parent re-ran it: clean).
  - `npx vitest run --no-file-parallelism` → 105 files / 1,142 tests passed
    (writer); parent re-ran the targeted file → 16/16 passed.
  - `npm run build` → passed (only the pre-existing >500 kB chunk warning).
- **RDD**: mode `on` (global). `review assess --base-ref origin/main
  --committed-only` → risk `medium`, `changed_lines` 274, `review_due: false`
  (`under_budget`) → **no native review due for this slice**.
- **Open findings (non-blocking)**: `fileTone()` duplicates the extension mapping
  already in `assistantFileIcon.ts`; `ContextSection` types its icon prop as
  `typeof Folder` instead of `LucideIcon`; one test reaches into the DOM via
  `document.querySelector`.
- **Pending**: owner's visual pass; `graphify --update` at session close (a
  mid-session incremental update was run by the writer but did not regenerate
  `GRAPH_REPORT.md`).

## Slice 2 — owner feedback after the visual pass (2026-10-11)

### S2-1 — Header: a single borderless toggle

Remove the decorative accent icon that sits before "Detalle del hilo". The ONLY
collapse/expand control is the button on the right, at the title's height, using
the **`PanelRight`** glyph **always**, black (`var(--corp-text)`), with **no
background and no border**. Do NOT touch the left pane's toggle styling (it
shares the `.assistant-workspace__pane-toggle` class — scope the change to the
context pane).

### S2-2 — Sections never expand (BUG, verified in a real browser)

Root cause: `ContextSection` defaults `expanded` to `false` and the parent only
passes `expanded` for `project`. Clicking the others calls `toggleContextSection`
and updates `contextSections`, but no section reads that value → `aria-expanded`
stays `false` forever. Verified with Playwright: clicking "Recursos del proyecto"
leaves `aria-expanded="false"` and the panel content hidden.

Fix: pass `expanded={contextSections[id] ?? false}` for every section (the
initial state already carries `project: true`). Strengthen the test to assert the
panel is actually **visible** after the click (`toBeVisible`) — the current
assertion only checked the text existed in the DOM, which is why a hidden panel
passed.

### S2-3 — The chatbox project selector is the source of truth

Today the right panel's Proyecto section follows the LEFT sidebar:
`activeProjectSlug = route.get("proyecto") || selectedProject`, where
`selectedProject` is the folder expanded on the left. Expanding a left folder
repaints the right panel while the chat's project (the composer's "Proyecto"
popover, i.e. `thread.proyecto`) stays put — the discrepancy the owner reported.

Decision: the composer's project selector wins. The left pane is navigation only;
expanding a folder must NOT select the project. Only "start conversation" selects
it (by creating/using a thread in that project).

Fix: derive the panel's project from the active thread. Add
`activeProjectSlug?: string` to `AssistantWorkspace` and pass
`thread?.proyecto ?? undefined` from `AgentChat`. Drop `|| selectedProject`.
Rename `selectedProject` → `expandedProjectSlug` so left-pane expansion state can
never be mistaken for the current project again.

### Slice 2 acceptance criteria

- Clicking any section row expands it (`aria-expanded="true"`, content visible);
  clicking again collapses it.
- The context header has exactly ONE button: the `PanelRight` glyph, dark, no
  background/border; it toggles the panel open/closed.
- Expanding a left project folder does NOT change the right panel's project;
  changing the project in the composer DOES.
- The left pane toggle, the rest of the panel, and Settings are unchanged.

### Slice 2 work units

- **WU3** `fix(assistant): expand context sections on click`
  — `AssistantWorkspace.tsx`, `AssistantWorkspace.test.tsx`.
- **WU4** `fix(assistant): source the context panel project from the active thread`
  — `AssistantWorkspace.tsx`, `AgentChat.tsx`, `AssistantWorkspace.test.tsx`.
- **WU5** `fix(assistant): single borderless toggle in the context panel header`
  — `AssistantWorkspace.tsx`, `AssistantWorkspace.css`, `AssistantWorkspace.test.tsx`.

Checks: the same three as slice 1 (`tsc -b --force --noEmit`,
`vitest run --no-file-parallelism`, `npm run build`), from `web/`.

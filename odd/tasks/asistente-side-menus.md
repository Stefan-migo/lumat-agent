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

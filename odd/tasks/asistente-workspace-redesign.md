# asistente-workspace-redesign

## Objective

Bring the **Asistente Lumat** workspace to the owner's references, reusing the shipped design
system and primitives instead of rebuilding from scratch:

- `refs/Diseño Lumat/AgenteLumat/LumatAgentNewthreadTools.png` — new thread + composer tools popover.
- `refs/Diseño Lumat/AgenteLumat/LumatAgentProjectContextWorkspace.png` — project context workspace.
- `refs/Diseño Lumat/AgenteLumat/LumatMulti-AgentWorkspace.png` — multi-agent thread activity.

The three references describe one workspace: global icon rail, a **Proyectos** pane with project
navigation, a center thread area with tabs + header + composer, and a right **Contexto / Actividad**
panel; plus a project context workspace reached from the project.

## Problem

The assistant frontend predates thre reference pass. Today `AgentChat.tsx` (1,144 lines) is a single
`PageFrame` column: no project sidebar, no per-thread tabs, no persistent right panel; `ProjectsPage`
detail is an empty frame; `AssistantTabs` are page-level section routes, not workspace tabs. The
references are the expected-state authority for **geometry and layout**.

## Why

The owner confirms the current assistant design is outdated and wants the workspace redone to the
references, **reusing** components already shipped in other sections so we do not rebuild from zero.

## References

Owner references (2026-10-07): the three PNGs above. Canonical design constraints live in
`openspec/changes/archive/2026-09-30-panel-design-system-final/design.md`; the owner waived further
visual analysis ("no hay mucho más análisis visual").

## Scope

**In:** the assistant workspace surfaces under `web/src/components/` — `pages/AgentChat.tsx`,
`pages/AssistantTabs.tsx`, `pages/ProjectsPage.tsx`, their CSS/tests/stories, and new region
components extracted from `AgentChat`. Shared primitives/shell are **reused**; only additive,
page-local changes when a finding demands them.

**Out:** backend routes/services/models (except a later, explicitly-approved backend slice), the
`tokens.css` palette, `PanelShell`/`AppShell` route ownership, and other panel sections.

## Constraints

- Do not reopen palette/tokens (`panel-design-system-final` settled them). References control
  geometry/layout, not palette.
- Do not invent routes or a parallel shell; `AppShell` owns routing, `PanelShell` owns shell chrome.
- Reuse existing primitives/shared components wherever they fit (see Reuse inventory).
- Chat in Rioplatense Spanish; artifacts, code, comments, commits in English; UI copy in neutral
  Chilean Spanish. Conventional Commits, no AI attribution.
- Honest UI only: where a reference element has **no backend contract**, render a real empty/disabled
  state — never fabricated agents, tasks, sources, or resources.

## Reuse inventory (verified from code)

Reuse as-is / adapt: `primitives/` — `Avatar`, `Badge`, `Button`, `Card`, `Dialog`, `Icon`, `Input`,
`Menu`, `Popover`, `SearchInput`, `Select`, `Skeleton`, `StatusBadge`, `Tabs`, `Textarea`, `Tooltip`,
`Combobox`; `shared/` — `DataTable`, `EmptyState`, `PageHeader`, `PageFrame`, `StateMessage`,
`Markdown`, `CollapsibleMessages`, `toneMaps`; `domain/` — `PanelShell`, `AppShell`, `panelRoutes`;
tokens in `web/src/tokens/`.

Net-new: projects pane with expanded sub-items, per-thread tabs, thread header controls, composer
tools popover + `@mention`, persistent right Contexto/Actividad panel, parallel-task/agent cards,
project workspace tabs (Contexto/Hilos/Agentes).

Note: the `conversaciones-redesign` merge (#508, `5606337f`) restyled `primitives/Menu.tsx`,
`primitives/Dialog.tsx`, `primitives/primitives.css`, `AppShell.tsx`, `panelRoutes.ts`; re-verify
those files before AW-1 and build on the current state.

## Backend gaps (honest empty states until a backend slice is approved)

1. Project instructions (edit/save).
2. Project resources/files (link, upload, "Elegir del proyecto").
3. Project agents with status (registry sub-agents are declared but **not wired** into the runtime).
4. Parallel/child task runs ("Trabajo en paralelo").
5. Per-thread sources ("Fuentes del hilo") — current evidence is generic tool/status/detail.
6. Per-thread tool toggles (web/KB/agenda) and a stop/cancel active-run endpoint.

## TDD resolution

No `strict_tdd` config in the repo. Effective mode: **not enabled** → ordinary functional checks per
slice (component tests written/updated + typecheck + build), not no checks. Runner: `npx vitest run`.

## Delivery strategy

- Forecast: **> ~1,000 authored changed lines** across several components → exceeds the ~400 budget.
- `delivery_strategy`: `ask-on-risk`; `chain_strategy`: `stacked-to-main` (owner-confirmed direction).
- Each work unit is independently green with its own commit(s) and verification; PRs stack to `main`
  in order. Push/PR/merge remain the owner's decision.

## Work units (stable IDs)

### AW-1 — Workspace layout foundation
- [x] Three-column assistant workspace (projects pane / thread area / right panel) with responsive
      collapse, inside the existing `PanelShell` composition; no data-semantics change.
- [x] New `AssistantWorkspace` layout component (`web/src/components/pages/AssistantWorkspace.tsx` +
      `.css`) wraps the existing chat; the existing `AgentChat` stays the center column unchanged
      (no internal extraction was needed yet — regions are placeholders for AW-2/AW-5).
- [x] Reuse `Icon`, `Tabs`, `Card`, `Button`, `SearchInput`, `EmptyState`; tokens only, no palette edits.
- [x] Tests added (`AssistantWorkspace.test.tsx`); no existing assertion weakened.
- [x] AW-1 evidence: commit `962945c8`; `npx tsc -b --force --noEmit` clean; focused
      `vitest` 3 files/50 tests; full suite serialized **1034/1034 (97 files)**; `npm run build` green.
- Owner-review item: whether to add the reference's dark global icon rail. Shell chrome left
  unchanged in AW-1 (no `PanelShell` edit).

### AW-2 — Proyectos pane
- [x] Project list + search + selection from the existing projects API; `SearchInput`, `Card`,
      `Badge`, `Menu`, `EmptyState`.
- [x] Expanded project sub-links "Contexto y archivos" / "Historial de hilos" (routing per existing
      `panelRoutes`; no new routes).
- [x] "Agentes del proyecto" section: honest empty state (no project-agent contract yet).

### AW-3 — Thread navigation + header
- [ ] Per-thread tabs (open threads) + create/close affordances from the existing thread API.
- [ ] Thread header: title + "Proyecto: <name>" subtitle + actions; reuse `Menu`, `Button`, `Icon`.
- [ ] Controls without a backend (clock/split) rendered only if they map to real behavior; otherwise
      omitted.

### AW-4 — Chat center + composer
- [ ] Restyle bubbles/Markdown/attachments/status to the reference; reuse `Markdown`, `Avatar`,
      `StateMessage`, `CollapsibleMessages`.
- [ ] Composer with attachment chips, `+` tools popover, `@mention`, "Planificar", send/stop.
      Supported today: upload ("Adjuntar archivo"), chips, send, Planificar (existing Cortex action).
      Unsupported (honest disabled/hidden): "Elegir del proyecto", tool toggles, stop.
- [ ] Preserve stream/error/retry/approval behavior and tests.

### AW-5 — Right panel (Contexto / Actividad)
- [ ] Persistent right panel with `Tabs`. Contexto: project + KB/capabilities + thread files (existing
      data). Actividad: existing per-run tool/evidence activity restyled.
- [ ] Project resources / project agents / "Fuentes del hilo" → honest empty states.

### AW-6 — Project context workspace
- [ ] Route-backed project workspace with tabs Contexto / Hilos / Agentes, reusing `Tabs`, `Card`,
      `Input`, `Textarea`, `Button`, `Menu`, `Badge`.
- [ ] Hilos: real project threads. Instrucciones / Archivos y conocimiento / Agentes → honest empty
      or disabled until backend contracts exist.

### AW-7 — Owner visual-review passes
- [ ] Iterative visual-review work units (`AW-N-r1`, `AW-N-r2`, …) recorded with commit + evidence,
      mirroring the conversaciones-redesign flow.

## Acceptance criteria

1. The workspace matches the references' geometry/layout at desktop/tablet/mobile using only the
   settled tokens and existing primitives.
2. No fabricated data: every unbacked region is an honest empty/disabled state.
3. Existing assistant behavior (stream, approvals, attachments, planning sessions, recovery,
   realtime) is preserved.
4. `npm test` and `npm run build` green; each work unit independently green.

## Checks

- Runner: `npx vitest run` (from `web/`); typecheck `npx tsc -b --force --noEmit`; build `npm run build`.
- Full frontend suite serialized if the parallel run flakes (`ClientFicha` timeouts are known).
- Graph Check per repo AGENTS.md before editing; record nodes consulted.
- Conventional Commits, no AI attribution; ≤5 files per work-unit commit where cohesive.
- RDD: `review assess` per work-unit commit; run the returned transition when `review_due`.

## Progress log

- Worktree `../lumat-agent-odd-asistente-workspace-redesign` on `odd/asistente-workspace-redesign`
  from `main` = `5606337f` (owner approved; note the `conversaciones-redesign` #508 merge landed
  during planning). Owner chose option 1: full visual redesign now, real data where it exists and
  honest empty states where backend is missing.
- **AW-1 done (committed)** — commit `962945c8`. `AssistantWorkspace` 3-column layout wrapping the
  existing chat (left "Proyectos" pane + right "Contexto del hilo" panel, both placeholders;
  responsive collapse). No shell/backend/token changes. Full suite 1034/1034; build green. Graph Check
  consulted `AgentChat`, `AssistantTabs`, `Tabs`, `Card`, `SearchInput`, `PageFrame`, `AppShell`,
  `PanelShell`. Open for owner visual review: the dark global icon rail.
- **AW-1 owner review in progress (2026-10-07)** — dev stack raised for review: API dev
  `infra-api-1` on `:8000` (bind-mounts the primary repo) + Vite dev server `:5173` from this
  worktree → `http://localhost:5173/panel/app/chat` (login `admin`; password in `infra/.env` →
  `PANEL_ADMIN_PASSWORD`). Session closed here at the owner's request; next chat resumes at **AW-2**.
- **Decision resolved (2026-10-07)** — the reference's dark icon rail is a **workspace-owned rail**,
  not a collapsed `PanelShell`. `PanelShell` keeps owning global chrome and stays untouched; the rail
  is an additive workspace region (to be built with AW-3). This unblocks AW-3.
- **Paused backlog** — Slice 8 of `asistente-sdb` (wire the verifier into `approve_plan → execute`)
  remains the prior backend feature; the frontend redesign takes priority.
- **AW-2 implemented (2026-10-07)** — feature commit `7d73af06` (`feat(assistant): render the real
  projects pane in the workspace`). Files: `web/src/components/pages/AssistantWorkspace.tsx`,
  `web/src/components/pages/AssistantWorkspace.css`, and
  `web/src/components/pages/AssistantWorkspace.test.tsx`. Projects load from `listProjects`; the
  pane provides name filtering, real status badges, expandable navigation through existing
  `panelRoutes`, retryable loading/error/empty feedback, and an honest project-agent empty state.
  The request is enabled only while the pane is visible, so a hidden sidebar does not issue an
  unnecessary project fetch alongside the existing chat fetch.
  - Verification from `web/`: `npx tsc -b --force --noEmit` — exit 0, no output;
    `npx vitest run src/components/pages/AssistantWorkspace.test.tsx` — 1 file, 3 tests passed;
    `npx vitest run --no-file-parallelism` — 97 files, 1037 tests passed;
    `npm run build` — passed (Vite emitted the existing >500 kB chunk-size advisory).
  - Graph Check consulted `listProjects()`, `AssistantWorkspace()`, `ProjectsPage.tsx`, `api.ts`,
    `types.ts`, `useAsyncData()`, `panelRoutes.ts`, `Card.tsx`, `Badge.tsx`, `Menu.tsx`,
    `SearchInput`, `EmptyState()`, and `StateMessage()`. `graphify path listProjects
    AssistantWorkspace` found no directed path.
- **AW-2 review closed (2026-10-07)** — native RDD review `review-383c5fc84adee850` (medium tier,
  single `review-reliability` lens) **approved** and was acknowledged (`authority: burned`). No
  BLOCKER/CRITICAL; no correction opened. Two non-blocking advisory findings to fold into AW-3/AW-7:
  - `R3-001` (`AssistantWorkspace.tsx:20`) — pane visibility is viewport-derived and reset on every
    resize with no persistent user toggle contract beyond the in-thread buttons; the narrow-viewport
    behaviour needs a real usable toggle.
  - `R3-002` (`AssistantWorkspace.css:120-132`) — at tablet/mobile widths showing a pane stacks it in
    normal flow, which can push the chat below the fold instead of using a collapsible overlay.
  These are advisories, not blockers; they do NOT reopen this review. Treat them as AW-3/AW-7 work.
- **Branch synced with main** — merged `origin/main` (`1c8f8802`, PR #509
  `fix/conversaciones-thread-menu`) into the branch at `fb76a199` before AW-2.

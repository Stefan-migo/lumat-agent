# asistente-mobile-redesign

Feature id: `asistente-mobile-redesign`
Branch: `odd/asistente-mobile-redesign`
Worktree: `/home/stefan/repos/lumat-agent-odd-asistente-mobile-redesign` (base `main` `89cd1494`, PR #573 merged)
Created: 2026-10-13

## Objective

Redesign the **Asistente Lumat** surface for **MOBILE** (phone, `< 40rem`), which is
currently broken, so it matches the owner's 4-screen reference.

Verified root cause (do not repeat an earlier wrong claim that px and rem
"disagree": `window.innerWidth > 1024` and `@media (max-width: 64rem)` are the
**same** boundary at a 16px root). The real problems are:

- **The tablet model is applied to phones.** The absolute side-overlay rules live
  at `@media (max-width: 64rem)` (`AssistantWorkspace.css:467-506`), so a phone
  gets two overlapping absolute side panels with a scrim and
  `width: min(20rem, calc(100vw - 4.5rem))`. That is the "broken" mobile.
- **There is no phone layout at all.** The `@media (max-width: 40rem)` blocks
  (`:508-519`) only set `width`/`height` and thread padding. No bottom sheets, no
  drag handle, no mobile navigation flow.
- **The visibility decision is a non-reactive one-shot read.**
  `AssistantWorkspace.tsx:36-37` calls `window.innerWidth > 1024` once at mount
  with **no `resize` listener and no `matchMedia`** → rotating or resizing never
  adapts the panels. The unit is also fragile under browser zoom / root-font
  changes. The repo has **no `matchMedia` convention** anywhere; introducing one
  is a deliberate choice, not an existing pattern.

This is the mobile counterpart of the desktop work shipped in PR #573
(`odd/tasks/asistente-side-menus.md`).

## Decisions taken by the owner

- **Shell chrome stays (option b).** Mobile keeps the documented shell: the dark
  mobile bar (`--corp-primary`) + the five bottom tabs (`panel-shell__footer-nav`)
  + the app drawer. The assistant reference is implemented **inside** that shell,
  **not** as a separate screen. The reference's top bar is **fused with the existing
  mobile bar**. `web/DESIGN_SYSTEM.md` is **not** changed.
- The owner's standing preference applies: build on the existing unified design
  system, reuse primitives, no new dependencies, no hex outside `tokens.css`.
- **D2 — the hamburger (decided 2026-10-13, option a).** On a phone, inside the
  assistant, the hamburger opens the assistant's **Navegación** sheet (Nueva
  conversación · Historial de conversaciones · Espacio de trabajo → Proyectos),
  **not** the app drawer. The hamburger itself belongs to the **shell header**
  (the mobile bar) — do not add a second assistant bar. In the other views the
  hamburger keeps opening the app drawer. Consequence: the shell mobile bar is
  the bar drawn in the reference, so while in the assistant it also hosts the
  assistant's project selector and info control.
- **D4 — the empty-state copy (decided 2026-10-13, option b).** The reference's
  empty-state copy (`¿En qué trabajamos hoy?` + `Consulta, planifica o trabaja en
  tus proyectos.` + the sparkle icon) applies **only at `< 40rem`**. Desktop
  (`>= 40rem`) keeps its existing copy **exactly**:
  - hero 1 (`!thread`): `h2` = the time-based greeting
    `Buenos días|Buenas tardes|Buenas noches{, nombre}` and `p` =
    `¿En qué trabajamos hoy?`, plus the existing `Iniciar conversación` button;
  - hero 2 (thread with no messages): `h2` = `¿En qué trabajamos hoy?` and `p` =
    `Consulta, planifica o trabaja en tus proyectos con el asistente Lumat.`
  The `userName` prop must stay **used** (M5 left it dead).

## Visual reference — target (4 surfaces)

Shared, across all four: the shell mobile bar (hamburger · project selector
`TestProject ⌄` · info icon) and the five bottom tabs remain visible.

1. **01 · Nueva conversación** — empty state centered: sparkle icon, title
   `¿En qué trabajamos hoy?`, subtitle `Consulta, planifica o trabaja en tus
   proyectos.` Below: the composer (`Escribe un mensaje…`, a `+` button, a
   **Planificar** pill, a send arrow) and, under it, a status row: project
   selector · attachments count (`0`) · tools count (`7`).
2. **02 · Navegación** — a bottom sheet titled `Navegación` with an `X`.
   Contents, in order: primary full-width **Nueva conversación** button;
   **Historial de conversaciones ›**; a `Espacio de trabajo` section with a
   **Proyectos (2) ›** row. Screen behind is dimmed; the shell bar stays visible.
3. **03 · Proyecto** — a bottom sheet titled `Proyecto` with an `X`. A
   `Buscar proyecto` input; a project list (`General`, `Proyecto2`, `TestProject`
   with a check on the selected row, highlighted); then a per-project section
   `TestProject` with rows **Contexto y archivos ›**, **Historial de hilos ›**,
   **Sesiones de planificación ›**; at the bottom a **+ Crear proyecto** button.
4. **04 · Detalle del hilo** — a bottom sheet titled `Detalle del hilo` with an
   `X`. A project row with a **Cambiar** action; then rows **Contexto del
   proyecto ›**, **Recursos del proyecto ›**, **Capacidades del asistente
   (Sin datos) ›**, **Archivos del hilo 0 ›**, **Artefactos del hilo 0 ›**,
   **Fuentes del hilo 0 ›**; footer note `Los adjuntos y resultados pertenecen a
   este hilo.`

**Mapping desktop → mobile:** the desktop in-assistant tabs
(`thread | planning | context | history | sessions`, `AssistantWorkspace.tsx:28-34`)
become the **rows inside sheets 03/04** — they are not a tab strip on mobile. The
desktop compact rail does **not** exist on mobile.

## Reuse map (verified)

- **Bottom sheet primitive already exists**: `Dialog` with `variant="sheet"`
  (`web/src/components/primitives/Dialog.tsx:16-17,46`;
  `primitives.css:930-944` — rises from the bottom, centered above `40rem`).
  Use it. Do not build a new overlay primitive.
- **Sheet 03 body** ← the desktop project tree, search and per-project actions
  (`AssistantWorkspace.tsx:364-442`).
- **Sheet 04 body** ← the desktop context panel sections
  (`AssistantWorkspace.tsx:535-570`) — context, resources, capabilities,
  attachments, artifacts, sources already exist.
- **01 composer + status row** ← `AgentChat.tsx` composer (`:1076+`) and the
  inactive-conversation status tray (`:1082-1103`).
- **Shell mobile bar + footer nav** ← `PanelShell.tsx` (`mobile-bar` L524,
  `footer-nav` L644); `primitives.css:2205-2214`, `1572`, `2357`.

## Constraints

- Reuse existing primitives and tokens. **No new dependencies.** No hex outside
  `tokens.css`.
- **Never regress the desktop layout** or the other five sections' shell. The
  mobile changes must be scoped to `< 40rem` (and must not alter the `>= 64rem`
  desktop rules).
- **Fix the breakpoint root cause**: `40rem` is the phone boundary (repo
  convention — 20 existing rules use it). The phone must stop inheriting the
  tablet side-overlay model, and the panel visibility decision must not be a
  non-reactive one-shot `window.innerWidth` read.
- All new UI copy in **neutral Chilean Spanish**.
- Storybook is a contract: `web/src/stories/pages/*.stories.tsx` +
  `*.stories.test.tsx`.
- Never hide send, plan, attach, or retry actions to make a layout fit.
- Do not extract/duplicate the whole `AssistantWorkspace` component: reuse the
  existing markup and state by extracting the sheet bodies.

## Work units (one commit each, Conventional Commits, no AI attribution)

- **M1** `fix(assistant): define the phone breakpoint and drop the side-overlay model below it`
  — introduce `40rem` as the phone boundary in `AssistantWorkspace.css`; below it
  the assistant stops using absolute side overlays. Replace the non-reactive
  one-shot `window.innerWidth > 1024` read in `AssistantWorkspace.tsx:36-37` with
  a decision that stays consistent with the CSS boundary and survives resize /
  rotation (a `matchMedia`/`resize` subscription, or by letting CSS own the
  mobile layout so JS state is not needed there). **Leave the `40–64rem` tablet
  behavior intact.**
- **M2** `feat(assistant): mobile navigation sheet`
  — `Navegación` bottom sheet (`Dialog variant="sheet"`, title `Navegación`, `X`)
  with: primary full-width **Nueva conversación** (reuse the existing
  create-thread handler), **Historial de conversaciones ›** (reuse the existing
  history action), and a `Espacio de trabajo` section with a **Proyectos (N) ›**
  row (reuse the existing project list/state; N = real project count). Wire it so
  that on a phone, in the assistant view, the **shell header hamburger** opens
  this sheet instead of the app drawer (a minimal optional prop on `PanelShell`;
  every other view and the `40–64rem`/`>= 64rem` behavior must be unchanged).
- **M3** `feat(assistant): mobile project sheet`
  — `Proyecto` bottom sheet reusing the project tree, search, per-project rows
  (Contexto y archivos / Historial de hilos / Sesiones de planificación) and
  `+ Crear proyecto`. Reference reading: **tapping a project selects it AND
  reveals that project's section** (the reference shows the check on the selected
  row plus its rows below). Also re-point the `Navegación` sheet's
  **`Proyectos (N) ›`** row (shipped in M2) so it opens **this** sheet — the
  reference flow is 02 → 03, not the standalone `projects` route.
- **M4** `feat(assistant): mobile thread detail sheet`
  — `Detalle del hilo` bottom sheet reusing the context panel sections and the
  `Cambiar` project action.
- **M5** `feat(assistant): mobile composer and empty state`
  — 01 surface: empty state, composer, and the project/attachments/tools status
  row, adapted to `< 40rem`.
- **M6** `docs(odd): record asistente-mobile-redesign evidence`
  — progress, checks, commits.

## Route

- **Delegated direct** — one writer per work unit. Trigger: every unit touches
  ≥ 2 non-trivial files (component + CSS + tests).
- Exploration and reading that prepare each write belong to that unit's writer.

## Acceptance criteria

- On a `< 40rem` viewport the four reference surfaces render as bottom sheets
  inside the shell, with the shell mobile bar and the five bottom tabs visible.
- The desktop layout (`>= 64rem`) is pixel-unchanged.
- At `< 40rem` the assistant no longer uses the tablet side-overlay model, and the
  layout adapts on resize / rotation (not only at mount).
- The `40–64rem` tablet behavior and the `>= 64rem` desktop layout are unchanged.
- Sheets are reachable, dismissible (back / Escape / scrim, plus drag where the
  primitive supports it) and correctly wired for a11y.
- Empty states and counts stay honest (no fabricated data).
- No new dependencies; no hex outside `tokens.css`.

## Checks (run from `web/`)

- `npx tsc -b --force --noEmit`
- `npx vitest run --no-file-parallelism`
- `npm run build`
- Browser pass at a phone viewport (owner does the visual pass).

## Notes / environment

- Graph `graphify-out/` rebuilt for this worktree at `89cd1494` (18605 nodes /
  31331 edges). Refresh with `graphify <root> --update` once at session close,
  not per commit.
- `web/node_modules` is **not** provisioned in this worktree yet → `npm install`
  from `web/` is required before dev/tests.
- Dev stack for this worktree: needs provisioning (API + isolated db + Vite on a
  free port; the desktop stack `:8001/:5433/:5174` was torn down).

## Graph nodes consulted (Step 1)

- `AssistantWorkspace.tsx` (community `AssistantWorkspace.tsx`) — `WorkspaceTab`
  at L28.
- `AgentChat.tsx` — path `AssistantWorkspace.tsx --references--> AgentChat.tsx`.
- `web/DESIGN_SYSTEM.md` — `Responsive behavior` (L352), `Application shell and
  information architecture` (L318).
- `odd/tasks/asistente-side-menus.md` — `Visual reference — target layout` (L24).
- God nodes (context): `session()`, `User`, `Customer`, `Conversation`, `Project`.

## Progress / Evidence

### M1 — phone breakpoint foundation

- Commit `21620755` `fix(assistant): define the phone breakpoint and drop the
  side-overlay model below it`.
- `AssistantWorkspace.css`: the tablet side-overlay rules are now scoped to
  `@media (min-width: 40rem) and (max-width: 64rem)`; a new `< 40rem` block makes
  the workspace a single column and hides the side panes + scrim
  (`.assistant-workspace__projects`, `__context`, `__scrim`), with the thread at
  `grid-column: 1`.
- `AssistantWorkspace.tsx`: new `useDesktopWorkspace()` replaces the one-shot
  `window.innerWidth > 1024` read — `matchMedia("(min-width: 64rem)")` with a
  `resize` fallback, subscribed on mount and cleaned up on unmount; pane
  visibility now follows breakpoint changes.
- Tests: `AssistantWorkspace.test.tsx` +1 phone-visibility / resize regression.
- Checks: `npx tsc -b --force --noEmit` pass · `npx vitest run
  src/components/pages/AssistantWorkspace.test.tsx` **27 passed** · `npm run
  build` pass.
- Native review assessment: risk `medium`, `review_due: false` (`under_budget`).
- **Not verified**: no browser visual pass yet.

### M2 — mobile navigation sheet

- Commit `a5e8430a` `feat(assistant): mobile navigation sheet` (amended once for
  the wiring defects below; first version was `faa6889b`).
- New `Navegación` bottom sheet built on `Dialog variant="sheet"`: primary
  full-width `Nueva conversación`, `Historial de conversaciones ›`, and a
  `Espacio de trabajo` section with `Proyectos (N) ›` (real count).
- Trigger (D2): `AppShell` holds `assistantMenuOpenerRef` and passes
  `registerAssistantMenuOpener` through `AgentChat` into `AssistantWorkspace`,
  which registers its opener in an effect; `PanelShell` gained the optional
  `onMobileMenuClick` prop. On a phone in the assistant the hamburger opens the
  sheet; elsewhere it opens the app drawer unchanged.
- `PanelShell` gained `useIsPhone()` (`matchMedia("(min-width: 40rem)")` with a
  `resize` fallback + cleanup), used once.
- **Correction applied (orchestrator readback)**: the first version wired the
  shell to the workspace with a `window`-global event
  (`window.dispatchEvent(new Event("assistant-navigation-open"))`) and called
  `window.matchMedia` inline three times in `PanelShell`'s render — the exact
  non-reactive pattern M1 removed. Both replaced (verified: no
  `assistant-navigation-open` remains).
- Tests: `AssistantWorkspace.test.tsx` + `PanelShell.test.tsx` → **63 passed**.
- Checks: `npx tsc -b --force --noEmit` pass · focused vitest 63 passed ·
  `npm run build` pass.
- Native review assessment: risk `medium`, `review_due: false` (`under_budget`).
- **Not verified**: no browser visual pass yet.

### M4 — mobile thread detail sheet

- Commit `24cbe6f6` `feat(assistant): mobile thread detail sheet`.
- `Detalle del hilo` bottom sheet: a project row with the `Cambiar` action (reuses
  `changeProject` / the existing project picker) and the rows `Contexto del
  proyecto`, `Recursos del proyecto`, `Capacidades del asistente`,
  `Archivos del hilo N`, `Artefactos del hilo N`, `Fuentes del hilo N` — counts
  are real (`attachments.length`, `artifacts.length`; sources stay `0`, matching
  the desktop section) — plus the footer note.
- **Trigger**: an info (ⓘ) control added to the shell mobile bar, shown only in
  the assistant on a phone. **This placement is the orchestrator's inference from
  the reference — the owner must confirm it in the visual pass.**
- The M2 bare opener was generalised to a typed
  `AssistantMobileActions { openNavigation, openThreadDetail }` (AppShell bridges
  via a ref); no globals.
- Tests: **64 passed**. Checks: `npx tsc -b --force --noEmit` pass · focused
  vitest 64 passed · `npm run build` pass.
- Native review assessment: risk `medium`, `review_due: false` (`under_budget`).
- **Not verified**: no browser visual pass yet.

### M6 — full checks

- Full web suite: `npx vitest run --no-file-parallelism` → **105 files / 1161
  tests passed** (360s).
- `npm run build` pass (existing >500 kB chunk warning only).
- `npx tsc -b --force --noEmit` pass.
- **Remaining**: the owner's browser pass at a phone viewport (the worktree's dev
  stack must be brought up first).

### Visual pass — the phone was still broken, and why

The owner's first pass at 390px showed a blank content area. Diagnosed with a
real headless-browser probe (Playwright, chromium build 1234 via
`executablePath`), not by guessing:

- **Defect A (introduced by M1) — the phone kept the 3-column grid.** The
  collapsed templates at `AssistantWorkspace.css:471` use
  `:not(...--projects-visible):not(...--context-visible)`, i.e. **specificity
  0,3,0**. M1's phone rule was a bare `.assistant-workspace` (0,1,0), so it lost
  **regardless of the media query**; the computed grid stayed
  `56px 278px 56px` and M1's `grid-column: 1` pinned the thread into the 3.5rem
  rail column (measured thread width: 56px, messages: 16px — the "tiny green
  dot"). The same specificity flaw already affected the **tablet** block.
  Fixed in `39b216fd` by repeating every modifier combination in both blocks.
- **Defect B (introduced by M5) — the phone status row wrapped onto two lines**
  (`flex-wrap: wrap` + `margin-left: auto` on `.assistant-chat__tools-summary`),
  so the first line was hidden behind the composer card. Fixed in `0b44a325`
  (`flex-wrap: nowrap`, shrinkable project popover, `flex: 0 0 auto` tools).
- Verified after the fixes at three widths: 390px → `390px` single column, phone
  copy; 700px → single column + overlay rails, desktop copy; 1280px → unchanged
  `320px 488px 360px`.
- **Lesson**: the JSDOM suite cannot catch this class of defect (it does not apply
  CSS). The phone layout needs a real-browser check; M1/M5's green tests passed
  while the phone was unusable.

### Open observations from the visual pass (not fixed)

- **Empty state has no composer.** With no thread the surface shows the hero plus
  an `Iniciar conversación` button; the composer (and the status row) appear only
  after a thread exists. The reference's 01 shows the composer immediately. This
  is a pre-existing flow difference, not a layout bug — needs an owner decision.
- **Pre-existing manifest link bug (not this branch).** `web/index.html` has
  `<link rel="manifest" href="/panel/app/manifest.webmanifest" />` and Vite
  prepends `base` (`/panel/app/`), producing
  `/panel/app/panel/app/manifest.webmanifest` → 404 → the browser parses HTML as
  a manifest and logs `Syntax error`. Last touched by `65b2062d` (PWA), not by
  this branch.
- The two `401 GET /panel/api/me` in the console are the **pre-login** load;
  after login there are zero HTTP >= 400.

- Commits: `f0fd1ca5` `feat(assistant): mobile composer and empty state`, then
  `a8cdef47` `fix(assistant): keep the desktop empty-state copy and scope the
  reference copy to the phone`.
- Phone (`< 40rem`) layout for the empty state, the composer (input, `+`,
  **Planificar** pill, send) and the status row. The composer, handlers and the
  status row are reused; the status-row **rendering condition is unchanged** (D3
  is still open). The composer placeholder stays
  `Escribe un mensaje al asistente…`.
- **Defect found by the orchestrator readback**: the first version changed the
  empty-state copy **globally** — it deleted the time-based greeting from the
  whole repo and left `userName` as a dead prop, violating the approved criterion
  "desktop pixel-unchanged". A first correction attempt (CSS-only duplicate
  variants) was **rejected**: JSDOM does not apply CSS, so both copies landed in
  the DOM and 21 tests failed on duplicate headings. The shipped fix uses a
  reactive `usePhoneViewport()` so **exactly one variant renders**.
- Per **D4 (option b)** the reference copy applies only at `< 40rem`; desktop
  keeps the greeting and its original copy.
- Tests: **98 passed**. Checks: `npx tsc -b --force --noEmit` pass · focused
  vitest 98 passed · `npm run build` pass.
- Native review assessment: risk `medium`, `review_due: false` (`under_budget`).
- **Known duplication (follow-up, not fixed here)**: there are now three similar
  local breakpoint hooks — `useIsPhone()` (`PanelShell.tsx`), `useDesktopWorkspace()`
  (`AssistantWorkspace.tsx`) and `usePhoneViewport()` (`AgentChat.tsx`). They
  should be consolidated into one shared hook.
- **Not verified**: no browser visual pass yet.

- Commit `53334dcf` `feat(assistant): mobile project sheet`.
- `Proyecto` bottom sheet (`Dialog variant="sheet"`): `Buscar proyecto` input,
  project list with `aria-pressed` selection + a check on the selected row, the
  selected project's section (`Contexto y archivos` / `Historial de hilos` /
  `Sesiones de planificación`), and `+ Crear proyecto`. All reuse existing
  project state, search, navigation handlers and the create-project flow.
- The `Navegación` sheet's `Proyectos (N) ›` row now opens this sheet (flow
  02 → 03), instead of the standalone `projects` route.
- Tests: `AssistantWorkspace.test.tsx` extended (sheet contents, real count,
  selection reveals the section, `Navegación` → `Proyecto`); **63 passed**.
- Checks: `npx tsc -b --force --noEmit` pass · focused vitest 63 passed ·
  `npm run build` pass.
- **Native review**: assessment `review_due: true` (`slice_budget_reached`, 444
  lines). Review START granted by the owner; risk `medium` → one lens
  (`review-reliability`); result **approved**; acknowledgement burned
  (`authority: burned`). The reviewed boundary now advances to `53334dcf`.
- **Review findings — non-blocking, recorded as follow-ups (do not re-review
  this candidate):**
  - **R3-001** `web/src/components/pages/AssistantWorkspace.tsx:380` — selecting a
    project in the sheet sets `expandedProjectSlug`, but the wider project-panel
    state/route (`panelProjectSlug` / `activeProject`) is not updated, so the
    sheet's selection and the panel context can diverge.
  - **R3-002** `web/src/components/domain/PanelShell.tsx:90` — `useIsPhone()`
    reads `window` in the `useState` initializer (guards `matchMedia`, not
    `window`), so it is SSR-unsafe. The panel is a client SPA today, so this is
    theoretical, but worth guarding if SSR ever lands.
- **Not verified**: no browser visual pass yet.

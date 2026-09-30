# ODD — panel-header-refine

Base: `d309992e` (main). Worktree: `../lumat-agent-odd-panel-header-refine`, branch `odd/panel-header-refine`.
Sources: owner directive 2026-09-30 (focus mode deprecated, header scope approved, chained PRs), source review,
canonical specs, and the design references.
References: `refs/Diseño Lumat/headerShell.png` (desktop header), `refs/Diseño Lumat/mobileTablet/mobilePanelShell.png`
(dark mobile header + drawer), `refs/Diseño Lumat/mobileTablet/TabletPanelShell.png` (tablet rail + expanded menu).

## Objective

Bring the panel shell's header surfaces to the reference design and the canonical requirements, and retire the
unused focus-mode feature, without rebuilding the design system and without inventing destinations, routes or tokens.

## Harness gotchas (learned this session — read before working)

- **`refs/Diseño Lumat/` is gitignored, so this worktree does NOT contain the reference images.** Read them from the
  main worktree: `/home/stefan/repos/lumat-agent/refs/Diseño Lumat/…`. Do not assume they exist here.
- **`graphify-out/GRAPH_REPORT.md`'s freshness header lags `graph.json`.** The graph was refreshed with
  `graphify /home/stefan/repos/lumat-agent --update` (8611 nodes). The report still says `c58e91e1`; trust
  `graph.json` and the source, and say so if they disagree.
- **The `explore` subagent has no shell**, so it cannot run `graphify`. The orchestrator must run the Graph Check and
  hand the evidence to the subagent, or the phase is falsely blocked.
- `rapso worktree create` does not install `web/node_modules`; `npm ci` was run in this worktree.
- The web suite is load-flaky: failures that move between runs are noise, but each one must be checked once against
  the affected file set before dismissing it.

## Problem

### Settled: focus mode is dead code and a canonical liability

Owner directive 2026-09-30: the focus mode is not used and must be deprecated. Measured on `d309992e`:

1. **Focus mode has no CSS at all.** `.panel-shell--focus-mode` and `.panel-shell__focus-close` appear only in
   `PanelShell.tsx:408` and `:549`; there is no rule for either in `primitives.css`. The feature therefore changes
   ARIA state and renders one unstyled button — it never visually focuses anything.
2. **No consumer.** `focusMode`/`onFocusModeChange` are declared (`PanelShell.tsx:71-72`) but no story, page or
   `AppShell` passes them; the only other reference in the repo is one test (`PanelShell.test.tsx:274-287`).
3. **No browser coverage remains.** `web/playwright/command-center.spec.ts` contains no focus-mode reference, although
   the archived `2026-09-15-ui-command-center` change once added one.
4. **Three canonical clauses still mandate it**, so deleting the code without amending them leaves the tree in
   violation: `openspec/specs/ui-command-center/spec.md:25` (CC-2), `openspec/specs/panel-design-system/spec.md:851`
   (DS-CC-2), and CC-4's verification clause plus its focus-mode scenario (`ui-command-center/spec.md:57,65-69`).

### Owner visual analysis (2026-09-30) — the scope authority

**Desktop:**
1. **The header background is no longer green — the reference is right.** Today `.panel-shell__header-row` uses
   `--corp-primary` (dark forest) with `--surface` text. The reference band measures **(222,228,218)** and the
   dedicated token **`--header-bg: #dee4db` = (222,228,219) already exists** (`tokens.css:44`) and was never consumed.
2. **Focus mode disappears.** Done in H0.
3. **The bell and the account control must sit at the END of the header**; today they do not. Cause: the header's
   `max-width: 78rem` (`primitives.css:1167`) caps the row on wide viewports and leaves the actions floating mid-header.

**Mobile:**
4. **A new mobile logo is needed: mark + wordmark on one line.** **Owner will deliver the asset** — pending, not
   implementable yet.
5. **The rest of the mobile header is fine; add the notification bell.**

### Measured evidence for the desktop inversion

- Reference band `headerShell.png` = (222,228,218); token `--header-bg` = (222,228,219) → **1.00:1 difference**.
- `Dashboard.png` renders the tokens exactly (`#e8ebe4` `--surface`, `#dbe1d6` `--bg`), so the mockups are
  colour-accurate and the band match is real, not a compression artifact.
- `tokens.test.ts:239-244` **already measures** `contrast(--text, --header-bg) >= 4.5` and
  `contrast(--text-muted, --header-bg) >= 4.5`: the design system was built for a light header using `--text` /
  `--text-muted`, and the implementation simply never used the token. DS-TKN-13 is satisfied by that existing
  measurement, re-confirmed by hand — `--text` **13.40:1**, `--text-muted` **4.69:1**, `--focus-ring` **4.67:1**,
  `--border` **1.10:1** (decorative hairline, no threshold; the reference band does not separate from the page either).
- Right-edge geometry: `headerShell.png` content ends 72 units from the image edge; scaled by the crop width
  (viewport − sidebar) that is **40px** = `--space-4` + `--space-6`, which is exactly the gap the implementation now
  renders (account right edge 1400 in a 1440 viewport). The left gap scales to ~24px = `--space-6`, also matching.

### Still open after the owner's analysis

- **Mobile bell behaviour**: the notifications popover lives inside the desktop header, which is `display: none`
  below 64rem, so a mobile bell cannot simply toggle it. Options: navigate to the notifications view, or move the
  popover out of the desktop header. **Owner decision pending.**
- **Mobile avatar**: PNL-APP-10 requires bell **and avatar** affordances tier-unqualified; the owner asked only for the
  bell. Either the avatar ships on mobile/tablet or PNL-APP-10 is amended. **Owner decision pending.**
- **Tablet header surface**: approved earlier as in scope but absent from the owner's analysis. `TabletPanelShell.png`
  shows bell + avatar at the top-right of the content. **Owner decision pending.**
- Reference-only details the owner did not raise: the **bell|account vertical divider** and the **bordered back
  square** in `headerShell.png`, plus the unaddressed 44px/focus-visible gaps in the notification popover and account
  menu (`primitives.css:1459, 1469`).

## Adjudication rules applied

- **The archived canonical spec beats the reference image.** References control **geometry and layout, not palette**.
- **Recorded decision (owner, 2026-09-30): retire the focus mode instead of keeping its control.** The reference
  header omits the control while canonical CC-2 / DS-CC-2 required it; the owner resolved the conflict by deleting the
  feature. **Spec-amendment form: the owner chose to delete CC-2 and DS-CC-2 outright.** The adjacent CC-4 clause that
  required Playwright coverage of "focus entry/escape/restoration", plus its focus-mode-only scenario, were also
  removed because they had become unsatisfiable; no replacement coverage obligation was invented. Recorded here so the
  amendment is deliberate, not silent (the same rule the sidebar unit applied to DS-SHELL-1).
- The drawer's top row in `mobilePanelShell.png` shows bell + avatar, but the canonical spec does not require the
  drawer to expose them and the mobile bar will; adding them there is reference-only and is **not** in scope
  (YAGNI) unless the owner asks.
- References are read from the main worktree (see harness gotchas).

## Scope

**In (settled):** retire the focus-mode feature end to end and amend its two canonical requirements.

**In (approved by owner 2026-09-30, tasks pending the visual analysis):** the desktop header surfaces, and the
notification-bell + avatar affordances on the mobile bar and at the tablet tier.

**Out:** palette and tokens, other primitives, other pages, the canonical specs other than CC-2/DS-CC-2, the
sidebar/drawer surfaces already adjudicated in `odd/tasks/panel-sidebar-refine.md`, the drawer's bell + avatar.

## Constraints

- Files authorized: `web/src/components/domain/PanelShell.tsx`, `web/src/components/primitives/primitives.css`,
  `web/src/components/domain/PanelShell.test.tsx`, `web/src/components/domain/AppShell.test.tsx` (only if its bridge
  breaks), `web/src/stories/pages/PanelEntry.stories.tsx`, `web/src/stories/domain/AppShell.stories.tsx`,
  `openspec/specs/ui-command-center/spec.md`, `openspec/specs/panel-design-system/spec.md`.
- No new dependency, no new destination, route or parallel navigation model. Every destination and role filter keeps
  deriving from `NAVIGATION` and `panelRoutes`/`pathForRoute()`.
- Verification for every task: `cd web && npm run build` (the **only** type-check path; a green Vitest suite does not
  prove the tree type-checks) plus the affected test files via `npx vitest run <files>`. Full `npm run test` once at
  the end.
- Artifacts and code comments in English; user-facing UI copy in neutral Chilean Spanish.
- One work-unit commit per task, tests alongside the behaviour, no AI attribution.

## Tasks

- [x] **H0 — retire focus mode. DONE.** Removed the `focusMode`/`onFocusModeChange` props, the internal state,
  `setFocusMode`, `closeFocusMode`, the Escape effect, `keepFocusInFocusMode`, the header control, the
  `panel-shell--focus-mode` class, the `focusMode`-driven `aria-hidden` on the sidebar and inspector, the
  `role`/`aria-label` on `#panel-main-content`, and the "Salir del modo foco" button. **Kept** `#panel-main-content`
  `tabIndex={-1}` (the skip-link target) and the drawer's own focus behaviour. Deleted the focus-mode test. Deleted
  CC-2, DS-CC-2, and the unsatisfiable CC-4 clause/scenario. No CSS to delete — no rules existed.
- [x] **D1 — desktop header chrome inversion. DONE.** `.panel-shell__header-row` uses `--header-bg` with
  `--corp-text` and a `--border` hairline; the header, the breadcrumb separator, the breadcrumb link, the
  current-page crumb, the header action buttons and the back/account controls all flip to `--corp-text` /
  `--corp-fg-muted` with `--surface-subtle` hovers. `font: inherit` was added to `.panel-shell__header-action`,
  killing the recorded Arial debt.
- [x] **D2 — header actions at the end. DONE.** Removed `max-width: 78rem` from `.panel-shell__header`; the actions
  now end at the row's right padding on wide viewports.
- [x] **M1 — mobile header bell + avatar. DONE.** The mobile bar exposes the bell (navigates to the notification
  center, because the popover lives in the desktop header which is `display: none` below 64rem) and the account
  avatar, both keeping the dark-chrome treatment. A controlled `AccountControl` was extracted so the desktop header
  and the mobile bar share one popover implementation with independent open state.
- [x] **M2 — tablet header surface. DONE.** At 640–1023 the header row is transparent with no border, the back and
  breadcrumbs are hidden, and the row carries only the bell and account affordances at the top-right of the content.
- [ ] **M3 — mobile one-line logo (mark + wordmark).** BLOCKED: the asset is an owner deliverable. The bar layout
  will be revisited with it.
- [ ] **Reference-only details** (bell|account divider, bordered back square, popover 44px/focus-visible) — pending
  the owner's call.

## Acceptance criteria

- No `focusMode` reference remains in `web/` (source, tests, stories) and no focus-mode control renders.
- `CC-2` and `DS-CC-2` no longer require a feature that does not exist; the amendment is recorded, not silent.
- `npm run build` passes; affected tests pass; the full suite passes once at the end.
- Visual header acceptance criteria are written only after the owner's visual analysis is recorded here.

## Debt recorded (NOT part of this unit)

- System-level WCAG fail: active mobile tab renders `--lime-500` 12px on `--primary-700` = 3.73:1 (WCAG 1.4.3).
- `.dialog__close` is 28×30, below the 44px house target.
- `.kpi` carries `--shadow-1` and `--radius-md` (8px) against the "cards carry no material shadow, ~10px" contract.
- Raw unstyled `<button>Reintentar` at `Dashboard.tsx:104`.
- The user profile page does not exist; do not add a dead menu entry.
- **The account menu (desktop header and mobile bar) has no outside-click or Escape close** — a pre-existing gap the
  notifications popover already solves (`closeOnOutsideClick`). Duplicated by M1, recorded, not fixed here.

## Route decisions

| Task | Route | Trigger evidence |
| --- | --- | --- |
| H0 | inline | deletion confined to files already read; no research needed |
| H1+ | pending | decided with the owner's visual analysis |

## Progress and evidence

**M1 — mobile header bell + avatar. DONE.**
Solution: extracted a controlled `AccountControl` (avatar trigger + menu) and reused it in the desktop header and the
mobile bar, each owning its open state; the bell's accessible label is computed once (`bellLabel`) and shared by both
bells. The mobile bell navigates to the notification center rather than opening a popover that is CSS-hidden at that
tier. The mobile bar's bell and account trigger keep the dark-chrome colours through `.panel-shell__mobile-bar`
scoping, and the compact account hides the identity and the chevron.

**M2 — tablet header surface. DONE.**
Solution: in the tablet media block the header row becomes `display: flex` with a transparent background and no
border, the back and breadcrumbs are hidden, and the header is right-aligned — the row carries only the bell and the
account affordances above the content.

Checks: `npm run build` OK. Affected test files → 6 files / 111 tests passed. Full suite → 92 files / 906 tests, exit 0.
Five existing tests were scoped to `.panel-shell__header-actions` (new `headerActions` helper in `AppShell.test.tsx`)
because the bell and account affordances now legitimately exist twice in the DOM and jsdom does not apply the tier CSS;
this follows the repo's existing convention of duplicating `Navigation` across the sidebar and the drawer. A new
DOM-level test asserts the mobile bar exposes a named bell and a named account affordance, that the account menu
opens, and that the mobile bell navigates.
Rendered verification (fresh `build-storybook`, Chrome):

| Tier | Mobile bar | Header row | Bell / account |
| --- | --- | --- | --- |
| desktop 1440 | `display:none` | `flex`, `rgb(222,228,219)` = `--header-bg` | bell 1235-1279, account 1287-1400 (40px gap) |
| tablet 768 | `display:none` | `flex`, transparent, no border | back + breadcrumbs `display:none`; bell 567-611, account 619-732 |
| mobile 390 | `flex`, `rgb(20,60,44)` dark chrome | `display:none` | bell + avatar present in `--surface`; identity + chevron `display:none` |

**D1 — desktop header chrome inversion. DONE.**
Solution: CSS only, in `primitives.css`. `.panel-shell__header-row` background `--corp-primary` → `--header-bg`,
colour `--surface` → `--corp-text`, border-bottom `color-mix(--surface 30%)` → `var(--border)`. `.panel-shell__header`
colour → `--corp-text`. Breadcrumbs: separator and link → `--corp-fg-muted`, current crumb and link hover →
`--corp-text`. `.panel-shell__header-action` colour → `--corp-text`, hover → `--surface-subtle`, plus `font: inherit`.
`.panel-shell__back` / `.panel-shell__account-trigger` colour → `--corp-text`, hover → `--surface-subtle`.
Checks: `npm run build` → `tsc -b` + vite OK. Affected test files (AppShell.stories, PanelEntry.stories, PanelShell,
AppShell, app, tokens) → 6 files / 110 tests passed. Two brittle CSS-text assertions in
`AppShell.stories.test.tsx` were rewritten toward the contract: the breadcrumb current-crumb colour now asserts
`var(--corp-text)` (it pinned `color-mix(--surface 70%)`, a dark-chrome value), and the "no green fill" test gained a
positive assertion that `.panel-shell__header-row` uses `var(--header-bg)`.
Rendered verification (fresh `build-storybook`, Chrome, `domain-appshell--desktop-admin-1280` at 1440):
`rowBg rgb(222,228,219)` = `--header-bg` exact; `rowColor`/`headerColor`/`breadcrumbCurrent` `rgb(17,26,46)` =
`--text`; `rowBorderBottom rgb(213,218,209)` = `--border`; `actionFontFamily` = `Inter, system-ui, sans-serif`
(was Arial).

**D2 — header actions at the end. DONE.**
Solution: removed `max-width: 78rem` from `.panel-shell__header` (`primitives.css:1167`). It never bound at 1440
(row 1200px) but capped the row on wide viewports, leaving the actions floating mid-header.
Rendered verification (same story, 1440): `headerMaxWidth: none`; the account control's right edge is **1400** of
1440 → a **40px** gap = `--space-4` + `--space-6`, which matches the reference (`headerShell.png` content ends 72
units from the edge; scaled by the crop width that is 40px).

**H0 — retire focus mode. DONE.**
Solution: deleted the feature in `PanelShell.tsx` — the `focusMode`/`onFocusModeChange` props, `internalFocusMode`,
`setFocusMode`, `closeFocusMode`, the Escape effect, `keepFocusInFocusMode`, the three focus refs, the header control,
the `panel-shell--focus-mode` class, the `focusMode`-driven `aria-hidden` on the sidebar and inspector, the
`role`/`aria-label` on `#panel-main-content`, and the "Salir del modo foco" button. Kept `#panel-main-content`
`tabIndex={-1}` (skip-link target) and the drawer's focus containment/restoration. Deleted the focus-mode test from
`PanelShell.test.tsx`. Canonical amendment: removed CC-2 (`ui-command-center`), DS-CC-2 (`panel-design-system`), and
CC-4's "focus entry/escape/restoration" clause plus its focus-mode-only scenario.
Checks: `npm run build` → `tsc -b` + vite build OK. Affected test files (PanelShell, AppShell, AppShell.stories,
PanelEntry.stories, app) → 5 files / 87 tests passed.
No CSS was removed because none existed for the feature.

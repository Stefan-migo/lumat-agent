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
4. **Two canonical requirements still mandate it**, so deleting the code without amending them leaves the tree in
   violation: `openspec/specs/ui-command-center/spec.md:25` (CC-2) and
   `openspec/specs/panel-design-system/spec.md:851` (DS-CC-2).

### Pending: the visual header gap

**Blocked on the owner's own visual analysis of the header (owner statement 2026-09-30).** Source-measured
candidates, to be confirmed or replaced by that analysis before any visual task is written:

- `.panel-shell__header-action` declares no `font`/`font-family` (`primitives.css:1409-1420`) → computes Arial.
  (Also recorded as debt in `odd/tasks/panel-sidebar-refine.md`.)
- The reference shows a **vertical divider between the notification bell and the account control**; none exists today.
- The reference's back control is a **bordered rounded square**; today it is `border: 1px solid transparent`
  (`primitives.css:1425-1440`). Boundary colour must resolve through `--border-strong`, not decorative `--border`
  (DS-TKN-13, spec ~913).
- Breadcrumb button has zero padding and no focus-visible rule (`primitives.css:1186`).
- Notification popover close and footer controls have no 44px target and no focus-visible rule
  (`primitives.css:1459, 1469`); account menu items have no explicit focus-visible rule.
- **PNL-APP-10** (`openspec/specs/panel-app/spec.md:149`) requires the header to expose notification-bell and avatar
  affordances for any authenticated user, tier-unqualified. Today the mobile bar exposes neither (brand + menu only)
  and the tablet tier exposes no header at all (`.panel-shell__header-row` is hidden below 64rem,
  `primitives.css:1226-1229`). The references agree: `mobilePanelShell.png` shows menu + brand + bell + avatar;
  `TabletPanelShell.png` shows bell + avatar at the top-right of the content.

## Adjudication rules applied

- **The archived canonical spec beats the reference image.** References control **geometry and layout, not palette**.
- **Recorded interpretation (owner, 2026-09-30): the reference header omits the focus control, but the canonical
  CC-2 / DS-CC-2 require a keyboard-operable activating control.** The owner has now resolved this by retiring the
  feature instead of keeping the control: the two requirements MUST be amended in the same change, never silently
  dropped (same rule the sidebar unit applied to DS-SHELL-1).
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

- [ ] **H0 — retire focus mode (settled).** Remove the `focusMode`/`onFocusModeChange` props, the internal state,
  `setFocusMode`, `closeFocusMode`, the Escape effect, `keepFocusInFocusMode`, the header control, the
  `panel-shell--focus-mode` class, the `focusMode`-driven `aria-hidden` on the sidebar and inspector, the
  `role`/`aria-label` on `#panel-main-content`, and the "Salir del modo foco" button. **Keep** `#panel-main-content`
  `tabIndex={-1}` (the skip-link target) and the drawer's own focus behaviour. Delete the focus-mode test
  (`PanelShell.test.tsx:274-287`). Amend CC-2 and DS-CC-2 in the canonical specs. No CSS to delete — no rules exist.
  Removes the dead feature and its canonical liability. **Spec-amendment form pending owner confirmation.**
- [ ] **H1+ — visual header.** Not written yet: blocked on the owner's visual analysis of the header.

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

## Route decisions

| Task | Route | Trigger evidence |
| --- | --- | --- |
| H0 | inline | deletion confined to files already read; no research needed |
| H1+ | pending | decided with the owner's visual analysis |

## Progress and evidence

_None yet. H0 has not started; the spec-amendment form is pending owner confirmation._

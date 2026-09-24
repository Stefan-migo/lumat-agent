# ODD — panel-text-zoom-reflow

## Objective

Make the panel survive **200% text zoom** without collapsing or clipping: the shell
rail and every layout track minimum must be immune to the root font-size doubling,
and the shell's remaining 200%-zoom overflow must be gone.

## Problem

At **viewport 1024 with 200% text zoom**, the Agenda layout breaks:

- `.agenda-page__layout` computes to `640px 0px` — the register column collapses to zero.
- `.panel-shell__content` reports `scrollWidth 716` vs `clientWidth 544`.

Mechanism, verified by reading the CSS:

1. `.agenda-page__layout` switches to two columns on a **viewport** media query
   (`primitives.css:2121`, `@media (min-width: 64rem)`) whose first track minimum is
   `minmax(20rem, 1fr)` (`:2122`). `20rem` resolves against the **root font-size**, so at
   200% text zoom the minimum becomes 640px.
2. The content box shrinks to 544px because the shell rail is
   `var(--shell-rail-expanded)` (`primitives.css:1060`) and that token is `15rem`
   (`tokens.css:130`) — **240px at default text size, 480px at 200%**.
3. Both defects land together: the minimum grows while the container shrinks.

Measured confirmation of (2): the sibling unit's shell-aware table records viewport
1024 → content 784px, i.e. a **240px** rail — which is exactly `15rem × 16px`. The same
table's 200%-zoom reading of 544px is exactly `1024 − 480`, i.e. `15rem × 32px`.

**This is a class-level defect, not Agenda's.** The same mechanism affects the rail and
any two-column page. It was deliberately left unfixed by `agenda-design-alignment`
(PR #351) because band-aiding it inside Agenda would only mask its instance.

## Why

`DESIGN_SYSTEM.md:267` ("Preserve 200% text zoom without clipping or lost actions") and
`:554` ("Text resizes to 200%; narrow reflow preserves content and actions") are part of
the shipped contract, and `:308` specifies the desktop sidebar as an absolute width.
Text zoom is an accessibility path, not a cosmetic one: a register column computing to
`0px` is lost content.

## Scope (authorized by the owner)

**In:** `web/src/tokens/tokens.css` (shell rail tokens), `web/src/components/primitives/
primitives.css` (shell rail grid, `.panel-shell__breadcrumbs`, `.panel-shell__footer-nav`,
`.agenda-page__layout` track minimums), and their tests/stories.

**Out:**

- **Narrowing the rail to the `192px` that `DESIGN_SYSTEM.md:308` still claims.** The
  shipped rail is 240px. Changing the width is a visual change for every page and a
  separate design decision — see Decision D2 and the drift finding below.
- `TechnicianAgenda` deviations (uppercase section title, `--radius-md`).
- The global `.btn` missing `min-height: 40px` (`DESIGN_SYSTEM.md:435`).
- The `AgendaPage.test.tsx` 5000ms suite flake (parallelism, not layout).
- The parked 403 unit on `origin/odd/agenda-operator-technicians`.

## Constraints

- **Strict TDD ON.** Runner: `cd web && npm test`. RED must be observed before GREEN.
- No linter, no formatter, no standalone type checker. The only type check is
  `cd web && npm run build` (`tsc -b`).
- CSS contract tests read the stylesheet with `readFileSync` and assert declarations.
  Precedent: `web/src/components/pages/Dashboard.test.tsx:99-105`; token-level precedent:
  `web/src/tokens/tokens.test.ts`.
- Media queries must use rem literals: `var()` is not valid in a media condition. Note
  that **`rem` inside a media query resolves against the initial font size and does NOT
  follow text zoom** — that asymmetry is the root cause, not a fixable detail.
- `jsdom` has no layout: no vitest test can prove reflow. Chromium measurement is the
  only proof; the CSS contract tests are a regression guard, not the evidence.
- Operator-facing copy in Spanish; code, identifiers, comments, tests and docs in English.
- Measurement discipline from the sibling unit: own worktree Storybook on port **6011**
  (never 6006), Playwright scripts in `/tmp/opencode/` only, temporary story deleted
  before `git status --porcelain` is required to be empty.

## Graph check

`graphify query "panel shell layout rail agenda page two column grid"` → nodes consulted:
`PageFrame()` and `shared/PageFrame.tsx`, `domain/PanelShell.tsx`, `Button()`,
`pages/AgendaPage.tsx` / `AgendaPage()`, `shared/agendaTime.ts`, and the
`web/src/components/primitives/primitives.css` community. `graphify-out/` was copied into
this worktree by `rapso worktree create`; no rebuild was needed for this map.

## Findings

### F1 — shell rail doubles under text zoom (the container shrink)

`--shell-rail-expanded: 15rem` (`tokens.css:130`) feeds `grid-template-columns:
var(--shell-rail-expanded) minmax(0, 1fr)` (`primitives.css:1060`). At 200% it consumes
480px of a 1024px viewport. `--shell-rail-compact: 4rem` (`tokens.css:129`, used at
`primitives.css:1441`) has the same defect: 64px → 128px on a 375px viewport.

### F2 — `.agenda-page__layout` track minimum doubles (the collapse)

`minmax(20rem, 1fr)` (`primitives.css:2122`) becomes a 640px floor at 200%, exceeding the
544px container, so the second track collapses to `0px`.

`20rem` at the default 16px root is **exactly 320px**, which is why the px fix below is a
zero-visual-change swap rather than a redesign.

### F3 — `DESIGN_SYSTEM.md:308` is stale by 48px

The DS says "Preserve the current compact **192px** desktop sidebar". The shipped token is
`15rem` = **240px**, and the sibling unit's own measurement table confirms 240px in the
running shell. This drift is reported, not silently resolved here (D2).

### F4 — breadcrumbs overflow at 200% (to be measured before fixing)

`.panel-shell__breadcrumbs ol` (`primitives.css:1036`) is a `flex` row with no
`min-width: 0` and no wrap. `--text-lg` breadcrumb text at 200% has no shrink path, so it
overflows the header row. Candidate mechanism: shrink-and-ellipsize the trail, matching
the footer-nav label rule at `:1378`. Not yet reproduced in this unit.

### F5 — footer nav at 375px (reported, likely a false positive — verify first)

`:1374` declares `repeat(4, minmax(0, 1fr))` and `:1376-1378` give the button
`min-width: 0` plus an ellipsizing span. Those are exactly the declarations that should
prevent the reported overflow, so the prior report needs a measurement before anything is
changed. The sibling unit's own lesson stands: two of six reported deviations there were
false positives.

## Decisions

- **D1 — layout arithmetic is px, typography is rem.** A track minimum participates in
  layout arithmetic against a breakpoint that text zoom cannot see; expressing it in `rem`
  makes it scale into a container that does not. The minimum becomes `320px` (identical to
  `20rem` at the default root) and the rail tokens become `240px` / `64px` (identical to
  `15rem` / `4rem`). Text still scales — only the layout floor stops scaling.
- **D2 — the rail keeps its shipped 240px width.** `DESIGN_SYSTEM.md:308`'s 192px is
  stale; adopting it inside a reflow fix would silently re-lay-out every panel page. The
  drift is reported to the owner as its own decision.
- **D3 — no container queries.** The repo has zero `@container` / `container-type`
  precedent, and a container query on `.agenda-page__layout` cannot work anyway (an
  element is not its own query container) — it would need a JSX wrapper. Introducing the
  pattern is not justified by a defect that two literal swaps remove.
- **D4 — `auto-fit` is rejected.** `repeat(auto-fit, minmax(min(20rem, 100%), 1fr))` does
  collapse correctly, but it forces both tracks to `1fr` and thereby changes the shipped
  desktop proportion from 1:1.35. Rejected as a redesign smuggled into a bugfix.
- **D5 — F5 is not fixed on report.** Footer-nav overflow gets measured before any change.

## Tasks

| ID | Task | Route |
|----|------|-------|
| T1 | Baseline measurement at `66625430`: `PanelShell` + `AgendaPage` in real Chromium, 11 widths, text zoom 200%, recording track sizes, content box, and the F4/F5 overflow readings. | delegated (shell + Storybook 6011 + Playwright) |
| T2 | RED: CSS contract assertions — rail tokens declared in px and `.agenda-page__layout` two-column minimum declared in px. Observe the failure. | delegated (writer) |
| T3 | GREEN: `tokens.css` rail tokens → `240px` / `64px`; `primitives.css:2122` → `minmax(320px, 1fr)`. Observe the pass. | delegated (writer, same unit of work as T2) |
| T4 | F4 breadcrumbs: reproduce at 200%, then fix with the mechanism the measurement supports (or record it as not-reproduced). | delegated |
| T5 | Re-measure with the T1 harness and record the before/after table. | delegated |
| T6 | Full web suite (`cd web && npm test`) + `npm run build`. | delegated per-action |

## Delivery

Forecast: two literal swaps plus contract assertions and possibly two small shell rules —
well under 30 authored changed lines. Far inside the ~400-line review budget → single PR,
no chained slices. Label `type:bug`.

## Progress / Evidence

- [ ] T1 baseline measurement
- [ ] T2 RED observed
- [ ] T3 GREEN observed
- [ ] T4 breadcrumbs resolved
- [ ] T5 after-measurement
- [ ] T6 suite + build

## Next step

Run T1 to re-confirm the mechanism on the current `main`, then T2/T3.

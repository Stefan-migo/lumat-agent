# ODD — agenda-design-alignment

## Objective

Align the operator Agenda surface (`AgendaPage` + `AgendaCalendar`) with the shipped
design system, and close the measurement gap that left its narrow-viewport behavior
unverified inside the real application shell.

## Problem

The owner reported that the Agenda page "breaks when shrinking the viewport". Two
measurement passes at six widths could not reproduce it. A sub-agent audit then
reported six design-system deviations; verifying each one against the code reduced
them to two real ones plus one judgment call, and exposed a **method gap**: every
prior measurement ran in Storybook **without** the application shell, so the 192px
sidebar was never subtracted and the `1025–1279px` band was never measured.

## Why

The owner explicitly asked to review the whole Agenda page and align it with the
current design system. Alignment must be evidence-based: report only deviations that
survive verification against `web/DESIGN_SYSTEM.md` and the shipped CSS, and measure
layout in the shell that users actually see.

## Scope (authorized by the owner)

**In:** `web/src/components/pages/AgendaPage.tsx`,
`web/src/components/shared/AgendaCalendar.tsx`,
`web/src/components/primitives/primitives.css` (Agenda selectors only), and their
tests/stories.

**Out:** `TechnicianAgenda` (owner chose AgendaPage-only). The global `.btn` 40px
minimum control height (`DESIGN_SYSTEM.md:435`) is also out: `.btn` has no
`min-height`, so it renders ~34px, but the blast radius is every button in the panel,
not Agenda — it belongs in its own unit.

## Constraints

- **Strict TDD ON.** Runner: `cd web && npm test`. RED must be observed before GREEN.
- No linter, no formatter, no standalone type checker. The only type check is
  `cd web && npm run build` (`tsc -b`).
- CSS contract tests read the stylesheet with `readFileSync` and assert declarations.
  Precedent: `web/src/components/pages/Dashboard.test.tsx:99-105`.
- Media queries must use rem literals: `var()` is invalid inside `@media`, so the
  `--bp-*` tokens are documentation plus Storybook viewport presets, never usable in
  a media condition.
- Operator-facing copy in Spanish; code, identifiers, comments, tests and docs in
  English.

## Deviations confirmed as real

1. `.agenda-calendar__weekday` forces `text-transform: uppercase` → renders `LUN`,
   `MAR`. Violates `DESIGN_SYSTEM.md:263` (sentence case) and `:266` (all caps only
   for short machine/status labels). Same class of fix as the removed dashboard `HOY`.
2. `.agenda-calendar` declares `border-radius: var(--radius-md)` while its grid
   sibling `.data-region` (the register) declares `var(--radius-lg)`.

## Deviations rejected after verification (do not implement)

- "Breakpoints hardcoded in rem instead of `--bp-*`" — `var()` cannot be used in
  `@media` in any browser; rem literals are the only option and the whole stylesheet
  uses them.
- "`Nueva visita` should live in `PageFrame.actions`" — no precedent for a primary
  create action in the header; `ClientesList` and `KbList` keep theirs in content.

## Tasks

| ID | Task | Route |
|----|------|-------|
| T1 | RED: add CSS contract assertions to `AgendaPage.test.tsx` — no `text-transform: uppercase` on `.agenda-calendar__weekday`, and `.agenda-calendar` declares `border-radius: var(--radius-lg)`. Observe the failure. | direct inline |
| T2 | GREEN: remove the uppercase declaration; set the calendar radius to `--radius-lg`. Observe the pass. | direct inline |
| T3 | Shell-aware measurement (`PanelShell` + `AgendaPage`) across the breakpoint bands plus 200% zoom; document the effective content width and the previously unmeasured `1025–1279px` band. | delegated (needs shell + Storybook + Playwright) |
| T4 | Full web suite (`npm test`) + `npm run build`. | delegated per-action |

## Decisions

- **D1 — radius `--radius-lg`.** `.agenda-calendar` is the card idiom verbatim
  (border + elevated background + `--space-4` padding). `DESIGN_SYSTEM.md:277` says
  cards use `--radius-lg`; its grid sibling `.data-region` is `--radius-lg`; the
  Dashboard unit already made this same md→lg correction. Reversible in one line.
- **D2 — `Nueva visita` stays in content.** No precedent for a primary create action
  in `PageFrame.actions`; list pages keep theirs in content too.
- **D3 — no ≥1280 treatment added.** `DESIGN_SYSTEM.md:325` is descriptive, not
  normative; the two-column layout from `min-width: 64rem` upward is allowed.
- **D4 — breakpoints stay rem literals.** See "Deviations rejected".

## Delivery

Forecast: fewer than 20 authored changed lines plus tests. Far under the ~400-line
review budget → single PR, no chained slices.

Delivered as **PR #351** (`type:bug`), base `main`.

## Progress / Evidence

- [x] T1 RED observed — `AgendaPage.test.tsx` CSS contract failed on the uppercase assertion.
- [x] T2 GREEN observed — assertion passes after the `primitives.css` edit.
- [x] T3 shell-aware measurement recorded — see below.
- [x] T4 suite + build recorded — `732 passed / 86 files`; `npm run build` clean.

Commits:

- `0b25f733` docs(odd): record the agenda-design-alignment unit
- `85d679f0` fix(web): align the agenda calendar with the design system

Flake note (belongs to the separate `AgendaPage` flake item): the first full-suite
run reported `4 failed | 728 passed`, all four 5000ms timeouts in `AgendaPage.test.tsx`
(`shows actionable inline mutation failures…`, `creates an appointment from the agenda…`).
An immediate re-run with identical code reported `732 passed`, zero failures. The flake
is therefore CPU-contention driven and reproduces **without** Storybook or Playwright
running — the earlier attribution to Storybook contention was too narrow.

## T3 — shell-aware measurement result

Measured `PanelShell` + `AgendaPage` (ready state) in real Chromium. Effective content
box is `.panel-shell__content`.

| Viewport | Content width | Two-column | Real Agenda overflow |
|---:|---:|:---:|---|
| 375 | 375 | no | none (shell footer labels overflow — see finding 2) |
| 639 | 639 | no | none |
| 640 | 640 | no | none |
| 768 | 768 | no | none |
| 1023 | 1023 | no | none |
| 1024 | 784 | yes | none |
| 1100 | 860 | yes | none |
| 1200 | 960 | yes | none |
| 1279 | 1039 | yes | none |
| 1280 | 1040 | yes | none |
| 1440 | 1200 | yes | none |

At **normal text size there is no break at any width from 375 to 1440** — the owner's
original complaint "breaks when shrinking the viewport" is still not reproducible inside
the real shell either.

### Finding 1 (out of scope — class-level defect): text-zoom reflow

At **viewport 1024 with 200% text zoom**, the Agenda layout breaks:

- `.agenda-page__layout` computes to `640px 0px` — the register column collapses to zero.
- `.panel-shell__content` reports `scrollWidth 716` vs `clientWidth 544`.

Mechanism (verified by reading the CSS, not just by measurement):

- `.agenda-page__layout` switches to two columns on a **viewport** media query
  (`@media (min-width: 64rem)`), and its first track minimum is `minmax(20rem, 1fr)`.
- `20rem` resolves against the **root font-size**, so at 200% text zoom the minimum
  becomes 640px while the available content box shrinks to 544px.
- The content box shrinks because the shell rail is `var(--shell-rail-expanded)`
  (rem-based) and therefore also doubles under text zoom, from 192px to 384px.
- `DESIGN_SYSTEM.md:308` specifies the rail as a **compact 192px** desktop sidebar
  (absolute), and `:267`/`:554` require 200% text zoom to preserve content and actions.

This is a **class-level defect, not Agenda-specific**: the same mechanism affects the
shell rail and any two-column page, and the measurement also found 200%-zoom overflow in
`.panel-shell__breadcrumbs` and a shell footer-nav label overflow at 375px. Band-aiding
it inside Agenda would leave the shell defect in place. Recommended as its OWN unit.

### Finding 2 (out of scope — shell): footer navigation overflow at 375px

At viewport 375 the `.panel-shell__footer-nav` label spans ("Notificaciones",
"Agente Lumat", "Conversaciones", "Agenda" at 200% zoom) exceed their cells. The panel
page itself is `375px` wide, so this is the shell's, not Agenda's.

## Decisions added by measurement

- **D5 — do not band-aid the text-zoom reflow inside this unit.** It is a shell-level
  class defect; Agenda would only mask its instance. Opened as a separate unit pending
  the owner's call.

## Next step

Unit closed. Delivered as PR #351.

Work handed off to its own unit, per the owner's call: the **200% text-zoom reflow**
defect (Finding 1) — the shell rail's rem doubling plus the `minmax(20rem, 1fr)` track
minimum — and the shell footer-nav overflow at 375px (Finding 2). Neither is fixed here.

Still open and owned by the owner: the original "breaks when shrinking the viewport"
report remains unreproduced after 11 widths measured **inside the real shell**.

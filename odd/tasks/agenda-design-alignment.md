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

## Progress / Evidence

- [ ] T1 RED observed
- [ ] T2 GREEN observed
- [ ] T3 shell-aware measurement recorded
- [ ] T4 suite + build recorded

## Next step

Start T1 (RED) in this worktree.

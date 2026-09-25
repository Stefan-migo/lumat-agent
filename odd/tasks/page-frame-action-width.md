# ODD — page-frame-action-width

## Objective

A page-level action rendered as a direct child of `PageFrame` must hug its label. Today
it stretches to the full width of the page content, which the page never asked for.

## Problem

The owner reported it on the Agenda ("el botón agregar cita o agregar a la agenda usa el
full width se ve horrible") → `Nueva visita`, `AgendaPage.tsx:203`. Verifying the
mechanism turned one report into **three instances of the same defect**.

Mechanism: `PageFrame` renders its children into `.page-frame__content`, a
`display: grid` container (`primitives.css:803-807`) with no `justify-items`. A grid item
defaults to `justify-self: stretch`, so **any `.btn` placed directly in that grid is
stretched to the full track width**. The stretch is imposed by the shared container — the
page does not opt into it, and `.btn` is `display: inline-flex` (`primitives.css:23-24`),
so on its own it would hug its label.

## Instances (all three verified in the code)

| Page | Action | How it becomes a bare grid child |
|------|--------|----------------------------------|
| `AgendaPage.tsx:203` | `Nueva visita` | direct child of `PageFrame` |
| `AutomationRulesPage.tsx:47` | `Crear regla` (admin only) | `{user?.role === "admin" && onOpenCreate ? <Button …/> : null}` |
| `KbDocumentDetail.tsx:108` | `Reintentar` (error state) | `{state === "error" ? <Button …/> : null}` |

The selector also covers the anchor form: `Button` renders `<a className="btn …">` when
`href` is set (`Button.tsx:32-45`), so a link-shaped action in the same position is fixed
too.

## Why fix it at the primitive

Per-page wrappers would fix these three pages and leave the trap armed for the next one.
The defect is owned by the container, so the guard belongs next to it: one declaration,
covering both element forms, in every page, today and later. This is also why the unit is
named after the page frame, not after Agenda.

## Scope (authorized by the owner)

**In:** `web/src/components/primitives/primitives.css` (one guard declaration beside
`.page-frame__content`), and a new `web/src/components/shared/PageFrame.test.tsx`.

**Out:**

- **Not moving any action into `PageFrame.actions` — SUPERSEDED 2026-09-25.** This scope
  boundary followed `agenda-design-alignment` D2, which `agenda-visual-alignment` (PR #362)
  reversed at the owner's request: `Nueva visita` now lives in `PageFrame.actions`. The guard
  this unit shipped is unaffected — it protects a bare `.btn` in `.page-frame__content`
  regardless of where a given page chooses to put its action.
- No JSX change to `AgendaPage.tsx`, `AutomationRulesPage.tsx` or `KbDocumentDetail.tsx`.
- `.page-frame__banner` children are **not** touched: the retry button at
  `ConversationThread.tsx:92` renders inside the banner, which is a distinct container
  with its own grid, and no owner report covers it. If the banner should also hug, that
  is a separate call.
- `TechnicianAgenda`, the global `.btn` `min-height: 40px`, the suite flake, and the
  `panel-text-zoom-reflow` unit.

## Decision

- **D1 — guard the container, not each page.** One declaration at the primitive fixes all
  three instances and every future one; three page-local wrappers would fix the symptom
  three times and leave the class in place.

## Constraints

- **Strict TDD ON.** Runner: `cd web && npm test`. RED must be observed before GREEN.
- No linter, no formatter, no standalone type checker. The only type check is
  `cd web && npm run build` (`tsc -b`).
- CSS contract tests read the stylesheet with `readFileSync` and assert declarations.
  Precedent: `web/src/components/pages/Dashboard.test.tsx:99-105`.
- `jsdom` has no layout, so the contract test is a regression guard, not the visual proof.
  The visual proof is a Chromium width reading of a real page action.
- Operator-facing copy in Spanish; code, identifiers, comments, tests and docs in English.
- Measurement discipline: own-worktree Storybook on port **6011** (never 6006), Playwright
  scripts in `/tmp/opencode/` only, temporary story deleted before the branch is finished.

## Graph check

`graphify query "PageFrame content grid Button page-level action full width"` → nodes
consulted: `PageFrame()` / `shared/PageFrame.tsx`, `Button()`, `pages/AgendaPage.tsx`
(`AgendaPage()`, `ActionFeedback`), `pages/AgentChat.tsx`, and the `pages/ClientesList`
community. `graphify-out/` was copied into this worktree by `rapso worktree create`.

## Tasks

| ID | Task | Route |
|----|------|-------|
| T1 | RED: new `web/src/components/shared/PageFrame.test.tsx` asserting the guard declaration for `.page-frame__content > .btn`. Observe the failure. | delegated (writer) |
| T2 | GREEN: add the guard declaration beside `.page-frame__content`. Observe the pass. | delegated (writer, same unit of work as T1) |
| T3 | Visual proof: Chromium width reading of the Agenda action inside `PanelShell` before/after — full content width → label width. | delegated |
| T4 | Full web suite (`cd web && npm test`) + `npm run build`. | delegated per-action |

## Delivery

One production declaration plus a small test → single PR against `main` (`66625430`),
label `type:bug`, well inside the ~400-line review budget. No chained slices.

Delivered as **PR #353** — https://github.com/Stefan-migo/lumat-agent/pull/353

Native review: `gentle-ai review assess --base-ref 66625430 --committed-only` → risk
**medium** (`executable_change` on the test file), 3 changed paths, 122 changed lines,
**`review_due: false`** with reason `under_budget`. No native review was due for this
slice; the tier and the reason are recorded rather than left implicit.

## Progress / Evidence

- [x] T1 RED observed — `PageFrame.test.tsx:8` failed: no `justify-self: start` on
      `.page-frame__content > .btn`.
- [x] T2 GREEN observed — focused run: `1 file passed, 1 test passed`.
- [x] T3 visual proof recorded — Chromium at viewport 1024: the action measured **736px**
      before the guard, identical to the 736px content box, and **112.5px** after it.
- [x] T4 suite + build recorded — `Test Files 87 passed (87)`, `Tests 738 passed (738)`;
      `npm run build` passed.

Commits:

- `e1d63829` docs(odd): record the page-frame-action-width unit
- `ae65b937` fix(panel): prevent page actions stretching in PageFrame

The reading came from composing `PanelShell` + `AgendaPage` in a Storybook served from
this branch on port 6011 and reading the action's bounding rect. Playwright's bundled
Chromium was missing in this environment; the reading ran on system Chrome at
`/usr/bin/google-chrome`.

## Next step

Unit complete and delivered as **PR #353**. Merge is the owner's decision, not this unit's.

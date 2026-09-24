# ODD — panel-text-zoom-reflow

## Objective

Make the panel survive **200% text zoom** without collapsing or clipping: the shell
rail and every layout track minimum must be immune to the root font-size doubling,
and the shell's remaining 200%-zoom overflow must be gone.

## Problem

At **viewport 1024 with 200% text zoom**, the Agenda layout breaks:

- `.agenda-page__layout` computes to `640px 0px` — the register column collapses to zero.
- `.panel-shell__content` reports `scrollWidth 716` vs `clientWidth 544`.

Mechanism, verified by reading the CSS and then by measurement:

1. `.agenda-page__layout` switches to two columns on a **viewport** media query
   (`primitives.css`, `@media (min-width: 64rem)`) whose first track minimum is
   `minmax(20rem, 1fr)`. `20rem` resolves against the **root font-size**, so at 200% text
   zoom the minimum becomes 640px.
2. The content box shrinks to 544px because the shell rail is
   `var(--shell-rail-expanded)` and that token is `15rem` — **240px at default text size,
   480px at 200%**.
3. Both defects land together: the minimum grows while the container shrinks.

**This is a class-level defect, not Agenda's.** The same mechanism affects the rail and
any two-column page. It was deliberately left unfixed by `agenda-design-alignment`
(PR #351) because band-aiding it inside Agenda would only mask its instance.

## Why

`DESIGN_SYSTEM.md:267` ("Preserve 200% text zoom without clipping or lost actions") and
`:554` ("Text resizes to 200%; narrow reflow preserves content and actions") are part of
the shipped contract, and `:308` specifies the desktop sidebar as an absolute width.
Text zoom is an accessibility path, not a cosmetic one: a register column computing to
`0px` is lost content.

## Root cause

`rem` inside a **media query** resolves against the initial font size and does **not**
follow text zoom, while ordinary `rem` does. So a layout floor expressed in `rem` grows
into a container that does not grow with it — and no media query can see text zoom,
because text zoom is not a viewport change.

**The correction is therefore: layout arithmetic is px; typography stays rem.**

## Scope (authorized by the owner)

**In:** `web/src/tokens/tokens.css` (shell rail tokens), `web/src/components/primitives/
primitives.css` (`.agenda-page__layout` track minimums), and their tests/stories.

**Out:**

- **Narrowing the rail to the `192px` that `DESIGN_SYSTEM.md:308` still claims.** The
  shipped rail is 240px, and the owner confirmed it stays 240px. Changing the width is a
  visual change for every page and a separate design decision — see F3 and D2.
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
- Media queries must use rem literals: `var()` is not valid in a media condition.
- `jsdom` has no layout: no vitest test can prove reflow. Chromium measurement is the
  only proof; the CSS contract tests are a regression guard, not the evidence.
- Operator-facing copy in Spanish; code, identifiers, comments, tests and docs in English.

## Graph check

`graphify query "panel shell layout rail agenda page two column grid"` → nodes consulted:
`PageFrame()` and `shared/PageFrame.tsx`, `domain/PanelShell.tsx`, `Button()`,
`pages/AgendaPage.tsx` / `AgendaPage()`, `shared/agendaTime.ts`, and the
`web/src/components/primitives/primitives.css` community. The copied report was stale
(`b181d5b2`), so the graph was refreshed incrementally and re-clustered.

## Findings

### F1 — shell rail doubles under text zoom (the container shrink) — FIXED

`--shell-rail-expanded: 15rem` feeds the shell grid. At 200% it consumed 480px of a
1024px viewport. `--shell-rail-compact: 4rem` had the same defect: 64px → 128px on a
375px viewport. Both are now absolute.

### F2 — `.agenda-page__layout` track minimum doubles (the collapse) — FIXED

`minmax(20rem, 1fr)` became a 640px floor at 200%, exceeding the 544px container, so the
second track collapsed to `0px`. `20rem` at the default 16px root is **exactly 320px**,
which is why the swap is a zero-visual-change fix rather than a redesign.

### F3 — `DESIGN_SYSTEM.md:308` is stale by 48px — REPORTED, NOT CHANGED

The DS says "Preserve the current compact **192px** desktop sidebar". The shipped token is
`15rem` = **240px**, and the shell-aware measurement confirms 240px in the running shell.
The owner confirmed the rail stays 240px; the DS drift is reported, not silently resolved.

### F4 — breadcrumbs overflow at 200% — RESOLVED, no separate fix needed

Measured at baseline 1024 / 200%: `.panel-shell__breadcrumbs` and its `ol` each reported
`scrollWidth 288` vs `clientWidth 270` — a real overflow. **After the rail fix both report
`510 / 510`: no overflow.** F4 was downstream of F1, not an independent defect. Had it been
"fixed" in the breadcrumbs, the rail would have stayed broken and the trail would have been
mangled for nothing.

### F5 — footer nav at 375px — FALSE POSITIVE, no change made

At 375 / 200% no footer button overflows. The label spans do clip their text
(`Notificaciones` `163/65`, `Agente Lumat` `158/61`, `Conversaciones` `183/65`,
`Agenda` `88/65`, `Panel` `63/63`), but that is the existing rule at `:1378`
(`overflow: hidden; text-overflow: ellipsis`) doing exactly its job: clipped text inside
its cell, not a broken layout. This is the third reported deviation in this thread that
dissolves on measurement.

## Decisions

- **D1 — layout arithmetic is px, typography is rem.** A track minimum participates in
  layout arithmetic against a breakpoint that text zoom cannot see; expressing it in `rem`
  makes it scale into a container that does not. The minimum becomes `320px` (identical to
  `20rem` at the default root) and the rail tokens become `240px` / `64px` (identical to
  `15rem` / `4rem`). Text still scales — only the layout floor stops scaling.
- **D2 — the rail keeps its shipped 240px width** (`DESIGN_SYSTEM.md:308`'s 192px is
  stale). Confirmed by the owner.
- **D3 — no container queries.** The repo has zero `@container` / `container-type`
  precedent, and a container query on `.agenda-page__layout` cannot work anyway (an
  element is not its own query container) — it would need a JSX wrapper.
- **D4 — `auto-fit` is rejected.** It collapses correctly but forces both tracks to `1fr`,
  changing the shipped desktop proportion from 1:1.35. A redesign smuggled into a bugfix.
- **D5 — F5 is not fixed on report.** It was measured before any change, and the
  measurement dissolved it.
- **D6 — F4 was not fixed either, and needed no fix.** It was a symptom of F1; the
  measurement after the rail change proves it.

## Tasks

| ID | Task | Route | State |
|----|------|-------|-------|
| T1 | Baseline measurement at 200% text zoom, plus the normal-size readings and the F4/F5 checks. | delegated (shell + Storybook 6011 + Playwright) | done |
| T2 | RED: CSS contract assertions — rail tokens in px, `.agenda-page__layout` minimum in px. | delegated (writer) | done |
| T3 | GREEN: the three literal swaps. | delegated (writer) | done |
| T4 | F4 breadcrumbs, measure-first. | delegated | done (dissolved) |
| T5 | Re-measure with the T1 harness; normal-size numbers must be identical. | delegated | done |
| T6 | Full web suite + build. | delegated per-action | done |

## Delivery

Forecast: two literal swaps plus contract assertions. Actual: **three literals and ten
test lines** — well inside the ~400-line review budget → single PR, no chained slices.
Label `type:bug`. Merge is the owner's decision.

Native review: `gentle-ai review assess --base-ref 92ec5c50 --committed-only` → risk
**medium** (`executable_change` on `AgendaPage.test.tsx`), 5 changed paths, 186 changed
lines, **`review_due: false`** with reason `under_budget`. No native review was due.

## Progress / Evidence

- [x] T1 baseline measurement
- [x] T2 RED observed
- [x] T3 GREEN observed
- [x] T4 breadcrumbs resolved (dissolved by F1's fix)
- [x] T5 after-measurement (normal-size numbers identical)
- [x] T6 suite + build

**T1/T5 — measured in real Chromium, composing `PanelShell` + `AgendaPage` in a Storybook
served from this branch (port 6011; 6006 serves the main worktree and shows stale code).**
Text zoom 200% is simulated with `document.documentElement.style.fontSize = '32px'`; real
browser zoom does not reproduce this, because it shrinks the CSS viewport and the media
query stops applying. Playwright's bundled Chromium is missing in this environment, so the
readings ran on system Chrome at `/usr/bin/google-chrome`.

| Viewport | Text zoom | Before (tracks / content) | After (tracks / content) |
|---:|---:|---|---|
| 1024 | 200% | `640px 0px` · `716 / 544` | `320px 396px` · `784 / 784` |
| 1280 | 200% | `640px 92px` · `800 / 800` | `413.609px 558.391px` · `1040 / 1040` |
| 1440 | 200% | `640px 252px` · `960 / 960` | `481.688px 650.312px` · `1200 / 1200` |

Normal text size, before and after — **identical, as the fix requires**:

| Viewport | Text zoom | Tracks | Content |
|---:|---:|---|---|
| 1024 | 100% | `320px 396px` | `784 / 784` |
| 1440 | 100% | `481.688px 650.312px` | `1200 / 1200` |

- T2 RED: the new assertions failed as designed — the token assertion received `4rem`
  where it expected `64px`, and the Agenda assertion found `minmax(20rem, 1fr)` where it
  expected the px contract. `2 failed | 39 passed`.
- T3 GREEN: focused run `2 files | 41 tests` passed. Token consumers checked: only the two
  shell grid consumers (expanded and compact) in `primitives.css`; no other source depends
  on their rem-ness.
- T6: `Test Files 87 passed (87)`, `Tests 740 passed (740)`; `npm run build` passed
  (`tsc -b` + Vite, only the pre-existing chunk-size warning). Re-run independently by the
  orchestrator: same `87 / 740` result.

Commits:

- `159e7127` docs(odd): record the panel-text-zoom-reflow unit
- `a41ce6fd` fix(panel): keep layout tracks stable at text zoom

The branch was rebased onto `origin/main` (`92ec5c50`, the merge of PR #353) before the
work, so the base is current rather than the stale `66625430`.

## Next step

Unit complete locally with a clean tree. Delivery (push + pull request) is pending the
owner's word, as is the merge.

# ODD — conversation-workspace-text-zoom

## Objective

The conversation workspace must survive **200% text zoom** without losing or clipping a
column: the thread and its inspector both stay reachable.

## Problem

`.conversation-workspace` is a two-column grid with **rem** track minimums and a clipping
container:

```css
.conversation-workspace { display: grid;
  grid-template-columns: minmax(24rem, 1fr) minmax(18rem, 24rem);
  ... height: clamp(30rem, calc(100dvh - 15rem), 46rem);
  ... overflow: hidden; }
```

At 200% text zoom those minimums resolve to **768px + 576px = 1344px of minimum** inside a
784px content box (viewport 1024, rail absolute since PR #355). The grid cannot fit, and
because the container declares `overflow: hidden` the failure mode is **clipping**, not a
horizontal scrollbar: the inspector column is the one that gets cut.

Its single-column fallback is `@media (min-width: 40rem) and (max-width: 63.99rem)`, a
**viewport** media query. At viewport 1024 with 200% text zoom it does not fire, so the
two-column rule stays in force — the identical trap documented in
`odd/tasks/panel-text-zoom-reflow.md`.

This is the second instance of the class fixed for the Agenda in PR #355. That PR fixed the
shell rail and `.agenda-page__layout` and deliberately did not touch this one; the gap is
recorded in the PR #355 comment thread.

**This is a repro candidate, not a claim.** Three deviations reported in this thread
dissolved on measurement — including one in the same file. The baseline gets measured
before a single declaration is written.

## Why

`DESIGN_SYSTEM.md:267` ("Preserve 200% text zoom without clipping or lost actions") and
`:554` are part of the shipped contract. A conversation inspector that is cut off at an
accessibility zoom level is lost content, and the sibling unit established the correction:
**layout arithmetic is px, typography stays rem.**

## Scope (authorized by the owner)

**In:** `web/src/components/primitives/primitives.css` — the `.conversation-workspace` track
minimums — plus the CSS-contract test that owns that rule (locate the existing one before
adding a new file).

**Out:**

- **The `height: clamp(30rem, calc(100dvh - 15rem), 46rem)`.** It also scales with the root
  font-size (the `30rem` floor becomes 960px at 200%), so it is measured and reported — but
  not changed unless the measurement shows *content loss* rather than a taller block that
  the page scrolls. A vertical scroll is not the defect this unit is about.
- The `≤63.99rem` single-column fallback and the `≤39.99rem` `display: block` override: both
  are viewport-scoped and correct at normal text size.
- No JSX change.
- `.page-frame__banner`, `TechnicianAgenda`, the global `.btn` height, and the parked 403
  unit.

## Constraints

- **Strict TDD ON.** Runner: `cd web && npm test`. RED must be observed before GREEN.
- No linter, no formatter, no standalone type checker; the only type check is
  `cd web && npm run build` (`tsc -b`).
- CSS contract tests read the stylesheet with `readFileSync` and assert declarations.
  Precedent: `web/src/components/pages/Dashboard.test.tsx:99-105`.
- `jsdom` has no layout: the contract test is a regression guard, and the Chromium reading
  is the only proof.
- Measurement recipe, learned the hard way in this repo: own-worktree Storybook on port
  **6011** (never 6006, which serves the main worktree), Playwright scripts in
  `/tmp/opencode/` only, **system Chrome at `/usr/bin/google-chrome`** (Playwright's
  bundled Chromium is missing in this environment), text zoom 200% simulated with
  `document.documentElement.style.fontSize = '32px'`, temporary story deleted before the
  branch is finished.
- Text zoom cannot be reproduced by real browser zoom: that shrinks the CSS viewport, so
  the media query stops applying.
- Operator-facing copy in Spanish; code, identifiers, comments, tests and docs in English.

## Graph check

`graphify query "conversation workspace grid columns inspector text zoom shell"` → nodes
consulted: `.conversation-workspace grid` and `.ai-agent-grammar__inspector` (both linked
from the sibling `conversation-inspector-layout` unit doc), the `ODD:
panel-text-zoom-reflow` community, `pages/AgentChat.tsx`.

## Expected fix shape — measurement decides

`minmax(24rem, 1fr) minmax(18rem, 24rem)` → `minmax(384px, 1fr) minmax(288px, 384px)`.

`24rem` is exactly 384px and `18rem` is exactly 288px at the default 16px root, so this
should be a zero-visual-change swap at normal text size — and **that is a requirement, not
a hope**: if any normal-size number moves, the swap is wrong and the unit stops. At 200% the
minimums become 384 + 288 = 672px against a 784px content box, so the grid fits with slack
and the inspector survives.

## Tasks

| ID | Task | Route |
|----|------|-------|
| T1 | Baseline measurement at viewport 1024 / 200%: computed columns of `.conversation-workspace`, whether the inspector is clipped, and the normal-size readings. Plus the `height` reading. | delegated (shell + Storybook 6011 + Playwright) |
| T2 | RED: contract assertion that the two-column minimums are px. | delegated (writer) |
| T3 | GREEN: the literal swaps. | delegated (writer, same unit of work as T2) |
| T4 | `height` clamp measured and reported; changed only if content is lost. | delegated |
| T5 | After-measurement; normal-size numbers must be identical to the baseline. | delegated |
| T6 | Full web suite + build. | delegated per-action |

## Delivery

Two literal changes plus contract assertions: far inside the ~400-line review budget →
single PR against `main`, label `type:bug`, no chained slices. Merge is the owner's
decision.

Native review: `gentle-ai review assess --base-ref 96ba8ca2 --committed-only` → risk
**medium** (`executable_change` on the test file), 3 changed paths, 131 changed lines,
**`review_due: false`** with reason `under_budget`. No native review was due.

## Progress / Evidence

- [x] T1 baseline measurement
- [x] T2 RED observed
- [x] T3 GREEN observed
- [x] T4 height clamp measured and reported (not changed, by scope)
- [x] T5 after-measurement
- [x] T6 suite + build

**T1/T5 — real Chromium (system Chrome, viewport height 900), the conversation thread
composed inside `PanelShell` in a Storybook served from this branch (port 6011).** Text zoom
200% via `document.documentElement.style.fontSize = '32px'`.

The premise held, and the failure mode was worse than a collapse: the container **clipped**.

| Reading | Baseline 1024 / 200% | After 1024 / 200% |
|---|---|---|
| computed columns | `768px 576px` | `384px 350px` |
| `.conversation-workspace` | `clientWidth 734`, `scrollWidth 1344` | `734 / 734` |
| inspector right edge vs workspace right edge | **1609 vs 1000 — 609px past it, clipped** | `999 vs 1000` — inside |

| Reading | Baseline 1280 / 200% | After 1280 / 200% |
|---|---|---|
| computed columns | `768px 576px` | `606px 384px` |
| `.conversation-workspace` | `990 / 1344` | `990 / 990` |
| inspector right edge vs workspace right edge | **1609 vs 1256 — 353px past it, clipped** | `1255 vs 1256` — inside |

Normal text size — **identical before and after**, which is the whole justification for the
swap:

| Viewport | Zoom | Columns | Workspace | Inspector right vs workspace right |
|---:|---:|---|---|---|
| 1024 | 100% | `384px 350px` | `734 / 734` | `999 vs 1000` |
| 1440 | 100% | `766px 384px` | `1150 / 1150` | `1415 vs 1416` |

- **T4 — the `height` clamp is measured and deliberately NOT changed.** It scales with the
  root font-size exactly as the same class predicts: `clamp(30rem, calc(100dvh - 15rem),
  46rem)` computes to `660px` at normal text and to **`960px` at 200%** (the `30rem` floor),
  inside a 900px viewport. The workspace becomes taller than the viewport and the **page
  scrolls vertically**. That is a genuine degradation of the clamp's "fit the viewport"
  intent, but it is a scroll rather than lost content, and it is outside this unit's
  authorization. Recorded as its own candidate.
- T2 RED: the contract assertion failed against the rem declaration — `1 failed, 19 passed`.
- T3 GREEN: focused run, `20 tests` passed.
- T6: `Test Files 87 passed (87)`, `Tests 742 passed (742)`; `npm run build` passed (`tsc -b`
  + Vite, only the pre-existing chunk-size warning). Re-run independently by the
  orchestrator: the same `87 / 742`.

Commits:

- `76c5c865` docs(odd): record the conversation-workspace-text-zoom unit
- `6f782a57` fix(conversations): keep workspace columns stable at text zoom

The contract test was **updated, not weakened**: `ConversationThread.test.tsx` already
carried `'gives the inspector column a bounded responsive width'`, asserting the same
`minmax` shape. The assertion now pins the px values instead of the rem ones, so the bound
is still enforced.

## Next step

Unit complete locally with a clean tree. Push + pull request pending the owner's word.

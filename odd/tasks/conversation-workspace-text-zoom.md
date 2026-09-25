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

- ~~The `height: clamp(30rem, calc(100dvh - 15rem), 46rem)`~~ — **promoted into scope by the
  owner** once the measurement showed the clamp's `30rem` floor doubling to 960px inside a
  900px viewport. It is now the second literal of this unit; see D2.
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

### Second literal — the height clamp (D2)

`height: clamp(30rem, calc(100dvh - 15rem), 46rem)` →
`height: clamp(480px, calc(100dvh - 15rem), 736px)`

`30rem` is exactly 480px and `46rem` is exactly 736px at the default root, so this is also a
zero-visual-change swap at normal text size.

**The middle term stays in rem on purpose.** That `15rem` is a *typography-driven chrome
allowance* — the shell header and titlebar genuinely grow with text zoom, which is exactly
why the term was written in rem. It is not layout arithmetic. Only the floor and the ceiling
become absolute, which is the same distinction the rail tokens and the column minimums
follow.

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
**medium** (`executable_change` on the test file), 3 changed paths, 215 changed lines (the
code is one production line and two assertions; the rest is this record), **`review_due:
false`** with reason `under_budget`. No native review was due.

Delivered as **PR #357** — https://github.com/Stefan-migo/lumat-agent/pull/357

## Progress / Evidence

- [x] T1 baseline measurement
- [x] T2 RED observed
- [x] T3 GREEN observed
- [x] T4 height clamp promoted into scope, measured and fixed (9px residual left, by decision)
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

- **T4 — the `height` clamp was promoted into scope and fixed (D2).** Same Chromium harness,
  viewport height 900:

| Text size | Workspace height | Shell chrome above it | Document scroll height | Vertical overflow |
|---|---:|---:|---:|---:|
| 200% before | `960px` | 405px | 1389px | 489px |
| 200% after | `480px` | 405px | 909px | **9px** |
| 100% before | `660px` | 273px | 957px | 57px |
| 100% after | `660px` | 273px | 957px | 57px |

  The swap removed 480px of a 489px overflow. **The 9px residual is smaller than the 57px
  that the same harness already overflows at normal text size**, so it is not a regression,
  not content loss — only a scroll. Left in place deliberately: removing the floor entirely
  (`dvh` bounds, a percentage floor) is a design decision the owner owns, and an invented
  mechanism would be worse than a measured residual.
- T2 RED: the contract assertion failed against the rem declaration — `1 failed, 19 passed`.
- T3 GREEN: focused run, `20 tests` passed.
- T6: `npm run build` passed (`tsc -b` + Vite, only the pre-existing chunk-size warning).
  The suite is contention-flaky. Two consecutive runs on this branch after the height change
  reported `2 failed | 741 passed`, then `1 failed | 742 passed` — every failure a 5000ms
  timeout in `AgendaPage.test.tsx`, the flake already documented in
  `agenda-design-alignment`. An orchestrator re-run of **identical code** reported
  `Test Files 87 passed (87)`, `Tests 743 passed (743)`, zero failures. Same code, different
  outcome: contention, not this change (which touches one CSS declaration and one assertion,
  and cannot reach an AgendaPage test).

Commits:

- `76c5c865` docs(odd): record the conversation-workspace-text-zoom unit
- `6f782a57` fix(conversations): keep workspace columns stable at text zoom
- `811f716e` fix(conversations): keep the workspace height stable at text zoom

The contract test was **updated, not weakened**: `ConversationThread.test.tsx` already
carried `'gives the inspector column a bounded responsive width'`, asserting the same
`minmax` shape. The assertion now pins the px values instead of the rem ones, so the bound
is still enforced.

## Next step

Unit complete and delivered as **PR #357**. Merge is the owner's decision, not this unit's.

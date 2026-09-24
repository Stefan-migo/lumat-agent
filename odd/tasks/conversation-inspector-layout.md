# ODD: conversation-inspector-layout

## Objective

Make the conversation thread's right-hand inspector usable: give its column a real width, let the
detail rows wrap, and stop it from growing an internal horizontal scrollbar.

Comes from the owner's report, and it is the follow-up the sibling unit
`conversation-thread-actions` explicitly declared out of scope. Independent of the `agenda-*` and
dashboard units.

## Problem

Owner's report:

> "el sidebar del lado derecho no se alcanza a ver bien, queda fuera del view port y se abre un
> scroll horizontal"

Diagnosed and measured with Playwright (headless chromium) against Storybook, and re-verified
against the code in this worktree. Three root causes, in cause order:

- **RC1 — the column is a fixed 144px.** `web/src/components/primitives/primitives.css:1911`:
  `.conversation-workspace { grid-template-columns: minmax(0, 1fr) calc(var(--space-8) * 4.5); }`.
  `--space-8` is `32px` (`web/src/tokens/tokens.css:82`), so the inspector track is exactly **144px**,
  which leaves 112px of content after the 16px padding each side (`primitives.css:1697`).
- **RC2 — the detail rows can never wrap.** `primitives.css:1700-1702`: `.ai-agent-grammar__detail`
  is `display: flex; justify-content: space-between` with no `flex-wrap`, and
  `.ai-agent-grammar__detail dd` has no `overflow-wrap`. `dt` + `dd` therefore always demand their
  min-content width and can never adapt.
- **RC3 — why it scrolls instead of reflowing.** `primitives.css:1914`:
  `.conversation-workspace .ai-agent-grammar__inspector { min-width: 0; overflow-y: auto; }`. With
  `min-width: 0` the grid never widens, and because `overflow-y: auto` computes `overflow-x: auto`,
  the inspector **clips its own content and grows an internal horizontal scrollbar** (measured
  `scrollWidth 285 / 647` against `clientWidth 143`).

The owner's description is literal and correct: the content does leave the viewport (measured right
edge 1829px on a 1366px viewport) and there is a horizontal scrollbar — but it is **inside the
sidebar**, not the page. Measured `document.scrollingElement.scrollWidth === clientWidth` at
1366/1280/1100: do not chase a page-level scroll.

**Where the defect actually applies — corrected against the handoff.** The handoff claims the sibling
change makes the 144px column matter at narrow widths too. Re-verified against this worktree's CSS,
that is not what the cascade does:

- `< 40rem` → `primitives.css:1942` sets `.conversation-workspace { display: block; ... }` → the
  inspector stacks at full width.
- `40rem–63.99rem` → `primitives.css:1925` sets `grid-template-columns: minmax(0, 1fr)` → single
  column, inspector stacked.
- `≥ 64rem` → `primitives.css:1911` → the two-column grid, and this is the only place the 144px
  defect exists.

So the fix needs no new responsive tier: the collapse already exists below 1024px.

**Why nobody caught it.** `web/src/stories/pages/_shared/mockData/conversations.ts` defines the mock
conversations with no `customer` and no `case`, and `ConversationContext` renders those sections only
when they exist. The inspector rendered empty in every story. That fixture gap is the real reason this
shipped; the sibling unit has since added an interactive story that supplies `customer`/`case` inline.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-conversation-inspector-layout`
- Branch: `odd/conversation-inspector-layout`
- Base: `794aae7a` (`main`, after PR #347 merged). This unit was branched from the sibling tip
  `b75a1c1d`, which is now part of `main`; it was rebased onto `794aae7a` before any source change.
- Files:
  - `odd/tasks/conversation-inspector-layout.md`
  - `web/src/components/primitives/primitives.css`
  - `web/src/components/pages/ConversationThread.test.tsx`
  - `web/src/stories/pages/ConversationThread.stories.tsx`
  - `web/src/stories/pages/ConversationThread.stories.test.tsx`

Any file outside this list needs a scope update here first.

## Constraints

- **Strict TDD: ON** — source `openspec/config.yaml:38`. Web runner `cd web && npm run test`.
- **No Python file changes, so the pytest suite is not applicable to this unit.** Not run.
- Type check is `cd web && npx tsc -b`. No linter or formatter in this repo.
- **CSS-contract tests follow the repository pattern**: a Vitest test that reads
  `src/components/primitives/primitives.css` with `readFileSync` and asserts declarations
  (`web/src/components/primitives/Button.test.tsx:65`).
- `web/src/components/style-boundary.test.ts` rejects `<style>` JSX blocks anywhere and forbids static
  `style={{...}}` in a named file list.
- `DS-TKN-1`: no hex outside the single `:root` of `tokens.css`. This unit adds no colour at all.
- **`DS-TKN-2` is scoped to `tokens.css`, not to `primitives.css`.** The canonical spec
  (`openspec/specs/panel-design-system/spec.md`) reads: "The token set in `tokens.css` MUST evolve
  additively". Editing an existing `primitives.css` declaration is therefore legitimate, and this unit
  must do exactly that for RC1. The handoff lists `DS-TKN-2` as a blanket additive-only rule; that
  reading is over-broad and would make the RC1 fix impossible.
- `DS-GRAMMAR-2` / `DS-UI-PRIMS`: styles live in the tokenized stylesheet, resolve through `var(--*)`,
  inject no `<style>`, contain no hard-coded colour.
- Raw `rem` literals are the established convention in `primitives.css` (`:1911` height `30rem/46rem`,
  `:1923` `11rem`, `:1960` `20rem`). The new width uses `rem` literals; no new token is added.
- **Language:** code, identifiers, comments, tests and this record are English. Operator-facing copy
  stays neutral Chilean Spanish.
- Conventional commits, **no AI attribution and no `Co-Authored-By`**.
- Work-unit commits are authorized. **Push and PR are separate decisions.**
- Delivery: `stacked-to-main`. PR #347 merged into `main` while this unit was being set up, so this
  unit is its own PR targeting `main` directly, rebased onto `794aae7a`. The provisional
  `feature-branch-chain` fallback (PR targeting `odd/conversation-thread-actions`) is no longer needed.

## Decisions

- **D1 — Build on the sibling unit, do not duplicate it.** This unit was branched from the sibling's
  tip `b75a1c1d` rather than from `main`, then rebased onto `main` once PR #347 merged. The sibling
  moved the actions into the header and deleted the inspector's `Acciones` section; this unit fixes
  the column those remaining sections live in. Branching from `main` at the time would have collided
  textually in `primitives.css` and would have made the pre-fix surface impossible to measure.
- **D2 — The width is `minmax(24rem, 1fr) minmax(18rem, 24rem)`.** The owner first chose the sidebar
  track as `minmax(18rem, 24rem)`. Measurement on the real story then showed that with a
  `minmax(0, 1fr)` sibling — which can collapse to zero — the sidebar track takes its 24rem maximum
  essentially always, so the fluid range rarely engages. At the tightest two-column width (1024px) the
  sidebar measured 384px against a 350px thread: the secondary surface wider than the primary content.
  The owner chose to floor the thread track instead, so the sidebar is the one that yields and stays
  inside its 18rem–24rem range. Measured on the same page: 1024px → thread 384 / sidebar 350;
  1280px → 606 / 384; 1366px → 692 / 384. Identical to the first choice at 1280 and 1366, corrected at
  1024. Wrapping (D3) handles the 647px worst case at any width.
- **D3 — Wrapping over widening.** `flex-wrap: wrap` on `.ai-agent-grammar__detail` and
  `overflow-wrap: anywhere` on its `dd`, so long values adapt instead of demanding width. Width alone
  can never absorb an unbounded token.
- **D4 — Close the leak with `overflow-x: hidden` on the inspector.** Whatever does not fit must wrap
  or clip, never scroll sideways. This is the guard that makes RC3 structurally unrepeatable.
- **D5 — Do not add `customer` / `case` to the shared mock.** This deliberately deviates from the
  handoff's "part 0" as literally written, and the deviation is measured, not assumed:
  - `web/src/stories/pages/_shared/mockData/conversations.test.ts:44-47` asserts the **exact** key set
    of `conversations[0]` as the `R-PRD-PG-3` serializer shape. Adding fields breaks it by design.
  - `web/src/components/pages/ConversationsList.tsx:75` renders
    `c.customer?.name ?? customerName?.(c.customer_id) ?? 'Cliente #${id}'`, so adding `customer` to
    `conversations[0]` flips `ConversationsList.stories.test.tsx:11,18` from `Cliente #1` to the
    customer's name — a different surface, outside this scope.

  The surface-specific fixture therefore lives in `ConversationThread.stories.tsx`, extending the
  existing `interactiveConversation` with a long `captured_data` value. That keeps the inspector
  measurable without mutating a contract that belongs to another surface.
- **D6 — No new responsive tier.** Below 64rem the workspace already stacks (`:1942`, `:1925`).
  Touching that would be scope the defect does not require.

## Route per task

| Task | Route | Trigger evidence |
| --- | --- | --- |
| T1–T4 | delegated (one bounded writer) | CSS plus stories plus tests across 4 non-trivial files; the writer trigger fired |

## Tasks

- [x] **T1 — RED (CSS contract).** Vitest `readFileSync` assertions: the `.conversation-workspace`
  track is `minmax(18rem, 24rem)`, `.ai-agent-grammar__detail` wraps, its `dd` breaks long words, and
  `.conversation-workspace .ai-agent-grammar__inspector` does not scroll sideways. Must fail before T2.
  Observed RED: 4 failed | 14 passed. The width assertion was later re-pointed at the D2 floor and
  observed RED again on its own before the D2 change.
- [x] **T2 — GREEN.** Apply the three CSS changes: width, wrapping, leak guard.
- [x] **T3 — Story fixture and contract.** Extend the interactive fixture with a long `captured_data`
  value; assert the inspector renders `Cliente`, `Caso` and `Datos capturados` with that value. RED
  first: the assertion fails while the fixture has no `captured_data`.
- [x] **T4 — Evidence.** Browser measurement at 1024 / 1280 / 1366 proving no internal horizontal
  scrollbar and no content past the viewport, plus the recorded command outputs.

## Acceptance criteria

1. Measured in a browser at 1024 / 1280 / 1366: the inspector's `scrollWidth === clientWidth` (no
   internal horizontal scrollbar) and its content's right edge stays inside the viewport. Measured, not
   inferred from CSS.
2. The inspector track measures between 288px and 384px at ≥64rem, and the thread track keeps a 24rem
   floor so the sidebar yields before the thread does. Measured: 1024px → thread 384 / sidebar 350;
   1280px and 1366px → sidebar 384.
3. Nothing below 64rem changes: the workspace still stacks at <64rem.
4. No new hex anywhere, no `<style>` injection, no static inline style, no new token declaration.
5. `cd web && npm run test` green (the load-fragile `AgendaPage` 5s-timeout test is recorded honestly
   if it trips, per the handoff trap 3); `cd web && npx tsc -b` exits 0; `cd web && npm run
   build-storybook` succeeds.
6. Only the files in Authorized scope change.

## Checks

- `cd web && npm run test`
- `cd web && npx tsc -b`
- `cd web && npm run build-storybook`
- Browser measurement against a Storybook served **from this worktree** (the server on port 6006 serves
  the main worktree and shows the old code), with the installed chromium binary passed explicitly
- `git diff --check`

## Progress

- [x] Created this ODD record before the first source change.
- [x] Base pinned to `b75a1c1d`; `graphify-out/` copied in and `.graphify_root` pointed at this worktree.
- [x] Graph Check run: hub community `ConversationsList.tsx` (holds `ConversationThread.tsx` and its
  test) and `PNL-APP-12 Conditional Conversation and Dense-Page Surfaces` ("Optional Inspector
  Region"). The graph was built from `4b31796c`; `main` has since advanced to `794aae7a`, so the graph
  is two merges behind. Refresh runs at session close.
- [x] Sibling PR #347 merged into `main` (`794aae7a`) while this unit was being set up; this branch was
  rebased onto it before any source change. No source change had been made yet, so the rebase was
  clean.
- [x] Re-verified on `794aae7a` that all three target declarations survive untouched: `.conversation-workspace`'s
  `calc(var(--space-8) * 4.5)` track, `.ai-agent-grammar__detail`/`dd` with no wrapping, and
  `.conversation-workspace .ai-agent-grammar__inspector { min-width: 0; overflow-y: auto; }`.
- [x] T1–T3 implemented by one bounded writer (commits `311645d7`, `5e34e6fb`); the orchestrator then
  verified the diff structurally, re-ran the focused tests itself, and re-ran the full suite.
- [x] D2 floor applied by the orchestrator as a mechanical two-file change, in TDD order: the width
  assertion was re-pointed first and observed RED on exactly that assertion, then the CSS changed and
  the focused pair came back GREEN. Commit `d1c175e6`.
- [x] T4 measured in a real browser against this worktree's own Storybook (port 6012, server cwd
  verified), with a same-page control that re-applies the pre-fix declarations.

## Verification evidence

Observed command output only.

- T1 RED (writer): `ConversationThread.test.tsx` → `Tests 4 failed | 14 passed (18)`; the four CSS
  assertions for width, wrapping, long-value breaking and overflow failed.
- T2 GREEN (writer): the same file → `Tests 18 passed (18)`.
- T3 RED (writer): `ConversationThread.stories.test.tsx` → `Tests 1 failed | 5 passed (6)`,
  "Unable to find an element with the text: Datos capturados".
- T3 GREEN (writer): the same file → `Tests 6 passed (6)`.
- D2 RED (orchestrator): after re-pointing the width assertion at `minmax(24rem, 1fr)`, the file
  reported exactly one failure — that assertion — with the other three green.
- D2 GREEN (orchestrator): focused pair → `Test Files 2 passed (2)`, `Tests 24 passed (24)`. This was
  the orchestrator's own re-run on the frozen tree, re-confirmed after the writer returned.
- `cd web && npx tsc -b`: exit 0, both before and after the D2 change.
- `cd web && npm run test`, full suite, three runs on this shared host:
  - run 1: `1 failed | 735 passed` — the failing test's name was lost to output truncation by the
    orchestrator. Recorded as unattributed: not claimed as a pass, not claimed as a flake.
  - run 2: `Test Files 86 passed (86)`, `Tests 736 passed (736)`.
  - run 3: `2 failed | 734 passed` — `AgendaPage > creates an appointment from the agenda and refreshes
    the visible period` (5318ms) and `AutomationRuleDetailPage > refreshes the persisted rule through
    GET after admin creation` (5370ms). Both are >5s timeouts on surfaces this change does not touch.
    `npx vitest run src/components/pages/AgendaPage.test.tsx` in isolation: `Tests 19 passed (19)`.
    That matches the documented load-fragility (handoff trap 3), not a regression.
- `cd web && npm run build-storybook`: exit 0 on the final tree (`✓ built in 26.78s`).
- `git diff --check`: clean.

Browser measurement (T4) — Playwright headless chromium against a Storybook served from this worktree
(port 6012; the listening process's `cwd` was verified as this worktree's `web/`). The "control"
column re-applies the pre-fix declarations through an injected override on the same page: it is a
same-page control, not a pre-fix build.

| viewport | control sidebar | control internal h-scroll | control overrun | fixed thread / sidebar | fixed internal h-scroll | fixed overrun | wrapped rows | page h-scroll |
| ---: | ---: | :--: | ---: | ---: | :--: | ---: | ---: | :--: |
| 1024 | 144px | yes (143 vs 453) | 294px past the inspector | 384 / 350 | no (383 vs 383) | none (−16px inside) | 1 | no |
| 1280 | 144px | yes (143 vs 453) | 294px past the inspector | 606 / 384 | no (383 vs 383) | none (−16px inside) | 1 | no |
| 1366 | 144px | yes (143 vs 453) | 294px past the inspector | 692 / 384 | no (383 vs 383) | none (−16px inside) | 1 | no |

Ten `dt`/`dd` rows render in every case; the long `captured_data` URL is present and wraps. The
Storybook server was terminated by PID after measuring (never by command-line pattern).

## Assess outcome

`gentle-ai review assess --cwd . --base-ref 794aae7a --committed-only --json`, read-only, exit 0:

- risk `medium` (`reasons: [executable_change]` on `ConversationThread.test.tsx`), 5 changed paths,
  251 changed lines, `review_due: false`, `review_due_reason: under_budget`.

No native review is due for this unit; the tier and reason are recorded per protocol. Note that the
251 changed lines include this record — the code-plus-tests delta is roughly 40 lines.

**Anomaly observed in the optional `--agent` path. Unresolved, and not smoothed over.**

Adding `--agent opencode` — the flag that carries the runtime identity for a `next_transition`
preflight — changed the same command's result and its exit code:

- the first invocation with `--agent opencode` returned the normal `medium` / `under_budget` /
  `review_due: false` envelope with exit 0;
- every later invocation with identical flags returned `risk: "high"`,
  `reasons: [{code: "unassessable", detail: "the active runtime is not eligible for immutable receipt
  review ... supported immutable review runtimes: <list>"}]`, `changed_paths: 0`, `changed_lines: 0`,
  `review_due: true`, `review_due_reason: high_risk`, exit 1;
- the supported-runtime list inside that message differed between invocations (`claude-code, codex`
  first, then `claude-code, opencode, codex`) while still reporting the active runtime as ineligible;
- the identical command **without** `--agent` has returned the normal assessment consistently, exit 0.

The read-only assessment is the authority for whether a review is due and it says none is, so this unit
is not gated by the anomaly. The cause is not determined: it is consistent both with a defect in the
eligibility check and with the installed managed assets being rewritten concurrently by another live
session in this repository. No report was filed and no retry loop was run.

## Corrections to the handoff (verified this session)

- The handoff's `STATE` section says the sibling is "NOT pushed and has NO PR". It was pushed, and
  **PR #347 merged into `main` as `794aae7a`** while this unit was being set up; the branch advanced
  from `341ad43a` to `407cf4f9` in that window. This unit was rebased onto that merge.
- The handoff claims the sibling change makes the 144px column matter at narrow widths. Measured
  against the cascade, the two-column defect exists **only at ≥64rem**; below that the workspace is
  `display: block` (`:1942`) or a one-column grid (`:1925`).
- The handoff places `.graphify_root` at the repo root. It actually lives at
  `graphify-out/.graphify_root`, and `--update` rewrites it with the root it was given.
- The handoff lists `DS-TKN-2` as a blanket additive-only constraint. The canonical spec scopes it to
  `tokens.css`.

## Delivery

- Branch `odd/conversation-inspector-layout` pushed to `origin`.
- Pull request **#350** against `main`, labelled `type:bug`, state `OPEN`, `MERGEABLE`.
  <https://github.com/Stefan-migo/lumat-agent/pull/350>
- Merge is a separate decision and was not taken by this unit.

## Recovery

Resume with `mem_context`, then the project-scoped `mem_search` for `conversation-inspector-layout`,
then `mem_get_observation` for the full document, then read this file.

# ODD: conversation-thread-narrow-actions

## Objective

Make the conversation thread's actions reachable at every viewport width, and preserve the read-only
context when the right-hand inspector is hidden.

Found during the panel design review. Independent of the `agenda-*` and dashboard units.

## Problem

Below 1024px the right-hand inspector is deleted from the DOM, and it is the only home of actions the
design system forbids hiding.

- `web/src/components/primitives/primitives.css:1707` opens `@media (max-width: 64rem)` — **1024px
  inclusive** — and `:1711` sets `.ai-agent-grammar__inspector { display: none; }`.
- That class is used in exactly one place: `web/src/components/pages/ConversationThread.tsx:47`
  (`<aside className="ai-agent-grammar__inspector" aria-label="Inspector de conversación">`). No
  other component renders it, so the rule's whole effect is this surface.
- Inside that aside live the conversation state controls — `Tomar`, `Devolver`, `Cerrar`
  (`ConversationThread.tsx:99`, gated by `interactive`) — and `Reconocer emergencia`
  (`ConversationThread.tsx:51`), gated by an unacknowledged emergency. It also holds the read-only
  `Cliente`, `Caso` and `Datos capturados` sections.
- `web/DESIGN_SYSTEM.md:327`: "Never hide emergency, handoff, send, acknowledge, save, or retry
  actions to produce a cleaner screenshot." `:554`: "Text resizes to 200%; narrow reflow preserves
  content and actions."
- **Consequence:** at 1024px and below — phones, tablets, and any laptop where the panel's content
  area falls under 1024 — the operator cannot take, return, or close a conversation. The action set
  the doc names explicitly (`handoff`, `emergency`, `acknowledge`) is exactly what disappears.

**Second defect found while auditing, smaller but real.** At exactly 1024px the workspace still
reserves the inspector's column while the item itself is hidden:
`.conversation-workspace` declares `grid-template-columns: minmax(0, 1fr) calc(var(--space-8) * 4.5)`
(`primitives.css:1912`) and only collapses to one column inside
`@media (min-width: 40rem) and (max-width: 63.99rem)` (`:1923-1926`), which stops at 1023.84px. So at
1024px there is a dead 144px strip.

**Not verified, declared rather than assumed.** The owner also reported a horizontal scroll on this
surface "inside the panel". A real-browser measurement of the Storybook story at 375 / 640 / 768 /
1023 / 1024 / 1280 found **no page-level horizontal scroll and no overflowing element** in this
component, and the grid is defensive (`minmax(0, 1fr)`, `min-width: 0`, `overflow: hidden`). The
owner's scroll is therefore not reproduced by this fix's evidence and is not claimed as fixed. It
needs the real panel (login + data) to be reproduced; that measurement is follow-up work.

## Scope

**In:**

1. Move `Tomar` / `Devolver` / `Cerrar` into the thread header, next to the `StatusBadge` whose state
   they change. Same `mutate` wiring, same labels, same disabled conditions.
2. Move `Reconocer emergencia` into the header as well, with its existing condition.
3. Delete the `Acciones` section from the context, so the actions have exactly one home.
4. Make the read-only context a collapsible `<details>` that survives at every width.
5. Stop hiding `.ai-agent-grammar__inspector`, which also removes the 1024px dead strip.
6. Tests: unit assertions for the new homes, the CSS contract, and a browser measurement.

**Out (deliberate):**

- The horizontal scroll the owner reported. Not reproduced; needs the real panel to reproduce first.
- The `≤64rem` shell rules for `.ai-agent-grammar__shell` / `.ai-agent-grammar__shell--compact` and
  `.panel-shell--with-inspector` (`primitives.css:1708,1710`). Those belong to AgentChat and
  PanelShell, not to this surface.
- Any restyling of the header beyond what the actions need.
- Any change to the composer, the realtime status line, the bubbles, or the mutation endpoints.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-conversation-thread-actions`
- Branch: `odd/conversation-thread-actions`
- Base: `4b31796c`
- Files:
  - `odd/tasks/conversation-thread-narrow-actions.md`
  - `web/src/components/pages/ConversationThread.tsx`
  - `web/src/components/pages/ConversationThread.test.tsx`
  - `web/src/components/primitives/primitives.css`
  - `web/src/stories/pages/ConversationThread.stories.tsx`
  - `web/src/stories/pages/ConversationThread.stories.test.tsx`

Any file outside this list needs a scope update here first.

## Constraints

- **Strict TDD: ON** — source `openspec/config.yaml:38`. Web runner `cd web && npm test`.
- **No Python file changes, so the pytest suite is not applicable to this unit.** Not run; CI runs it
  unchanged.
- No linter, formatter or type checker. The only type check is `cd web && npm run build` (`tsc -b`).
- **CSS-contract tests follow the repository pattern**: a Vitest test that reads
  `src/components/primitives/primitives.css` with `readFileSync` and asserts declarations
  (`web/src/components/primitives/Button.test.tsx:65`).
- `web/src/components/style-boundary.test.ts` rejects `<style>` JSX blocks anywhere and forbids
  static `style={{...}}` in a named file list. `ConversationThread.stories.tsx` is not on that list,
  and it already uses inline styles, but prefer an existing class over a new inline style.
- **D6 language:** code, identifiers, comments, tests and this record are English. Everything the
  operator reads stays Spanish (`Tomar`, `Devolver`, `Cerrar`, `Reconocer emergencia`,
  `Inspector de conversación`).
- Work-unit commits are authorized. **Push and PR are separate decisions.**
- Delivery: `stacked-to-main`. This unit is its own PR.

## Decisions

- **D1 — The actions belong with the state badge.** `Tomar` / `Devolver` / `Cerrar` mutate the
  conversation state, and the `StatusBadge` that shows that state already lives in the header
  (`ConversationThread.tsx:105`). Separating a control from the thing it changes was the original
  architectural mistake; the header is the correct home, not a workaround.
- **D2 — One home for the actions.** The `Acciones` section is deleted from the context rather than
  duplicated, so there is never a second, silently stale copy.
- **D3 — The context `<details>` is `open` by default at every width.** Varying `open` by viewport
  needs a `matchMedia` hook or duplicated markup; neither is justified. Collapsing is an operator
  affordance, not a layout switch, and defaulting to open means the wide-screen inspector behaves as
  it does today.
- **D4 — Keep the `aria-label="Inspector de conversación"` on the aside and keep the inner `h2`
  headings.** The existing accessibility contract and two tests depend on them.
- **D5 — Remove the `display: none` rule rather than override it.** The class has exactly one
  consumer, so the rule is dead weight once the surface should stay visible. The workspace already
  collapses to one column below 1024 (`primitives.css:1926`, `:1943`), so the context stacks instead
  of vanishing.
- **D6 — Add an interactive story.** `ConversationThreadView` does not pass `interactive`, so no story
  can currently render `Tomar` / `Devolver` / `Cerrar` at all. This unit's central claim is that those
  controls stay reachable, so the story contract must be able to show them — otherwise the claim is
  unmeasurable.
- **D7 — No pytest run.** No Python file changes.

Implementation notes:

- The emergency action keeps the effective original guard: `conversation.case` must be present,
  `conversation.emergency` must be true, `conversation.acknowledged_at` must be empty, and
  `conversation.case_id` must be non-null. The case guard is retained because the prior action was
  nested inside the case section and moving it without that guard would change observable behavior.
- The header uses one minimal `.ai-agent-grammar__header-actions` flex-wrap group so actions wrap
  without changing the header's existing layout or order.

## Route per task

| Task | Route | Trigger evidence |
| --- | --- | --- |
| T1–T6 | delegated (one bounded writer) | 6 non-trivial files across component, CSS, stories and tests; the writer trigger fired |

## Tasks

- [ ] **T1 — RED (component contract).** Vitest: `Tomar` / `Devolver` / `Cerrar` render in the thread
  header when `interactive`, `Reconocer emergencia` renders there for an unacknowledged emergency,
  the context renders as a `<details>`, and the context no longer contains an actions section. Must
  fail before T2.
- [ ] **T2 — GREEN.** Move the actions to the header; wrap the context in `<details open>`.
- [ ] **T3 — RED (CSS contract).** `readFileSync`: the `max-width: 64rem` block no longer hides
  `.ai-agent-grammar__inspector`.
- [ ] **T4 — GREEN.** Remove the rule; change nothing else in that block.
- [ ] **T5 — Story contract.** Add the interactive story and assert it in the stories test.
- [ ] **T6 — Evidence.** Browser measurement at 375 / 768 / 1024 / 1280 proving the actions are
  visible, plus the command outputs.

## Acceptance criteria

1. Measured in a browser at 375 / 768 / 1024 / 1280: with `interactive`, `Tomar`, `Devolver` and
   `Cerrar` are present **and visible** (non-zero box); `Reconocer emergencia` is visible for an
   unacknowledged emergency. Measured, not inferred from CSS.
2. Each action appears exactly once in the DOM — no duplication between the header and the context.
3. The read-only context is reachable at every width and is collapsible.
4. Mutation wiring, labels, disabled conditions, the composer and the realtime line are unchanged.
5. `aria-label="Inspector de conversación"` and the `Cliente` / `Caso` headings still resolve; the two
   existing inspector tests keep passing.
6. `cd web && npm test` green; `cd web && npm run build` passes.
7. Only the files in Authorized scope change.

## Checks

- `cd web && npm test`
- `cd web && npm run build`
- Browser measurement at 375 / 768 / 1024 / 1280 (Playwright, against a Storybook served from this
  worktree — the one on port 6006 serves the main worktree and shows the old code)
- `git diff --check`

## Progress

- [x] Created this ODD record before the first source change.
- [x] T1 RED and T2 GREEN: component action/context contract added and implementation passed focused tests.
- [x] T3 RED and T4 GREEN: CSS contract added and the inspector hide rule removed.
- [x] T5: interactive emergency story and story contract added.
- [x] T6: browser evidence collected from this worktree's Storybook on port 6011.

## Verification evidence

Observed evidence:

- T1/T3 RED: `ConversationThread.test.tsx (14 tests | 2 failed)` — the action header assertion failed
  because the buttons were still in the inspector, and the CSS assertion failed because the 64rem block
  still contained `.ai-agent-grammar__inspector { display: none; }`.
- Focused GREEN: `2 test files passed, 19 tests passed`.
- Full web test, observed by the orchestrator on the frozen tree with nothing else running:
  `Test Files 86 passed (86)`; `Tests 724 passed (724)`. An earlier run by the implementing worker
  reported `85 files passed, 1 failed / 723 passed, 1 failed`, with the unrelated
  `AgendaPage > creates an appointment from the agenda and refreshes the visible period` timing out at
  5000ms. That failure did not reproduce on the clean re-run. It is the same 5-second-timeout flake seen
  in the `panel-dashboard-alignment` unit, in both cases while a Storybook and a Playwright process were
  competing for CPU. It is pre-existing test brittleness under load, not a signal about this change, and
  it is recorded rather than smoothed over. The record below was corrected to the observed green run; the
  worker's own doc entry had captured the earlier failing run.
- Build: `npm run build` passed (`tsc -b && vite build`, 2222 modules transformed).
- Browser command: `node /tmp/opencode/measure-conversation-thread.mjs` against Storybook `:6011`.
  At 375x812, 768x900, 1024x900 and 1280x900, each of `Tomar`, `Devolver`, `Cerrar` and
  `Reconocer emergencia` had `count: 1`, `nonZero: true`, and `offsetParent: true`; context was reachable
  at 375px. Measurements were `scrollWidth == innerWidth` at every viewport: 375, 768, 1024 and 1280.
- `git diff --check` passed. No pytest run per D7.

**Correction applied by the orchestrator after the worker returned.** The worker left
`.ai-agent-grammar__actions` (`primitives.css:1705`) declared after deleting the only section that
rendered it — dead CSS created by this change. The declaration was removed. The full suite and the
build above were re-run on the resulting tree.

## Assess outcome

`gentle-ai review assess --base-ref 4b31796c --committed-only` over this branch is recorded below.

## Recovery

Resume with `mem_context`, then the project-scoped `mem_search` for `conversation-thread-narrow-actions`,
then `mem_get_observation` for the full document, then read this file.

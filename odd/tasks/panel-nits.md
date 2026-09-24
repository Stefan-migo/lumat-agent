# ODD: panel-nits

## Objective

Close the two remaining `panel-nits` items from `odd/tasks/panel-visual-foundation.md` — the Dialog
story fixture that renders browser-default controls, and the `ClientMemories` region that nests a
page-level `PageHeader` inside a `Card`.

## Problem

Every claim below was verified this session against `f0330667` in
`/home/stefan/repos/lumat-agent-odd-panel-nits`, not inherited from the handoff.

**N1 — the Dialog story fixture renders browser defaults.**
`web/src/stories/primitives/Dialog.stories.tsx:32-45` renders three raw `<button>` elements with no
`className`, so they fall back to UA styling instead of the Lumat `Button` primitive. The same
fixture carries two static inline `style` props (`:36` on the `<p>`, `:39` on the action row), which
the tokenized-stylesheet boundary (`DS-GRAMMAR-2`) forbids. The Dialog primitive itself
(`Dialog.tsx:35-70`) renders no action buttons at all — only header, close control and `{children}`
— so this is story-fixture work, not a primitive change.

Ponytail check on the fix: the `<p>` margin and the right-aligned action row are the only two static
shapes. No existing class covers either, and production dialogs (`AgendaPage.tsx:148-151`,
`AutomationRuleDetailPage.tsx:187-190`) stack `<p>` + `<Button>` with no wrapper at all. Two scoped
classes next to the Dialog block in `primitives.css` are the minimum that preserves the current
rendering exactly.

**N2 — `ClientMemories` nests a page component inside a region.**
`web/src/components/domain/ClientMemories.tsx:75-76` wraps `<PageHeader title="Memorias" meta="Ficha
de …" />` inside `<Card title="Memorias del cliente">`. `PageHeader` always renders an `<h1>`
(`PageHeader.tsx:11-22`), so the region introduces a second page-level heading — an accessibility
defect, not only a duplicated label. `ClientFicha.tsx:159-165` already renders the page-level
`PageFrame` header with `Ficha: {customer.name}`, so the nested meta repeats what the page owns.
`Card` supports only `title` / `children` / `className` (`Card.tsx:4-8`) — there is no meta slot to
move the customer name into.

## Scope

**In:** `web/src/stories/primitives/Dialog.stories.tsx`, a new
`web/src/stories/primitives/Dialog.stories.test.tsx`,
`web/src/components/primitives/primitives.css`, `web/src/components/domain/ClientMemories.tsx`,
`web/src/components/pages/ClientFicha.tsx`,
`web/src/stories/pages/ClientMemories.stories.tsx`,
`web/src/stories/pages/ClientMemories.stories.test.tsx`, this record, and the
record-hygiene target `odd/tasks/panel-visual-foundation.md`.

**Out:** the N3 inline-style sweep (split out — see below); the dead `primitives.css:67-72` block and
its `tokens.test.ts:195` assertion (owner decision, per the handoff — not ours to remove); the
`Button` arbitrary-attribute-forwarding gap (`Button.tsx` advertises `ButtonHTMLAttributes` but
spreads no rest props — a real pre-existing finding, but a separate unit); `tokens.css` values; the
`uv.lock` drift (explained and deliberate); any other page.

## Split decision (recorded before the first source write)

Owner decision, 2026-09-24: `panel-nits` carries **N1 + N2 only**. **N3** — the 22 inline
`style={{}}` props in production code — is split out as its own follow-up unit.

Reason: N1 and N2 are two mechanical nits across one story fixture and one region component, with a
closed blast radius. N3 is a different kind of change — it needs a static/dynamic classification pass
over roughly nine production components, touches shared layout styles, and carries real visual
regression risk that needs its own Storybook check. Mixing them would put an infrastructure refactor
of the style layer inside a "nits" PR and make the review diff incoherent.

N3 follow-up unit name: `inline-style-boundary` (not opened here; record only).

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-panel-nits`
- Branch: `odd/panel-nits`
- Base: `f0330667`
- Files: the eight paths listed under **In** above.

## Constraints

- `DS-TKN-1`: every token stays in the single `:root` of `tokens.css`; **no hex outside it**.
- `DS-TKN-2`: additive only — every pre-existing declaration stays byte-identical.
- `DS-TKN-8` / `DS-TKN-10`: the drift guard stays green (pinned palette, `tokens.ts` mirror
  equality, no-hard-coded-hex walk).
- `DS-GRAMMAR-2` / `DS-UI-PRIMS`: styles live in the tokenized stylesheet boundary, resolve through
  `var(--*)`, inject no `<style>`, contain no hard-coded colour.
- `style-boundary.test.ts` keeps its five-file inline-`<svg>` guard. It scans production and stories
  alike but only matches `<style` tags, so a story `style` prop is not what it catches — the new
  guard for that is the `[style]` assertion in the new Dialog story test.
- `tokens.test.ts:195` pins `primitives.css:67-72` (`.btn > svg`, `.dialog__close > svg` →
  `--icon-md`). That block may be dead but the assertion pins it: **leave both alone**.
- Security class untouched: WCAG 2.2 AA contrast, keyboard/focus operation, roles, destructive
  confirmation, colour-never-alone.
- UI copy: neutral Chilean Spanish. Artifacts (commits, docs, code comments): English.
- Conventional commits, **no AI attribution and no `Co-Authored-By`**.
- **Strict TDD: ON.** Source: `odd/tasks/panel-visual-foundation.md` and the handoff (the frontend
  runner for this unit). The `sdd-init` record (#1556) names pytest, which is the *backend* runner —
  this slice is frontend-only, so the applicable runner is Vitest: `cd web && npm run test`.
  Observe RED before each source change; never invent RED evidence.

## Decisions taken (with rationale)

- **D1 — N1 variants.** Trigger `Eliminar registro` → `Button variant="secondary"`; in-dialog
  `Cancelar` → `variant="secondary"`, `Eliminar` → `variant="primary"`. The `Button` primitive
  already defaults `type="button"` (`Button.tsx:22`), so no explicit `type` is added. The trigger
  stays secondary so the dialog's own primary action is the strongest emphasis in the story.
- **D2 — N1 layout classes.** Add `.dialog__message` (`margin: 0 0 var(--space-3)`) and
  `.dialog__actions` (`display: flex; gap: var(--space-2); justify-content: flex-end`) beside the
  existing Dialog block. This reproduces the current inline styles exactly, tokenized.
- **D3 — N2 heading.** The `Card` title `Memorias del cliente` survives as the single region heading;
  the nested `PageHeader` is removed. Two existing assertions already pin that title
  (`ClientFicha.test.tsx:72`, `ClientFicha.stories.test.tsx:66`) and stay green.
- **D4 — N2 `customerName` prop is removed.** With the `PageHeader` gone the prop has no remaining
  consumer: its documented purpose was the PageHeader meta, the page already owns the client identity
  through `PageFrame`, and `Card` has no meta slot. Keeping it would be a dead prop, and adding a
  `card__meta` slot would grow the primitive for a case the page already covers. Consumers to update:
  `ClientFicha.tsx:207`, `ClientMemories.stories.tsx:15`,
  `ClientMemories.stories.test.tsx:51`.
- **D5 — N2 test contract.** `ClientMemories.stories.test.tsx:9-12` currently asserts the nested
  `PageHeader`; that assertion *is* the bug. It is rewritten to the new contract: exactly one region
  heading (`Memorias del cliente`), no `Memorias` heading, and no `h1` inside the region.

## Tasks

- [x] **T1 (N1, TDD)** — RED: add `web/src/stories/primitives/Dialog.stories.test.tsx` asserting the
  fixture renders `btn` / `btn--secondary` / `btn--primary` controls and contains zero `[style]`
  attributes. Extract the fixture body into an exported `DialogConfirmView` component and add it to
  `excludeStories`, mirroring the `ClientMemoriesView` pattern (`ClientMemories.stories.tsx:9-20`).
- [x] **T2 (N1, GREEN)** — convert the three raw `<button>` elements to the `Button` primitive, apply
  `.dialog__message` / `.dialog__actions`, and add both classes to `primitives.css`. Re-run T1 → green.
- [x] **T3 (N2, TDD)** — RED: rewrite the `ClientMemories` region-heading test to the D5 contract.
- [x] **T4 (N2, GREEN)** — remove the nested `PageHeader` and the `customerName` prop plus its
  import; update `ClientFicha.tsx`, `ClientMemories.stories.tsx` and the remaining
  `ClientMemories.stories.test.tsx` call site. Re-run T3 → green.
- [x] **T5 — Guards + typecheck + build.** `npm run test`, `npx tsc -b`,
  `npm run build-storybook` all green; record the real test count.
- [x] **T6 — Visual check** at 1366×768 with the 640/1024/1280 references for the Dialog story and
  the client ficha memories region.
- [x] **T7 — Record hygiene carried from the handoff** (see below).

## Checks

```bash
cd web && npm run test        # baseline this session: 85 files / 714 tests, all passing
cd web && npx tsc -b          # must exit 0
cd web && npm run build-storybook
```

Guard tests that must stay green: `tokens.test.ts`, `style-boundary.test.ts`,
`dependency-boundary.test.ts`.

## Forecast and delivery

- Forecast authored change: roughly 60–90 lines across 8 files, dominated by the new test file and
  the two CSS rules. Well under the ~400-line review budget.
- Delivery strategy: `single-pr` — `odd/panel-nits` → `main`, one PR.
- PR boundary: the whole unit. Work units are the two atomic commits below.
- Record hygiene for the PR (T7):
  1. Add slice 3's visual-check result to `odd/tasks/panel-visual-foundation.md` under
     `## Visual check results` (it passed with no visual changes; slices 1 and 2 are the pattern).
  2. Reconcile the false `## Open items` entry at `:615-618` ("Slice 2 PR boundary … No PR has been
     opened; nothing is pushed") — slices 2a, 2b and 3 all shipped and merged.
  3. Correct the `ClientMemories.tsx` path to `web/src/components/domain/ClientMemories.tsx`.
  4. Mark the `panel-nits` follow-up bullet (`:664-672`) as consumed by this unit.

## Work units (commits)

1. `docs(odd): record the panel-nits unit and its split decision` — this record. Committed **first**,
   so the split decision is on the branch before the first source write. T7's record hygiene joins
   this commit only if it stays a pure-docs change; otherwise it is its own commit.
2. `fix(web): use the Button primitive in the Dialog story fixture` — T1, T2.
3. `refactor(web): drop the page-level PageHeader from the ClientMemories region` — T3, T4.

## Progress

- 2026-09-24 — Worktree `../lumat-agent-odd-panel-nits` created on `odd/panel-nits` from
  `f0330667` (owner consent given for this unit). `graphify-out/` copied in from main and
  `.graphify_root` corrected to the worktree path.
- 2026-09-24 — Baseline `cd web && npm run test`: **85 files / 714 tests passed**, matching the
  handoff exactly. `npm install` run in `web/`.
- 2026-09-24 — Graph Check: `graphify query` on the Dialog/Button story area and on the
  ClientMemories/Card/PageHeader region. Nodes consulted: `Dialog()`, `Dialog.tsx`, `Button()`,
  `Button.tsx`, `Button.stories.tsx`, `ClientMemories()`, `ClientMemoriesProps`, `Card()`,
  `PageHeader()`, `ClientFicha.tsx`, `primitives.css`, `tokens.test.ts`,
  `style-boundary.test.ts`, `dependency-boundary.test.ts`. Community: `ClientFicha.tsx`.
- 2026-09-24 — Split decision recorded (N3 out) before the first source write.
- 2026-09-24 — T1 RED observed: the new Dialog contract test failed because `DialogConfirmView` was
  undefined; T1/T2 then passed with the Button primitive and tokenized classes.
- 2026-09-24 — T3 RED observed: the rewritten ClientMemories contract failed against the base source
  with `expected document not to contain element, found <h1>` — the region's page-level heading.
  Re-verified independently by the orchestrator by restoring `ClientMemories.tsx` from `f0330667`
  and re-running the test file (1 failed / 6 passed), then restoring the worktree byte-identical.
  T3/T4 then passed after removing the nested `PageHeader` and the `customerName` prop.
- 2026-09-24 — T5 passed: `npm run test` reported **86 files / 715 tests passed**; `npx tsc -b`
  and `npm run build-storybook` both exited 0. Existing act/navigation and Storybook chunk-size
  warnings remained non-failing.
- 2026-09-24 — Implementation commits: `a5354df5` (`fix(web): use the Button primitive in the
  Dialog story fixture`) and `5ccc12b8` (`refactor(web): drop the page-level PageHeader from the
  ClientMemories region`).
- 2026-09-24 — Orchestrator-side verification: diff read line by line; `cd web && npm run test`
  re-run as the independent spot check → **86 files / 715 tests passed**; `npx tsc -b` exit 0.
  Source-only authored change is **90 lines** (`git diff --numstat` excluding this record), far
  under the ~400 budget.
- 2026-09-24 — RDD gate read without changing it: mode `on` (global). `gentle-ai review assess`
  over the committed slice (`--base-ref f0330667 --committed-only`) reports risk `medium`,
  `review_due: false`, `review_due_reason: under_budget` — no native review is due for this
  candidate.
- 2026-09-24 — T7 record hygiene applied to `odd/tasks/panel-visual-foundation.md`: added the
  slice 3 visual-check subsection, reconciled the false `## Open items` "Slice 2 PR boundary" entry
  against the four MERGED PRs, corrected the `ClientMemories.tsx` path to
  `web/src/components/domain/ClientMemories.tsx`, and marked the `panel-nits` follow-up bullet as
  N1+N2 consumed with N3 split out.
- 2026-09-24 — **T6 remains open**: the visual check needs the owner in a browser at 1366×768.

## Visual check results

### `panel-nits` (2026-09-24, Storybook :6006, PR #342)

The owner ran the manual visual check against the checklist and reports **PASSED with no findings**.
Storybook was served from this worktree at `http://localhost:6006` (the stale main-worktree server on
the same port was stopped first, so the check could not have been reading merged-code output).

The checklist covered, in three blocks:

1. `primitives-dialog--confirmacion` — the three controls render as the `Button` primitive and match
   `primitives-button--secondary` / `--primary`; correct variants; right-aligned single row; paragraph
   spacing preserved; keyboard focus visible; `#storybook-root [style]` count is 0.
2. `pages-clientmemories--default` and `pages-clientficha--default` — a single region heading
   (`Memorias del cliente`), the card shortened by exactly the removed duplicate, and `h1` count on
   the ficha equal to 1 (was 2).
3. Regression sweep — `pages-agendapage--cancel-confirmation` and
   `pages-automationruledetailpage--confirmation` (production dialogs on `.dialog__body`) unchanged,
   and the two docs pages render with no console errors.

No finding was raised, so nothing needed a fix. The exact set of reference widths the owner
exercised is the owner's report and is not instrumented here; 1366×768 plus the 640/1024/1280
references were what the checklist asked for.

## Open items

- **`inline-style-boundary`** (follow-up, not started) — the N3 sweep: classify and migrate the
  static inline `style={{}}` props in `web/src` production code. The genuinely dynamic ones stay:
  per-instance CSS custom properties (`Dashboard.tsx:191,197,233`, `StateMessage.tsx:22,25`),
  per-render computed values (`Dashboard.tsx:223`, `DataTable.tsx:71,80`, `Skeleton.tsx:14`,
  `StatCard.tsx:11`), and `fontVariantNumeric: "var(--corp-value)"` (`DataTable.tsx:28`,
  `StatCard.tsx:13`) which is a deliberate behavioural token (D3), not a bug.
- **`Button` attribute forwarding** — `ButtonProps` extends `ButtonHTMLAttributes` but `Button.tsx`
  spreads no rest props, so `aria-*` / `data-*` / `name` / `value` typecheck and are silently
  dropped. Pre-existing; its own unit.
- **`primitives.css:67-72`** — possibly dead block pinned by `tokens.test.ts:195`. If it is removed,
  the CSS and its assertion must go in the same commit. Owner decision, not this unit's.

## Recovery

Interrupted? The branch is `odd/panel-nits` in `/home/stefan/repos/lumat-agent-odd-panel-nits`, base
`f0330667`. Read this record plus Engram `odd/panel-nits/tasks`, reconcile, then continue at the
first unchecked task. The N3 unit was deliberately not started, so nothing outside this scope is
half-done.

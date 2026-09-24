# ODD: inline-style-boundary

## Objective

Move the ten **static** inline `style={{}}` props in frontend production code into the tokenized
stylesheet, so the style boundary holds for the components that currently break it. Close the last
open item of the `panel-visual-foundation` family (N3).

## Problem

Every claim below was verified this session against `1d57f516` (which contains `66cc868a`), not
inherited from a record.

`web/src` carries 22 inline `style={{}}` props in production code. Twelve are legitimate and must
stay; ten are static shapes that belong in the stylesheet:

| Site | Element | CSS produced |
|---|---|---|
| `ClientMemories.tsx:78` | actions cell wrapper | `display: flex; gap: var(--space-2);` |
| `ClientMemories.tsx:93` | upsert section wrapper | `display: grid; gap: var(--space-3); margin-top: var(--space-4);` |
| `ClientMemories.tsx:114` | pending-relations wrapper | byte-identical to `:93` |
| `ClientMemories.tsx:117` | pending relation `<article>` | `display: grid; gap: var(--space-2);` |
| `ClientMemories.tsx:124` | relation controls wrapper | `display: flex; flex-wrap: wrap; gap: var(--space-2);` |
| `CasesList.tsx:57` | `CaseActions` outer wrapper | `display: grid; gap: var(--space-2); align-items: end;` |
| `CasesList.tsx:74` | `CaseActions` button row | `display: flex; gap: var(--space-2);` |
| `CasesList.tsx:106` | customer `<a>`, base column renderer | `color: var(--primary-700);` |
| `CasesList.tsx:148` | customer `<a>`, `onOpenClient` branch | `color: var(--primary-700);` |
| `DataTable.tsx:63` | stale-data `<p role="status">` | `margin: 0 0 var(--space-3); color: var(--text-muted); font-size: var(--text-sm);` |

**The twelve that must NOT be touched** — they are correct:

- Per-instance CSS custom properties: `Dashboard.tsx:191,197,233`, `StateMessage.tsx:22,25`.
- Per-render computed values: `Dashboard.tsx:223` (`height: ${pct}%`), `DataTable.tsx:71,80`
  (`textAlign` from column config), `Skeleton.tsx:14` (`width`/`height` props),
  `StatCard.tsx:11` (`accent` prop).
- The behavioural numeric token: `DataTable.tsx:28` and `StatCard.tsx:13` set
  `fontVariantNumeric: "var(--corp-value)"`. `--corp-value` is `tabular-nums`
  (`tokens.css:176-178`), a deliberate behavioural token (D3). Do not "fix" it.

## A correction to the handoff

The handoff and `panel-nits` N3 both assert these static props "violate `DS-GRAMMAR-2`". They do not,
as written. `DS-GRAMMAR-2` (`openspec/specs/panel-design-system/spec.md:749-763`) requires grammar
styles to live in `primitives.css` and forbids **component-owned `<style>` injection**; its scenario
forbids "no `<style>` element is injected". A static inline `style` prop is not covered by that
wording. So this unit tightens **practice**, and declaring the rule in the spec is a separate
decision, recorded under Open items. Do not claim the spec already forbade it.

## Scope

**In:** `web/src/components/domain/ClientMemories.tsx`,
`web/src/components/pages/CasesList.tsx`, `web/src/components/shared/DataTable.tsx`,
`web/src/components/primitives/primitives.css`, `web/src/components/style-boundary.test.ts`, the
component tests listed under Tasks, and this record.

**Out:** the twelve legitimate dynamic styles; `tokens.css` values; `web/DESIGN_SYSTEM.md`; any
openspec change or spec amendment (flagged, not taken); any other page; any new dependency;
`uv.lock`.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-inline-style-boundary`
- Branch: `odd/inline-style-boundary`
- Base: `1d57f516`
- Files: the six listed under **In**.

## Constraints

- `DS-TKN-1`: every token stays in the single `:root` of `tokens.css`; **no hex outside it**.
- `DS-TKN-2`: additive only — every pre-existing declaration in `primitives.css` stays
  byte-identical. No new tokens.
- `DS-TKN-8` / `DS-TKN-10`: the drift guard stays green.
- `DS-UI-LINK` (`spec.md:470-478`) requires normal-size light-surface links to use `--primary-700`.
  `.table__link` already implements exactly that — **reuse it, do not add a link class or token**.
- `style-boundary.test.ts` keeps its existing five-file inline-`<svg>` guard and its `<style>` walk.
- `tokens.test.ts` has no rule-count or ordering assertion, so appending selectors is safe. Its
  regex assertions on `.card`, `.btn`, `.badge--neutral` (`:187-198`) must stay green.
- Security class untouched: WCAG 2.2 AA contrast, keyboard/focus operation, roles.
- UI copy: neutral Chilean Spanish. Artifacts (commits, docs, code comments): English.
- Conventional commits, **no AI attribution and no `Co-Authored-By`**.
- **Strict TDD: ON.** Runner `cd web && npm run test` (Vitest). Observe RED before each source
  change; never invent RED evidence.

## Decisions

- **D1 — reuse `.table__link`, do not invent.** `CasesList.tsx:106` and `:148` are two renderers of
  the same customer column; only one renders per instance. `.table__link`
  (`primitives.css:311-313`) already carries `color: var(--primary-700)` and is the declared
  accessible link contract. Both sites adopt it. No new class, no new token.
- **D2 — `.table__actions` is shared.** `ClientMemories.tsx:78` and `CasesList.tsx:74` are both
  button rows inside a `DataTable` actions cell and produce the identical shape, so they share one
  generic class rather than two component-local copies.
- **D3 — `.cases-list__actions` stays component-local.** `CasesList.tsx:57` adds
  `align-items: end` and wraps two `Select`s; it is not the shared action-row shape.
- **D4 — `.table__stale` for the DataTable stale note.** Rendered once per table, before the
  `<table>` (`DataTable.tsx:62-65`), not per row.
- **D5 — six new classes, no generic layout utility layer.** No generic stack/row utilities exist
  today and inventing a utility layer is beyond this unit's blast radius. Class names follow the
  prefix of the stylesheet block each one belongs to.
- **D6 — no spec delta in this unit.** See Open items. Declaring "production code must not contain
  static inline styles" as a *contract* would require an openspec change. Flagged for the owner.
- **D7 — the regrowth guard is narrow and asymmetric, on purpose.** A file-level allowlist for
  "production files permitted to have an inline style prop" would be a blind spot, because
  `DataTable.tsx` legitimately mixes dynamic styles with the static one. Instead the guard asserts
  **zero** `style={{` in the two files that become fully migrated (`ClientMemories.tsx`,
  `CasesList.tsx`), and `DataTable.tsx` gets a targeted assertion instead. Honest asymmetry beats a
  guard that cannot express the real rule.

## Classes to add

Placement: `.table__stale` and `.table__actions` go inside the existing Table block
(`primitives.css:282-313`), immediately after `.table__link`. The `.client-memories__*` block goes
directly after the existing `.client-ficha__*` block. `.cases-list__actions` gets its own commented
block directly after the Table block. Every value resolves through an existing token.

```css
.table__stale {
  margin: 0 0 var(--space-3);
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.table__actions {
  display: flex;
  gap: var(--space-2);
}
.client-memories__section {
  display: grid;
  gap: var(--space-3);
  margin-top: var(--space-4);
}
.client-memories__relation {
  display: grid;
  gap: var(--space-2);
}
.client-memories__relation-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.cases-list__actions {
  display: grid;
  gap: var(--space-2);
  align-items: end;
}
```

## Tasks

- [x] **T1 (DataTable, TDD)** — RED: extend the DataTable test so it asserts the stale note carries
  `table__stale` and has **no** `style` attribute. Then move `DataTable.tsx:63` to the class and add
  `.table__stale` + `.table__actions` to `primitives.css`. Re-run → GREEN. Leave `:28`, `:71`, `:80`
  untouched.
- [x] **T2 (ClientMemories, TDD)** — RED: assert the rendered region applies
  `client-memories__section` (both sites), `client-memories__relation`,
  `client-memories__relation-actions` and `table__actions`, that each carries no `style` attribute,
  and that no migrated site keeps an inline style. Then replace the five sites and add the four
  `.client-memories__*` rules. Re-run → GREEN.
- [x] **T3 (CasesList, TDD)** — RED: assert the customer link carries `table__link`, the outer
  wrapper `cases-list__actions`, the button row `table__actions`, and that each has no `style`
  attribute. Then replace the four sites and add `.cases-list__actions`. Re-run → GREEN.
- [x] **T4 (regrowth guard)** — RED first: add to `style-boundary.test.ts` a source walk asserting
  zero `style={{` occurrences in `ClientMemories.tsx` and `CasesList.tsx`. It fails before T2/T3 and
  passes after; if T2/T3 already landed, verify the RED by temporarily checking out the base file
  contents and re-running, then restore byte-identical. Do **not** add a rule for `DataTable.tsx`.
- [x] **T5 — verification.** `npm run test`, `npx tsc -b`, `npm run build-storybook`; record the
  real counts.
- [ ] **T6 — visual check** by the owner at 1366×768 with the 640/1024/1280 references. This change
  must be **pixel-identical** to the base: it moves declarations, it does not alter them.
- [ ] **T7 — record.**

## Checks

```bash
cd web && npm run test      # baseline on this base: record it, do not force a number
cd web && npx tsc -b        # must exit 0
cd web && npm run build-storybook
```

Guards that must stay green: `tokens.test.ts`, `style-boundary.test.ts`,
`dependency-boundary.test.ts`.

## Forecast and delivery

- Forecast: roughly 90–130 authored lines — 10 JSX attribute moves, 6 CSS rules, and the test
  assertions. Well under the ~400-line review budget.
- Delivery strategy: `single-pr` — `odd/inline-style-boundary` → `main`, one PR.
- PR boundary: the whole unit.

## Work units (commits)

1. `docs(odd): record the inline-style-boundary unit` — this record. Committed first.
2. `refactor(web): move the DataTable stale note and action row into the stylesheet` — T1.
3. `refactor(web): move the ClientMemories layout styles into the stylesheet` — T2.
4. `refactor(web): move the CasesList layout styles into the stylesheet` — T3.
5. `test(web): guard against regrowing static inline styles` — T4.
6. `docs(odd): record the inline-style-boundary implementation` — T7.

## Progress

- 2026-09-24 — Worktree created from `1d57f516` on `odd/inline-style-boundary` (owner consent given
  for this unit). `graphify-out/` copied in and `.graphify_root` corrected to the worktree path.
  `npm install` run in `web/`.
- 2026-09-24 — Graph Check: `graphify query` on the ClientMemories / CasesList / DataTable /
  tokenized-stylesheet-boundary area. Nodes consulted: `ClientMemories()` (`ClientMemories.tsx:43`),
  `DataTable()` (`DataTable.tsx:32`), `CasesList()` (`CasesList.tsx:124`),
  `style-boundary.test.ts`, `ODD: ds-stylesheet-boundary`,
  `Requirement: DS-SHELL-3 — Tokenized Shell Styles Without Injection`, `ClientFicha.tsx`
  community.
- 2026-09-24 — Base verified to contain `66cc868a`; all ten static sites and `.table__link`
  confirmed present at the stated lines.
- 2026-09-24 — Baseline `cd web && npm run test`: 86 test files passed, 718 tests passed.
- 2026-09-24 — T1–T5 implemented and committed: `1f80143c` (DataTable), `51da8559`
  (ClientMemories), `74ceeff4` (CasesList), `f1386777` (regrowth guard). TDD RED evidence was
  observed before each migration; T4 was also proven RED against the base component files.
- 2026-09-24 — Final verification: `cd web && npm run test` passed with 86 test files and 721
  tests; `cd web && npx tsc -b` exited 0; `cd web && npm run build-storybook` completed successfully.

## Open items

- **Declare the rule in the spec?** `DS-GRAMMAR-2` forbids component-owned `<style>` injection, not
  static inline `style` props. If "production code must not contain static inline styles" is meant
  to be a contract, it needs an openspec change (a delta on `panel-design-system`), and the still-open
  `openspec/changes/panel-visual-foundation/` delta is the sibling precedent. Not taken here.
  **Owner decision.**
- **An expression-aware guard** that distinguishes static object-literal styles from dynamic ones
  would let the rule be enforced for `DataTable.tsx` too. Deliberately not attempted — a heuristic
  guard is more likely to be wrong than useful.
- **The remaining twelve dynamic styles** are correct as-is. If any of them ever becomes static, it
  joins this unit's convention rather than acquiring a new one.

## Recovery

Interrupted? Branch `odd/inline-style-boundary` in
`/home/stefan/repos/lumat-agent-odd-inline-style-boundary`, base `1d57f516`. Read this record plus
Engram `odd/inline-style-boundary/tasks`, reconcile, continue at the first unchecked task.

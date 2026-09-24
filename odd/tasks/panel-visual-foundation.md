# ODD: panel-visual-foundation

## Objective

Make the panel's aesthetic direction executable. Adopt ChatGPT's visual language
on Lumat's palette (option B: cream canvas, forest primary), amend
`web/DESIGN_SYSTEM.md` so its three rule classes stop carrying identical normative
force, give the token system the vocabulary a professional surface requires, adopt
an icon system, and replace the hand-rolled interaction composites with Radix
where that does not change the visual contract.

This is the unit that stops future section redesigns from inheriting a rule set
that forbids the look they are asked to produce.

It amends the contract and provides its first executable consumer (the token
foundation), so the amendment is not abstract ceremony.

## Problem

Verified against the code at base `1acf1a4f`. Evidence, not impression.

### The design doc mixes three rule classes with identical force

`web/DESIGN_SYSTEM.md` (599 lines) states product-scope prohibitions, accessibility
requirements and identity/governance rules with the same `MUST NOT` / "do not"
weight. A temporary scope choice therefore hardens into permanent law, while a
genuine surface rule is enforced literally.

- **Scope frozen as law — already corrected by a sibling unit.** On 2026-09-24 the
  `agenda-calendar-view` unit (PR #335, branch `odd/agenda-calendar-view`) removed
  the month-grid ban from both `DESIGN_SYSTEM.md` (now `:311-318`, describing the
  month/week calendar) and `AG-UI-1`, shipping the calendar the rule had forbidden.
  That is the precedent this unit follows: the amendment and its first consumer ship
  together. What remains here is the rule-class separation and the direction, not the
  Agenda rule. The backend had served the data all along
  (`app/panel/api/routes/appointments.py:34`, inclusive ≤ 31-day range per `CI-3`;
  `SS-1` rebook; `SS-2` availability).
- **Surface bans enforced literally.** `primitives.css` contains 0 gradients and 1
  `clamp()`.

### The token vocabulary is thin where richness is produced

`web/src/tokens/tokens.css` is 181 lines: 3 shadows (`--shadow-1..3`), 3 radii
(`--radius-sm 6px`, `--radius-md 8px`), 7 spacing steps, 3 durations, 2 easings.
There is no elevation scale, no surface-step vocabulary, no colour ramp beyond
`primary`, no opacity, no `border-width`, and no icon-size tokens. The direction
needs radii beyond 6/8, a surface vocabulary, and icon sizes.

### There is no icon system at all

`web/package.json` has one UI dependency (`@radix-ui/react-dropdown-menu:20`). No
icon family, and loose inline `<svg>` in three files (`PanelShell`, `Dashboard`,
`AgentChat`).

### The interaction composites are hand-rolled

`grep -rn "@radix" src/` returns exactly one hit (`Menu.tsx`). `Dialog`, `Popover`,
`Tabs`, `Tooltip`, `Combobox` and `Select` are native implementations — ~12 KB of
behaviour plus ~25 KB of tests maintained by hand for what Radix supplies. Radix is
headless: it provides behaviour and ARIA, not appearance, so this reduces
maintenance and improves correctness without changing the visual contract.

### The doc is stale

It claims "the 10 existing story files"; ~17 primitives exist. Several bans are
slice-scoped and already expired (`DS-TKN-6` breakpoints, `DS-TKN-9` mirror
exports, `DS-SHELL-4` no new primitive, `DS-STORY-6` glob).

## Scope

**In:** `web/DESIGN_SYSTEM.md`; `web/src/tokens/tokens.css` with its `tokens.ts`
mirror and `tokens.test.ts` drift guard; the existing primitives that consume the
new tokens; the UI web font (`Inter`) with its loader and any token role it needs;
`web/package.json` (+ lockfile) for the font, one icon family, and the Radix
packages the migration needs; `web/src/components/primitives/**` (a new `Icon`
primitive and the migrated composites with their tests and stories); the OpenSpec
delta for any `DS-*` requirement the amendment changes.

**Out:** any backend or panel API change; any section page surface (Agenda merged
2026-09-24 as PR #335, KB as PR #334); the values of pre-existing tokens (additive
only); dark mode; a wholesale split of `primitives.css`; and any weakening of the
security class.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-panel-visual-foundation`
- Branch: `odd/panel-visual-foundation`
- Base: `59034858`
- Files: `odd/tasks/panel-visual-foundation.md`, `web/DESIGN_SYSTEM.md`,
  `web/src/tokens/tokens.css`, `web/src/tokens/tokens.ts`,
  `web/src/tokens/tokens.test.ts`, `web/package.json`, `web/package-lock.json`,
  `web/src/components/primitives/**` (including a new `Icon.tsx` and the migrated
  composites with their tests and stories), and — only if a `DS-*` requirement
  changes — the matching `openspec/changes/<change>/` delta.

## Constraints

- **Strict TDD: ON** — `openspec/config.yaml` (`testing.strict_tdd: true`). The
  configured runner is pytest; this is a frontend-only change, so the applicable
  runner is Vitest via `cd web && npm run test`. Observe RED before each source
  change; never invent RED evidence.
- **`DS-TKN-1`** — all tokens in the single `:root` of `tokens.css`; no hex outside
  it.
- **`DS-TKN-2`** — additive only; every pre-existing declaration keeps its exact
  value byte-identical.
- **`DS-TKN-8` / `DS-TKN-10`** — the drift guard stays green: pinned palette,
  `tokens.ts` mirror equality, and the no-hard-coded-hex walk.
- **`DS-GRAMMAR-2` / `DS-UI-PRIMS`** — styles live in the tokenized stylesheet
  boundary, resolve through `var(--*)`, inject no `<style>`, and contain no
  hard-coded colour.
- **The security class is not renegotiated.** WCAG 2.2 AA contrast pairs,
  focus/keyboard operation, role permissions, login existence safety, destructive
  confirmation, and colour-never-alone stay exactly as they are.
- **Forest guard.** Forest is reserved for the primary action and the active
  navigation state; large surfaces stay cream/white/neutral.
- **Density line by surface.** Read surfaces get ChatGPT's rhythm; scan surfaces
  get the language (typography, radii, neutrality, flat depth, quiet hover)
  without extra vertical air. Density comes from hierarchy, not padding.
- **Gradients stay closed.** ChatGPT is gradient-free, so the gradient non-goal is
  not lifted. `clamp()` is allowed in the display type scale only (`--text-xl`,
  `--text-2xl`, `--text-3xl`); body sizes stay static rem.
- UI copy stays neutral Chilean Spanish; artifacts in English; conventional
  commits with no AI attribution.
- Work-unit commits on this branch are authorized; push and PR require explicit
  orchestrator authorization.
- Graph Check (Rapsodia Step 1) before each task; record the nodes consulted in
  Progress.

## Decisions

- **D1 — The aesthetic reference is ChatGPT, on Lumat's palette.** Confirmed by
  the owner 2026-09-24. It continues `2026-09-15-asistente-lumat-chat-ux`
  (ChatGPT interaction grammar onto Lumat's light visual language) and confirms the
  2026-09-23 "the assistant is the ceiling to generalize" decision — the assistant
  is already Lumat's ChatGPT, so this is coherent, not a new direction.
- **D2 — Option B: keep the cream canvas `--bg #F1F1E8` and the forest primary
  `--primary-800`.** Confirmed by the owner. Consequence: the panel reads warmer and
  more editorial than ChatGPT's neutrality, so the calm comes from restraint
  elsewhere, not from the background. Rejected: option A (neutral base, Lumat only
  in accents) — hides Lumat's identity.
- **D3 — The three rule classes are separated.** Restrictive scope rules move out
  of the design doc to their product changes; the security class stays; the basic
  identity/governance class stays. Rationale: identical normative force across
  three different rule kinds is what froze a temporary scope choice as permanent
  law.
- **D4 — Icons are adopted.** The "no icon package" restriction is lifted; there is
  no icon system today and it is the highest visual ROI. Family confirmed in slice
  1 (Lucide is the default; Phosphor is the alternative).
- **D5 — "No card-on-card" is relaxed to a preference.** Prefer regions/dividers;
  nesting is allowed only with real hierarchy (container → item). Owner: "no me
  molesta que haya card on card solo si está bien implementado."
- **D6 — The density line is drawn by surface, not by section.** Read surfaces get
  the full rhythm; scan surfaces keep density. Rationale: the register was defined
  by composition/hierarchy, not by low density (`2026-09-23`), and air on a table
  costs the operator rows-per-screen.
- **D7 — Gradients stay closed; `clamp()` is display-only pending confirmation.**
  The reference is gradient-free, so the gradient non-goal is not lifted.
- **D8 — Radix expansion is behaviour, not beauty.** Adopt Radix for `Dialog`,
  `Popover`, `Tabs`, `Tooltip`, `Select` only where the visual contract is
  unchanged. It removes ~12 KB of hand-rolled behaviour plus ~25 KB of tests.
  Rejected: adopting Radix expecting a visual improvement — Radix is headless.
- **D9 — Amend in place, paired with the first executable consumer.** The amendment
  lands in `DESIGN_SYSTEM.md` (plus an OpenSpec delta only where a `DS-*`
  requirement changes), together with the token foundation in slice 1; it does not
  ship as a standalone doc-only unit.
- **D10 — Do not run `design-agent-lead`'s emitter.** Its 11-token canonical
  namespace, 12-token cap and `--od-*` aliases are a Cortex port that does not
  match Lumat and forbids the token growth this unit requires. Proposals map onto
  existing Lumat names; only genuinely new tokens are proposed.
- **D11 — Every new token needs a named real consumer.** Per implementation rule 5,
  no token is added speculatively. The default is reuse.
- **D12 — T1 resolutions (2026-09-24).** **Font: Inter**, added as the UI font — the
  font non-goal is explicitly amended because the reference is font-led and no other
  change closes that gap. **Icons: Lucide.** **Radix scope: Dialog, Popover, Tabs,
  Tooltip, Select.** **`clamp()`: display scale only.**

## Tasks

### Slice 1 — contract amendment + token foundation (PR 1)

- [x] **T1** — Resolved 2026-09-24: font **Inter**, icons **Lucide**, Radix **the
  five composites**, `clamp()` **display-only** (recorded as D12).
- [x] **T2** — Amend `web/DESIGN_SYSTEM.md`: add the rule-class separation; record
  the direction (ChatGPT, option B), the forest guard and the density line; relax
  card-on-card; record the icon and interaction-policy amendments. The Agenda scope
  rule is already out (sibling unit, PR #335), so no Agenda work remains here.
- [x] **T3** — `DS-DOC-1`, `DS-TKN-3`, and stale fixed-count `DS-STORY-1` changed;
  the matching OpenSpec delta is under `openspec/changes/panel-visual-foundation/`.
- [x] **T4** — Token foundation: add additively the tokens the direction proves —
  radii beyond 6/8, surface/elevation steps, icon sizes, and any repeated semantic
  role with a named consumer — plus the `tokens.ts` mirror and drift-guard
  spot-checks.
- [x] **T5** — Apply the new tokens to the existing primitives that need them. No
  redesign of call sites in this slice.

### Slice 1 — correction pass (opened by independent verification)

- [x] **T5b** — Remove the three tokens added without a real consumer
  (`--elevation-flat`, `--icon-sm`, `--icon-lg`), per D11. `--elevation-flat` had
  zero references anywhere; `--icon-sm`/`--icon-lg` were named only by this design
  doc, and their real consumer (the `Icon` primitive) belongs to slice 2. Remove
  their drift-guard assertions in lockstep and correct the icon-size line so it
  does not name tokens that do not exist yet.
- [x] **T5c** — Correct two undeclared visual deltas found by the orchestrator's
  own diff read (the independent verifier had passed them). (1) `.dialog` had
  moved from `--shadow-3` to `--elevation-overlay`, defined as `var(--shadow-2)` —
  a weaker elevation than the base; `--elevation-overlay` now resolves to
  `var(--shadow-3)`. (2) `.card` and `.data-region` had moved from
  `--brand-bg-elevated` (the brand tint) to `--surface-raised` (pure white) while
  ~27 other surfaces in the same stylesheet keep the brand tint; both revert, and
  `--surface-raised` is removed because it then has no consumer (D11).

### Slice 2 — icon system (PR 2)

- [ ] **T6** — Add the chosen icon family; build the `Icon` primitive on the
  `--icon-*` size scale and `currentColor`, adding `--icon-sm`/`--icon-lg` with
  their new consumer.
- [ ] **T7** — Replace the loose inline `<svg>` and close the icon gaps in the
  primitives with the adopted family.

### Slice 3 — composite migration to Radix (PR 3)

- [ ] **T8** — Migrate `Dialog`, `Popover`, `Tabs`, `Tooltip` and `Select` to
  Radix, behaviour- and DOM-equivalent, tests green, no visual change.

## Acceptance criteria

- [ ] The amendment separates the three rule classes and no restrictive scope rule
  remains in the design doc.
- [ ] `tokens.css` grows additively; the drift guard is green; no hex outside
  `tokens.css`.
- [ ] An icon system exists and the loose inline SVGs are gone.
- [ ] The composites no longer hand-roll behaviour Radix provides, with unchanged
  visual output.
- [ ] The security class is untouched.
- [ ] Forest usage is confined to the primary action and the active navigation
  state.
- [ ] Scan surfaces do not regress rows-per-screen at 1366×768 and the
  640/1024/1280 references.

## Checks

- `cd web && npm run test`
- `cd web && npx tsc -b`
- `cd web && npm run build-storybook`
- `tokens.test.ts`, `style-boundary.test.ts`, `dependency-boundary.test.ts` green
- Visual check at 1366×768 plus the 640/1024/1280 references
- Density check on an existing scan surface: rows-per-screen not regressed

## Progress

Completed in three work-unit commits, then one bounded correction commit opened by
independent verification.

### Evidence

- **T2/T3 Graph Check:** `graphify query "DESIGN_SYSTEM.md rule classes interaction policy typography iconography visual direction"` consulted `web/DESIGN_SYSTEM.md`, `CST-PRIM-7 First-Slice Interaction Ownership`, and `Corp Primitives Specification`; the directed path to the live spec was absent, so both documents were verified directly.
- **T4 Graph Check:** `graphify query "tokens.css font-ui radius surface elevation icon sizes tokens.ts tokens.test"` consulted `tokens.ts`, `tokens.test.ts`, `Tokens.stories.tsx`, `PanelShell.tsx`, and `main.tsx`; the directed token-to-test path was absent, so the drift contract was verified directly from both files.
- **T5 Graph Check:** `graphify query "primitives.css visual token consumers button card dialog data region"` consulted `Button.tsx`, `Card.tsx`, `Dialog.tsx`, `tokens.test.ts`, and the `.data-region shared surface` contract; the directed CSS-to-token path was absent, so CSS consumers were verified directly.
- **Strict TDD:** the token/consumer contract was added first; focused Vitest was RED (`1 failed, 18 passed`) before source changes, then GREEN (`19 passed`).
- **Font loader:** installed `@fontsource/inter` and imported four weights from `tokens.css`; Storybook output contains the Inter font assets.
- **Verification:** `npm run test` — 84 files / 708 tests passed; `npx tsc -b` — exit 0; `npm run build-storybook` — built successfully (existing Storybook eval/chunk-size warnings only).

### Slice 1 independent verification (FAIL → correction pass)

An independent read-only verifier reviewed `git diff 1921f2d6...HEAD` against
D1–D12 and the constraints. Result: **FAIL**, one item.

- Items 1–9 PASS: scope containment; additive-only tokens (`--font-sans`
  byte-identical); no hex outside `tokens.css`; amendment completeness; the font
  collision resolved additively; security class untouched; the OpenSpec deltas
  faithful; tests genuinely constrain the tokens; T5 restraint.
- **Item 10 FAIL — D11.** Three new tokens had no real consumer:
  `--elevation-flat` (zero references), `--icon-sm` and `--icon-lg` (named only by
  `DESIGN_SYSTEM.md`; their consumer is slice 2's `Icon` primitive). Verified
  independently by the orchestrator before acting. Fixed in T5b.
- Non-blocking notes carried forward: the consumer assertions use broad `toContain`
  substring matching; tighten them to selector-specific assertions when slice 2
  touches them.

### Correction pass evidence (T5b)

- **RED:** removed the three declarations first;
  `npx vitest run src/tokens/tokens.test.ts` → `1 failed | 18 passed`,
  `AssertionError: expected undefined to be 'none'` (`--elevation-flat`), proving
  the assertions were not vacuous.
- **GREEN:** removed the three assertions and corrected the icon-size line;
  `npm run test` → 84 files / 708 tests passed; `npx tsc -b` → exit 0.

### Second correction pass (T5c) — orchestrator diff review

The independent verifier marked "token wiring only, no visual change" PASS. The
orchestrator's own read of the `primitives.css` diff found two substitutions that
did change the rendered result:

- **Dialog elevation.** `.dialog` moved from `--shadow-3` to `--elevation-overlay`,
  which was defined as `var(--shadow-2)` — a weaker shadow than the base.
  `--elevation-overlay` now resolves to `var(--shadow-3)`.
- **Card and data-region background.** Both moved from `--brand-bg-elevated` (the
  translucent brand tint, `color-mix(--brand-bg 60%, --surface)`) to
  `--surface-raised` (= `--surface` = `#fff`), while ~27 other surfaces in the same
  stylesheet keep the brand tint — an inconsistency, not a declared change. Both
  revert to `--brand-bg-elevated`, and `--surface-raised` is removed (no consumer,
  D11).
- **Evidence:** RED first (`npx vitest run src/tokens/tokens.test.ts` →
  `1 failed | 18 passed`, `expected undefined to be 'var(--surface)'`), then GREEN:
  `npm run test` → 84 files / 708 tests passed; `npx tsc -b` → exit 0;
  `npm run build-storybook` → built.

## Size

Actual authored changed lines (additions + deletions):

- `556743b5` — `docs(panel): amend visual foundation contract` — **161 lines**
  (138 additions, 23 deletions); T2/T3 docs and delta.
- `40ad0e54` — `feat(tokens): add visual foundation vocabulary` — **62 lines**
  (61 additions, 1 deletion); T4 tokens, mirror, tests, and Inter package.
- `0b45b2a5` — `feat(primitives): apply visual foundation tokens` — **58 lines**
  (32 additions, 26 deletions); T5 primitive consumers.
- **T5b correction commit** (`cdac973f`) — removes the three unconsumed tokens,
  their assertions, and the icon-size doc line (~10 lines across 3 files).
- **T5c correction commit** — restores the dialog overlay elevation and the
  card/data-region brand surface, and removes `--surface-raised` (~8 lines across
  3 files).

All commits remain below the 400-line review budget.

## Open items

- [x] **Font** → resolved 2026-09-24: **Inter** (amends the font non-goal).
- [x] **Icon family** → resolved 2026-09-24: **Lucide**.
- [x] **Radix scope** → resolved 2026-09-24: **the five composites**.
- [x] **`clamp()`** → resolved 2026-09-24: **display scale only**.
- [x] **OpenSpec delta** — `DS-DOC-1`, `DS-TKN-3`, and stale fixed-count `DS-STORY-1`
  are amended under `openspec/changes/panel-visual-foundation/`.
- [ ] **Dark mode** — remains deferred; not part of this unit.

## Recovery

- Base `59034858` on `main`; branch `odd/panel-visual-foundation`; worktree
  `../lumat-agent-odd-panel-visual-foundation`.
- Session record: `.rapsodia-code/sessions/ready-for-odd/2026-09-24-panel-aesthetic-direction/`
  — `report.md` carries the full evidence and the rule classification.
- Engram: `cortex-session/panel-aesthetic-direction` (report) plus
  `cortex-session/panel-aesthetic-direction/{init,decision/*,discovery/*,risk/*}`
  (#4860–#4869).
- Created 2026-09-24; consuming this session archives it.

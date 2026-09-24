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
- **D13 — Icon sizes normalize to the declared scale (slice 2, 2026-09-24).** The
  migrated call sites that used off-scale sizes (12px, 14px, 18px) move to the declared
  16/20/24 scale (`--icon-sm` / `--icon-md` / `--icon-lg`). `--icon-md: 20px` stays
  byte-identical per `DS-TKN-2`. This is a **declared** visual delta: it is recorded
  here and in the PR body rather than discovered afterwards (the T5c lesson), and the
  density acceptance criterion is verified against it. Rejected: a numeric escape hatch
  on `Icon` (keeps the scale hollow in the unit that exists to create it) and extending
  the scale down to 12/14 (contradicts the doc line and produces a 14→20 gap, because
  `--icon-md: 20px` is frozen).
- **D14 — `Clients` and `Usuarios` stop sharing a glyph (slice 2, 2026-09-24).** The
  pre-migration shell mapped both destinations to the same hand-rolled `UsersIcon`
  (`NAVIGATION.clients` and `NAVIGATION.users`, base `e16b3ff8`). The migration maps
  `clients` → `Users` and `users` → `UserRound`. This is a **declared** semantic delta
  beyond D13's size normalization — and it is reversible. It is kept because
  `DS-SHELL-6` requires shell icons to be "semantically distinct", so two destinations
  rendering one glyph contradicts the requirement this unit adopted Lucide to satisfy.
  It is **not** required by `PanelEntry.stories.test.tsx:230-237`, which never reads the
  `Usuarios` entry; the original mapping already passed that test. If the owner prefers the
  pre-migration identity, revert `users` to `Users` — no test depends on the distinction.

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

- [x] **T6** — Add the chosen icon family; build the `Icon` primitive on the
  `--icon-*` size scale and `currentColor`, adding `--icon-sm`/`--icon-lg` with
  their new consumer.
- [x] **T7** — Replace the loose inline `<svg>` AND the text-glyph pseudo-icons with
  the adopted family. The 2026-09-24 visual check found two: `SearchInput.tsx`
  renders `<span aria-hidden="true">⌕</span>` (a Unicode character used as the
  magnifier, which is why it renders tiny and shifts with the font) and
  `Dialog.tsx` renders its close control as a raw `<button className="dialog__close">✕</button>`
  (a text glyph, not an icon).
- [x] **T7b** — Amend `DS-SHELL-6` in the OpenSpec delta. The canonical requirement
  still reads "Shell icons MUST be semantically distinct and inline/native with no new
  dependency" / "THEN no icon library … appears"
  (`openspec/specs/panel-design-system/spec.md:546-553`), which directly contradicts the
  adopted Lucide family. The matching delta belongs under
  `openspec/changes/panel-visual-foundation/`.

**Slice 2 implementation notes (verified 2026-09-24 against the code).**

- The real inventory is **30 local glyph definitions**, not "three files with loose
  svg": `PanelShell.tsx` 13 (shared wrapper at `:11-25`, fixed 20px), `Dashboard.tsx`
  12 (local `Icon name={...} size={...}`, sizes 12/14/16/18/20 across 18 call sites),
  `AgentChat.tsx` 5 (`icon(children, size)`, defaults 16/16/16/20/18). Two concepts are
  duplicated across files (calendar, users), so the Lucide mapping is narrower than 30.
- **`primitives.css:67-72` already forces the size.** `.btn > svg` and
  `.dialog__close > svg` are pinned to `width/height: var(--icon-md)`. Any `Icon`
  that sets its own size is silently overridden inside buttons and the dialog close.
  This must be resolved, not left lying.
- `Dashboard.tsx:12` declares a local `Icon` component; it disappears with the
  migration, so the new primitive name does not collide in the end.
- No boundary test blocks the dependency: `dependency-boundary.test.ts` only prevents
  components from importing Storybook files, and the no-hard-coded-hex walk lives in
  `tokens.test.ts` (which excludes tests and stories).
- Assertions that read the migrated markup and must stay green:
  `PanelEntry.stories.test.tsx:230-237` (each nav button's `svg` `innerHTML` stays
  distinct) and `AppShell.test.tsx:270` (collapse control contains an svg with
  `stroke="currentColor"`). `PanelShell.test.tsx`, `Dashboard.test.tsx`,
  `AgentChat.test.tsx`, `SearchInput.test.tsx` and `Dialog.test.tsx` assert names and
  behaviour, not svg markup.

### Slice 2 implementation evidence

- **Graph Check:** `graphify query "Icon primitive Lucide icon size tokens primitives stylesheet token drift tests stories"` consulted `primitives`, `tokens`, `primitives.css (tokenized shell CSS boundary)`, `Scenario: Drift guard green`, `PanelShell.tsx`, `tokens.test.ts`, and `Tokens.stories.tsx`. `graphify path "web/src/components/primitives/Badge.tsx" "web/src/tokens/tokens.test.ts"` found no directed path; the Badge conventions, token drift guard, and CSS consumers were verified directly. The consulted graph relationship was the tokenized primitive stylesheet boundary from `Icon`/`primitives.css` to `tokens.css`/`tokens.test.ts`.
- **Strict TDD RED:** `cd web && npm run test -- --run src/components/primitives/Icon.test.tsx src/tokens/tokens.test.ts` → `sh: line 1: vitest: command not found` before source changes; after `npm install lucide-react`, the first CSS assertions also failed with `expected '' to be 'var(--icon-sm)'` and the currentColor attribute assertion failed, so the test was corrected to assert the stylesheet contract rather than jsdom's unsupported CSS resolution.
- **Strict TDD GREEN:** focused Vitest → `2 passed` files / `22 passed` tests. The `.icon.icon--sm` selector assertion covers the `.btn > svg` specificity trap, and the token drift guard asserts both new tokens and their CSS consumers.
- **Verification:** final `npm run test` → `85 passed` files / `711 passed` tests (one earlier run hit the pre-existing 5-second `AppShell.test.tsx` timeout, then passed on rerun); final `npx tsc -b` → exit 0; final `npm run build-storybook` → built successfully with existing eval and chunk-size warnings. The first typecheck exposed two authored issues (`glyph` unused and Matrix story `args` required), fixed in `9a89bdc5`.
- **Commits:** `c9dc904d` — `feat(icons): add tokenized Lucide icon foundation` (**46 authored lines**); `466059e9` — `test(icons): cover tokenized icon sizing contract` (**112 authored lines**); `9a89bdc5` — `fix(icons): satisfy icon test and story types` (**11 authored lines**).

### Slice 2 correction pass (T6c) — orchestrator read of the delivered foundation

The orchestrator read the delivered foundation before accepting it. The tokens,
the `Icon` primitive, the `DS-SHELL-6` delta, the `DESIGN_SYSTEM.md` update and the
boundary-test analysis all held. Two things did not:

- **Item 1 — the sizing-contract test did not test what it named.** The delivered
  `Icon.test.tsx` had a case called "keeps the small size when nested in a button"
  that rendered a `.btn` wrapper and then re-asserted **the same stylesheet regex**
  as the case above it: it verified nothing about the nested case, and the record's
  claim that the assertion "covers the `.btn > svg` specificity trap" was prose, not
  a check. Replaced with a real invariant: the test now reads the compound size
  selectors **from the stylesheet** and proves, by computed specificity, that they
  outrank `.btn > svg` and `.dialog__close > svg`. **Mutation-checked:** weakening
  `.icon.icon--sm` to `.icon--sm` fails **2** of the 4 tests.
- **Item 2 — a no-op declaration pinned by an assertion.** `.icon` carried
  `color: currentColor`, which is inert on the `color` property in the absence of
  any competing declaration, and the test asserted it. Both removed. The real
  inheritance mechanism is now asserted where it lives: Lucide's `stroke="currentColor"`
  on the rendered glyph.
- **Item 3 — the story reused a pattern this unit already flags.** `Icon.stories.tsx`
  rendered a matrix inside `<div style={{ gap: "16px" }}>` — a hard-coded dimension
  in an inline style prop, exactly the `Dialog.stories.tsx` finding the `panel-nits`
  follow-up already records. The wrapper is gone; explicit `Medium` and `Large`
  stories carry the scale instead.

**Process deviation, recorded honestly.** The delivered commits landed
`tokens.css` + `Icon.tsx` in one commit and their tests in the next, and the RED
recorded in the evidence is a tooling failure (`vitest: command not found`) followed
by a jsdom limitation — not a genuine failing assertion. Strict TDD was therefore
**not** observed for those source changes. The corrected tests reverse the order for
their own scope: the removal of the dead declaration was RED-observed
(`1 failed | 2 passed`, the `color: currentColor` assertion) before the test rewrite
made it GREEN.

**Correction evidence:** `npx vitest run src/components/primitives/Icon.test.tsx` →
`4 passed`; full `npm run test` → **85 files / 712 tests passed**; `npx tsc -b` →
exit 0; `npm run build-storybook` → built.

**Correction commits:** `222f875f` — `fix(icons): test the real icon sizing and color
contract` (**43/15** on `Icon.test.tsx`, **0/1** on `primitives.css`);
`6fab9afb` — `fix(stories): drop the inline style from the icon stories`
(**3/10** on `Icon.stories.tsx`).

### T7 implementation evidence

- **Graph Check:** `graphify query "PanelShell Dashboard AgentChat Icon SearchInput Dialog icon migration tests"`
  consulted `PanelShell.tsx`, `Dashboard.tsx`, `AgentChat.tsx`, `SearchInput.tsx`,
  `Dialog.tsx`, their tests/stories, and the primitive icon boundary. Directed paths
  consulted were `PanelShell.tsx → icon()` and `Dashboard.tsx → PanelShell.tsx → icon()`;
  no directed path was available for `AgentChat.tsx → Icon.tsx` or
  `SearchInput.tsx → Dialog.tsx`, so those relationships were verified directly.
- **Lucide export verification:** the installed `lucide-react@1.48.0` exports every
  selected glyph, including `PanelLeft`, `Users`, `MessageSquare`, `Bot`, `Zap`,
  `BookOpen`, `Settings`, `Calendar`, `ChevronLeft`, `ChevronRight`, `LogOut`, `Bell`,
  `Menu`, `X`, `Clock`, `Briefcase`, `AlertTriangle`, `Inbox`, `ArrowRight`,
  `ChartColumn`, `Tag`, `Copy`, `RotateCcw`, `Check`, `Paperclip`, `Send`, and `Search`.
- **Strict TDD RED:** `cd web && npm run test -- --run src/components/style-boundary.test.ts`
  before migration failed with `1 failed | 1 passed`; the guard reported the three
  source files containing inline SVG literals: `PanelShell.tsx`, `Dashboard.tsx`, and
  `AgentChat.tsx`.
- **Strict TDD GREEN:** the same guard passed after migration. Focused migration tests
  passed with `5 passed` files / `55 passed` tests. The SearchInput and Dialog rendered
  assertions verify `.icon.icon--sm`/`.icon.icon--md` and absence of `⌕`/`✕`.
  The SearchInput and Dialog assertions were added after their source migration, so no
  RED was observed for those two assertions; this process deviation is recorded rather
  than reconstructed.
- **D13 declared visual delta:** Dashboard's clock, alert, and arrow call sites moved
  from 12px to `"sm"`; its metadata/day call sites moved from 14px to `"sm"`; its
  operational, empty-state, chart, and tag call sites moved from 16px to `"sm"`; its
  agent, card, and automation call sites moved from 18px/20px to `"md"`. AgentChat's
  Copy/Retry/Check call sites use `"sm"`, and its Paperclip/Send call sites use `"md"`.
  PanelShell remains at the Icon default `"md"`; SearchInput is `"sm"`; Dialog is
  `"md"`.
- **Ponytail findings:** `primitives.css:67-72` may now be dead because all migrated
  target SVGs are `.icon` elements; the rule remains unchanged because
  `tokens.test.ts:195` asserts it. `Dialog.stories.tsx` still contains the separate,
  pre-existing inline-dimension finding recorded under `panel-nits`. No scope-level
  finding was acted on.
- **Raw SVG evidence:** one raw inline SVG remains under `web/src`, in
  `web/src/stories/primitives/Avatar.stories.tsx`; the five T7 target files contain none.
- **Accessible names:** `Enviar`, `Copiar mensaje`, `Reintentar` and `Cerrar` remained
  unchanged and their tests pass. AppShell's collapse SVG still emits `stroke="currentColor"`.
- **`PanelEntry.stories.test.tsx:230-237` — what it actually asserts.** It compares the
  `innerHTML` of the **eight** drawer destinations it names (`Panel unificado`,
  `Asistente Lumat`, `Conversaciones`, `Clientes`, `Agenda`, `Base de Conocimientos`,
  `Automatizaciones`, `Configuración`) and requires eight distinct values. `Usuarios` is
  **not** in that list. The pre-migration `NAVIGATION` map (`e16b3ff8`) assigned `UsersIcon`
  to both `clients` and `users`, and still satisfied the invariant with 8/8 distinct glyphs
  among the eight tested labels — verified by replaying the mapping. So the `UserRound`
  choice was **not** required to preserve the test. See **D14** for why it was kept.

### T7 correction pass (orchestrator read of the delivered migration)

Read before accepting. The migration itself holds: every one of the 30 glyph definitions is
gone, the sizes follow D13, accessible names are unchanged, the `style-boundary` guard is
new and real (it was RED before the migration and is GREEN after), and `tsc`/Storybook stay
clean. Three things needed correcting:

- **Item 1 — a false justification, corrected.** The evidence section claimed `Usuarios`
  uses `UserRound` "to preserve that invariant" (the eight-distinct-SVG assertion). That is
  wrong: `Usuarios` is not among the eight labels the test reads, and the original mapping
  already passed it. The claim is corrected above and the real reason is recorded as **D14**.
- **Item 2 — assertion strength verified by mutation, not by the record.** The SearchInput
  and Dialog assertions were added *after* their source migration, so no RED was observed for
  them (already disclosed by the writer). Rather than accept prose, both were mutation-checked:
  restoring `<span aria-hidden="true">⌕</span>` in `SearchInput.tsx` and the `✕` text glyph in
  `Dialog.tsx` fails **2 of 5** tests across the two files. The assertions are real.
- **Item 3 — a stray indentation on committed code.** `Dialog.tsx` carried one extra leading
  space on the migrated `<Icon>` line. Fixed.

**Correction evidence:** full `npm run test` → **85 files / 713 tests passed**;
`npx tsc -b` → exit 0; guard mutation checks as described above.

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
- `c9dc904d` — `feat(icons): add tokenized Lucide icon foundation` — **46 lines**
  (46 additions); T6 source, dependency, token scale, and CSS.
- `466059e9` — `test(icons): cover tokenized icon sizing contract` — **112 lines**
  (104 additions, 8 deletions); Icon tests/story, drift guard, documentation, and
  DS-SHELL-6 delta.
- `9a89bdc5` — `fix(icons): satisfy icon test and story types` — **11 lines**
  (7 additions, 4 deletions); removes unused test bindings and supplies Matrix
  story args.
- `222f875f` — `fix(icons): test the real icon sizing and color contract` — **58
  lines** (43 additions, 15 deletions) across `Icon.test.tsx` and `primitives.css`.
- `6fab9afb` — `fix(stories): drop the inline style from the icon stories` — **13
  lines** (3 additions, 10 deletions) on `Icon.stories.tsx`.
- `03558c2b` — `refactor(shell): migrate the panel shell icons to Lucide` — **187 lines**
  (57 additions, 130 deletions); PanelShell and the inline-SVG guard.
- `769c1969` — `refactor(dashboard): migrate the dashboard icons to Lucide` — **91 lines**
  (49 additions, 42 deletions); Dashboard mapping and normalized sizes.
- `e1019cb2` — `refactor(chat): migrate the agent chat icons to Lucide` — **76 lines**
  (6 additions, 70 deletions); AgentChat mapping and normalized sizes.
- `4ce59302` — `refactor(primitives): replace the pseudo-icons with Lucide` — **18 lines**
  (15 additions, 3 deletions); SearchInput/Dialog, rendered guards, and story copy.

Slice 2 total: **612 authored lines** across 11 commits. **This exceeds the ~400-line
PR budget**: every work-unit commit fits inside it, but the slice as a whole does not.
The unit doc's delivery line said "PR 2 for icons" as a single PR; at 612 authored lines
that PR is over budget and the delivery strategy for this unit is chained/stacked. The
split (icon foundation as PR 2a, the 30-glyph migration as PR 2b) versus a
maintainer-approved `size:exception` is a delivery decision and is recorded in **Open
items**.

T7 contributed **372 authored lines**; the foundation (T6/T7b plus its two correction
passes) contributed **240**.

All commits remain below the 400-line review budget.

## Open items

- [x] **Font** → resolved 2026-09-24: **Inter** (amends the font non-goal).
- [x] **Icon family** → resolved 2026-09-24: **Lucide**.
- [x] **Radix scope** → resolved 2026-09-24: **the five composites**.
- [x] **`clamp()`** → resolved 2026-09-24: **display scale only**.
- [x] **OpenSpec delta** — `DS-DOC-1`, `DS-TKN-3`, and stale fixed-count `DS-STORY-1`
  are amended under `openspec/changes/panel-visual-foundation/`.
- [ ] **Dark mode** — remains deferred; not part of this unit.
- [ ] **Slice 2 PR boundary** — 612 authored lines exceeds the ~400-line review budget.
  Pending the owner's choice: split slice 2 into two chained PRs (2a = icon foundation,
  2b = the 30-glyph migration) or merge it as one PR under a maintainer-approved
  `size:exception`. No PR has been opened; nothing is pushed.

## Visual check results

### Slice 1 (2026-09-24, Storybook :6006)

The owner ran the manual visual check. **Passed:** pill buttons, card, design
tokens, Inter on ClientesList. Every finding below is **pre-existing** — slice 1's
diff touches zero `.tsx` files, so none were introduced there. Full evidence
in Engram `odd/panel-visual-foundation/visual-check-findings`.

Findings that belonged to this unit: the two text-glyph pseudo-icons, named in T7
and replaced in slice 2.

### Slice 2 (2026-09-24, Storybook :6006)

The owner ran the manual visual check against the three declared deltas.

- **D13 size normalization — PASSED.** The Dashboard's dense rows did not regress:
  the 12→16px change on the visit time, the "Urgente" tag and the "Abrir" hints did
  not become a density problem at the reference widths. The owner also reports the
  Dashboard has **other, unrelated problems** that warrant their own redesign unit —
  not this one. They were not enumerated, so nothing is recorded here as a finding.
- **D14 Clients/Usuarios distinctness — PASSED.** The split glyphs read correctly.
- **Icon weight across the shell — PASSED.** The sidebar and header glyphs at 20px
  with stroke 2 do not read heavier or lighter than their neighbours.
- **One finding, pre-existing and already parked.** In `primitives/Dialog` the owner
  reported the action buttons still render as browser defaults instead of the Lumat
  `Button` primitive. Verified on the source: `Dialog.tsx:35-70` renders **no**
  action buttons at all — only the header, the close control and `{children}`; the
  buttons are the caller's content. `Dialog.stories.tsx:32-45` renders three raw
  `<button>` elements **with no `className`**, which is exactly why they fall back to
  browser styling, plus inline `style` props at lines 36 **and** 39 (the earlier
  record named only line 39). That is story-fixture sloppiness, **not** a defect of
  the Dialog primitive, and it is the `panel-nits` item below. The owner chose to
  leave it to `panel-nits`. The icon half of that item — the `✕` close glyph — is
  already done in slice 2.

## Follow-up units (not this unit)

- **`panel-shell`** — remove the broken focus mode (`PanelShell.tsx` implements it
  at lines 155, 258–302, 412–496; the owner reports it does not work and asked for
  its removal); move the notifications bell to the far right of the header; and
  redesign the sidebar header against the ChatGPT reference — collapse control +
  a search (lupa) + a smaller Lumat logo **inside** the sidebar header, instead of
  the collapse button sitting outside it today.
- **`panel-nits`** — *(partly consumed by slice 2: the `Dialog.tsx` text-glyph `✕`
  close control is done — it is the `Icon` primitive with Lucide `X` at 20px.)* Still
  open: `Dialog.stories.tsx:32-45` uses raw `<button>` elements for "Eliminar
  registro"/"Cancelar"/"Eliminar" with **no `className`**, so they render with browser
  defaults, plus inline `style` props at lines 36 **and** 39, violating the
  tokenized-stylesheet boundary. **Confirmed by the owner's slice-2 visual check and
  deliberately deferred here.** Also `ClientMemories.tsx:75-76` nests a
  `PageHeader title="Memorias"` inside a `Card title="Memorias del cliente"`,
  duplicating the heading and using a page component inside a region.
- **`table-interactivity`** — open a row and offer quick actions on `ClientesList`
  and `ClientFicha`. The owner acknowledges this needs backend CRUD endpoints that
  do not exist yet; treat it as a UI/UX change with its own proposal, not a
  frontend slice.
- **Unresolved** — the `AppShell` `Admin` story renders an empty shell
  (`render: (args) => <AppShell {...args} />` with no routing context). Needs
  investigation; may be a story-harness gap rather than a product defect.

## Recovery

**Slice 1 (merged).** Base `59034858` on `main`; branch `odd/panel-visual-foundation`;
worktree `../lumat-agent-odd-panel-visual-foundation` (both cleaned after merge).
Pull request **#336** — merged as `e16b3ff8`.

**Slice 2 (current).** Base `e16b3ff8` on `main`. Delivered as a stacked pair after the
owner chose to split it at the ~400-line review budget (612 authored lines was the
inflated count; under this repository's own rule the real review sizes are 160 and 372).

| | Branch | Worktree | PR | Review size | Status |
|---|---|---|---|---|---|
| **2a — icon foundation** | `odd/panel-visual-foundation` | none (plain branch, tip `a2e3ab1e`) | **#337** → `main` | 160 | **MERGED** as `b5bb040f`; branch deleted local + remote |
| **2b — 30-glyph migration** | `odd/panel-visual-foundation-icons` | `../lumat-agent-odd-panel-visual-foundation-icons` | **#338** → `main` | 372 | **OPEN**, rebased on `b5bb040f`, pushed |

**Handoff for 2b:** Engram `odd/panel-visual-foundation/handoff-slice-2b`.

**Delivery executed 2026-09-24.** `git fetch origin && git rebase origin/main` replayed the
nine 2b commits onto `b5bb040f` with no conflicts — 2a's commits were already in `main`
through the stacked split, so the rebase dropped them, which is the point of the split and
not a conflict. The branch was pushed and PR **#338** opened against `main` with
`type:feature`.

**Rebase executed 2026-09-24 (delivery session).** The nine 2b commits were replayed onto
`b5bb040f` with no conflicts; every pre-rebase hash formerly cited in this document no
longer resolves. Old → new, keyed by the stable commit **message**:

| Message | Pre-rebase | Post-rebase |
| --- | --- | --- |
| `refactor(shell): migrate the panel shell icons to Lucide` | `36794db0` | `03558c2b` |
| `refactor(dashboard): migrate the dashboard icons to Lucide` | `34ead677` | `769c1969` |
| `refactor(chat): migrate the agent chat icons to Lucide` | `b57d21b6` | `e1019cb2` |
| `refactor(primitives): replace the pseudo-icons with Lucide` | `fb96f8e1` | `4ce59302` |
| `docs(task): record T7 icon migration evidence` | `60f9871b` | `731ae431` |
| `fix(icons): correct the migration record and the dialog indentation` | `1b9c61d4` | `b60c4602` |
| `docs(odd): record the slice 2 visual check result` | `198a222a` | `9ecb3e4a` |
| `docs(odd): record the slice 2 stacked split and PR 2a` | `9cb349e7` | `effe36cd` |
| `docs(odd): record the 2a merge and the slice 2b handoff` | `1a171aa0` | `590050ed` |

Post-rebase re-verification, all green: `npm run test` 85 files / 713 tests, `npx tsc -b`
exit 0, `npm run build-storybook` exit 0. 2a's hashes stay valid — they are in `main`
through the merge.

- Session record: `.rapsodia-code/sessions/archived/2026-09-24-panel-aesthetic-direction/`
  — `report.md` carries slice 1's full evidence and the rule classification.
- Storybook dev server for visual checks: `cd web && npm run storybook` (port 6006);
  stop with `pkill -f "storybook dev -p 6006"`. Note: `pkill -f` matches its own
  command line, so the shell that runs it can kill itself — run it in its own call.
- Engram: `cortex-session/panel-aesthetic-direction` (slice 1 report, #4860–#4869),
  `odd/panel-visual-foundation/handoff-slice-2` (#4910),
  `odd/panel-visual-foundation/slice-2-state` (#4918),
  `odd/panel-visual-foundation/visual-check-slice-2` (#4919).
- Created 2026-09-24; consuming this session archives it.

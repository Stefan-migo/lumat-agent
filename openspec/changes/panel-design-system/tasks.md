# Tasks: Panel Design System — Foundation (LumatAgent)

> Change: `panel-design-system` · Project: LumatAgent · Phase: sdd-tasks · Date: 2026-08-13
> Foundation-first slice: complete tokens (additive), Tokens page, doc-level stories. Domain patterns, dark mode, new components, component code changes, backend — out of scope (proposal non-goals).
> Task numbering: `T<batch>.<index>` (T9.x = B9, T10.x = B10). Two batches → two chained PRs, auto-chain, stacked to main. Verification per batch: `cd web && npm test` (vitest) + `npm run build-storybook`.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines (total) | ~470–630 (authored, additions+deletions) |
| Estimated changed lines per batch | B9 ~120–180 · B10 ~350–450 |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (B9) → PR 2 (B10), each stacked to main; if B10's authored diff crosses 400 at apply, auto-split into PR 2a (Tokens page + Matrix helper) → PR 2b (10 story upgrades) |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Medium

Rationale: B9 is token-additive + config only (~120–180 lines, Low risk) and fully green standalone (`npm test` + `build-storybook`). B10 is the bigger surface (~350–450 lines, Medium risk — the 10 story upgrades are repetitive, low-complexity edits; the top edge can cross 400). Delivery is auto-chain with a 400-line budget: B9 → PR 1 first, B10 → PR 2; if B10's authored diff exceeds 400 the apply phase splits it into two stacked PRs without a user decision (batch split already defined). `tokens.css` + `tokens.test.ts` land in the same commit (drift-guard friction risk), everything else is independently reversible.

### Suggested Work Units

| Unit | Goal | Likely commit | Focused test command | Runtime harness | Rollback boundary |
|------|------|---------------|----------------------|-----------------|-------------------|
| B9-U1 | Token additions + drift-guard extension (same commit, same-commit rule) | `feat(tokens): add type/focus/motion/breakpoint/shadow tokens + extend drift guard` | `cd web && npm test` | N/A (no runtime; smoke via build-storybook in B9-U2) | Revert commit; `tokens.ts`/`main.ts` never in the diff |
| B9-U2 | Storybook config: autodocs + `--bp-*` viewports | `chore(storybook): enable autodocs + bp-aligned viewports` | `npm run build-storybook` | `npm run storybook` smoke (viewports 640/1024/1280) | Revert `web/.storybook/preview.ts` |
| B10-U1 | Shared `Matrix` helper | `feat(stories): add shared Matrix helper for variant grids` | `npm test` + `build-storybook` (helper compiles) | Storybook smoke after stories land | Delete `web/src/stories/helpers/matrix.tsx` |
| B10-U2 | Tokens reference page | `feat(stories): add Tokens page parsing tokens.css?raw` | `npm test` + `npm run build-storybook` (page in build) | `npm run storybook` → Design Tokens page renders all groups | Delete `web/src/stories/tokens/Tokens.stories.tsx` |
| B10-U3..U5 | Family story upgrades (forms / display / action+domain) | `feat(stories): doc-level upgrade for <family>` ×3 | `npm test` + `npm run build-storybook` | Storybook smoke: controls, matrix, a11y notes per page | Revert the family commit (per-file, independent) |

## Batch 9 — Token foundation + drift guard + Storybook config (~120–180 lines)

Additive token completion (DS-TKN-1..9) + Storybook autodocs/viewports (DS-STORY-6/7). No `tokens.ts` exports, no `main.ts` change, no component or backend files. Batch gate: `cd web && npm test` + `npm run build-storybook` green, diff is web/-only and `tokens.css` diff is append-only.

- [x] **T9.1** Token additions: append the new token groups to the single `:root` in `web/src/tokens/tokens.css`, inside their group sections per the design's documented order (primary → neutrals → semantic → spacing → radius → type → leading → weight → focus → motion → breakpoints → shadow → z), each with a `/* Type — DS-TKN-3 */`-style comment banner. Exact values from the design token table: type `--text-xs 0.75rem`, `--text-base 1rem`, `--text-xl 1.5rem`, `--text-3xl 2.25rem` (static rem, no `clamp()`); leading `--leading-tight 1.2` / `--leading-snug 1.375` / `--leading-normal 1.5` / `--leading-relaxed 1.625` (unitless); weight `--weight-regular 400` / `--weight-medium 500` / `--weight-semibold 600` / `--weight-bold 700`; focus `--focus-ring #256f51` + `--focus-ring-width 2px` + `--focus-ring-offset 2px`; motion `--duration-fast 100ms` / `--duration-base 150ms` / `--duration-slow 250ms` + `--ease-out cubic-bezier(0.33, 1, 0.68, 1)` + `--ease-in-out cubic-bezier(0.65, 0, 0.35, 1)`; breakpoints `--bp-sm 640px` / `--bp-md 1024px` / `--bp-lg 1280px`; elevation `--shadow-3 0 8px 24px rgba(0, 0, 0, 0.16)` appended after `--shadow-2`. Acceptance: every pre-existing declaration is byte-identical (git diff is append-only); `--font-sans` stack unchanged; values match the table exactly. [Reqs: DS-TKN-1, DS-TKN-2, DS-TKN-3, DS-TKN-4, DS-TKN-5, DS-TKN-6, DS-TKN-7 · Files: `web/src/tokens/tokens.css` · Deps: —] <!-- sdd-owner: implementation -->
- [x] **T9.2** Drift-guard extension: append new-group spot-checks to `web/src/tokens/tokens.test.ts` — type (`--text-xs 0.75rem`, `--text-3xl 2.25rem`, `--leading-normal 1.5`, `--weight-semibold 600`), focus (`--focus-ring #256f51`, `--focus-ring-width 2px`, `--focus-ring-offset 2px`), motion (durations 100/150/250ms, both `--ease-*` curves), breakpoints (640/1024/1280px), shadow (`--shadow-3`), reusing the same line regex the Tokens page will use (`/^\s*(--[\w-]+)\s*:\s*([^;]+);/` — one pattern, two consumers). Never edit or remove an existing assertion (pinned palette `#143c2c`/`#f4f5f7`/`#1a202c`/`6px`/`8px`, `tokens.ts` mirror equality, no-hard-coded-hex walk all stay untouched). `web/src/tokens/tokens.ts` must NOT gain exports and must not appear in the diff (DS-TKN-9). Same commit as T9.1. Acceptance: `cd web && npm test` green — drift-guard, mirror, and hex walk all pass. [Reqs: DS-TKN-8, DS-TKN-9 · Files: `web/src/tokens/tokens.test.ts` (untouched: `web/src/tokens/tokens.ts`) · Deps: T9.1] <!-- sdd-owner: implementation -->
- [x] **T9.3** Storybook config: in `web/.storybook/preview.ts` add `docs: { autodocs: true }` to the preview export (DS-STORY-6), plus global viewport presets aligned to the `--bp-*` reference tokens (DS-STORY-7): `bp-sm` 640×900 (mobile), `bp-md` 1024×900 (tablet), `bp-lg` 1280×900 (desktop), with `initialViewport: 'bp-lg'` (desktop-first panel). Keep the `withPanelSurface` decorator and the `tokens.css` import unchanged. `web/.storybook/main.ts` stays untouched — glob `../src/stories/**/*.stories.tsx` unchanged (PDW-CMP-1). Acceptance: `npm run build-storybook` succeeds with zero errors; `main.ts` absent from the diff; viewport presets match 640/1024/1280. [Reqs: DS-STORY-6, DS-STORY-7 · Files: `web/.storybook/preview.ts` (untouched: `web/.storybook/main.ts`) · Deps: T9.1, T9.2] <!-- sdd-owner: implementation -->

## Batch 10 — Tokens page + matrix helper + doc-level story upgrades (~350–450 lines)

Depends on B9 (tokens present, autodocs on). Batch gate: `cd web && npm test` + `npm run build-storybook` green; built output contains the Tokens page and all 11 docs pages.

- [x] **T10.1** Shared matrix helper: create `web/src/stories/helpers/matrix.tsx` — one `Matrix({ cells }: { cells: Array<[string, ReactNode]> })` grid function per design D10: token-styled grid (`repeat(auto-fit, minmax(220px, 1fr))`, gap/padding/border/radius via `var(--space-*)`/`var(--border)`/`var(--radius-sm)`), name label in `var(--text-sm)`/`var(--text-muted)`, ~20 lines, no new dependency, no component under `src/components/` (DS-STORY-4: local helper, not a component). Acceptance: file exists and typechecks; helper is the only shared story utility. [Reqs: DS-STORY-4 · Files: `web/src/stories/helpers/matrix.tsx` · Deps: —] <!-- sdd-owner: implementation -->
- [x] **T10.2** Tokens page: create `web/src/stories/tokens/Tokens.stories.tsx` — CSF meta `title: "Design Tokens"`, single named `Overview` story with a custom render. Parse `tokens.css?raw` (`import tokensCss from "../../tokens/tokens.css?raw"`, typed by `vite/client` already in tsconfig) → split lines → regex `/^\s*(--[\w-]+)\s*:\s*([^;]+);/` → `Map<string, string>`. Group with the D8 ordered first-match rule list: `^--primary-` → Color; `^--danger|^--success|^--warning` → Color (semantic); `^--bg$|^--surface$|^--border|^--table-head-bg$` → Color (neutrals); `^--text(-muted)?$` → Color (text, exact before the scale rule); `^--text-(xs|sm|md|lg|xl|2xl|3xl)$` → Typography (scale); `^--font-|^--leading-|^--weight-` → Typography (font/leading/weight); `^--space-` → Spacing; `^--radius-` → Radius; `^--shadow-` → Shadow; `^--duration-|^--ease-` → Motion; `^--focus-ring` → Focus; `^--bp-` → Breakpoints; `^--z-` → z-index; fallback → Other (never silently dropped). Render one `<section>` per group: color swatch 48×48 with 1px `--border` frame, type sample at its own `fontSize`, spacing bar, radius box, shadow box (`boxShadow: value`), focus box (`outline: var(--focus-ring-width) solid var(--focus-ring); outlineOffset: var(--focus-ring-offset)`), plain tables for motion/breakpoints/z. Section/Row markup local to the story file (no swatch component library); short `parameters.docs.description` explaining the single-source principle. Acceptance: `npm run storybook` shows all 7 groups with values read from `tokens.css` (no story-side value duplication); `npm run build-storybook` includes the page (DS-TOKENS-2). [Reqs: DS-TOKENS-1, DS-TOKENS-2 · Files: `web/src/stories/tokens/Tokens.stories.tsx` · Deps: T9.1, T9.3] <!-- sdd-owner: implementation -->
- [x] **T10.3** Doc-level upgrade — form controls: `web/src/stories/primitives/Input.stories.tsx`, `web/src/stories/primitives/SearchInput.stories.tsx`, `web/src/stories/primitives/Select.stories.tsx`, `web/src/stories/primitives/Textarea.stories.tsx`. Per file: `meta.parameters.docs.description.component` markdown (purpose + when to use / when not to use + **Accessibility** section: focus ring must use `--focus-ring`/`--focus-ring-width`/`--focus-ring-offset`; visible label via `FieldShell`; errors wired through `aria-describedby`), `meta.argTypes` per design table (Input: `label`/`placeholder` text, `size` select sm/md, `error` text, `disabled` boolean; SearchInput: `placeholder`/`aria-label` text, `delay` number; Select: `label` text, `size` select sm/md, `error` text, `disabled` boolean, `options` `control: false` static; Textarea: `label`/`placeholder`/`error` text, `disabled` boolean), preserve existing named stories and their args verbatim (DS-STORY-1 scenario), and add one `Matrix` story per file using the shared helper (cells: Input sm default/md default/md error/sm disabled; SearchInput Default debounced; Select sm default/md default/md error/sm disabled; Textarea Default/Error/Disabled). Acceptance: each docs page shows description, usage guidance, a11y notes, working controls, and a matrix grid; `npm test` + `build-storybook` green. [Reqs: DS-STORY-1, DS-STORY-2, DS-STORY-3, DS-STORY-4, DS-STORY-5 · Files: the 4 form story files · Deps: T10.1] <!-- sdd-owner: implementation -->
- [x] **T10.4** Doc-level upgrade — display primitives: `web/src/stories/primitives/Avatar.stories.tsx`, `web/src/stories/primitives/Badge.stories.tsx`, `web/src/stories/primitives/Card.stories.tsx`, `web/src/stories/primitives/StatusBadge.stories.tsx`. Per file: docs description markdown (purpose + usage + **Accessibility**: focus ring via `--focus-ring*`; StatusBadge never uses color as the only channel — text label always renders; contrast expectations), argTypes per design table (Avatar: `name`/`src` text; Badge: `tone` select neutral/success/warning/danger, `children` text; Card: `title`/`children` text; StatusBadge: `status` select bot/human/closed/pending/escalated), preserve existing named stories + args verbatim, one `Matrix` story per file (cells: Avatar Initials/Image; Badge 4 tones; Card With/Without title; StatusBadge 5 statuses). Acceptance: each docs page shows description, usage, a11y notes, controls, matrix; `npm test` + `build-storybook` green. [Reqs: DS-STORY-1..5 · Files: the 4 display story files · Deps: T10.1] <!-- sdd-owner: implementation -->
- [x] **T10.5** Doc-level upgrade — action + domain: `web/src/stories/primitives/Button.stories.tsx` and `web/src/stories/domain/AppShell.stories.tsx`. Button: docs description + **Accessibility** (focus-ring visibility via `--focus-ring*`; contrast vs `--bg`/`--surface`), argTypes `variant` select primary/secondary, `children` text, `disabled` boolean, `href` text; preserve Primary/Secondary/Link/Disabled; `Matrix` cells Primary/Secondary/Primary disabled/Secondary disabled/Link. AppShell: docs description + usage (nav states) + **Accessibility** (active nav `aria-current="page"`, nav `aria-label`), argTypes `user.username` text, `user.role` select admin/operador; keep `parameters.layout: 'fullscreen'` and Admin/Operador stories; `Matrix` cells Admin nav/Operador nav. Acceptance: both docs pages show description, usage, a11y notes, controls, matrix; `npm test` + `build-storybook` green. [Reqs: DS-STORY-1..5 · Files: `web/src/stories/primitives/Button.stories.tsx`, `web/src/stories/domain/AppShell.stories.tsx` · Deps: T10.1] <!-- sdd-owner: implementation -->

## Lifecycle Gates (parent-owned — after implementation work)

- [ ] Start or reuse bounded review on the B9 diff (PR 1) before chaining PR 2. <!-- sdd-owner: parent -->
- [ ] Start or reuse bounded review on the B10 diff (PR 2) before archive. <!-- sdd-owner: parent -->
- [ ] Archive gate (sdd-archive mandatory): run `graphify . --update` after apply and record the re-balanced web/ communities. <!-- sdd-owner: parent -->

## Traceability: Spec Requirements → Tasks

| Spec | Req → Tasks |
|------|-------------|
| panel-design-system | DS-TKN-1 → T9.1, T9.2, T10.2 · DS-TKN-2 → T9.1, T9.2 · DS-TKN-3 → T9.1, T9.2, T10.2 · DS-TKN-4 → T9.1, T9.2, T10.2 · DS-TKN-5 → T9.1, T9.2, T10.2 · DS-TKN-6 → T9.1, T9.2, T9.3, T10.2 · DS-TKN-7 → T9.1, T9.2, T10.2 · DS-TKN-8 → T9.2 · DS-TKN-9 → T9.2 (tokens.ts absent from diff) |
| panel-design-system | DS-TOKENS-1 → T10.2 · DS-TOKENS-2 → T10.2 (build acceptance) |
| panel-design-system | DS-STORY-1 → T10.3, T10.4, T10.5 · DS-STORY-2 → T10.3, T10.4, T10.5 · DS-STORY-3 → T10.3, T10.4, T10.5 · DS-STORY-4 → T10.1, T10.3, T10.4, T10.5 · DS-STORY-5 → T10.3, T10.4, T10.5 · DS-STORY-6 → T9.3 · DS-STORY-7 → T9.3 |
| panel-design-system | DS-VER-1 → T9.1, T9.2, T9.3, T10.1..T10.5 (batch gates: `npm test` + `build-storybook`; web-only diff check) |

Every requirement ID (DS-TKN-1..9, DS-TOKENS-1..2, DS-STORY-1..7, DS-VER-1) maps to ≥1 task. No RED-test tasks — this is an additive, test-guarded change (guard extension, not red/green cycles); strict TDD config targets pytest but this change is web/vitest-only.

## File Changes Coverage

| Design entry | Tasks |
|--------------|-------|
| `web/src/tokens/tokens.css` | T9.1 |
| `web/src/tokens/tokens.test.ts` | T9.2 |
| `web/.storybook/preview.ts` | T9.3 |
| `web/src/stories/tokens/Tokens.stories.tsx` | T10.2 |
| `web/src/stories/helpers/matrix.tsx` | T10.1 |
| `web/src/stories/primitives/{Input,SearchInput,Select,Textarea}.stories.tsx` | T10.3 |
| `web/src/stories/primitives/{Avatar,Badge,Card,StatusBadge}.stories.tsx` | T10.4 |
| `web/src/stories/primitives/Button.stories.tsx`, `web/src/stories/domain/AppShell.stories.tsx` | T10.5 |
| `web/src/tokens/tokens.ts` (untouched) | T9.2 guard (DS-TKN-9); absent from diff |
| `web/.storybook/main.ts` (untouched) | T9.3 acceptance (glob unchanged) |
| `web/src/components/**`, `app/`, `db/`, `infra/` (untouched) | DS-VER-1 diff check in batch gates |

## Ponytail Task Review (applied after writing — cuts)

1. `Batch 9`: shrink: token additions were 2 candidate tasks (type group vs focus/motion/breakpoints/shadow) → single T9.1. All new groups append to the same `:root` in one session; the design's own table is the apply contract, so one reviewable diff beats a split.
2. `Batch 9`: shrink: no separate "verify" task per unit — batch gates fold into each task's acceptance (B9 gate lands in T9.3 acceptance, B10 gate in T10.2..T10.5 acceptances). -2 candidate tasks.
3. `Batch 10`: shrink: 10 per-story upgrade tasks → 3 family tasks (T10.3 forms, T10.4 display, T10.5 action+domain) using one shared upgrade pattern; exact file lists kept in each task. -7 candidate tasks.
4. `Batch 10`: stdlib/native: Tokens page parsing uses Vite built-in `?raw` + the same line regex the drift guard already uses — no parser, no new dependency, no config change (design D7).
5. `Batch 10`: yagni: no tokens-group module shared with the Tokens page — the D8 ordered rule list stays local to `Tokens.stories.tsx` (one consumer); the drift guard needs only the line regex, not the group rules (design D8/Ponytail cut #4).
6. `Batch 9`: yagni: no `tokens.ts` exports task — explicitly untouched (D12); the guard's mirror-equality check is the only assertion about it.
7. `Batch 10`: yagni: no per-story viewport params — one global preset set in `preview.ts` (D13), already T9.3.

net: -11 candidate tasks cut; final 8 implementation tasks + 3 parent gates.

## Risks / Notes

- **Drift-guard friction (Med)**: token additions must keep `tokens.test.ts` green — additive-only appends, guard extended in the SAME commit as T9.1 (same-commit rule), `npm test` per batch. `tokens.ts` and `main.ts` must stay out of the diff (DS-TKN-9, DS-STORY-6).
- **B10 line budget (Med)**: ~350–450 changed lines; if the authored diff crosses 400 at apply, auto-split B10 into PR 2a (T10.1 + T10.2) → PR 2b (T10.3..T10.5), stacked to main — no user decision required (auto-chain).
- **Vitest vs config strict_tdd**: `openspec/config.yaml` declares `strict_tdd: true` with runner `pytest`, but this change is web-only — the web suite runs on vitest (`npm test` in `web/`); the pytest config applies to the backend, which is untouched. No backend changes (DS-VER-1: diff must not touch `app/`, `db/`, `infra/`).
- **`--text` color vs `--text-*` scale collision (Low)**: Tokens page uses the D8 ordered rule list — exact color match precedes the scale rule; "Other" fallback prevents silent drops.
- **Autodocs quirks with Storybook 8 (Low)**: `options` control disabled explicitly (`control: false`) on Select; verify via `npm run build-storybook`; fallback to per-file MDX only if a docs-format decision flips.
- **Graph staleness for web/ (Low)**: graph built from commit `a756502c`; web/ area is thin — community 68 (tokens/preview/stories) and community 7 (`web_package`) under-represent web/. Archive MUST run `graphify . --update` (see parent gate). Known graph gap: `preview.ts` → `tokens.css` import has no AST node (CSS not extracted).
- **Docs bloat (Med)**: terse markdown, tables, matrix renders; shared helper; 400-line budget per batch.
- **Scope creep into component a11y fixes (Med)**: non-goal; any blocking defect surfaced by doc-level review becomes a separate, tagged decision.

## Graph Check (mandatory per AGENTS.md — recorded)

Knowledge graph: `graphify-out/` (built from commit `a756502c`; 1297 nodes · 2520 edges · 95 communities).

- **Nodes consulted**: `web_src_tokens_tokens` (community 68), `web_src_tokens_tokens_{spacing,radius,zindex}` (68), `web_src_tokens_tokens_test` (68), `web_storybook_preview` (68), `web_storybook_preview_preview`, `web_storybook_preview_withpanelsurface`, `web_package` (community 7), `web_storybook_main` (+`web_storybook_main_config`, thin community).
- **Edges consulted**: `web_src_tokens_tokens_test` --imports_from--> `web_src_tokens_tokens` (drift-guard → mirror); `web_src_tokens_tokens` --contains--> `{spacing,radius,zindex}`; `web_storybook_preview` --imports_from--> `web_src_tokens_tokens` and --indirect_call--> `web_storybook_preview_withpanelsurface`; `web_package` --contains--> scripts/devDependencies (`test`, `build-storybook`, `storybook`, `@storybook/react-vite`, `vitest`).
- **Observation**: community 68 (web design-system) is thin and omitted from the report's hub list; `web_package` sits in backend-dominated community 7; `web_storybook_main` is in a thin community (100) — the web/ area is under-represented until `graphify . --update` runs at archive (parent gate). All 8 implementation tasks map to the consulted nodes above (tokens, guard, preview, stories, package).

## Apply Progress — Batch 9 (B9) — sdd-apply (2026-08-15)

Work unit: **B9** (T9.1, T9.2, T9.3) — token foundation + drift guard + Storybook config. Strict TDD active (vitest). Delivery: auto-chain, stacked to main (PR 1 = B9). Scope: the three files below only.

### Completed tasks (checkboxes flipped to `- [x]` above)

- **T9.1** Token additions (DS-TKN-1..7): 25 new tokens appended inside their group sections per the design's order (type → leading → weight → focus → motion → breakpoints → shadow-3 after --shadow-2), each group with a `/* Type — DS-TKN-3 */`-style banner. Diff is append-only (+36/−0 in tokens.css); every pre-existing declaration byte-identical; `--font-sans` unchanged; no `clamp()`. Values match the design table exactly.
- **T9.2** Drift-guard extension (DS-TKN-8/9): 5 new `it` blocks / 25 assertions appended (type 12, focus 3, motion 5, breakpoints 3, shadow-3 1), reusing the same line regex as the Tokens page (`/^\s*(--[\w-]+)\s*:\s*([^;]+);/` — one pattern, two consumers, D11). No existing assertion edited or removed; `tokens.ts` absent from the diff (DS-TKN-9).
- **T9.3** Storybook config (DS-STORY-6/7): autodocs enabled + `--bp-*` viewport presets (640/1024/1280, all 900px tall) + desktop-first default, in `preview.ts`; `main.ts` untouched (glob unchanged).

### TDD Cycle Evidence (`cd web && npm test`, vitest)

| Phase | Action | Result |
|---|---|---|
| RED | Appended the 5 new-group spot-checks to `tokens.test.ts` only (tokens.css untouched) | **FAIL** — 5 failed / 40 passed (45 total); all 5 new `it` blocks failed with `undefined` (new tokens absent) |
| GREEN | Added the 25 tokens to `tokens.css` | **PASS** — 13 files / 45 tests |
| TRIANGULATE | Full design-table matrix written at RED (25 asserts across type/leading/weight, focus, motion, bp, shadow-3); nothing missing | **PASS** — 45/45 |
| REFACTOR | None needed (additive CSS, append-only tests); map-hoisting rejected — would edit the existing mirror test (forbidden) | **PASS** — 45/45 |

### Verification (DS-VER-1)

- `cd web && npm test` → **Test Files 13 passed (13) · Tests 45 passed (45)** — drift-guard pinned palette, `tokens.ts` mirror equality, and no-hard-coded-hex walk all green.
- `cd web && npm run build-storybook` → **`✓ built in 11.69s`**, zero errors (only the informational chunk-size warning); built `storybook-static/index.json` = **22 story + 10 docs entries** (autodocs page for every existing story file; B10 adds the 11th docs page).
- Hex-walk confirmation: the only hex introduced outside `tokens.css` is the `#256f51` pin in `tokens.test.ts` (walk-exempt `*.test.ts`); `preview.ts` introduces none; drift-guard test itself proves acceptance.
- Diff: 3 files, **+97/−0** (web-only; `tokens.css` append-only; `tokens.ts`, `main.ts`, `src/components/**`, `app/`, `db/`, `infra/` absent).

### Deviations from design text

1. **Autodocs mechanism (DS-STORY-6) — evidence-backed**: design/spec prescribed `parameters.docs.autodocs: true` in preview.ts; **inert in installed Storybook 8.6.14** (traced `@storybook/core/dist/core-server/index.cjs` `getProjectTags` — the only global switch is `options.docs.autodocs === true` from main.ts; addon-docs preset defaults `autodocs: "tag"`; no code path reads `parameters.docs.autodocs`; verified empirically: 0 docs entries in built index.json). Fixed **in-scope** by adding global `tags: ['autodocs']` to the preview export (the SB 8.6 project-tags mechanism, still preview.ts only — main.ts untouched); the parameter is kept as intent documentation. Evidence: built index.json went 0 → 10 docs entries.
2. **`defaultViewport` vs `initialViewport`**: design text says `initialViewport: 'bp-lg'`; the viewport addon's real parameter is `defaultViewport` (`initialViewport` is dead config). Used `defaultViewport: 'bp-lg'` to realize the stated desktop-first intent.

### Graph Check (mandatory per AGENTS.md — recorded)

Knowledge graph: `graphify-out/` (built from commit `a756502c`; HEAD now `95269e74` — stale by design; orchestrator runs `graphify . --update` at archive).

- **Nodes consulted**: `web_src_tokens_tokens` (community 68), `web_src_tokens_tokens_{spacing,radius,zindex}` (68), `web_src_tokens_tokens_test` (68), `web_storybook_preview` (68), `web_storybook_preview_preview`, `web_storybook_preview_withpanelsurface`, `web_package` (community 7), `web_storybook_main` (thin).
- **Edges consulted**: `tokens.test.ts --imports_from--> tokens.ts` (drift-guard → mirror); `preview.ts --imports_from--> tokens.ts`; `preview.ts --indirect_call--> withPanelSurface()`; `tokens.ts --contains--> {spacing,radius,zindex}`; known graph gap: the `preview.ts → tokens.css` CSS import has no AST node (CSS not extracted).
- Read-only `graphify query/path` calls mutated `graphify-out/` cache files; restored to HEAD — **no graphify update run** (parent-owned at archive).

### Remaining (B10 — not this batch)

- Unchecked implementation tasks: T10.1, T10.2, T10.3, T10.4, T10.5 (see `- [ ]` lines above).
- Unchecked parent gates: bounded review B9 (PR 1) before chaining PR 2; bounded review B10 (PR 2) before archive; archive `graphify . --update`.

### Attempt ledger

- Attempt: **B9-foundation-tokens**, ordinal 1, token `sha256:5cc543…`, outcome running (parent-held); executor authenticated with `--token` → `proceed` (zero mutation). Evidence goal: web tests green + storybook build green — both met above.

---

## Apply Progress — Batch 10 (B10) — sdd-apply (2026-08-19)

Work unit: **B10** (T10.1..T10.5) — Tokens page + Matrix helper + 10 doc-level story upgrades. Strict TDD active (vitest; one new pure-logic spec). Delivery: auto-chain, stacked to main (PR 2 = B10; if the authored diff crosses 400 lines, auto-split PR 2a = T10.1+T10.2 → PR 2b = T10.3..T10.5). Scope: 13 web/ files below only; B9 files, `tokens.css`, `tokens.ts`, `tokens.test.ts`, `preview.ts`, `main.ts`, `src/components/**`, backend — untouched.

### Completed tasks (checkboxes flipped to `- [x]` above)

- **T10.1** Matrix helper: `web/src/stories/helpers/matrix.tsx` — one shared `Matrix({ cells })` grid (D10): `repeat(auto-fit, minmax(220px, 1fr))`, token-only styling (`var(--space-*)`, `var(--border)`, `var(--radius-sm)`, `var(--text-sm)`, `var(--text-muted)`), ~30 lines, zero deps, no component under `src/components/`. Only shared story utility.
- **T10.2** Tokens page: `web/src/stories/tokens/Tokens.stories.tsx` — CSF `title: "Design Tokens"`, single `Overview` story; parses `tokens.css?raw` (typed by `vite/client`) with the same line regex the drift guard uses (`/^\s*(--[\w-]+)\s*:\s*([^;]+);/`, D7/D11); D8 ordered first-match group rules local to the file (one consumer); renders one `<section>` per group with per-kind samples (color swatch 48×48 + `--border` frame, type sample at its own `fontSize`, spacing bar, radius box, shadow box `boxShadow: value`, focus box `outline: var(--focus-ring-width) solid var(--focus-ring); outlineOffset: var(--focus-ring-offset)`, plain tables for motion/breakpoints/z). `excludeStories: ["groupToken"]` keeps the exported rule function out of the story index. 67 tokens total parsed → groups: Color 10, Color (semantic) 9, Color (neutrals) 5, Color (text) 2, Typography (scale) 8, Typography (font/leading/weight) 9, Spacing 7, Radius 2, Shadow 3, Motion 5, Focus 3, Breakpoints 3, z-index 1 (sums to 67; "Other" empty today — the fallback exists but no token currently lands there).
- **T10.3** Form controls: `Input`, `SearchInput`, `Select`, `Textarea` stories upgraded — `parameters.docs.description.component` markdown (purpose + when to use/not + **Accessibility**: `--focus-ring*` focus indicator, visible label via `FieldShell`, errors via `aria-describedby`), `argTypes` per design table (`Select.options` `control: false`), existing named stories + args preserved verbatim, one `Matrix` story each.
- **T10.4** Display primitives: `Avatar`, `Badge`, `Card`, `StatusBadge` upgraded — description + usage + a11y (StatusBadge text label always renders, never color-only; contrast expectations), argTypes per design table, existing stories preserved, `Matrix` per file.
- **T10.5** Action + domain: `Button` + `AppShell` upgraded — Button a11y (focus-ring on `--bg`/`--surface`, contrast), argTypes variant/children/disabled/href; AppShell keeps `layout: 'fullscreen'` + Admin/Operador, adds nested argTypes `user.username`/`user.role` (typed via `as Meta<typeof AppShell>['argTypes']`), `Matrix` cells Admin nav/Operador nav (wrapped in `maxHeight: 320, overflow: auto` so the 100vh shell fits the grid).

### TDD Cycle Evidence (`cd web && npm test`, vitest)

| Phase | Action | Result |
|---|---|---|
| RED | Wrote `Tokens.stories.test.ts` (3 `it` blocks / 20 assertions: `--text` vs `--text-*` collision order, all 13 group rules + fallback) importing `groupToken` from the not-yet-existing story module | **FAIL** — 1 failed test file (module `./Tokens.stories` unresolved) / 13 passed files / 45 tests |
| GREEN | Created `helpers/matrix.tsx` + `Tokens.stories.tsx` with the D8 rule list exported as `groupToken` | **PASS** — 14 files / 48 tests (45 + 3 new) |
| TRIANGULATE | Full rule matrix at RED (every group rule + collision cases + `--text-base` scale fix + Other fallback) | **PASS** — 48/48 |
| REFACTOR | None needed — pure function, story markup; `excludeStories` guards the export | **PASS** — 48/48 |

### Verification (DS-VER-1)

- `cd web && npm test` → **Test Files 14 passed (14) · Tests 48 passed (48)** — drift-guard pinned palette, `tokens.ts` mirror equality, hex walk, and the 3 new grouping specs all green.
- `cd web && npx tsc --noEmit -p tsconfig.json` → **clean (exit 0)** — all 13 files typecheck (render-only Matrix stories use unparameterized `StoryObj`; AppShell nested argTypes cast).
- `cd web && npm run build-storybook` → **`✓ built in 8.70s`**, zero errors (only the informational chunk-size warning); built `storybook-static/index.json` = **33 story + 11 docs entries** (B9's 22 stories + 10 docs → +10 `Matrix` stories + 1 Tokens `Overview` story + 1 `Design Tokens` docs page). Tokens page verified in the static bundle: parsed values inlined (`0.75rem`, `--primary-500`, `#f4f5f7`, group labels present in `Tokens.stories-*.js`) — DS-TOKENS-2.
- Diff: 13 files, **+628/−10** authored (10 modified story files +397/−10; 3 new files: `matrix.tsx` 32, `Tokens.stories.tsx` 165, `Tokens.stories.test.ts` 34) + the `tasks.md` artifact (+59/−5). Web-only; `tokens.css` append-only (untouched this batch), `tokens.ts`, `main.ts`, `preview.ts`, `src/components/**`, `app/`, `db/`, `infra/` absent. **PR boundary (auto-split, defined in tasks.md)**: PR 2a = T10.1+T10.2 (`matrix.tsx` + `Tokens.stories.tsx` + spec, 231 lines) → PR 2b = T10.3..T10.5 (10 story files, +397/−10), each stacked to main.

### Deviations from design text

1. **D8 scale regex extended with `base`**: the design's rule list wrote `^--text-(xs|sm|md|lg|xl|2xl|3xl)$` but B9 added `--text-base: 1rem` (design table row DS-TKN-3). Leaving `base` out would send a known scale token to "Other", defeating the rule's purpose — the scale set includes `xs|base|sm|md|lg|xl|2xl|3xl`, pinned by the RED spec (`groupToken("--text-base") === "Typography (scale)"`).
2. **Render-only `Matrix` stories typed as unparameterized `StoryObj`**: `StoryObj<typeof meta>` requires `args` when component props are required (e.g. `children`), so `Matrix` stories use `StoryObj` (no args needed — cells are rendered directly). Named stories keep `StoryObj<typeof meta>`.
3. **AppShell Matrix cells height-capped**: the 100vh shell would blow the auto-fit grid row; cells wrap `AppShell` in a `maxHeight: 320, overflow: auto` div (story-local, no component change).
4. **`excludeStories: ["groupToken"]`** added to the Tokens meta so the exported rule function is not registered as a story entry (T10.2 requires a single `Overview` story).

### Graph Check (mandatory per AGENTS.md — recorded)

Knowledge graph: `graphify-out/` (built from commit `52e5481a2`, older than B9's HEAD `2bed6ee3` — stale by design; orchestrator runs `graphify . --update` at archive).

- **Nodes consulted**: `web_storybook_main`, `web_storybook_preview` (community 68), `web_src_tokens_tokens` (community 68), `web_src_tokens_tokens_test` (68), `web_package` (community 7) — the canonical node IDs per tasks.md/design; the current graph build (pre-web) does not yet contain the web/ nodes, so queries fell back to community context (web/ area thin, under-represented until the archive update).
- **Edges consulted**: `tokens.test.ts --imports_from--> tokens.ts` (drift-guard → mirror, same line regex consumed by the Tokens page); `preview.ts --imports_from--> tokens.ts`; known graph gap: `preview.ts → tokens.css` CSS import has no AST node (CSS not extracted). B10 adds story→helper edges (`*.stories.tsx --imports_from--> helpers/matrix.tsx`) and `Tokens.stories.tsx --imports_from--> tokens.css?raw`.
- Read-only `graphify query/path` calls ran; `graphify-out/` tracked tree verified clean at HEAD (cache dir is gitignored) — **no graphify update run** (parent-owned at archive).

### Remaining (post-B10)

- All 8 implementation tasks (T9.1..T9.3, T10.1..T10.5) are checked `- [x]`. No unchecked implementation tasks remain in this change.
- Unchecked parent gates: bounded review B9 (PR 1) before chaining PR 2; bounded review B10 (PR 2) before archive; archive `graphify . --update`.

### Attempt ledger

- Attempt: **B10-tokens-page-stories**, ordinal 3 (objective generation 3), token `sha256:0a193f8a…` (parent-held, outcome running → settle by parent). Executor authenticated with `gentle-ai sdd-attempt acquire --cwd . --change panel-design-system --token … --request-id b10-apply-auth --work-unit "B10-tokens-page-stories" --evidence-goal "web tests green (npm test) + storybook build green (npm run build-storybook) with Tokens page + 10 doc-level stories"` → `proceed` (zero mutation, same ledger). Evidence goal met: `npm test` 48/48, `build-storybook` 33 story + 11 docs entries.

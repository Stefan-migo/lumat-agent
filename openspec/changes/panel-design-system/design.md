# Design: Panel Design System — Foundation (LumatAgent)

> Change: `panel-design-system` · Project: LumatAgent (client: Lumat, gasfitería, Chile) · Phase: sdd-design · Date: 2026-08-13
> Satisfies specs: `panel-design-system` (DS-TKN-1..9, DS-TOKENS-1..2, DS-STORY-1..7, DS-VER-1).
> Artifact language: English (technical). The spec deliberately deferred exact values to this design — the **Exact Token Value Table** below is the contract for apply.

## Technical Approach

Complete the design-system **foundation** additively and with zero new dependencies:

- **Tokens**: extend the single `:root` in `web/src/tokens/tokens.css` by *appending* four type-scale steps, line-height and weight groups, a composable focus-ring set, a 3+2 motion scale, three reference breakpoints, and `--shadow-3`. Every pre-existing declaration keeps its byte-identical value (DS-TKN-2). No fluid `clamp()`, no dark mode, no build pipeline.
- **Guard**: extend `tokens.test.ts` with spot-checks for the new groups; keep the pinned-palette checks, the `tokens.ts` mirror-equality check, and the no-hard-coded-hex walk untouched (DS-TKN-8). `tokens.ts` gains **no** exports (DS-TKN-9).
- **Storybook config**: enable autodocs globally and register `--bp-*`-aligned viewport presets in `preview.ts`; `main.ts` glob stays `../src/stories/**/*.stories.tsx` (DS-STORY-6/7).
- **Tokens page**: one CSF story at `src/stories/tokens/Tokens.stories.tsx` that parses `tokens.css?raw` (Vite built-in, typed by the already-present `vite/client`) and renders grouped swatches/tables — single source, no duplicated values, no MDX, no new dependency (DS-TOKENS-1/2).
- **Doc-level stories**: upgrade the 10 existing story files in place — meta description + usage guidance, argTypes, a preserved set of named stories, one variant-matrix story per file rendered by a shared local helper (`src/stories/helpers/matrix.tsx`), and a11y notes embedded in each docs page (DS-STORY-1..5). No component code changes.

Apply lands in two batches: **B9** (tokens + guard + Storybook config) and **B10** (Tokens page + 10 story upgrades).

## Architecture Decisions

| # | Decision | Choice | Alternatives rejected | Rationale |
|---|---|---|---|---|
| D1 | Token source | Single `:root` in `tokens.css`; additive appends only, grouped by concern with comment banners | Split files (`colors.css`, `type.css`…) via `@import`; CSS build tooling (Style Dictionary) | DS-TKN-1/2 mandate the single source and byte-identical evolution; split files add import-order risk and a build step with zero consumers (YAGNI) |
| D2 | Type scale | Extend `--text-*` with `xs`/`base`/`xl`/`3xl` static rem; add unitless `--leading-*` and `--weight-*` groups | Full 12-step scale; fluid `clamp()`; separate `--line-height-*` naming | The panel already uses sm/md/lg/2xl — extending is zero-migration; static rem per user decision **a**; unitless line-height inherits correctly and is the CSS standard |
| D3 | Focus-ring set | `--focus-ring: #256f51` (primary-700) + `--focus-ring-width: 2px` + `--focus-ring-offset: 2px` | primary-600 (`#349d73` — only 3.1:1 vs `--bg`, too tight); a new blue (palette expansion, out of scope); per-component values | One composable set per DS-TKN-4; primary-700 clears WCAG 2.4.11 ≥3:1 with margin: **6.0:1 vs `--surface`, 5.5:1 vs `--bg`**; 2px width + 2px offset is the standard focus-indicator recipe |
| D4 | Motion scale | `--duration-fast/base/slow` = 100/150/250 ms; `--ease-out` = `cubic-bezier(0.33, 1, 0.68, 1)`, `--ease-in-out` = `cubic-bezier(0.65, 0, 0.35, 1)` | More duration steps; bespoke curves; keyframe tokens | DS-TKN-5 fixes the three steps; the chosen curves are the exact CSS-standard `ease-out`/`ease-in-out` — boring, recognizable, tokenized |
| D5 | Breakpoints | Reference tokens `--bp-sm 640px / --bp-md 1024px / --bp-lg 1280px`; consumed only by Storybook viewports | Wiring into layout code; a 4-step scale | Desktop-first admin panel; DS-TKN-6 explicitly forbids layout consumption this slice |
| D6 | Elevation | `--shadow-3: 0 8px 24px rgba(0, 0, 0, 0.16)` appended after `--shadow-2` | Larger shadow set; inset variants | One overlay/drawer tier continues the existing progression (offset 1→4→8, blur 2→12→24, alpha 0.08→0.12→0.16); DS-TKN-7 pins 1/2 unchanged |
| D7 | Tokens page | CSF story parsing `tokens.css?raw` (Vite `?raw` import, typed by `vite/client` already in tsconfig `types`) | MDX page; hand-written tables; `tokens.ts` exports; Style Dictionary | Single source, zero duplication, zero deps, glob unchanged (PDW-CMP-1); `tsconfig.json` already ships `"types": ["vite/client", "node"]` so `?raw` typechecks with no config change |
| D8 | Tokens page grouping | Ordered first-match rule list (regex) local to the story; resolves the `--text` color vs `--text-*` scale collision | Prefix-only map (collides on `--text`/`--text-muted`); hand-maintained group lists | Deterministic and unambiguous: exact-match color rules run before the `--text-*` scale rule; unknown tokens fall to an "Other" group so nothing is silently dropped |
| D9 | Docs format | Autodocs global (`docs.autodocs: true`) + per-meta `parameters.docs.description` markdown (usage + a11y sections) + meta `argTypes` | Per-component MDX companions; manual addon-docs block composition | DS-STORY-6; zero extra files per story; a11y notes live in the docs page body — no separate a11y story needed |
| D10 | Matrix helper | One shared `Matrix` grid function in `src/stories/helpers/matrix.tsx` | Per-file copy (10× duplication); a component under `src/components/` | DS-STORY-4 says *local helper, no new component*; one ~20-line function, token-only styling, shared by all 10 stories |
| D11 | Drift guard | Append new-group spot-checks to `tokens.test.ts`; never remove/edit existing assertions | Rewriting the guard to a snapshot of the whole file | DS-TKN-8: pinned palette, mirror equality, and the hex walk stay as the no-drift contract; new checks pin the new groups (values from the table below) |
| D12 | `tokens.ts` surface | Untouched — no new exports | Mirroring new tokens into TS for hypothetical JS consumers | DS-TKN-9 + decision **e**: only mirror what JS actually consumes (spacing/radius/zIndex); the Tokens page reads CSS directly |
| D13 | Storybook viewports | Global presets in `preview.ts` (`bp-sm/bp-md/bp-lg` = 640/1024/1280) | Per-story viewport params; viewport addon config in `main.ts` | DS-STORY-7; one place, matches the reference tokens; `main.ts` stays untouched |

## Token Architecture

- **Single `:root` source** (D1): all tokens are custom properties in `web/src/tokens/tokens.css`. Components, stories, and the Tokens page consume `var(--*)` only; the drift-guard walks `web/src` to enforce the no-hard-coded-hex rule (exemptions: `tokens.css` itself, `*.test.*`, `*.stories.tsx` — the walk already encodes this).
- **Naming**: kebab-case, domain-prefixed groups — `--text-*`, `--leading-*`, `--weight-*`, `--focus-ring*`, `--duration-*`, `--ease-*`, `--bp-*`, `--shadow-*`, plus the existing `--primary-*`, `--space-*`, `--radius-*`, `--z-*`. No aliases, no duplicates.
- **Additive-only migration**: every new declaration is *appended inside its group section*; pre-existing declarations are never edited or removed (DS-TKN-2). Revert = `git revert` of the batch commits — no prior behavior to restore.
- **Group ordering inside `:root`** (documented in the file header): primary scale → neutrals → semantic pairs → spacing → radius → type (`--font-sans`, `--text-sm…2xl`, then new `xs/base/xl/3xl`) → leading → weight → focus → motion (duration then ease) → breakpoints → shadow (1, 2, then new 3) → z. Each new group carries a `/* Type — DS-TKN-3 */`-style comment banner.
- **Drift-guard strategy** (D11): the guard mirrors the token source of truth — it parses `tokens.css` with the same line regex the Tokens page uses and asserts (a) the pinned palette/radii, (b) `tokens.ts` mirror equality, (c) no hard-coded hex outside `tokens.css`, and (d) new spot-checks from the table below. Any future addition to `tokens.css` requires extending the guard in the same commit.

## Exact Token Value Table (apply contract)

| Token | Value | Requirement |
|---|---|---|
| `--text-xs` | `0.75rem` | DS-TKN-3 |
| `--text-base` | `1rem` | DS-TKN-3 |
| `--text-xl` | `1.5rem` | DS-TKN-3 |
| `--text-3xl` | `2.25rem` | DS-TKN-3 |
| `--leading-tight` | `1.2` | DS-TKN-3 (unitless) |
| `--leading-snug` | `1.375` | DS-TKN-3 (unitless) |
| `--leading-normal` | `1.5` | DS-TKN-3 (unitless) |
| `--leading-relaxed` | `1.625` | DS-TKN-3 (unitless) |
| `--weight-regular` | `400` | DS-TKN-3 |
| `--weight-medium` | `500` | DS-TKN-3 |
| `--weight-semibold` | `600` | DS-TKN-3 |
| `--weight-bold` | `700` | DS-TKN-3 |
| `--focus-ring` | `#256f51` (primary-700) | DS-TKN-4 — 6.0:1 vs `--surface`, 5.5:1 vs `--bg` |
| `--focus-ring-width` | `2px` | DS-TKN-4 |
| `--focus-ring-offset` | `2px` | DS-TKN-4 |
| `--duration-fast` | `100ms` | DS-TKN-5 |
| `--duration-base` | `150ms` | DS-TKN-5 |
| `--duration-slow` | `250ms` | DS-TKN-5 |
| `--ease-out` | `cubic-bezier(0.33, 1, 0.68, 1)` | DS-TKN-5 (CSS `ease-out`) |
| `--ease-in-out` | `cubic-bezier(0.65, 0, 0.35, 1)` | DS-TKN-5 (CSS `ease-in-out`) |
| `--bp-sm` | `640px` | DS-TKN-6 |
| `--bp-md` | `1024px` | DS-TKN-6 |
| `--bp-lg` | `1280px` | DS-TKN-6 |
| `--shadow-3` | `0 8px 24px rgba(0, 0, 0, 0.16)` | DS-TKN-7 |

**Unchanged (pinned by existing spot-checks)**: `--primary-*` scale (brand `#143c2c`), neutrals (`--bg #f4f5f7`, `--text #1a202c`, …), semantic pairs, `--space-1..8`, `--radius-sm 6px`/`--radius-md 8px`, `--font-sans`, `--text-sm 0.85rem`/`md 0.95rem`/`lg 1.25rem`/`2xl 2rem`, `--shadow-1`, `--shadow-2`, `--z-modal`.

## Tokens Page Design (`src/stories/tokens/Tokens.stories.tsx`)

- **Story shape**: `title: "Design Tokens"`, meta with a local `TokensPage` render component; single named story `Overview` with a custom `render`. Discovered by the existing glob — `main.ts` untouched.
- **Parse** (no deps): `import tokensCss from "../../tokens/tokens.css?raw"` (typed by `vite/client`, already in tsconfig) → split on lines → `/^\s*(--[\w-]+)\s*:\s*([^;]+);/` → `Map<string, string>`. This is the same regex the drift-guard uses — one pattern, two consumers, no duplication of *values*.
- **Grouping** (D8 — ordered rule list, first match wins):
  1. `^--primary-` → **Color**
  2. `^--danger|^--success|^--warning` → **Color (semantic)**
  3. `^--bg$|^--surface$|^--border|^--table-head-bg$` → **Color (neutrals)**
  4. `^--text(-muted)?$` → **Color (text)** — exact match, before the type-scale rule
  5. `^--text-(xs|sm|md|lg|xl|2xl|3xl)$` → **Typography (scale)**
  6. `^--font-|^--leading-|^--weight-` → **Typography (font/leading/weight)**
  7. `^--space-` → **Spacing**
  8. `^--radius-` → **Radius**
  9. `^--shadow-` → **Shadow**
  10. `^--duration-|^--ease-` → **Motion**
  11. `^--focus-ring` → **Focus**
  12. `^--bp-` → **Breakpoints**
  13. `^--z-` → **z-index**
  14. fallback → **Other** (never silently dropped)
- **Rendering**: one `<section>` per group; rows are name + value + a visual sample — color swatch (48×48, 1px `--border` frame), type sample rendered *at the token's own value* (`fontSize: var(--text-xl)` inline style), spacing bar (`width: value`), radius box (48×48 with the radius), shadow box (`boxShadow: value`), focus box (`outline: var(--focus-ring-width) solid var(--focus-ring); outlineOffset: var(--focus-ring-offset)`), and plain tables for motion/breakpoints/z. Section/Row markup stays local to the story file (`ponytail:` — no swatch component library).
- **Autodocs**: global autodocs also generates a docs page for this story; the story render *is* the page content. A short `parameters.docs.description` explains the single-source principle.
- **Static build**: `?raw` is inlined by Vite at build time, so `npm run build-storybook` includes the page with no runtime fetch (DS-TOKENS-2).

## Story Doc-Level Upgrade Plan (10 files)

Shared helper — **`src/stories/helpers/matrix.tsx`** (D10):

```tsx
import type { ReactNode } from "react";

/** Local story-grid helper (DS-STORY-4) — token-styled, no component tree change. */
export function Matrix({ cells }: { cells: Array<[string, ReactNode]> }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "var(--space-3)", padding: "var(--space-2)" }}>
      {cells.map(([name, node]) => (
        <div key={name} style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-sm)",
                                 padding: "var(--space-3)" }}>
          <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--text-muted)" }}>{name}</p>
          <div style={{ marginTop: "var(--space-2)" }}>{node}</div>
        </div>
      ))}
    </div>
  );
}
```

Per-file upgrade pattern (applies to all 10; existing named stories and their args are preserved verbatim — DS-STORY-1 scenario "Existing stories preserved"):

1. `meta.parameters.docs.description.component` — markdown: purpose, **when to use / when not to use**, and an **Accessibility** section covering focus-ring visibility (`--focus-ring*` tokens), label requirements, and contrast expectations (DS-STORY-2, DS-STORY-5).
2. `meta.argTypes` — controls where meaningful (DS-STORY-3).
3. One `Matrix` story per file rendering all variants in one grid (DS-STORY-4).

| File | argTypes (controls) | Matrix cells |
|---|---|---|
| `primitives/Avatar.stories.tsx` | `name` (text), `src` (text) | Initials · Image (`src`) |
| `primitives/Badge.stories.tsx` | `tone` (select: neutral/success/warning/danger), `children` (text) | 4 tones |
| `primitives/Button.stories.tsx` | `variant` (select: primary/secondary), `children` (text), `disabled` (boolean), `href` (text) | Primary · Secondary · Primary disabled · Secondary disabled · Link |
| `primitives/Card.stories.tsx` | `title` (text), `children` (text) | With title · Without title |
| `primitives/Input.stories.tsx` | `label` (text), `placeholder` (text), `size` (select: sm/md), `error` (text), `disabled` (boolean) | sm default · md default · md error · sm disabled |
| `primitives/SearchInput.stories.tsx` | `placeholder` (text), `aria-label` (text), `delay` (number) | Default (debounced) |
| `primitives/Select.stories.tsx` | `label` (text), `size` (select: sm/md), `error` (text), `disabled` (boolean), `options` (`control: false`, static) | sm default · md default · md error · sm disabled |
| `primitives/StatusBadge.stories.tsx` | `status` (select: bot/human/closed/pending/escalated) | 5 statuses |
| `primitives/Textarea.stories.tsx` | `label` (text), `placeholder` (text), `error` (text), `disabled` (boolean) | Default · Error · Disabled |
| `domain/AppShell.stories.tsx` | `user.username` (text), `user.role` (select: admin/operador) | Admin nav · Operador nav |

A11y notes content per file (in the docs description): focus ring must use `--focus-ring`/`--focus-ring-width`/`--focus-ring-offset`; form controls require a visible label (via `FieldShell`) and errors are wired through `aria-describedby`; StatusBadge never uses color as the only channel (text label always renders); AppShell active nav uses `aria-current="page"` and the nav has an `aria-label`.

## Storybook Config Changes

**`web/.storybook/preview.ts`** (modified):
- Add `docs: { autodocs: true }` to the preview export (DS-STORY-6).
- Add global viewport presets aligned to the `--bp-*` reference tokens (DS-STORY-7):
  - `bp-sm` — `640px × 900px`, type `mobile`
  - `bp-md` — `1024px × 900px`, type `tablet`
  - `bp-lg` — `1280px × 900px`, type `desktop`
  - plus `initialViewport: 'bp-lg'` (desktop-first panel).
- Keep `withPanelSurface` decorator and the `tokens.css` import unchanged.

**`web/.storybook/main.ts`**: unchanged — glob `../src/stories/**/*.stories.tsx` and addons stay as-is (PDW-CMP-1, DS-STORY-6 scenario "Glob unchanged").

## File Layout

| File | Action | Contents |
|---|---|---|
| `web/src/tokens/tokens.css` | Modify (additive) | New type steps + leading/weight, focus-ring, motion, breakpoints, `--shadow-3`; group comment banners; every pre-existing declaration byte-identical |
| `web/src/tokens/tokens.test.ts` | Modify | Append new-group spot-checks (values from the token table); keep palette spot-checks, mirror equality, and the no-hard-coded-hex walk unchanged |
| `web/.storybook/preview.ts` | Modify | `docs.autodocs: true` + `--bp-*` viewport presets + `initialViewport` |
| `web/src/stories/tokens/Tokens.stories.tsx` | Create | Tokens reference page: `tokens.css?raw` parse → grouped swatches/tables (DS-TOKENS-1/2) |
| `web/src/stories/helpers/matrix.tsx` | Create | Shared `Matrix` grid helper (DS-STORY-4) |
| `web/src/stories/primitives/{Avatar,Badge,Button,Card,Input,SearchInput,Select,StatusBadge,Textarea}.stories.tsx` (9) | Modify | Doc-level: description+usage+a11y markdown, argTypes, preserved stories, `Matrix` story |
| `web/src/stories/domain/AppShell.stories.tsx` | Modify | Doc-level upgrade (Admin/Operador nav matrix, `layout: 'fullscreen'` kept) |
| `web/src/tokens/tokens.ts` | Untouched | No new exports (DS-TKN-9) |
| `web/.storybook/main.ts` | Untouched | Glob unchanged (DS-STORY-6) |
| `web/src/components/**`, `app/`, `db/`, `infra/` | Untouched | No component/backend changes (DS-VER-1) |

## Verification Plan (DS-VER-1)

1. `cd web && npm test` — vitest run: drift-guard (new-group spot-checks + pinned palette + `tokens.ts` mirror + no-hard-coded-hex walk) and all component tests green.
2. `cd web && npm run build-storybook` — build succeeds with zero errors; built output contains the Tokens page (DS-TOKENS-2) and all 11 docs pages.
3. `npm run storybook` smoke check — Tokens page renders all groups; viewport presets match 640/1024/1280; a Matrix story renders its grid.
4. Diff review — web-only (`web/` paths); `tokens.css` diff is append-only; `tokens.ts`/`main.ts`/`src/components/**` absent from the diff.
5. Manual a11y spot-check — focus ring visible on interactive primitives using the new tokens; docs pages show the Accessibility section.

## Batch Anticipation

- **B9 — Token foundation + config** (~120–180 changed lines): `tokens.css` additions, `tokens.test.ts` extension, `preview.ts` autodocs + viewports. Fully green on its own (`npm test`, `build-storybook`).
- **B10 — Tokens page + story upgrades** (~350–450 changed lines): `Tokens.stories.tsx`, `helpers/matrix.tsx`, 10 story upgrades. Depends on B9 (autodocs on, tokens present).
- Each batch is independently reviewable (≈400-line budget per batch); `npm test` + `build-storybook` gates run per batch.

## Graph Check (mandatory per AGENTS.md — recorded)

Knowledge graph: `graphify-out/graph.json` (built from commit `a756502c`; web/ area under-represented — see below).

- **Nodes consulted**: `web_storybook_preview` (community 68), `web_storybook_preview_preview`, `web_storybook_preview_withpanelsurface`, `web_src_tokens_tokens` (community 68), `web_src_tokens_tokens_{spacing,radius,zindex}` (community 68), `web_src_tokens_tokens_test` (community 68), `web_package` (community 7), `web_package_scripts_{test,build_storybook,storybook}`.
- **Edges consulted**: `web_storybook_preview` --imports_from--> `web_src_tokens_tokens` (preview→tokens mirror; the `tokens.css` import at preview.ts L2 has no AST node — CSS files are not extracted, so the semantic preview→tokens.css edge is a known graph gap); `web_src_tokens_tokens_test` --imports_from--> `web_src_tokens_tokens` (drift-guard→tokens mirror); `web_src_tokens_tokens` --contains--> `{spacing,radius,zindex}`; `web_storybook_preview` --indirect_call--> `web_storybook_preview_withpanelsurface`; `web_package` --contains--> scripts/devDependencies.
- **Observation**: community 68 (web design-system: tokens, preview, stories) is thin and omitted from the report's hub list; `web_package` sits in backend-dominated community 7 — confirming the proposal's note. Apply/archive should run `graphify . --update` to re-balance after the batches land.

## Ponytail Plan Review (applied — cuts)

1. `Section "Token Architecture"`: delete any token build pipeline → regex parse in the Tokens page, drift-guard regex in the test; zero new deps, zero config.
2. `Section "Tokens Page"`: delete a swatch component library → Section/Row markup local to the story file; only the cross-story `Matrix` helper is shared.
3. `Section "Story Upgrades"`: delete separate a11y stories/MDX → a11y notes live in `parameters.docs.description` markdown (DS-STORY-5 satisfied with zero extra files).
4. `Section "Tokens Page"`: delete a shared tokens-group module → the ordered group-rule list is local to `Tokens.stories.tsx` (only one consumer).
5. `Section "tokens.ts"`: delete new JS exports → `tokens.ts` untouched (D12; DS-TKN-9).
6. `Section "Storybook Config"`: delete per-story viewport params → one global preset set in `preview.ts` (D13).
7. `Section "Token Values"`: delete fluid `clamp()` type and dark-mode variants → out of scope per proposal decisions **a** and non-goals; static rem only.

net: -7 items cut from design.

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Drift-guard friction: additions must keep `tokens.test.ts` green | Med | Additive-only appends; guard extended in the same commit (B9); run `npm test` per batch |
| `--text` color vs `--text-*` scale collision in the Tokens page grouping | Low | Ordered first-match rules (D8) — exact color match precedes the scale rule; "Other" fallback prevents silent drops |
| Autodocs quirks with Storybook 8 (e.g. controls inference on `options` object) | Low | `options` control disabled explicitly (`control: false`); verify via `build-storybook` |
| Docs bloat across 10 files + Tokens page | Med | Terse markdown, tables, matrix renders; ~400-line budget per batch; helper shared |
| Scope creep into component a11y fixes | Med | Non-goals section; any blocking defect becomes a separate tagged decision |
| Graph staleness for the web/ area | Low | `graphify . --update` at archive; communities 7/68 under-represented today |

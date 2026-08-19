# Proposal: Panel Design System — Foundation (LumatAgent)

> Change: `panel-design-system` · Project: LumatAgent (client: Lumat, gasfitería, Chile)
> Phase: sdd-propose · Date: 2026-08-13 · Status: proposal draft — awaiting orchestrator/user confirmation
> Artifact language: English (technical). User-facing design decisions are confirmed with the client in Spanish (see Proposal Question Round).
> Scope decision (user intent, verbatim): "trabajar en el diseño con storybook y armar un system design profesional, con una ui/ux sencilla y estándar para agentes" — **FUNDACIÓN PRIMERO**: this slice is the design-system foundation only.

## Intent

Turn the Lumat admin panel (`web/`, package `lumat-panel`) into a professional, standard, simple design system for the agent-facing panel. Today the panel has a partial token set (`web/src/tokens/tokens.css`, seeded from brand `#143c2c`) and 10 args-playground stories — there is no full type scale, no focus/motion/breakpoint tokens, no Tokens reference page, and stories do not document usage or accessibility.

**Foundation-first slice:** complete the token foundation, stand up a Tokens page in Storybook, and upgrade the existing stories to doc-level (controls, variant matrix, a11y + usage guidance). Domain patterns (conversation thread, cases, KPIs, KB manager, settings) are **explicitly out** — they consume this foundation in later slices. No component behavior changes, no new components.

## Scope

### In Scope

1. **Complete token foundation in `tokens.css` (single `:root` source, PDW-TKN-1 stays)** — additive only; every existing token value keeps its current value (no visual drift):
   - **Typography**: extend the `--text-*` scale (add `xs`, `base`, `xl`, `3xl`), add line-height tokens (`--leading-*`) and font-weight tokens (`--weight-*`). Keep the `system-ui` stack.
   - **Focus / a11y tokens**: `--focus-ring` color + `--focus-ring-width` + `--focus-ring-offset` — one composable set for all interactive primitives.
   - **Motion tokens**: minimal duration scale (`--duration-*` ≈ 100/150/250 ms) + two easings (`--ease-*`).
   - **Breakpoints**: `--bp-sm` / `--bp-md` / `--bp-lg` (desktop-first admin panel reference values; not yet consumed by layout code).
   - **Elevation**: extend shadows with `--shadow-3` (overlays/drawers); `--shadow-1/2` unchanged.
2. **`tokens.ts` + drift-guard test stay green (PDW-TKN-2)** — if new tokens gain JS consumers, mirror them in `tokens.ts` and extend `tokens.test.ts` (spot-checks for new groups; keep the no-hard-coded-hex walk). Recommended default: **no new JS exports** — see Open Decisions **e**.
3. **Tokens page in Storybook** — `src/stories/tokens/Tokens.stories.tsx` renders token groups (colors, type, spacing, radius, shadows, motion, focus) directly from `tokens.css?raw` (single source, no duplication).
4. **Doc-level stories for all 10 existing story files** (9 primitives: Avatar, Badge, Button, Card, Input, SearchInput, Select, StatusBadge, Textarea + `domain/AppShell`):
   - component description + usage guidance,
   - interactive controls (argTypes) where meaningful (variants, sizes, disabled, placeholder),
   - a variant **matrix** story rendering all variants in one grid (local helper, no new component),
   - a11y notes (focus ring, label requirements, contrast) in each docs page.
5. **Storybook config polish** — viewports aligned to `--bp-*`; autodocs enabled globally if the docs-format decision lands on autodocs.

### Out of Scope (explicit non-goals)

- **Domain patterns** — conversation thread, cases, KPIs, KB manager, settings views (later slices consume this foundation).
- **Dark mode** — deferred: requires semantic-token rework; only revisited by explicit decision.
- **Runtime/dynamic theming** — no theme switching, no data-attribute variants, no token pipeline/build tooling (Style Dictionary etc.; YAGNI at this scale).
- **New components** — zero new primitives; `FieldShell` stays as-is (no story in this slice).
- **Component code changes** — a11y/UX *fixes inside component CSS/TSX* are out; if doc-level review surfaces a blocking defect it becomes a separate, tagged decision.
- **Backend** — no changes to `app/`, `db/`, `infra/`, backend tests (`pytest`); web uses `vitest` (`npm test` in `web/`).

## Open Decisions (recommendations — orchestrator confirms)

| Decision | Recommendation | Rationale |
|---|---|---|
| **a. Type scale naming** | Extend existing `--text-*` (add `xs`/`base`/`xl`/`3xl`) + `--leading-*` + `--weight-*` | No migration, consistent with `--text-sm/md/lg/2xl` already in use; static rem scale, **no fluid `clamp()`** in this slice |
| **b. Motion scale** | Introduce 3-step `--duration-*` (100/150/250 ms) + 2 `--ease-*` tokens | Standard, near-zero cost; "professional/standard" intent; panel is mostly static so 3 steps is enough |
| **c. Focus-ring token set** | Yes — `--focus-ring` color + `--focus-ring-width` + `--focus-ring-offset` | A11y is a stated product goal; one composable set beats per-component values |
| **d. Docs format: autodocs vs MDX** | **Autodocs** (`docs.autodocs: true` in `preview.ts`, per-meta `tags` where needed) + Tokens page as a **CSF story** (custom render parsing `tokens.css?raw`) | Autodocs gives controls/args/description tables with zero file overhead; keeps the `main.ts` glob `*.stories.tsx` unchanged (PDW-CMP-1); MDX only if custom narrative is needed later |
| **e. `tokens.ts` surface** | No new JS exports in this slice; Tokens page reads `tokens.css?raw`, components consume CSS custom properties | Ponytail: only mirror what JS actually consumes; keeps drift-guard churn at zero |
| **f. Keep PDW-* IDs** | Yes — continue PDW-* traceability (e.g., PDW-TKN-3 for the extended tokens, PDW-CMP-2 for doc-level stories) | Established convention in the web/ area (PDW-TKN-1/2, PDW-CMP-1); consistency beats a new scheme |

## Capabilities (contract with sdd-spec)

| New capability | Covers (→ `openspec/specs/<name>/spec.md`) |
|---|---|
| `panel-design-system` | Token completeness (type/leading/weight, focus, motion, breakpoints, elevation) with `tokens.css` as single source (RFC 2119 requirements); Tokens page presence; doc-level story requirements (controls, matrix, a11y + usage guidance) |

**Modified capabilities:** none — the `admin-panel` capability (backend views/auth) is unaffected; this is a frontend foundation change.

## Approach

- **Additive tokens only.** Append new custom properties to the single `:root` in `tokens.css`; never change an existing value. The existing spot-check assertions in `tokens.test.ts` (brand `#143c2c`, `#f4f5f7`, `#1a202c`, `6px`/`8px`…) act as the no-drift guard.
- **Tokens page = CSF story** that parses `tokens.css?raw` into groups (prefix → group label map local to the story). No duplicate token values in docs, no `tokens.ts` growth, no MDX glob change.
- **Stories upgraded in place** under `web/src/stories/` (primitives/ + domain/), preserving existing named stories (Primary/Secondary/…) and adding matrix + docs content.
- **Verify:** `npm test` in `web/` (vitest incl. drift-guard) + `npm run build-storybook` (no errors) + `npm run storybook` smoke check.
- **Ponytail cuts:** no token build pipeline, no dark mode, no fluid type, no new dependencies, no MDX unless decision **d** flips, no component code changes, `main.ts` glob untouched.

## Knowledge graph consulted (Graph Check — graphify-out/)

- Nodes: `storybook` (community 7, src `web/package.json` L32), `@storybook/react-vite`, `@storybook/addon-essentials` (community 7), `web_package` (community 7), `tokens.ts`/`tokens.test.ts`/`spacing`/`radius`/`zIndex` (community 68), `web_storybook_main`/`web_storybook_preview`, primitives nodes (Button/Avatar/Card/Badge/StatusBadge/Input/Select/Textarea/FieldShell + their `*.stories` nodes).
- Communities 7 and 68 cover the web/design-system area; the graph is backend-dominated (god nodes: `Message`, `get_or_create_customer`, `Propuesta … PDF`) because B5–B8 (web scaffold/tokens/primitives) just landed — run `graphify . --update` after apply to re-balance.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `web/src/tokens/tokens.css` | Modified (additive) | Type scale + leading/weight, focus-ring, motion, breakpoints, `--shadow-3` |
| `web/src/tokens/tokens.ts` | Modified (only if decision **e** flips) | Mirror new JS-consumed tokens; otherwise untouched |
| `web/src/tokens/tokens.test.ts` | Modified (guard) | New-group spot-checks; keep drift + no-hardcoded-hex guards |
| `web/.storybook/preview.ts` | Modified | Autodocs flag, viewports aligned to `--bp-*` |
| `web/src/stories/primitives/*.stories.tsx` (9) | Modified | Doc-level upgrade: description, argTypes, matrix, a11y notes |
| `web/src/stories/domain/AppShell.stories.tsx` | Modified | Doc-level upgrade (nav states, usage) |
| `web/src/stories/tokens/Tokens.stories.tsx` | New | Tokens reference page |
| `web/src/components/**` | Untouched | No component code changes in this slice |
| `app/`, `db/`, `infra/`, `openspec/config.yaml` | Untouched | Backend / infra out of scope |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Drift-guard friction: token additions must keep `tokens.test.ts` green | Med | Additive changes only; extend guard + mirror in the same commit; run `npm test` per batch |
| Perceived visual change from "token work" | Low | Existing values never change; spot-check assertions pin the palette; primitives tests stay green |
| Docs bloat / cognitive load (10 stories + Tokens page) | Med | Terse descriptions, tables, matrix renders; apply cognitive-doc-design patterns; review budget 400 lines/batch |
| Scope creep into component a11y fixes | Med | Non-goals section; component fixes require a separate decision/commit |
| Storybook 8 autodocs quirks | Low | Verify with `build-storybook`; fallback: per-file MDX (decision **d**) |
| Graph staleness for web/ area | Low | `graphify . --update` after apply; communities 7/68 under-represented today |

## Rollback Plan

- Additive-only change set: revert = `git revert` of the batch commits; no prior behavior to restore because existing token values, component code, and tests are untouched.
- `tokens.ts`/`tokens.test.ts` revert atomically with `tokens.css` (same logical unit).
- Storybook config changes are isolated in `web/.storybook/`; a revert restores the previous glob/decorators.
- No data migrations, no backend surface, no client-facing runtime impact — the panel SPA is dev-stage.

## Dependencies

None client-side — purely internal `web/` change. No Meta/DNS/KB dependencies.

## Success Criteria

- [ ] `tokens.css` covers type scale (with leading/weight), focus-ring, motion, breakpoints, and `--shadow-3`; every pre-existing token value is byte-identical (spot-check test green)
- [ ] `npm test` in `web/` passes, including drift-guard and no-hard-coded-hex checks
- [ ] Storybook renders a Tokens page showing color/type/spacing/radius/shadow/motion/focus groups from `tokens.css` (single source)
- [ ] All 10 story files are doc-level: controls interactive, variant matrix present, a11y + usage guidance visible
- [ ] `npm run build-storybook` succeeds without errors
- [ ] No new components, no domain patterns, no backend changes (diff is web/-only)

## Proposal Question Round

Execution is auto — questions are pre-registered for orchestrator/user confirmation before design:

1. **Type scale breadth** — Is the static rem scale (xs→3xl) enough for the panel, or do you want fluid `clamp()` sizing? *Assumption: static rem scale in this slice; fluid deferred.*
2. **Motion tokens now?** — The panel is mostly static today. *Assumption: minimal 3-duration + 2-easing set now (standard, cheap); no animation work yet.*
3. **Dark mode confirmed deferred?** — *Assumption: yes, deferred; it needs semantic-token rework and is not part of FUNDACIÓN PRIMERO.*
4. **Breakpoint values** — Desktop-first admin. *Assumption: `--bp-sm 640px / --bp-md 1024px / --bp-lg 1280px` as reference values, wired only into Storybook viewports.*
5. **Docs format** — *Assumption: autodocs + CSF Tokens page (decision **d**); MDX only if a custom narrative is required.*

## Delivery

The foundation is expected to apply in 1–2 batches (B9/B10): **B9** = token foundation + `tokens.ts`/guard updates + Storybook config; **B10** = Tokens page + doc-level story upgrades. Review budget: 400 changed lines per batch.

# 2026-08-20 — V1 shell: sidebar brand + panel header (continuous top bar)

## Why

The V2 design-system proposal (`2026-08-20-design-system-v2-proposal`) was
abandoned mid-slice. The user wants to keep the V1 originals — same palette,
typography, components — and make only narrow visual changes to the shell.

### Iteration history

1. **First slice** — added a separate `<header>` above the shell chrome with a
   gradient (`var(--header-gradient)`). User rejected after Storybook eval:
   the gradient header did not look right.
2. **Second slice** — extended the existing sidebar brand in `PanelShell` to
   act as the header (`Lumat` + `Panel operativo` + `Design system · v1.0`
   tag, flex layout, name grew to `--text-xl`). The user evaluated the
   result and asked for a pivot: the sidebar brand was correct **before** the
   extension, the problem was that the content area had no header at all —
   not that the brand needed a tag.
3. **This slice** — restore the sidebar brand to its original V1 form
   (two spans, grid layout, no tag, name at `--text-lg`) AND add a new
   panel header at the top of the content area. Both have the same height
   and the same `--primary-800` green so they read as one continuous bar.
   The sidebar's lime left rule and the panel header's lime bottom rule
   frame that bar. This is the standard admin-panel pattern the user asked
   for ("que parezca una continuidad").

The page background stays at cream `#F1F1E8`; the `--header-gradient` token
remains dropped.

## What

- **`PanelShell.tsx` — sidebar brand restored to V1.** `.panel-shell__brand`
  is back to `display: grid; gap: var(--space-1)` with no flex, no
  `justify-content: space-between`, no `__brand-info` wrapper, no
  `__brand-tag`. `.panel-shell__brand-name` is back to `font-size: var(--text-lg)`.
  The `Brand` JSX is back to two spans. The mobile brand is also reverted to
  V1 (no tag, no flex). The drawer brand inherits the revert automatically
  because it reuses the same `Brand` component.
- **`PanelShell.tsx` — new panel header.** Adds `.panel-shell__header`,
  `.panel-shell__header-title`, and `.panel-shell__content-area` (a grid
  wrapper that holds the header + the existing content). The header renders
  inside the content area (top of column 2 on desktop, below the mobile bar
  on mobile) and shows `NAVIGATION[currentView].label` (defaults to `"Panel"`).
  Same padding as the brand (`var(--space-5) var(--space-4)`), same
  `--primary-800` background, lime bottom rule (mirror of the brand's lime
  left rule).
- **`AppShell.tsx` — placeholder `<h2>` removed.** The panel header now owns
  the view label, so the duplicate `<h2 style={{ color: 'var(--text)' }}>`
  is deleted. The placeholder `<p>` and `VIEW_LABELS` lookup stay (the `<p>`
  still reads "Vista … disponible en un batch posterior").
- **`AppShell.stories.test.tsx` — tests pivoted.** The tag assertions are
  gone; brand assertions keep the lockup copy and the V1 background/lime
  rule. New assertions cover: panel header renders the current view label,
  uses `--primary-800` background, has a lime bottom rule, and shares the
  same padding token as the brand.

## Scope

**In** — `web/src/components/domain/PanelShell.tsx`,
`web/src/components/domain/AppShell.tsx`,
`web/src/stories/domain/AppShell.stories.test.tsx`,
`openspec/changes/2026-08-20-v1-shell-header-and-bg/` (this dir).

**Out** — V2 palette, V2 radii, V2 typography, V2 mockup stories, the
`--v2-*` token namespace, any other file under `web/src/components/**` or
`web/src/stories/**`, anything in `app/`, `db/`, `infra/`, and the parallel
`memoria-persistente-lumat-s1` slice.

## Approach

1. Revert `.panel-shell__brand` to V1 grid layout (remove flex, remove
   `__brand-info` wrapper, remove `__brand-tag`).
2. Revert `.panel-shell__brand-name` font-size from `--text-xl` to
   `--text-lg`.
3. Revert the `Brand` component JSX to two spans; revert the mobile brand
   rules (no tag, no flex wrapper).
4. Add `.panel-shell__header` (flex, `--primary-800` bg, lime bottom rule,
   same padding as the brand) and `.panel-shell__header-title` (`--text-xl`,
   bold, surface color).
5. Add `.panel-shell__content-area` (grid wrapper `auto minmax(0, 1fr)`)
   and place the new header + the existing content inside it. Update the
   desktop media query so `grid-column: 2` lives on the wrapper.
6. Delete the duplicate `<h2>` from `AppShell.tsx`.
7. Update the regression test file to reflect the new shape: keep brand
   lockup + V1 green + lime left rule; drop tag assertions; add panel
   header assertions (label, V1 green, lime bottom rule, same padding as
   the brand).

## Acceptance

- `npm test -- --run` — all tests pass, 0 fail.
- `npm run build-storybook` — clean build, all stories compile.
- `web/src/components/domain/AppShell.tsx` is touched (placeholder `<h2>`
  removed).
- `web/src/components/domain/PanelShell.tsx`'s `Brand` is back to the V1
  grid layout with two spans and no tag.
- `web/src/components/domain/PanelShell.tsx` adds `.panel-shell__header`
  rendering `NAVIGATION[currentView].label` at the top of the content area.
- Diff stats: 3 modified files (`PanelShell.tsx`, `AppShell.tsx`,
  `AppShell.stories.test.tsx`), 1 unchanged spec dir, 0 deletions outside
  the reverted CSS rules inside `PanelShell.tsx`.
- User evaluates the visual change in Storybook before commit.

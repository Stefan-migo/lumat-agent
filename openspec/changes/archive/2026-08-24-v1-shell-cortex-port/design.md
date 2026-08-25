# Design: V1 shell port to CortexDesign contract + sidebar bug fixes (slice-2)

## Technical Approach

Bug-first, contract-port, minimal-diff (DS-SHELL-1..5). Fix the two user-reported sidebar bugs by correcting the shell's own CSS (drop the shared 44px `min-height`; add the flex `min-width:0` chain), then re-target every color/spacing in `PANEL_SHELL_STYLES` to `--corp-*` slots or existing tokens (hex-free, CST-PRIM-1 extends to `PanelShell`), reusing `Badge`/`Avatar` primitives for the header badge and sidebar avatar. No new primitive, no new dependency, no component rewrite (rejected — over-engineering). Fix pre-existing tsc errors, re-align story assertions in lockstep, and verify Bug 2 in a real Storybook render (jsdom cannot exercise media-query overflow). Working tree stays a single-panel re-author; chip dashboard/story cleanup out.

## Architecture Decisions (D#)

| # | Decision | Options | Chosen |
|---|---|---|---|
| D1 | Collapse toggle sizing (DS-SHELL-1) | `min-height:0` vs explicit `min-height:2.25rem` (36px) | **Explicit `min-height: 2.25rem` + keep `width/height: 2.5rem`**. The shared `:248` rule sets `min-height: calc(var(--space-8) + var(--space-3))` = 44px, which beats the 40px `height`. Setting `min-height: 2.25rem` (36px) escapes the shared rule, keeps canvas ≥40px via the `2.5rem` box, is `--corp-*`-free and readable. |
| D2 | Toggle placement (part of DS-SHELL-1) | Align left vs right edge vs keep margin | **Anchor to nav left/right edges with `margin: 0 var(--space-3) var(--space-3)` in expanded; `align-self:center` in collapsed** (keep current layout). Only the 44px height is wrong; switching to a content-box 36-40px renders the icon centered in the same rhythm as nav items. |
| D3 | Hover/focus language (DS-SHELL-1/3) | `--corp-surface-hover` vs shell-local `--primary-700` | **Shell-local `--primary-700` hover + `--brand-lime` focus** (hex-free). `--corp-surface-hover` resolves `--table-head-bg` (light) — the dark-green sidebar needs the brand dark hover; documented as a shell-scoped exception with a `ponytail:` note. |
| D4 | Hover containment (DS-SHELL-2) | `overflow:hidden` only vs `min-width:0` chain | **`min-width:0` on `.panel-shell__sidebar-inner` and `.panel-shell__navigation` + `overflow:hidden` safety on `.panel-shell__sidebar`**. Flex column defaults to `min-width:auto`, letting the button's min-content widen the inner past the fixed 192/96px track. `min-width:0` stops that shrink-block; `overflow:hidden` guarantees paint (hover/`aria-current`) stays inside as a safety net. |
| D5 | Contract re-target (DS-SHELL-3) | Raw `--primary-*` vs full `--corp-*` | **Every color/spacing → `--corp-*` or existing token**; only dark-hover + active + focus stay branch-scale (documented exception). No new alias; the existing 17 `--corp-*` slots cover shell needs. |
| D6 | Component reuse (DS-SHELL-4) | PanelShell keeps hand-rolled badge/avatar vs primitives | **Reuse `Badge` + `Avatar`**. Header `statusBadge` slot → `<Badge>`; sidebar user avatar → `<Avatar name={...}>`. Zero new primitives (ponytail). |
| D7 | Verification depth (DS-SHELL-5) | jsdom-only vs real render | **Unit/RTL on behavior + real Storybook render at 390/640/768/1024/1280px × expanded/collapsed for Bug 2**. jsdom ignores `@media (min-width:64rem)`, so overflow can only be proven in a real browser/Storybook. |
| D8 | Dashboard/story cleanup | In-slice vs chained | **Chained out**. In-scope is shell + both bugs + tsc; `.dashboard-activity__time` (`--corp-value`) and hero/KPI polish are a separate slice to hold this diff within the 400-line budget. |

## Data Flow

```
tokens.css (--corp-*)                 AppShell.test.tsx / stories.test (assertions)
      │  aliases-only                          ▲ lockstep
      ▼                                        │
PANEL_SHELL_STYLES ──▶ PanelShell ──▶ Badge/Avatar primitives ──▶ real Storybook render (Bug 2)
      │  (flex min-width chain)
      └─ collapse button: min-height 2.25rem, ≥40px hit
```

- Toggle state stays session-only (`useState` in `PanelShell`), unchanged.
- Re-target mapping (D5): sidebar bg `--primary-800`→`--corp-primary`; white text `--surface`→`--corp-primary-fg`; nav text `--surface`→`--corp-primary-fg`; border hairline `color-mix(var(--surface))`→`color-mix(var(--corp-primary-fg))`; role text `--brand-aqua`→`--brand-aqua` (existing token); drawer backdrop `--primary-900`→`--primary-900` (existing token).

## Component/Story Structure

- **PanelShell**: one inline `PANEL_SHELL_STYLES` string; no new subcomponents. Header badge → `Badge`; avatar → `Avatar` (both already shipped primitives).
- **AppShell.stories.tsx** (DS-STORY-2): docs copy re-targeted — replace `var(--primary-800)` brand references with `--corp-primary`; drop stale "Design system · v1.0" tag copy (already removed; keep copy aligned).
- **Dashboard/PanelEntry/PageFrame**: untouched (chained D8).

## File Changes

| File | Action | Description |
|---|---|---|
| `web/src/components/domain/PanelShell.tsx` | Modify | Bug 1 (`min-height:2.25rem`), Bug 2 (`min-width:0` ×2 + `overflow:hidden`), `--corp-*` re-target, `Badge`/`Avatar` reuse, `ponytail:` dark-hover note |
| `web/src/components/domain/AppShell.test.tsx` | Modify | Fix TS6133 (:110 unused `s`) + TS2345 (:118 non-null assert / typed finder) |
| `web/src/stories/domain/AppShell.stories.test.tsx` | Modify | Re-align brand-bg/hex assertions to `--corp-*` (untracked today; dropped into change) |
| `web/src/stories/domain/AppShell.stories.tsx` | Modify | DS-STORY-2 docs re-target to `--corp-*` |
| `web/src/tokens/tokens.css` | — | No change (D7 touch block targets `.btn`/`.field__control` only; shell toggle free) |

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit (RTL) | Toggle `aria-expanded` toggling, label hide/show, active `aria-current`, Badge/Avatar render | `AppShell.test.tsx`; fix tsc first |
| Story (RTL) | `--corp-*` consumption, no raw `--primary-*` in brand/hover, hex-free | `AppShell.stories.test.tsx` string regex in lockstep |
| Real Storybook | Bug 2 overflow at 390/640/768/1024/1280px × expanded/collapsed (jsdom can't) | Manual browse of `domain/AppShell` stories; toggle expanded/collapsed |
| Gates | `npx tsc -b`, `npm test` 300+ green, hex walk | CI |

## Threat Matrix

`N/A` — CSS-only re-author of a React shell component + test/story edits. No routing, shell command, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary.

## Batch/PR Plan

**PR (single, ~380 authored lines)**: PanelShell bug fixes + `--corp-*` re-target + Badge/Avatar reuse + tsc fixes + story assertions/docs. Work-unit commits per file (`fix(web): sidebar collapse toggle sizing`, `fix(web): contain sidebar hover overflow`, `feat(web): port shell to --corp-* contract`, `test(web): tsc + story assertions`). Verify `npm test` + `tsc -b` + real Storybook render before chain.
**Chained out**: Dashboard/story cleanup (hero, KPI, `--corp-value` in `.dashboard-activity__time`, `PageFrame` overlap) → separate slice. 400-line risk: Low for the in-scope panel slice.
**Final batch**: `docs(openspec): mark 2026-08-20-v1-shell-header-and-bg as superseded` — an openspec-docs commit recording the abandonment (see Supersession).

## Supersession

The stale change `openspec/changes/2026-08-20-v1-shell-header-and-bg/` (describes the continuous-green-bar header, no longer implemented) is **superseded** by this port (proposal `#6`; spec.md:103-104). Its dir **stays on disk**, untouched — no code deletion. The abandonment is **recorded at archive time** (spec schema: "recorded, not deleted, archived abandoned"), surfaced via an openspec-docs commit in the final batch. No stale file is edited, deleted, or resurrected here.

## Migration / Rollout

No migration, no flags, no schema/backend change. Rollback = `git revert` the working-tree re-author commit (single PanelShell + tests/stories diff); token layer untouched, so a clean file-level revert.

## Graph Notes

Consulted (graph stale @ d8f26896, structural nodes valid): `PanelShell.tsx` (root), `AppShell.tsx`, `AppShell.test.tsx`, `AppShell.stories.tsx`, `Badge.tsx`, `Avatar.tsx`, `tokens.css` (`--corp-*`), `AppShell.stories.test.tsx`, `Dashboard.stories.tsx`, `PanelEntry.stories.tsx` (chained-out surface). Communities: AppShell.tsx, AppShell.stories.tsx, Dashboard.stories.tsx, PanelEntry.stories.tsx.

## Open Questions

- None blocking. (Badge/`--corp-*` slot-consumption confirms the re-target is safe; primary hover exception agreed as shell-scoped.)

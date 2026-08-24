# Design: Design System "Calma Operacional" — Slice-1 Catalog Adaptation

## Technical Approach

Additive token-alias layer + existing-primitive adaptation, zero color/font/icon change. Append a 17-slot `--corp-*` block to `tokens.css` mapping CortexDesign DC-004 slots onto existing frozen tokens (never raw hex — hex guard). Re-target existing same-name primitives (Button, Badge, Card, Input/Select/Textarea, StatusBadge, StateMessage→Alert) to consume those slots. Micro-changes: tabular-nums + fix stale `--bg` in `DESIGN_SYSTEM.md`. Defer ~30 Corporate components to chained slices (400-line budget).

## Architecture Decisions (D#)

| # | Decision | Options | Chosen |
|---|---|---|---|
| D1 | Alias location | new file vs append `tokens.css` | **Append `tokens.css` `:root`** — single-source `DS-TKN-1`; hex guard covers it; additive `CST-ALIAS-2`. |
| D2 | Dimensional `--corp-size/-w/-h` | map spacing vs fall back | **Fall back to component defaults; warn on `--corp-size`** `CST-ALIAS-4` — spacing tokens aren't control dims. |
| D3 | `--corp-value` slot | color vs behavior | **Behavioral: `font-variant-numeric: tabular-nums` on data roles** `CST-ALIAS-5`/`DS-TKN-11`. |
| D4 | Select slots | catalog `native-select` set | **Adopt `--corp-border/-text/-bg/-radius` (shared with Input/Textarea)** |
| D5 | StateMessage | full BEM vs minimal | **Minimal Alert mapping; refactor deferred** (budget). |
| D6 | Alias links | new token vs keep | **No new token; `--corp-primary`=`--primary-800`, links `--primary-700`** `CST-PRIM-2` (`--primary-600` forbidden). |
| D7 | 44px touch hit area | `::before` expansion vs media bump | **`@media (hover: none)` `min-height: 44px` on `.btn` + `.field__control`** — one CSS block (B2); 40px desktop preserved; `::before` over-spec. |
| D8 | Complete states | new props vs document + CSS-only | **Document shipped variants + CSS-only pairings** — disabled already dims with label/opacity, never `--text-muted` alone; no new props (budget). |

## Token Alias Layer (`tokens.css`) — 17 slots

| Slot | Maps to |
|---|---|
| `--corp-primary` | `var(--primary-800)` |
| `--corp-primary-fg` | `var(--surface)` |
| `--corp-accent` | `var(--info)` |
| `--corp-border` | `var(--border)` |
| `--corp-fg` | `var(--text)` |
| `--corp-fg-muted` | `var(--text-muted)` |
| `--corp-text` | `var(--text)` |
| `--corp-muted` | `var(--text-muted)` |
| `--corp-surface` | `var(--surface)` |
| `--corp-surface-hover` | `var(--table-head-bg)` |
| `--corp-bg` | `var(--bg)` |
| `--corp-radius` | `var(--radius-sm)` |
| `--corp-gap` | `var(--space-3)` |
| `--corp-value` | `tabular-nums` behavior (D3) |
| `--corp-size/-w/-h` | unresolved → component default (D2) |

## Component/Structure (slice-1)

- **Button/Input/Select/Textarea**: `.tsx` unchanged; `primitives.css` swaps values to `--corp-*` (e.g. `--primary-800`→`--corp-primary`). Badge/Card same.
- **StatusBadge**: already returns `<Badge tone=…>`; **no `.tsx`/CSS change** — tone map drives Badge.
- **StateMessage**: keep `.dashboard-state` + inline `<style>` (D5); `STATE_TONES` already tokenized; full BEM refactor deferred.
- **primitives.css**: re-target to `--corp-*`; add `.kpi__value` numeric rule + D7 touch block; **no new hex**.

## Complete States (slice-1) — CST-PRIM-4

Existing first-class variants per primitive (no new props/code on most):

| Primitive | Disabled | Loading | Empty | Error |
|---|---|---|---|---|
| Button | native `disabled` + `aria-disabled`; opacity 0.5 (dims label) | deferred (1) | deferred (1) | n/a |
| Badge | n/a (non-interactive) | n/a | n/a | `danger` tone + label |
| Card | n/a (non-interactive) | n/a | via `EmptyState` | via `StateMessage` |
| Input/Select/Textarea | native `disabled` + `field--disabled` (muted bg+text) | n/a | n/a | `error` → `aria-invalid` + linked text |
| StateMessage | n/a | `spinner` + `role=status` | via title text | `danger`/warning + `role=alert` |
| DataTable | n/a | `loading` prop | `emptyMessage` prop | `stale` note |

(1) Button loading/empty deferred: needs new props + spinner markup; no consumer requires it (budget).

## Micro-changes

- `tabular-nums` (already in StatCard/DataTable) extends via `--corp-value` to timestamps/IDs + remaining KPI contexts.
- `DESIGN_SYSTEM.md` line 120: `#F4F5F7` → `#F1F1E8` (`DS-TKN-12`).

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit `tokens.test.ts` | aliases under hex guard; each slot resolves to a token; pre-existing values byte-identical | extend drift walk + spot-check targets |
| Unit `primitives*.test` | still render, hex-free; disabled pairs dim+semantics | RTL smoke + hex scan |
| Unit | StateMessage `role=` + label + tone | RTL |
| Unit | `.btn`/`.field__control` ≥44px under `(hover:none)` | CSS media check |
| Storybook | widths 390/640/768/1024/1280px (`preview.ts` viewports) | `build-storybook` + viewport review |
| Gate | `npm test` + `build-storybook` green; hex guard covers aliases | CI |

## Threat Matrix

`N/A` — additive token/CSS; no routing, shell, subprocess, VCS/PR automation, or process-integration boundary.

## Batch/PR Plan (auto-chain, work-unit commits)

| Batch | Scope | ~Lines | Verify |
|---|---|---|---|
| B1 | `tokens.css` aliases (+17) + `tokens.test.ts` guard | ~90 | `npm test` |
| B2 | `primitives.css` re-target + StateMessage + touch block | ~155 | test + build-storybook |
| B3 | Micro-changes: DESIGN_SYSTEM bg fix, tabular-nums | ~25 | `npm test` |
| B4 | Tests: primitive smoke + alias spot-checks | ~60 | `npm test` |

Each `<400` lines; `feat(web):` commits; stacked-to-main.

## Migration / Rollout

No migration, no flags. Rollback = `git revert`: additive tokens + re-targeted CSS; primitives fall back to prior token BEM. No schema/backend/API.

## Open Questions

- `--corp-size` fallback: desktop 40px; touch ≥44px via `(hover:none)` (D7); token naming deferred.
- `count-up`/`fade-content` decorative anims: **not in slice-1** (proposal non-goals).
- Standalone `Alert` file vs through StateMessage — deferred to B2 (D5).

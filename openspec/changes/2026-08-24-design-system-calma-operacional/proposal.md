# Proposal: Design System "Calma Operacional" — Slice-1 Catalog Adaptation

## Intent

Upgrade the Lumat panel design system to `Calma Operacional` (clean, simple, minimalist, user-friendly) by adopting the **CortexDesign Corporate family** (DC-004 v1.2.0, 39 components) adapted to the **frozen** Lumat palette. Slice-1 grounds the catalog contract via a `--corp-*` token alias layer and re-targets existing same-name primitives to that contract — no color change, no new dependencies. This is the first, independently shippable slice of the full catalog adoption.

## Scope

### In Scope (slice-1)
- `--corp-*` alias layer in `tokens.css` (17 slots) mapped to existing tokens (executable source wins).
- Adapt existing same-name primitives to consume the catalog contract: Button, Badge, Card, Input/Select/Textarea, StatusBadge→Badge.
- StateMessage→Alert compatibility mapping (minimal, see decision gap).
- Fix stale `--bg` in `DESIGN_SYSTEM.md` (line 120: `#F4F5F7` → `#F1F1E8`); executable `tokens.css` wins.
- Micro-change: tabular-nums (`font-variant-numeric`) for data values (KPIs/timestamps/IDs/sec) per DESIGN_SYSTEM.md.
- Keep `npm test` + `build-storybook` green; hex guard preserved.

### Out of Scope (non-goals / deferred)
- Decorative animation components (glitch, gradient-text, magnet, marquee, blob-cursor, scroll-reveal, text-pressure) — violate DESIGN_SYSTEM.md.
- Palette changes, web fonts, icon packages, dark mode.
- Full 39-component Corporate adoption (Table, Tabs, Dialog, Tooltip, Popover, DropdownMenu, Accordion, Pagination et al.) — chained slices.
- Jinja panel migration.
- Agent scope, permissions, backend.

## Capabilities

### New Capabilities
- `corp-token-aliases`: the `--corp-*` slot layer mapping CortexDesign DC-004 slots to frozen Lumat tokens.
- `corp-primitives`: slice-1 primitive contract consumed via `--corp-*` slots (Button, Badge, Card, Input/Select/Textarea, Alert, StatusBadge).

### Modified Capabilities
- `panel-design-system`: existing primitives now resolve through the Corporate catalog contract; `DS-TKN-1` hex guard extended to the alias layer; tabular-nums mandated for data values.

## Approach

1. Append `--corp-*` aliases in `tokens.css` mapping to existing tokens (never raw hex − hex guard).
2. Adapt slice-1 primitives in `primitives/` + `primitives.css` to reference `--corp-*` slots.
3. Apply micro-changes (tabular-nums; DESIGN_SYSTEM.md stale bg).
4. Verify `npm test` + `build-storybook`; Storybook review at reference widths.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `web/src/tokens/tokens.css` | Modified | Add `--corp-*` alias layer (17 slots) |
| `web/src/tokens/tokens.test.ts` | Modified | Extend hex-guard/drift to alias layer |
| `web/src/components/primitives/` | Modified | Adapt slice-1 components to catalog contract |
| `web/src/components/primitives/primitives.css` | Modified | `--corp-*` + tabular-nums |
| `web/src/stories/pages/_shared/` | Modified | StateMessage→Alert minimal mapping; KPI tabular-nums |
| `web/DESIGN_SYSTEM.md` | Modified | Fix stale `--bg` (line 120) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Hex guard fails on alias/adoption files | Med | Route all color through `--corp-*`/existing tokens; extend drift test |
| 400-line budget exceeded | High | Staged slice-1; remaining components chained |
| StateMessage inline `<style>` normalization scope creep | Med | Keep minimal in slice-1; not a blocker |
| `--corp-size/--corp-w/--corp-h` fall back to defaults | Med | Document warnings; rely on component defaults |

## Rollback Plan

- Revert the alias block and primitive edits in `tokens.css`/`primitives/`; primitives fall back to their prior token-only BEM. `git revert` of slice-1 PR is safe: no schema/backend/API change, additive tokens only.

## Dependencies

- Existing `tokens.css` token set (all mapped slots pre-exist).
- CortexDesign catalog DC-004 v1.2.0 (Corporate family) + `web/.cortex/catalog-query.js` for indexing follow-up slices.

## Success Criteria

- [ ] All `--corp-*` slots map to existing tokens, zero new hex; `npm test` green.
- [ ] Slice-1 primitives render from the catalog contract in Storybook at 390/640/768/1024/1280px.
- [ ] No color, font, or icon change; `--primary-600`-for-links rule honored.
- [ ] DESIGN_SYSTEM.md `--bg` corrected; tabular-nums applied to data values.
- [ ] Remaining ~30 Corporate components indexed for chained PRs.

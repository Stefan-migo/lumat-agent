# Exploration — Corporate Components Port (Table / Tabs / Dialog)

> Change: `2026-08-24-corp-components-port` · Project: LumatAgent · Phase: sdd-explore
> Mode: hybrid (OpenSpec authoritative + Engram secondary) · Date: 2026-08-24
> Branch: `feat/corp-components-port` (from origin/main @ 8d850428 — Calma Operacional merged)

## Context

- Main already carries the merged Calma Operacional design system: `--corp-*` alias layer (17 slots, frozen palette), primitives re-targeted, shell port, dashboard cleanup. 318/318 tests, tsc 0, build-storybook OK on main.
- Catalog: `web/.storybook/component-catalog.json` (DC-004 v1.0.0, 90 entries). Corporate family is the target; decorative effects were rejected in the Calma Operacional finalize (per DESIGN_SYSTEM.md).
- This change ports the first three Corporate components the user selected: **Table, Tabs, Dialog**.
- Adapter protocol: `component-adapter` skill + `web/.cortex/catalog-query.js` (CA-001). No new dependencies.

## Catalog anatomy (DC-004)

| Component | visualContext | moodTags | tokenSlots | variants |
|---|---|---|---|---|
| `table` | `["table"]` | `["corporate","clean"]` | `--corp-border, --corp-text, --corp-bg` | Default, HeadersOnly |
| `tabs` | `["tabs","navigation"]` | `["corporate"]` | `--corp-border, --corp-text, --corp-muted, --corp-accent, --corp-surface` | Default, Controlled |
| `dialog` | `["overlay","modal","form"]` | `["corporate"]` | `--corp-border, --corp-bg, --corp-radius, --corp-fg` | Default |

## Current state in the panel

### Table
- `web/src/stories/pages/_shared/DataTable.tsx` (design D6 / DS-UI-TABLES) is the shared table used by CasesList, ClientesList, KbList, ConversationsList, ClientFicha. Emits `.table` primitive; has empty/loading/stale states; `tabularNum()` resolves `--corp-value`.
- `.table` CSS in `primitives.css` still uses **raw tokens** (`--text`, `--border`, `--table-head-bg`) — slice-1 did NOT retarget it to `--corp-*`.
- DESIGN_SYSTEM.md §Data table: semantic markup, caption/context, sticky headings, narrow-width scanning (do not auto-convert tables into cards).

### Tabs
- **No tabs component exists.** PanelShell navigation is sidebar buttons (`aria-current="page"`), not tabs.
- No page currently needs tabs (ClientFicha uses stacked Cards: Notas, Historial).

### Dialog
- **No dialog/modal component exists.** Current feedback is inline (FlashMessage, StateMessage). No destructive-confirmation flows in page stories today.
- DESIGN_SYSTEM.md §Dialog and disclosure (authoritative contract): dialogs for destructive confirmation or blocking tasks; meaningful initial focus; focus trap while open; Escape where safe; restore focus on close. `--shadow-2`/`--shadow-3` reserved for dialogs/overlays; `--radius-md` for dialogs.

## Adaptation mapping (frozen palette — zero visual change in values)

| Catalog slot | Lumat alias | Current value |
|---|---|---|
| `--corp-border` | `--corp-border` | `var(--border)` |
| `--corp-text` | `--corp-text` | `var(--text)` |
| `--corp-bg` | `--corp-bg` | `var(--bg)` |
| `--corp-muted` | `--corp-muted` | `var(--text-muted)` |
| `--corp-accent` | `--corp-accent` | `var(--info)` |
| `--corp-surface` | `--corp-surface` | `var(--surface)` |
| `--corp-radius` | `--corp-radius` | `var(--radius-sm)` |
| `--corp-fg` | `--corp-fg` | `var(--text)` |

All slots already exist as aliases — the port is contract alignment, not new values.

## Recommendations

1. **Table**: retarget `.table` primitive CSS to `--corp-*` aliases (no visual change). Skip `HeadersOnly` variant (YAGNI — no consumer). Keep DataTable API as-is; consumers unchanged.
2. **Tabs**: new `Tabs` primitive (Default + Controlled variants per catalog; `role="tablist"`/`tab`/`tabpanel`, `aria-selected`, keyboard arrows) + story + tests. Additive; no page adoption yet (no real consumer — ClientFicha adoption is a future slice if the user wants it).
3. **Dialog**: new `Dialog` primitive implementing the DS contract (focus trap, Escape, restore focus, `--shadow-2`/`--shadow-3`, `--radius-md`) + story + tests. Additive; destructive-confirmation page adoption is a future slice.
4. **Slice shape** (review budget 400): two chained PRs — (A) table retarget + Tabs primitive; (B) Dialog primitive. Both land as primitives with stories, so the user sees them in Storybook under `stories/primitives/`.

## Risks

- Dialog a11y is the heaviest piece: focus trap + Escape + restore requires careful tests (jsdom focus simulation limits — use role/aria assertions and fireEvent.keyDown).
- Tabs keyboard navigation (arrow keys) is mandated by WAI-ARIA; keep implementation minimal (roving tabindex only if cheap; otherwise click + `aria-selected` and document keyboard as follow-up).
- No page adoption in this change keeps the diff small and review-focused; the "visible in the panel" effect comes via page adoption in follow-up slices.
- `KbList.stories.tsx` literal tabular-nums (known follow-up from slice-3) stays out of scope.

## Graph nodes consulted

`graphify query "components primitives"` / `"DataTable table tabs dialog modal"`: DataTable(), DataTable.tsx, DataTable.test.tsx, `.table` community, primitives.css cluster, page story communities (CasesList, ClientesList, KbList, ClientFicha, Settings, ConversationsList), StateMessage.tsx, PanelShell navigation cluster, tokens.test.ts.

## Next recommended phase

`propose`
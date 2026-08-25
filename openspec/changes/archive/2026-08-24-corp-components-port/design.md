# Design — Corporate Components Port (Table / Tabs / Dialog)

> Change: `2026-08-24-corp-components-port` · Project: LumatAgent · Phase: sdd-design
> Mode: hybrid · Date: 2026-08-24 · Branch: `feat/corp-components-port`

## D1 — Placement and files

| File | Action |
|---|---|
| `web/src/components/primitives/primitives.css` | Retarget `.table` block to `--corp-*`; add `.tabs` and `.dialog` blocks |
| `web/src/components/primitives/Tabs.tsx` | New primitive (Default + Controlled) |
| `web/src/components/primitives/Dialog.tsx` | New primitive (DS §Dialog contract) |
| `web/src/stories/primitives/Tabs.stories.tsx` | Storybook story |
| `web/src/stories/primitives/Dialog.stories.tsx` | Storybook story |
| `web/src/components/primitives/Tabs.test.tsx` | Colocated vitest (strict TDD — written first) |
| `web/src/components/primitives/Dialog.test.tsx` | Colocated vitest (strict TDD — written first) |

No new dependencies, no portal, no context, no animation library (Ponytail).

## D2 — Tabs API

```tsx
export interface TabItem { id: string; label: string }
export interface TabsProps {
  tabs: TabItem[];
  /** Controlled: active tab id. Omit for uncontrolled (first tab active). */
  activeTab?: string;
  onTabChange?: (id: string) => void;
  /** Render active panel content. */
  children: (activeId: string) => ReactNode;
  /** Accessible tablist label. */
  ariaLabel?: string;
}
```

- Uncontrolled: internal state seeded with `tabs[0].id`; click sets active + calls `onTabChange` if provided.
- Controlled: `activeTab` prop wins; click calls `onTabChange` only.
- Semantics: `<div role="tablist" aria-label>` → `<button role="tab" aria-selected aria-controls>` → `<div role="tabpanel" id>`; panel id = `tabs-<id>-panel`, tab id = `tabs-<id>-tab`; only the active panel is rendered.
- Keyboard: click activation only in this slice (WAI-ARIA arrow-key roving is a documented follow-up; keeps the diff small and jsdom-tractable).

## D3 — Dialog API

```tsx
export interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  closeLabel?: string; // default "Cerrar" (DS-UI-COPY)
}
```

- Renders `null` when `!open`.
- Structure: `.dialog-overlay` (fixed, full-viewport scrim) → `.dialog` (role="dialog", aria-modal="true", aria-labelledby=title id) with header (title + close button `aria-label={closeLabel}`) and body.
- Focus contract (CORP-DIALOG-3):
  - On open: capture `document.activeElement`; focus first focusable inside (button, input, [tabindex]) or the dialog itself.
  - Trap: `keydown` on dialog — Tab cycles the focusable set (wrap at ends); Shift+Tab reverses.
  - Escape: `onClose()` (CORP-DIALOG-2).
  - On close/unmount: restore focus to the captured element.
- Overlay click does NOT close (destructive-confirmation safety; explicit action or Escape only — matches DS intent "block background interaction").
- `useEffect` keyed on `open` handles focus; `useEffect` cleanup restores. Focusables query: `button, input, select, textarea, a[href], [tabindex]:not([tabindex="-1"])`.

## D4 — CSS (primitives.css additions)

```css
/* .table retarget (D5): */
.table { color: var(--corp-text); }                    /* was var(--text) */
.table th, .table td { border-bottom: 1px solid var(--corp-border); } /* was var(--border) */
/* th background stays --table-head-bg (sanctioned surface-hover value, slice-2 note) */

/* .tabs */
.tabs { display: flex; gap: var(--space-1); border-bottom: 1px solid var(--corp-border); }
.tabs__tab { background: none; border: 0; padding: var(--space-2) var(--space-3);
  color: var(--corp-muted); font: inherit; font-size: var(--text-sm); cursor: pointer;
  border-bottom: 2px solid transparent; }
.tabs__tab[aria-selected="true"] { color: var(--corp-text); border-bottom-color: var(--corp-accent); }
.tabs__tab:focus-visible { outline: 2px solid var(--corp-accent); outline-offset: 2px; }
.tabs__panel { padding: var(--space-3) 0; color: var(--corp-text); }

/* .dialog */
.dialog-overlay { position: fixed; inset: 0; z-index: 10; display: flex; align-items: center;
  justify-content: center; background: color-mix(in srgb, var(--corp-bg) 55%, transparent); }
.dialog { background: var(--corp-surface); border: 1px solid var(--corp-border);
  border-radius: var(--corp-radius); box-shadow: var(--shadow-3); width: min(28rem, calc(100vw - var(--space-5)));
  color: var(--corp-fg); }
.dialog__header { display: flex; align-items: center; justify-content: space-between;
  gap: var(--space-3); padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--corp-border); }
.dialog__title { margin: 0; font-size: var(--text-md); font-weight: var(--weight-semibold); }
.dialog__close { background: none; border: 0; color: var(--corp-muted); cursor: pointer; font-size: var(--text-md); }
.dialog__close:focus-visible { outline: 2px solid var(--corp-accent); outline-offset: 2px; }
.dialog__body { padding: var(--space-4); }
```

Scrim uses `color-mix` over `--corp-bg` — no new color value (palette frozen). `--shadow-3` is the DS-reserved overlay shadow.

## D5 — Table retarget

Only the two color declarations in the `.table` block change (`--text` → `--corp-text`, `--border` → `--corp-border`). DataTable.tsx untouched. Zero visual change (alias identity).

## D6 — Tests (strict TDD, written before implementation)

- `Tabs.test.tsx`: tablist/tab/tabpanel roles; first tab `aria-selected=true`; click moves selection + swaps panel; controlled variant honors `activeTab` and fires `onTabChange`.
- `Dialog.test.tsx`: `role="dialog"` + `aria-modal` + close button `Cerrar`; Escape fires `onClose`; focus moves to first focusable on open and returns to trigger on close; Tab trap wraps (assert `document.activeElement` after repeated Tab).
- Existing `tokens.test.ts` (drift guard) untouched and green.

## D7 — Stories

- `Tabs.stories.tsx`: Default (3 tabs with mock content), Controlled (state via `useState` — storybook-only, inline).
- `Dialog.stories.tsx`: trigger button + open Dialog with title and a confirm/cancel body; shows `Cerrar` close and Escape behavior.
- Both follow existing `stories/primitives/*.stories.tsx` conventions (Spanish copy, `component` + `render` CSF3).

## D8 — Slices and delivery

- **PR-A** (slice-1): D5 table retarget + D2/D4/D6/D7 Tabs. ~250 changed lines → under 400.
- **PR-B** (slice-2): D3/D4/D6/D7 Dialog. ~220 changed lines → under 400.
- Auto-chain stacked-to-main; each PR gets native RDD review (consent per candidate) before merge; work-unit commits (tests + component + story per unit).

## Follow-ups (out of scope, recorded)

- Tabs arrow-key roving; page adoption (ClientFicha tabs, destructive confirmations); Tooltip/Popover/DropdownMenu/Accordion/Pagination; KbList tabular-nums advisory.
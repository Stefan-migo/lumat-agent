# Design: Storybook Redesign — Full design-system adoption across all Storybook surfaces

## Technical Approach

Hybrid (Approach C): promote the shared frame and label maps once, then restyle each of the 9 old pages to consume them in reviewable slices. Dashboard
is the proving ground — its proven look and tests remain the regression sentinel; the shared frame must render Dashboard identically before any page
adopts it. All work is token-only (no new tokens, no hex, no deps); `primitives.css` focus/motion swaps are the only production-impacting edit and are
token-equivalent.

Graph record: `graphify query "storybook stories panel primitives helpers"` (430-node traversal, C1/C26/C36); paths `PageHeader() <--imports.. CasesList.stories --imports..> DataTable()`, `StatCard() <--imports..> Dashboard.stories`, `StatusBadge() <--imports..> ConversationsList`.

## Architecture Decisions

| # | Option | Tradeoff | Decision |
|---|---|---|---|
| D1 | Spanish label maps at root vs per-page literal strings | Root = one fix for all consumers; per-page = drift | Root: extend `toneMaps.ts` with label maps + give `StatusBadge` a label prop/default map. Raw states never appear on non-technical views. |
| D2 | New `PageFrame` component vs copying `DASHBOARD_STYLES` 9× | Copy = drift (today's problem); component = one contract | New `PageFrame` under `_shared/` owning titlebar (lime rail + `--primary-100` tint) + banner slot + content region, echoing `panel-shell__brand`. |
| D3 | Promote story-local `StateMessage` to `_shared/` vs keep per page | Promotion = single banner language + roles; keeps Dashboard green | Promote to `_shared/StateMessage.tsx` (tone/role/title/detail/spinner). Dashboard consumes it; sentinel tests unchanged. |
| D4 | `StatusBadge` label map keyed by raw `State` vs extend `Badge` | Keyed map keeps one primitives primitive; extended Badge couples display to domain | Add `label` prop + per-domain default maps in `toneMaps.ts`; `StatusBadge` takes an optional `label`; pages pass approved labels. |
| D5 | DataTable empty default ES vs per-page prop | Per-page = repeat; default = one Spanish source | `emptyMessage` default → `No hay registros`; `actionsHeader` default → `Acciones`; add `loading`/`stale` props. |
| D6 | Tabular-num in StatCard core vs Dashboard-scoped CSS | Core = one KPI source; scoped = drift | Fold `font-variant-numeric: tabular-nums` + right-align numeric into StatCard core and a `tabularNum` column helper. |
| D7 | Token swaps in `primitives.css` only (no new tokens) | All roles exist (`--focus-ring*`, `--duration-*`, `--ease-*`, `--info`) | Swap in place; add a `prefers-reduced-motion` block; token guard stays green (no hex added). |
| D8 | Login lockup via typographic block vs asset | No production logo asset exists (non-goal) | Typographic lockup reusing `panel-shell__brand` language (`Lumat` + `Panel operativo`); note the missing asset for a later change. |
| D9 | ClientFicha tone fix | Uses `customerStateTone` for case status (bug) | Switch case rows to `caseStatusTone`; label maps make both correct and Spanish. |
| D10 | Slice ordering (S1→S6) | Foundation first de-risks pages | S1 tokens → S2 frame+labels → S3 lists → S4 conversations → S5 ficha/chat/login → S6 KB/settings. Each slice green. |

## Data Flow

```
StatusBadge/label map ── raw state ──→ approved Spanish label (pages + primitives stories)
PageFrame (titlebar) ── PageHeader ──→ page title/meta/actions
StateMessage (banner) ── role/tone ──→ loading|empty|stale|partial-error|fatal-error
DataTable (loading/stale/empty) ── tabularNum ──→ right-aligned numeric cells
```

## File Changes

| File | Action | Description |
|---|---|---|
| `web/src/components/primitives/primitives.css` | Modify | `.btn` transition→`--duration-base`/`--ease-out`; `.btn:focus-visible`,`:focus`,`:focus-within`→`--focus-ring-width`/`--focus-ring`/`--focus-ring-offset`; `.spinner__indicator` top→`--info`+`--duration-slow`; add reduced-motion block |
| `web/src/components/primitives/StatusBadge.tsx` | Modify | `label` prop + Spanish default map; render label not raw status |
| `web/src/components/primitives/SearchInput.tsx` | Modify | default `aria-label="Buscar"` |
| `web/src/stories/pages/_shared/toneMaps.ts` | Modify | Add `conversationLabel`, `customerStateLabel`, `caseStatusLabel`, `kbLabel`, `directionLabel` maps + tone references |
| `web/src/stories/pages/_shared/StateMessage.tsx` | Create | Promoted from Dashboard (tone/role/title/detail/spinner) |
| `web/src/stories/pages/_shared/PageFrame.tsx` | Create | Titlebar + banner slot + content region |
| `web/src/stories/pages/_shared/DataTable.tsx` | Modify | ES default empty/actions header, `loading`/`stale`, `tabularNum` helper |
| `web/src/stories/pages/_shared/StatCard.tsx` | Modify | tabular-num core |
| `web/src/stories/pages/*.stories.tsx` (9 old) | Modify | Restyle to shared frame, Spanish, complete state matrix, `--primary-700` links |
| `web/src/stories/primitives/*.stories.tsx`, `web/src/stories/pages/_shared/*.test.tsx` | Modify | Spanish copy + state-matrix coverage |

## Interfaces / Contracts

```tsx
// _shared/StateMessage.tsx — promoted
type StateTone = "info" | "warning" | "danger";
type StateRole = "status" | "alert";
interface StateMessageProps { tone: StateTone; role: StateRole; title: string; detail?: string; spinner?: boolean }

// _shared/PageFrame.tsx
interface PageFrameProps {
  title: string; meta?: ReactNode; actions?: ReactNode;
  children: ReactNode; state?: ReactNode; // banner slot
}

// _shared/DataTable.tsx — extensions
interface DataTableProps<T> {
  columns: Column<T>[]; rows: T[];
  emptyMessage?: string;     // default "No hay registros"
  actions?: (row: T) => ReactNode;
  actionsHeader?: string;    // default "Acciones"
  loading?: boolean; stale?: boolean;
  tabularNum?: (row: T, cell: ReactNode) => ReactNode; // right-align + tabular-nums
}
type Column<T> = { key: string; header: string; render: (r: T) => ReactNode; align?: "left" | "right" };

// toneMaps.ts additions
const LABELS = {
  conversation: { bot: "Agente atendiendo", human: "Atención humana", closed: "Cerrada" },
  customer:     { nuevo: "Nuevo", activo: "Activo", inactivo: "Inactivo", bloqueado: "Bloqueado" },
  case:         { abierto: "Abierto", en_evaluacion: "En evaluación", escalado: "Escalado", cerrado: "Cerrado" },
  kb:           { activo: "Activo", deshabilitado: "Deshabilitado", procesando: "Procesando", error: "Error" },
  direction:    { inbound: "Entrante", outbound: "Saliente" },
};
export const conversationLabel / customerStateLabel / caseStatusLabel / kbStatusLabel / directionLabel: (k: string) => string;
```

## Testing Strategy

| Layer | What to Test | Approach (TDD) |
|---|---|---|
| Unit (new, red first) | Maps cover every `types.ts` state; label non-empty; tone resolve | `toneMaps.test`, `StatusBadge.test` |
| Unit | `StateMessage` role/tone/spinner; `PageFrame` titlebar/banner; `DataTable` ES defaults + loading/stale | `_shared/*.test` updated to Spanish |
| Unit | ClientFicha case row uses `caseStatusTone`; Login preserves username on error | `ClientFicha.test`, `Login.test` |
| Per-slice | Each slice keeps `cd web && npm test`, `npx tsc --noEmit`, `npm run build-storybook` green | run after every slice; update EN/raw assertions in that slice's tests |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary. Storybook page/primitives only.

## Migration / Rollout

6 chained ≤400-line PRs (S1→S6), each green. No data migration, no flags. Rollback per-PR; `primitives.css` swaps isolated to one file, token-equivalent, reverts independently. Dashboard sentinel proves the frame before broad adoption.

## Open Questions

None. All requirements resolve against existing tokens and the Dashboard reference.

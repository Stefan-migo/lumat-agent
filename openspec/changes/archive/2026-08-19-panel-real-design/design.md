# Design: Panel Real Design — Page-First Storybook Workflow

## Technical Approach

Recreate each panel page as a **Storybook page story** under `web/src/stories/pages/`, composed from archived `src/components/` primitives + story-local helpers under `_shared/`, styled by consuming the dead-but-tokenized classes already in `primitives.css` (`.table`, `.kpi`, `.empty-state`, `.flash-message`, `.spinner`). **Production untouched** — `web/src/components/**`, `app/**`, routes, and API stay as-is. The Storybook glob `../src/stories/**/*.stories.tsx` already picks up `stories/pages/`, so `.storybook/main.ts` is unchanged (R-PRD-PG-1). This is a pure additive Delta over the archived `panel-design-system` foundation.

## Architecture Decisions

### D1 — Story-local helpers vs real components

| Option | Tradeoff | Decision |
|---|---|---|
| Production `src/components/domain/*` | Real reuse now, but violates session scope (stories/helpers/fixtures only) | **Rejected** |
| Story-local `_shared/` helpers + later extraction | Keeps phase strict; helpers are thin compose layers; promotion documented for a later phase | **Chosen** |

DataTable, PageHeader, StatCard, EmptyState, FlashMessage live under `stories/pages/_shared/` (R-PRD-PG-2). They emit `primitives.css` class names + tokenized inline styles (mirroring `AppShell.tsx`/`matrix.tsx`).

### D2 — Page story shape

| Option | Tradeoff | Decision |
|---|---|---|
| Single `Overview` story + custom render | Minimal glob noise; but hides per-state differences | Dashboard, Clientes list, ficha, thread, KB, Settings, Login |
| **Named stories per page state** (default/loading/empty/error) | State variants visible as discrete stories; ~2-4 stories/page; fits CSF | **Chosen for list pages** (Clientes, Cases, Conversations, KB) |

CSF `meta.title: "pages/{Page}"`, typed `StoryObj`, `excludeStories` for exported helpers (matches `Tokens.stories.tsx`).

### D3 — Mock data approach

| Option | Tradeoff | Decision |
|---|---|---|
| Shared `mockData.ts` factory | One file could balloon past 400-line budget | **Rejected** |
| **Per-page modules** `_shared/mockData/{dashboard,clients,cases,kb,settings,conversations}.ts` | Each batch owns its fixtures; no cross-page coupling (R-PRD-PG-3) | **Chosen** |

Each mock is typed against `web/src/types.ts` (`Kpis`, `Customer`, `Case`, `Doc`, `Settings`, `Conversation`) matching serializer shapes in `app/panel/api/serializers.py` (snake_case, ISO dates, nullables). Fixtures are realistic (Chilean names/phones, Lumat services).

### D4 — StatusBadge/Case tone maps

`StatusBadge` maps conversation statuses only (`Status` = bot/human/closed/pending/escalated). Case statuses and Customer states need explicit maps to `Badge` tones:

**Case status → BadgeTone**

| Case.status | Tone | Rationale |
|---|---|---|
| `abierto` | `neutral` | Open/pending |
| `en_evaluacion` | `warning` | In progress, attention |
| `escalado` (or emergency) | `danger` | Escalated/urgent |
| `cerrado` | `success` | Done |

**CustomerState → BadgeTone**

| Customer.state | Tone | Rationale |
|---|---|---|
| `nuevo` | `warning` | New, unhandled |
| `activo` | `success` | Active/healthy |
| `inactivo` | `neutral` | Idle |
| `bloqueado` | `danger` | Blocked |

Defined in `_shared/toneMaps.ts` (exports `caseStatusTone`, `customerStateTone`); a test iterates all statuses/states from `types.ts` asserting each maps to a valid `BadgeTone`, none unmapped (R-PRD-PG-7).

### D5 — Conversations list design (no backend source)

No Jinja/API list endpoint exists; only the thread GET. Design the list from `Customer`/`Conversation` shapes. **Columns (product spec for the future endpoint)**: `#` (id), Customer (name + muted phone from `Customer`), State, Summary, Last message (from `last_message_at`), Created. Flag `GET /conversations` as a backend gap in `tasks.md`.

### D6 — DataTable contract

`_shared/DataTable.tsx`:

```tsx
interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;      // cell content; e.g. <Badge/>, link
  align?: "left" | "right";
}
interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  emptyMessage?: string;              // renders .empty-state when rows empty
  actions?: (row: T) => ReactNode;    // actions cell (Cases update/ack)
}
```

Emit `.table` + `.table th/td` classes; tokenized inline gap via `--space-3`.

### D7 — Per-page state variants

| Page | Stories | States |
|---|---|---|
| Dashboard | Overview | data |
| Clientes list | Default / Loading / Empty | search + table; empty "No customers found" |
| Clientes ficha | Default | card + state form + notes + history |
| Conversation thread | Default | header + messages + no-reply note **and** bubble variant |
| Cases | Default / Empty | table + inline update/ack |
| Conversations list | Default / Empty | new design |
| KB | Default / Empty | add-doc + docs table + edit accordion |
| Settings | Default | 6 form cards + spend snapshot |
| Login | Default / Error | centered auth card |

### D8 — Batch boundaries (each ≤400 lines)

| Batch | Files created | Verifies |
|---|---|---|
| B1 `_shared/` base | `DataTable.tsx`, `PageHeader.tsx`, `StatCard.tsx`, `EmptyState.tsx`, `FlashMessage.tsx`, `toneMaps.ts` (+ test), `mockData/dashboard.ts` | tests + build |
| B2 Dashboard + Clientes list | `pages/Dashboard.stories.tsx`, `pages/ClientsList.stories.tsx`, `mockData/clients.ts` | green |
| B3 ficha + thread | `pages/ClientFicha.stories.tsx`, `pages/ConversationThread.stories.tsx`, `mockData/conversations.ts` | green |
| B4 Cases + Conversations list | `pages/CasesList.stories.tsx`, `pages/ConversationsList.stories.tsx`, `mockData/cases.ts` | green |
| B5 KB + Settings + Login | `pages/KbList.stories.tsx`, `pages/Settings.stories.tsx`, `pages/Login.stories.tsx`, `mockData/kb.ts`, `mockData/settings.ts` | green |

All batches: web-only diff, `npm test` + `npm run build-storybook` green after each (R-PRD-PG-4/5), auto-chain, stacked-to-main.

## File Changes

| Path | Action | Description |
|---|---|---|
| `web/src/stories/pages/_shared/DataTable.tsx` | Create | Generic table (D6), `.table` classes |
| `web/src/stories/pages/_shared/PageHeader.tsx` | Create | Title + subtitle/meta inline styles |
| `web/src/stories/pages/_shared/StatCard.tsx` | Create | `.kpi`-class KPI card |
| `web/src/stories/pages/_shared/EmptyState.tsx` | Create | `.empty-state` wrapper |
| `web/src/stories/pages/_shared/FlashMessage.tsx` | Create | `.flash-message--{tone}` |
| `web/src/stories/pages/_shared/toneMaps.ts` + `.test.ts` | Create | D4 maps + coverage assert |
| `web/src/stories/pages/_shared/mockData/{dashboard,clients,cases,kb,settings,conversations}.ts` | Create | Typed mocks (D3) |
| `web/src/stories/pages/{Dashboard,ClientsList,ClientFicha,ConversationsList,ConversationThread,CasesList,KbList,Settings,Login}.stories.tsx` | Create | 9 page stories |
| `web/src/components/**`, `.storybook/main.ts` | Guard | Zero modifications (R-PRD-PG-1) |

## Interfaces / Contracts

Pages reference `web/src/types.ts` types only; mocks match serializer dicts. No new production interface; `page-*` story components accept mock props directly.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | `toneMaps` coverage of all `Case` statuses + `Customer` states → valid `BadgeTone` | vitest `describe` in `toneMaps.test.ts` |
| Unit | Helper rendering (DataTable empty→`.empty-state`, StatCard `.kpi`) | vitest + RTL per helper |
| Build | 9 pages present in built index | `build-storybook` + index nav inspection (R-PRD-PG-5) |

## Threat Matrix

`N/A` — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary. Change is additive Storybook-only (stories, helpers, mocks); no ADRs expand into exec/pr process vectors.

## Migration / Rollout

Additive-only; no data migration, flags, or phased rollout. Revert = delete batch commits or `stories/pages/`. Safe mid-batch.

## Ponytail Cuts

- **No Tabs** — ficha history stays stacked sections (Jinja parity).
- **No router** — AppShell already switches views via state; stories render page content directly.
- **No new deps** — zero packages added to `web/package.json`.
- **No new CSS files** — all classes reused from `primitives.css`.
- **No mock duplication** — one mock module per page; stories import their own.
- **No shared state library** — helpers are static renders of mock props.
- **No modal** — KB edit stays native `<details>` accordion (no `.modal` consumption needed).

## Open Questions

- [ ] `GET /conversations` list endpoint: confirm backend gap acceptance before implementation.
- [ ] Thread bubble variant: keep flat `.table` as canonical, bubble as secondary story?

## Key Learnings

1. Every dead-token class in primitives.css (`.table/.kpi/.empty-state/.flash-message/.spinner`) is a ready consumer for page-story helpers with zero new CSS.
2. StatusBadge only maps conversation statuses; Case statuses and Customer states need explicit Badge tone maps asserted by a unit test.
3. The Conversations list page has no Jinja/API source; it is designed from Customer/Conversation types and flags a future list endpoint.

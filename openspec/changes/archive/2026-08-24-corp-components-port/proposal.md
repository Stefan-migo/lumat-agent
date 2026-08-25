# Proposal — Corporate Components Port (Table / Tabs / Dialog)

> Change: `2026-08-24-corp-components-port` · Project: LumatAgent · Phase: sdd-propose
> Mode: hybrid (OpenSpec authoritative + Engram secondary) · Date: 2026-08-24
> Branch: `feat/corp-components-port` · Preflight: auto | both | auto-chain | review budget 400

## Intent

Port the first three Corporate-family components of the CortexDesign catalog — **Table, Tabs, Dialog** — into the Lumat panel primitives, following the Calma Operacional contract: frozen palette, `--corp-*` alias layer only, no new dependencies, no visual value changes. This makes the design system visible in Storybook and lays the a11y-safe foundation for page adoption.

## Scope

1. **Table (contract alignment)**: retarget `.table` primitive CSS from raw tokens (`--text`, `--border`, `--table-head-bg`) to the catalog slots (`--corp-border`, `--corp-text`; keep `--table-head-bg` as-is — it is the sanctioned surface-hover value per slice-2 ponytail note). DataTable API unchanged; zero visual change; existing consumers untouched.
2. **Tabs (new primitive)**: catalog `tabs` (visualContext `tabs|navigation`, corporate) — Default + Controlled variants; WAI-ARIA tablist/tab/tabpanel, `aria-selected`, click activation; colocated story + tests.
3. **Dialog (new primitive)**: catalog `dialog` (visualContext `overlay|modal|form`) implementing the DESIGN_SYSTEM.md §Dialog contract: meaningful initial focus, focus trap while open, Escape close, restore focus on close, `--shadow-2`/`--shadow-3` + `--radius-md`; colocated story + tests.

## Out of scope

- Page adoption (ClientFicha tabs, destructive-confirmation dialogs) — future slices; no real consumer today (YAGNI).
- `HeadersOnly` table variant (no consumer).
- Tooltip / Popover / DropdownMenu / Accordion / Pagination — follow-ups.
- `KbList.stories.tsx` literal tabular-nums follow-up (from slice-3 advisory).
- Any token value change (palette frozen).

## Approach

- Work-unit commits (tests with code, conventional commits, no AI attribution).
- Auto-chain, stacked-to-main, 2 PRs:
  - PR-A: table retarget + Tabs primitive (stories + tests).
  - PR-B: Dialog primitive (story + tests).
- Each PR goes through native RDD review (RDD global ON, consent per candidate) before archive.

## Acceptance

- All new components visible in Storybook under `stories/primitives/`.
- `npm test` green (existing 318 + new), `tsc --noEmit` 0, `npm run build-storybook` OK.
- No token value changes; only alias usage (drift guard tokens.test.ts keeps passing).
- RDD native review approved + bound per slice.
# ODD Task: dashboard-hoy-chart-redesign

Status: in progress
Worktree: `/home/stefan/repos/lumat-agent-odd-dashboard-hoy-chart-redesign`
Branch: `odd/dashboard-hoy-chart-redesign`
Base: `f8a4bf20` (= `origin/main`, after PR #465)
Source: owner review (2026-10-02) against the **seeded** dev database.
Delivery strategy: `ask-on-risk`
Chain strategy: `stacked-to-main` (owner standing decision)
TDD: Strict TDD ON. Frontend `cd web && npm run test`. No backend change.

## Objective

Two things, one unit:

1. **Stop the HOY cards from breaking the page.** With real seeded volume (20 unanswered
   conversations, 9 urgent cases) the two metric cards render their *entire* list, the row
   stretches to the tallest card, and "Agenda de hoy" is dragged into a huge empty gap. The cards
   must show a **summary only**: at most **3 rows**, with more compact rows.
2. **Redesign the period row** ("Contactos por día" + "Motivos") to the new owner reference:
   y-axis with gridlines, header total, footers, and a **taller, shared height** for both cards.

## Why this unit exists

The `dashboard-chart-seed` unit seeded the dev DB with 30 days of demo data. That is what finally
exposed the overflow: `.dashboard__card-ops` is a grid with rows `auto / minmax(0,1fr) / auto` and
`.dashboard__list` has no `max-height`/`overflow`, so the row height is content-driven and unbounded.
Before the seed there were never enough rows to notice.

The chart legibility fix from that same unit was explicitly **not** a redesign — the owner now
judges it against real data and asks for the reference treatment.

## Scope

**In:**
- `web/src/components/pages/Dashboard.tsx`
- `web/src/components/pages/Dashboard.test.tsx`
- the `.dashboard*` rules in `web/src/components/primitives/primitives.css`

**Out:** `tokens.css` (read-only — reuse existing tokens), the shell, every other page, the
backend, the KPI row presentation, the shortcut icon colours, the app-wide `button { font: inherit }`
root cause. All still deferred.

## Target design (the owner reference)

### HOY cards — summary, not a dump

- Each of the three `.dashboard__card-ops` lists renders **at most its first 3 rows**. The count
  (metric value / head chip) still reflects the true total; the "Ver …" link remains the way to
  see everything.
- Rows are **more compact**: reduce `.dashboard__row` padding and vertical rhythm so three rows feel
  light. Keep the row click/navigation behaviour and the urgent row tone unchanged.
- No "+N más" indicator — not requested (YAGNI).

### "Contactos por día" (chart)

- Head: bar-chart icon + `Contactos por día`, and the total on the right
  (`{chartTotal} contactos · {bars.length} días`) — already exists, keep.
- Plot: a **numeric y-axis** on the left and **dashed horizontal gridlines** across the plot.
  - `axisMax = Math.max(maxBarCount + 1, 4)` (verified against the reference: max bar 2 → axis 4;
    max bar 3 → axis 4; max bar 4 → axis 5). Ticks are integers `0..axisMax`.
  - Bars scale to `axisMax`, not to the raw max: `pct = count / axisMax * 100` (keep the existing
    minimum sliver for non-zero counts).
  - Keep the current bar colours/radius (`--primary-300`, `--primary-700` peak, `--brand-forest`
    today) and the existing label thinning (`Math.ceil(N / 7)`; day labels and the value above the
    bar follow the same thinning).
  - Plot height **192px** (`calc(var(--space-8) * 6)`, double the previous 96px).
- Foot: hairline separator, then a calendar icon + `18 sep – 1 oct 2026` on the left and
  `Cada barra representa un día.` on the right. Range end = the last trend bucket's `start` (fall
  back to `today.local_date` when there are no buckets).
- Empty state (no non-zero bucket) is unchanged; the foot is hidden with it.

### "Motivos de contacto"

- Title `Motivos de contacto` (not just "Motivos") plus a muted subtitle `Ordenados por frecuencia`.
- Ranked rows: label left, count pill right. Row fill uses **`--brand-bg-elevated`** (a token),
  because the reference rows are a subtle sage fill — note `--surface-subtle` resolves to `--surface`
  and is invisible here.
- Foot: hairline separator, right-aligned `{chartTotal} contactos en el período`.
- The list is the flexible middle row: it scrolls when it overflows instead of growing the card.

### Height parity and height increase

- `.dashboard__period` stays a 2-col grid and relies on the grid default `align-items: stretch`, so
  both cards share the row height (do **not** reintroduce `align-items: start`).
- `.dashboard__chart` and `.dashboard__motivos` become 3-row grids (`auto / minmax(0,1fr) / auto`):
  head, flexible body, foot pinned to the bottom.
- `.dashboard__motivos-list` gets `min-height: 0` + `overflow-y: auto` and **drops its fixed
  max-height**, so the shared height is now driven by the taller (chart) card.

### Test-contract change (justified)

`Dashboard.test.tsx` asserts `.dashboard__motivo { background: var(--surface) }`. The redesign fills
the row, so that one assertion changes to `var(--brand-bg-elevated)` — still a design-system token,
so the contract keeps its meaning.

## Work units

### WU1 — HOY summary cap and compact rows
- Cap each HOY list at 3 rows in `Dashboard.tsx`; compact `.dashboard__row`.
- Update/extend tests: a list longer than 3 renders exactly 3 rows while the count keeps the total.

### WU2 — period row redesign
- Chart restructure (axis, gridlines, footer, taller plot, scale to `axisMax`).
- Motivos restructure (title/subtitle/footer/ranked fill).
- Height parity CSS.
- Update tests: motivos title/subtitle/footer, y-axis ticks, range footer; adjust the CSS-contract
  assertion; keep the label-thinning count (`6` days / `30` bars) intact.

## Checks

- `cd web && npm run test`
- `cd web && npx tsc -b --noEmit`
- `cd web && npm run build` ← the only real type check
- `git diff --check`

## Progress

- [x] Graph Check (Step 1) from `/home/stefan/repos/lumat-agent`: nodes consulted — `Dashboard()`,
      `Dashboard.tsx`, `periodStartLabel()`, `primitives.css`, `services/dashboard.py`, `AD-HOY-1`,
      `Chart / Motivos height parity` (129 nodes, communities `Dashboard.tsx` / `seed_demo.py`).
- [x] Worktree created and provisioned (`rapso worktree create dashboard-hoy-chart-redesign --yes`,
      `uv sync`, `cd web && npm ci`, `infra/.env` copied).
- [x] WU1 — HOY summary cap — commit `304a1acb` (`fix(dashboard): cap the HOY lists to a three-row
      summary`). Each list slices to 3; the metric value and head chip keep the true total.
- [x] WU2 — period row redesign — commit `b638406e` (`feat(dashboard): redesign the period chart and
      motivos cards`). Chart y-axis (`axisMax = max(max+1, 4)`) with dashed gridlines, bars scaled to
      `axisMax`, 192px plot, range + hint footer; Motivos retitled/subtitled/ranked with a footer;
      `grid-template-rows: auto minmax(0,1fr) auto` for equal, taller cards.
- [x] **Orchestrator correction `4d4ed9e0`** — the structural readback caught a real gap the writer's
      tests could not: removing the Motivos list `max-height` re-opened the unbounded-growth defect on
      that side (a long list would drive the row height). Re-capped it to
      `calc(var(--space-8) * 6 + var(--space-6))` (the chart body height) plus `align-content:start` on
      the chart body, so the row stays chart-driven and the list scrolls.
- [x] **Verification of record** — `npm run test` → **94 files / 953 tests passed**;
      `npx tsc -b --noEmit` → exit 0; `npm run build` → exit 0; `git diff --check` → clean. Re-run on
      the final candidate after the correction.
- [x] **Review measurement** — RDD `on (global)`; `review assess --base-ref f8a4bf20` → **medium**
      (244 changed lines, reason `under_budget`), `review_due: false`. The native transport remains
      unavailable in this runtime, so the writer's foreground verification is the verification of
      record. Owner visual review pending.
- [ ] Owner visual review on the seeded dashboard

## Carried gaps

- The owner judges the rendered chart/motivos against the reference; a visual correction round is the
  norm for this section (see the previous unit's lesson).
- Dropped the per-bar value label in favour of the y-axis (the reference omits it in the 7- and
  30-day views). Reversible if the owner disagrees.
- The `--surface-subtle`/`button { font: inherit }` root causes remain unowned and out of scope.

## Recovery

- Base `f8a4bf20`. `graphify-out/` is gitignored: query from `/home/stefan/repos/lumat-agent`.
- The findings ledger is on `main` (`odd/analysis/findings-ledger.md`).

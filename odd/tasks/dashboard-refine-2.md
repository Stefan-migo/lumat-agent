# ODD Task: dashboard-refine-2

Status: complete — PR #463, owner-approved except two items moved to the next unit
Worktree: `/home/stefan/repos/lumat-agent-odd-dashboard-refine-2`
Branch: `odd/dashboard-refine-2`
Base: `405f6af5` (= `origin/main`, after PRs #459–#462)
Source: the owner's post-implementation review of the merged dashboard (2026-10-01). This is a
correction round, not a new analysis — every item below is owner-observed on the rendered app.
Delivery strategy: `ask-on-risk`
Chain strategy: `stacked-to-main` (owner standing decision)
TDD: Strict TDD ON — frontend `cd web && npm run test`. **This round is frontend-only: no `app/`
change, so no test DB and no backend suite.**

## Objective

Fix the seven visual defects the owner found after the dashboard implementation merged, so the
dashboard actually matches the adjudicated references on desktop, tablet and mobile.

## Why this unit exists

The WU1–WU3 run implemented the ledger findings correctly at the level the analysis described, but
the analysis classified symptoms, not causes. The owner's review found: an HOY grid with the wrong
column ratios, a shortcuts grid with the wrong column count and a full-width `Automatizaciones`,
an undersized assistant glyph, **a font-family bug affecting every dashboard button**, hard grey
borders where the design system specifies a decorative hairline, invisible icon tiles, and a period
selector that renders as a raw native `<select>`.

## Root causes (verified in the code)

- **Font.** `<button>` does not inherit `font-family`. This repo patches every button by hand —
  `.btn` sets `font-family: var(--font-ui)` (`primitives.css:31`) and the shell buttons use
  `font: inherit` (`:1192`, `:1332`, `:1499`). The dashboard's `.dashboard__card`,
  `.dashboard__card-ops__link` and `.dashboard__row` set nothing, so the whole shortcuts/HOY
  section renders in the browser's default UI font instead of Inter.
- **Borders.** `.dashboard__card` and `.dashboard__row` use `--border-strong` (`#7e858f`), while
  every other dashboard container uses `--corp-border` = `--border` (`#d5dad1`), which the token
  itself documents as the *"decorative container hairline"*. The dashboard is internally
  inconsistent and the shortcuts are the ones with the hard outline.
- **Backgrounds.** All containers already use `var(--surface)` (`#e8ebe4`) — there is no real
  background divergence. What looks wrong is the border, plus the icon tiles using
  `--surface-subtle`, which resolves through `--table-head-bg` to **`--surface` itself** — i.e. the
  tiles are invisible on the card.
- **Icon size.** `--icon-md` is 20px inside a 64px tile; the reference's glyph is ~28–30px.

## Scope

**In:** the `.dashboard*` rules in `web/src/components/primitives/primitives.css`,
`web/src/components/pages/Dashboard.tsx` (markup only), `web/src/components/pages/Dashboard.test.tsx`.

**Out:** `app/` (no backend change this round); `tokens/tokens.css`; the shared
`primitives/Select.tsx`, `primitives/Icon.tsx` or `primitives.css` rules outside the `.dashboard*`
block; the shell; every other page; the findings ledger.

## The seven fixes

- **F1 — HOY grid.** Desktop is `repeat(3, 1fr)`: three equal columns. The reference is ~46%/24%/24%.
  → `minmax(0,1.9fr) minmax(0,1fr) minmax(0,1fr)`. At ≤63.99rem the grid drops to two equal columns
  without the agenda spanning, and at ≤48rem it collapses to one column — but the tablet AND mobile
  references both show the agenda on its own full row and "Sin respuesta" / "Urgentes" side by side.
  → two columns with the agenda spanning `1 / -1`; remove the ≤48rem single-column collapse.
- **F2 — shortcuts grid.** `.dashboard__grid` is `repeat(4, 1fr)` with the agent spanning 4, so five
  shortcuts can never fit one row; and `.dashboard__card--wide` is `grid-column: span 4`, which
  stretches **Automatizaciones** to full width exactly like the assistant banner — the owner's
  reported bug. → five columns on desktop and tablet; `--wide` loses its span there. The mobile
  reference does show the last card full width, so `--wide` keeps `span 2` at ≤48rem only.
- **F3 — assistant glyph.** Keep the 64px tile (it matches the reference) and size the glyph to
  ~1.75rem inside `.dashboard__card--agent .dashboard__card__icon`. Dashboard-scoped rule only —
  do not change the shared `Icon` primitive.
- **F4 — font family.** Add `font-family: var(--font-ui)` to `.dashboard__card`,
  `.dashboard__card-ops__link` and `.dashboard__row`. **Also report the root cause**: the reset has
  no global `button { font: inherit }`, which is why every button in this repo is patched one by
  one. The global fix is app-wide and is NOT in this unit's scope — flag it as a candidate.
- **F5 — borders.** `.dashboard__card`, `.dashboard__row` and `.dashboard__row--urgent` switch from
  `--border-strong` to `--corp-border`. `.dashboard__card:hover` currently turns the border
  near-black (`--chrome-950`) — soften it to an existing accent and flag the choice.
- **F6 — icon tiles.** `--surface-subtle` is a no-op for the tiles. Give them a real existing tint
  (`--brand-bg`, `#dde2d6`) and verify against the reference. Flag if the reference shows no tile.
- **F7 — period selector (visual).** It renders as a raw native `<select>`: `--border-strong`
  border, no chevron, native arrow. → `appearance: none`, `--corp-border` border, `--surface`
  background, `--radius-pill`, room for both icons, and a right-hand chevron `<Icon>` positioned
  symmetrically to the existing left calendar icon (add `ChevronDown` to the `ICONS` map in
  `Dashboard.tsx`). The accessible label stays sr-only, as today.

## Constraints

- Frontend only. No `app/` change → no test DB, no backend suite.
- Do NOT touch `tokens.css`, the shared primitives, the shell, or any other page.
- Do NOT modify the findings ledger or this file.
- No new dependency. UI copy stays neutral Chilean Spanish.
- **Honest testing position:** jsdom cannot assert computed styles or media queries, so the CSS
  fixes cannot be pinned by unit tests. Pin what IS pinnable — the markup (five shortcut cards, the
  period control's structure and options, the caption) — and say plainly in the report which fixes
  are machine-verified and which are visually verified by the owner. Do not invent brittle
  class-name assertions to look covered.

## Checks

- `cd web && npm run test`
- `cd web && npx tsc -b --noEmit`
- `cd web && npm run build` ← the only real type check
- `git diff --check`

## Progress

- [x] Graph Check (Step 1) from `/home/stefan/repos/lumat-agent`: `graphify query "dashboard panel
      section unified panel"` at plan time; nodes consulted `Dashboard()`, `Dashboard.tsx`,
      `primitives.css`, `PanelShell.tsx`, `panelRoutes.ts`, `useAsyncData()`, `getDashboardKpis()`,
      `getDashboardTrend()`. Community `Dashboard.tsx`. Report now current (graph refreshed at the
      close of the previous unit, 8676 nodes).
- [x] Worktree created and provisioned (`rapso worktree create dashboard-refine-2 --yes`, then
      `cd web && npm ci`). No venv needed — frontend only.
- [x] F1–F7 implemented (`e928b73a`, corrected by `75ba8c7b`)
- [x] A/B/D/E implemented (`4aed835b`, completed by `3a691492`)
- [x] verification recorded
- [x] review measurement

## Close

**Unit closed 2026-10-01.** Six commits on `odd/dashboard-refine-2`, one PR (#463), `stacked-to-main`.
The owner reviewed the rendered result against the three references and approved everything except the
two items moved to the next unit (below).

### Evidence

- `cd web && npm run test` → **94 files / 950 tests passed**; `npx tsc -b --noEmit` → exit 0;
  `npm run build` → exit 0; `git diff --check` → clean. Re-run by the orchestrator, not only by the writer.
- Native assessment over `405f6af5..HEAD` → risk `medium`, 267 changed lines, `review_due: false`.
- One defect the writer shipped and the orchestrator caught in diff review: `.dashboard__card--wide`
  kept `flex-direction: row` after losing its span, so Automatizaciones still rendered as a horizontal
  banner on desktop. Fixed in `75ba8c7b`.
- One scope boundary reproduced a known pattern twice: a changed string leaves stale assertions behind.
  The page-title change broke four assertions in `AppShell.test.tsx` / `Dashboard.stories.test.tsx` /
  `PanelEntry.stories.test.tsx`; the subtitle date change broke `Dashboard.stories.test.tsx:14`. Both
  times the writer stopped instead of widening scope silently, and the orchestrator widened it.

### Carried gaps (owner decisions on the record)

- **KPI row presentation deferred by the owner.** The app renders four separate KPI cards with coloured
  top borders; the reference shows one card with four columns and vertical dividers. Not fixed here.
- **Shortcut icon colours deferred by the owner.** The reference colours each shortcut glyph
  individually; the app uses a single ink colour.
- **The font root cause is app-wide.** There is no `button { font: inherit }` in the reset, which is why
  every button in the repository is patched by hand. Fixing it globally touches components outside this
  unit; it remains a separate candidate.

### Moved to the next unit (found by the owner while reviewing this one)

- **The chart breaks in the 30-day view.** `.dashboard__bars` is a flex row with `flex: 1` columns and a
  `--space-2` gap, so thirty columns leave no room for the three-letter day labels or the value above each
  bar; they collide. The 7-day reference is the only designed state.
- **The chart and the Motivos card do not share a height.** `.dashboard__period { align-items: start }`
  overrides the grid default; a longer Motivos list grows past the chart.

### What this unit proved

The owner's eye keeps finding what both the analysis and the machine checks miss: the analysis classified
symptoms (a wrong grid, a border) while the causes were a `<button>` font-inheritance gap, a token
(`--surface-subtle`) that resolves to the surface it is drawn on, and an `align-items` override. Two of
the seven fixes could not have been found without rendering the page — which is exactly why the CSS half
of this unit is verified by the owner and not by jsdom.

## Recovery

- Base `405f6af5`. PR #462 closed the previous unit; the previous worktree and branches are gone.
- `graphify-out/` is gitignored: query from `/home/stefan/repos/lumat-agent`.
- Dashboard findings are recorded in `odd/analysis/dashboard/findings.md`.

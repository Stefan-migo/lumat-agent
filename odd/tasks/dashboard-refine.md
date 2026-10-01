# ODD Task: dashboard-refine

Status: in progress
Worktree: `/home/stefan/repos/lumat-agent-odd-dashboard-refine`
Branch: `odd/dashboard-refine`
Base: `1c6e9595` (= `origin/main`)
Source: `odd/analysis/findings-ledger.md` on `main` (commits `c0d24805`, `74768739`) — the
dashboard section run of the `panel-section-analysis` machine.
Depends on: nothing.
Delivery strategy: `ask-on-risk`
Chain strategy: **pending owner decision** (forecast exceeds the ~400-line budget).
TDD: Strict TDD ON — frontend `cd web && npm run test`; backend `uv run pytest tests/`.

## Objective

Close the 12 validated dashboard findings from the shared findings ledger, so the panel
dashboard matches the owner's adjudicated reference across desktop, tablet and mobile.
This run doubles as the **acceptance test of the analysis itself**: every finding is one task,
and the owner compares the implemented result against the reference.

## Why this unit exists

The read-only `panel-section-analysis` run produced 12 validated rows (13 emitted, one
withdrawn by the owner) in ONE shared ledger. This is the first time that analysis is taken to
implementation, and its purpose is to judge the analysis quality before the machine runs over
the remaining six sections.

## Scope

**In:** `web/src/components/pages/Dashboard.tsx`, the `.dashboard*` rules in
`web/src/components/primitives/primitives.css`, `web/src/api.ts` (`getDashboardTrend`, and the
KPI window call), `app/panel/api/routes/dashboard.py`, their tests
(`web/src/components/pages/Dashboard.test.tsx`,
`web/src/stories/pages/Dashboard.stories.tsx`, `tests/functional/test_api_dashboard.py`),
and the spec deltas required by the owner decisions.

**Out:** the shell (`PanelShell.tsx`, `AppShell.tsx`, `panelRoutes.ts`) — no route changes;
the "Hoy" urgent-case rows, which stay on `navigate("cases")` per AD-HOY-1; `tokens.css`
values; any new dependency; any other section.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-dashboard-refine`
- Branch: `odd/dashboard-refine`
- Files: as listed in Scope.
- Reference images (read-only, from the PRIMARY worktree — `refs/` is gitignored and absent
  here): `/home/stefan/repos/lumat-agent/refs/Diseño Lumat/Dashboard.png`,
  `/home/stefan/repos/lumat-agent/refs/Diseño Lumat/mobileTablet/dashboardMobile.png`,
  `/home/stefan/repos/lumat-agent/refs/Diseño Lumat/mobileTablet/dashboardTablet.png`

## Constraints

- Strict TDD ON: observe RED before each production change; never invent RED.
- Frontend verification: `cd web && npm run test`, `cd web && npx tsc -b --noEmit`,
  `cd web && npm run build`. **`npm run build` is the only real type check** — a green Vitest
  run does NOT prove the tree type-checks.
- Backend verification (only if `app/` is touched): `bash infra/test-db.sh up`, then
  `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/`, then `bash infra/test-db.sh down`.
- Artifacts in English. Conventional Commits, no AI attribution. Merge commits, never squash.
  Exactly one `type:*` label per PR.
- UI copy stays neutral Chilean Spanish.
- Push, PR and merge require explicit owner authorization.
- Graph Check (Rapsodia Step 1) before each task; record consulted nodes in Progress.
- `graphify-out/` is stale (built from `71b9d8ec`); query from
  `/home/stefan/repos/lumat-agent`, treat the report as advisory.

## Owner decisions (2026-10-01) — binding

- **008** — label "Configuración" on desktop/tablet, "Config" on mobile.
- **013** — **withdrawn**. The tablet reference's "Chats" label is a design error: "Chats"
  belongs only in the mobile bottom nav. The dashboard shortcut stays "Conversaciones" on
  every breakpoint. No task.
- **007** — desktop has no heading above the shortcuts; mobile/tablet show "Accesos rápidos".
- **005** — assistant is a full-width banner with an "Abrir asistente →" action on
  desktop/tablet, and a card with a chevron on mobile.
- **010** — the "Últimos 7 días" selector **must be functional**: changing it changes the
  window and refetches.

## Findings → tasks

### WU1 — upstream (shared-primitive)

- [ ] **T1 (dashboard-004)** — the three "Hoy" ops cards get the reference footer links:
  "Ver agenda" → `navigate("agenda")`, "Ver conversaciones" → `navigate("conversations")`,
  "Ver casos" → `navigate("cases")`. Today each card body renders only its list/empty state.
- [ ] **T2 (dashboard-005)** — the assistant stops being a 2×2 grid tile
  (`.dashboard__card--agent` `grid-column:span 2; grid-row:span 2`) and becomes a full-width
  banner with an "Abrir asistente →" action on desktop/tablet; a card with a chevron on mobile.
- [ ] **T3 (dashboard-007)** — remove the "Atajos" heading on desktop; show "Accesos rápidos"
  on mobile/tablet. The heading treatment is breakpoint-specific.
- [ ] **T4 (dashboard-008)** — the shortcut set carries a settings entry in place of the
  reference's "Casos": "Configuración" (desktop/tablet) / "Config" (mobile), navigating to the
  existing `settings` view. Must NOT touch the "Hoy" urgent-case rows (AD-HOY-1).
- [ ] **T5 (dashboard-012)** — Motivos render as one row per reason with a trailing count badge,
  not inline chips (`label · count`).

### WU2 — local copy (`Dashboard.tsx`)

- [ ] **T6 (dashboard-001)** — page title becomes "Dashboard" (currently "Panel"; the reference's
  "Panel unificado" is also ruled out).
- [ ] **T7 (dashboard-002)** — the "Hoy" date chip capitalises the weekday ("Martes, 29 de
  septiembre"), currently lowercase from `Intl.DateTimeFormat("es-CL", { weekday: "long" })`.
- [ ] **T8 (dashboard-003)** — the agenda ops card title becomes "Agenda de hoy".
- [ ] **T9 (dashboard-006)** — the agent surface is labelled "Asistente Lumat", not "Agente Lumat".
- [ ] **T10 (dashboard-009)** — the activity heading becomes "Actividad del período", not "Período".
- [ ] **T11 (dashboard-011)** — the chart empty state adopts the reference copy: "Sin contactos
  en este período" + "La actividad aparecerá aquí cuando se registren contactos." (currently
  "Sin actividad registrada en el período", no supporting sentence).

### WU3 — functional period selector (dashboard-010)

- [ ] **T12** — the activity section gains the reference's period selector + "Desde el …"
  caption, and it is **functional**. `getDashboardTrend(timezone)` already takes explicit
  `start`/`end`, so the trend can follow the window from the client; `/panel/api/kpis` reads
  `kpi.window_days` from a setting (`app/panel/api/routes/dashboard.py:34`) and must accept the
  requested window so the KPI row and Motivos stay consistent with the selector. Touches
  `web/src/api.ts`, `Dashboard.tsx` and the backend route + its tests.

## Forecast

| Slice | Findings | Est. authored lines (code + tests) |
| --- | --- | --- |
| WU1 | 004, 005, 007, 008, 012 | ~230–300 |
| WU2 | 001, 002, 003, 006, 009, 011 | ~80–120 |
| WU3 | 010 (frontend + backend) | ~150–220 |

Total ≈ **460–640** authored lines, over the ~400 review-focus budget → `ask-on-risk` triggers
the chain-strategy decision before the slice that crosses it. Measure with
`git diff --stat <base>..HEAD` after each work unit; do not guess.

## Acceptance criteria

1. Every task T1–T12 is implemented and pinned by a test, or explicitly dropped with a reason.
2. The dashboard matches the owner's adjudicated reference on desktop, tablet and mobile for
   every finding above; nothing outside Scope changes.
3. The "Hoy" urgent-case rows still call `navigate("cases")` (AD-HOY-1 holds).
4. `cd web && npm run test`, `cd web && npx tsc -b --noEmit` and `cd web && npm run build` pass.
5. If `app/` is touched: `uv run pytest tests/` passes and the test DB is torn down after.
6. No new dependency; no `tokens.css` change.

## Checks

- `cd web && npm run test`
- `cd web && npx tsc -b --noEmit`
- `cd web && npm run build`
- `bash infra/test-db.sh up && eval "$(bash infra/test-db.sh env)" && uv run pytest tests/ && bash infra/test-db.sh down` (only if `app/` is touched)
- `git diff --check`

## Progress

- [x] Worktree created and provisioned (`rapso worktree create dashboard-refine --yes`, then
      `uv sync` and `cd web && npm ci` — `rapso worktree provision` alone does not install
      `web/node_modules` or the venv).
- [x] Graph Check (Step 1) at plan time, from `/home/stefan/repos/lumat-agent`:
      `graphify query "dashboard panel section unified panel"` (BFS depth=2, 320 nodes).
      Nodes consulted: `Dashboard()` (`web/src/components/pages/Dashboard.tsx:108`);
      `Dashboard.tsx`; `panelRoutes.ts`; `PanelShell.tsx`; `AppShell.tsx`;
      `PathForView()` (`panelRoutes.ts:46`); `PANEL_ROUTES` (`panelRoutes.ts:19`);
      `PanelView` (`PanelShell.tsx:30`); `useAsyncData()`; `getDashboardToday()` /
      `getDashboardTrend()` (`web/src/api.ts:200-201`); `motivoAccent()` (`Dashboard.tsx:58`);
      `dayLabel()` (`Dashboard.tsx:66`); `Dashboard.stories.tsx`; `Dashboard.test.tsx`.
      Communities: `Dashboard.tsx`, `AppShell.tsx`, `useAsyncData`. The graph report is built
      from `71b9d8ec` (advisory only; anchors verified by reading the files directly).

## Recovery

- Test DB (if used): `bash infra/test-db.sh up|down|env`, project
  `lumat-test-lumat-agent-odd-dashboard-refine`.
- `graphify-out/` is gitignored: query from `/home/stefan/repos/lumat-agent`.
- The findings ledger lives on `main` (`odd/analysis/findings-ledger.md`); this worktree is
  based on `1c6e9595` and carries the pre-analysis copy — read the ledger from the main
  worktree, never from here.
- Nothing to resume until the first work unit lands.

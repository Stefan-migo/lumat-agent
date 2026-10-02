# ODD Task: dashboard-refine

Status: complete — both slices merged (PRs #459, #461); findings ledger landed in PR #460
Worktree: `/home/stefan/repos/lumat-agent-odd-dashboard-refine`
Branch: `odd/dashboard-refine`
Base: `1c6e9595` (= `origin/main`)
Source: the dashboard findings record on `main` (commits `c0d24805`, `74768739`) — the
dashboard section run of the `panel-section-analysis` machine.
Depends on: nothing.
Delivery strategy: `ask-on-risk`
Chain strategy: `stacked-to-main` (owner decision 2026-10-01) — PR1 = the visual pass
(WU1 + WU2), PR2 = the functional period selector (WU3).
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

- [x] **T1 (dashboard-004)** — the three "Hoy" ops cards get the reference footer links:
  "Ver agenda" → `navigate("agenda")`, "Ver conversaciones" → `navigate("conversations")`,
  "Ver casos" → `navigate("cases")`. Today each card body renders only its list/empty state.
- [x] **T2 (dashboard-005)** — the assistant stops being a 2×2 grid tile
  (`.dashboard__card--agent` `grid-column:span 2; grid-row:span 2`) and becomes a full-width
  banner with an "Abrir asistente →" action on desktop/tablet; a card with a chevron on mobile.
- [x] **T3 (dashboard-007)** — remove the "Atajos" heading on desktop; show "Accesos rápidos"
  on mobile/tablet. The heading treatment is breakpoint-specific.
- [x] **T4 (dashboard-008)** — the shortcut set carries a settings entry in place of the
  reference's "Casos": "Configuración" (desktop/tablet) / "Config" (mobile), navigating to the
  existing `settings` view. Must NOT touch the "Hoy" urgent-case rows (AD-HOY-1).
- [x] **T5 (dashboard-012)** — Motivos render as one row per reason with a trailing count badge,
  not inline chips (`label · count`).

### WU2 — local copy (`Dashboard.tsx`)

- [x] **T6 (dashboard-001)** — page title becomes "Dashboard" (currently "Panel"; the reference's
  "Panel unificado" is also ruled out).
- [x] **T7 (dashboard-002)** — the "Hoy" date chip capitalises the weekday ("Martes, 29 de
  septiembre"), currently lowercase from `Intl.DateTimeFormat("es-CL", { weekday: "long" })`.
- [x] **T8 (dashboard-003)** — the agenda ops card title becomes "Agenda de hoy".
- [x] **T9 (dashboard-006)** — the agent surface is labelled "Asistente Lumat", not "Agente Lumat".
- [x] **T10 (dashboard-009)** — the activity heading becomes "Actividad del período", not "Período".
- [x] **T11 (dashboard-011)** — the chart empty state adopts the reference copy: "Sin contactos
  en este período" + "La actividad aparecerá aquí cuando se registren contactos." (currently
  "Sin actividad registrada en el período", no supporting sentence).

### WU3 — functional period selector (dashboard-010)

- [x] **T12** — the activity section gains the reference's period selector + "Desde el …"
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

### WU1 record

- [x] **WU1 implemented** — commit `9e0565d6` (`feat(dashboard): refine navigation and motive rows`),
      3 files, 76 insertions / 51 deletions: `Dashboard.tsx`, `Dashboard.test.tsx`,
      `primitives.css`. T1–T5 done; urgent-case rows still call `navigate("cases")` (AD-HOY-1 holds).
- [x] **WU1 verification of record** — `cd web && npm run test` → **94 files / 940 tests passed**;
      `npx tsc -b --noEmit` → exit 0; `npm run build` → exit 0 (pre-existing >500 kB chunk warning);
      `git diff --check` → clean.
- [x] **WU1 parent spot check** — the orchestrator re-ran `npm run build` → exit 0.
- [x] **WU1 independent verification** (required: the writer returned `partial`, having not observed
      RED independently for T3/T4) — fresh-context read-only verifier; all five claims CONFIRMED, no
      false claims, no scope violations, no weakened tests for T1/T5.
- [x] **WU1 native review measurement** — `gentle-ai review assess --base-ref 1c6e9595
      --committed-only` → `risk: medium`, 300 changed lines, `review_due: false`
      (`under_budget`). The reviewed boundary stays at `1c6e9595`.
- [x] **dashboard-006 applied early** — T2 rewrote the assistant JSX, so the "Asistente Lumat" label
      and its `aria-label` were corrected inside WU1 rather than left as "Agente Lumat" in rewritten
      code. WU2 keeps only its confirmation.
- [ ] **WU1 recorded gaps** — (a) T2/T3/T4 responsive behaviour is implemented in CSS media queries but
      is NOT pinned by viewport-sensitive tests; a regression would be silent. (b) Visual fidelity
      against the three reference images was NOT machine-verified — the independent verifier could not
      read them. The owner's own comparison is the instrument for this one.

### WU2 record

- [x] **WU2 implemented** — commit `ecd9e1a6` (`feat(dashboard): update local dashboard copy`),
      `Dashboard.tsx` + `Dashboard.test.tsx`. T6 title "Dashboard"; T7 date chip capitalised;
      T8 "Agenda de hoy"; T10 "Actividad del período"; T11 chart empty-state copy. T9
      ("Asistente Lumat") reported `already satisfied` from WU1. RED observed **per task** in
      isolation this time, with the failure output recorded in the writer's report.
- [x] **WU2 scope widened (orchestrator)** — the first WU2 commit left the suite red: four stale
      assertions still expected the old page heading "Panel" (`AppShell.test.tsx:98,488`;
      `Dashboard.stories.test.tsx:8`; `PanelEntry.stories.test.tsx:127`). The instruction's file
      boundary was too narrow; the title change is owner-mandated and correct (the shell breadcrumb
      already read "Panel › Dashboard", `PanelShell.tsx:571`). The three test files were added to
      the authorized scope and updated in commit `d9e7483f`
      (`test(dashboard): follow the renamed dashboard page title`). The shell's bottom-nav label
      "Panel" and the breadcrumb root were deliberately left alone.
- [x] **WU2 verification of record** — `cd web && npm run test` → **94 files / 945 tests passed**;
      `npx tsc -b --noEmit` → exit 0; `npm run build` → exit 0; `git diff --check` → clean.
- [x] **WU2 parent spot check** — the orchestrator re-ran `npm run test` → **94 files / 945 tests passed**.
- [x] **WU2 native review measurement** — `risk: medium`, 366 changed lines, `review_due: false`
      (`under_budget`). Boundary still `1c6e9595`.
- [ ] **WU1/WU2 visual verdict pending** — the owner must compare the rendered dashboard against the
      three reference images; this is the acceptance test of the analysis and the gate before WU3.

### WU2 record — recorded gaps

- The responsive behaviour of T2/T3/T4 remains unpinned by viewport-sensitive tests (carried from WU1).

### WU3 record

Branch `odd/dashboard-refine-wu3`, based on `origin/main` = `3d92ed88` (PR #459 merged).

- [x] **WU3 implemented** — commits `2bfc3bfc` (`feat(dashboard): accept requested KPI window`) and
      `78ec0d0e` (`feat(dashboard): add functional activity period selector`). 6 files,
      101 insertions / 16 deletions.
- [x] **Backend contract** — `GET /panel/api/kpis` accepts an optional `window_days` query parameter
      validated `ge=1, le=31` (the range the assistant tool declares,
      `app/chat/assistant/tools/registry.py:91`) and falls back to the `kpi.window_days` setting when
      absent. `compute_kpis` is reused unchanged. **The API shape changed — the PR body must say so.**
- [x] **Frontend** — the window lives in `Dashboard` state (default 7) and is passed to both the KPI and
      trend fetches; `api.ts` takes the window instead of hardcoding 7 days. **`useAsyncData` keys on
      `[attempt, enabled, refreshKey]`, not the fetch-callback identity** — the selected window is passed
      as `refreshKey`, which is what makes the change refetch.
- [x] **WU3 verification of record** — backend `uv run pytest tests/` → **1737 passed** (225.40s);
      frontend `npm run test` → **94 files / 946 tests passed**; `npx tsc -b --noEmit` → exit 0;
      `npm run build` → exit 0; `git diff --check` → clean; test DB torn down at the end.
- [x] **WU3 parent spot check** — frontend suite re-run → 94 files / 946 tests; `npm run build` → exit 0;
      focused backend `tests/functional/test_api_dashboard.py` over a fresh test DB → **25 passed**.
- [x] **WU3 native review measurement** — `risk: medium`, 117 changed lines, `review_due: false`
      (`under_budget`), base `3d92ed88`.
- [x] **Unblock** — the writer could not start the test DB: `infra/.env` is gitignored and absent from a
      fresh worktree. The orchestrator copied it from the primary checkout (setup, not a code edit);
      `rapso worktree create` does not do this.

### WU3 record — observations and assumptions to surface

- **Redundancy (deliberate, not resolved):** the page-header `meta` already states the window and its
  start date, so the new "Desde el …" caption repeats it. Both were kept because both were explicitly
  decided by the owner; the PR should surface it for a ruling.
- **`es-CL` renders September as "sept"**, while the reference shows "sep" ("Desde el 22 sep 2026").
  Cosmetic divergence from the reference; flagged, not silently "fixed".
- **Selector options 7 / 14 / 30 days are an assumption**, derived from the backend's `1..31` range.
  Trivially changeable if the owner wants a different set.
- The "Hoy" urgent-case rows still call `navigate("cases")` (AD-HOY-1 intact).

## Closure

**Unit closed 2026-10-01.** Both slices are on `main` through the `stacked-to-main` chain the owner
chose: PR #459 (`odd/dashboard-refine`, merge `3d92ed88`) carried WU1 + WU2, and PR #461
(`odd/dashboard-refine-wu3`, merge `f7f7d2c5`) carried WU3. The findings ledger landed separately in
PR #460 (merge `db8f4af0`).

All twelve tasks T1–T12 are delivered and pinned by tests. Final state on `main`:

- `cd web && npm run test` → 94 files / 946 tests passed; `cd web && npx tsc -b --noEmit` → exit 0;
  `cd web && npm run build` → exit 0; `git diff --check` → clean.
- `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/` → 1737 passed.
- AD-HOY-1 holds: the "Hoy" urgent-case rows still call `navigate("cases")`.
- No `tokens.css` change and no new dependency.

### Carried gaps (recorded, not silently dropped)

- The responsive behaviour of dashboard-005, dashboard-007 and dashboard-008 is CSS-only and is not
  pinned by viewport-sensitive tests.
- Visual fidelity was verified by the owner against the three reference images, not by a machine check.
- The activity caption duplicates the page-header `meta`'s window text; `es-CL` renders September as
  "sept" against the reference's "sep"; the selector's 7/14/30 options are an assumption over the
  backend's `1..31` range.

### What this unit proved about the analysis machine

The dashboard analysis was **11 of 12 accurate** — the only wrong row was the subtitle, and it was an
interpretation error, not an invented finding. The machine's weak points surfaced during execution, not
during validation: the validator gate is mechanical (it caught inflated fix scope but passed a
semantically inverted row and a bundled row), and the analyst's first pass was materially incomplete
until the orchestrator sent it back with concrete gaps. Both are candidates for hardening the skill
before the remaining six sections run.

## Recovery

- Test DB (if used): `bash infra/test-db.sh up|down|env`, project
  `lumat-test-lumat-agent-odd-dashboard-refine`.
- `graphify-out/` is gitignored: query from `/home/stefan/repos/lumat-agent`.
- Dashboard findings live on `main` (`odd/analysis/dashboard/findings.md`); this worktree is
  based on `1c6e9595` and carries the pre-analysis copy — read the ledger from the main
  worktree, never from here.
- Nothing to resume until the first work unit lands.

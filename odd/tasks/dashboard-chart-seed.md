# ODD Task: dashboard-chart-seed

Status: complete — PR pending, owner judges the chart with seeded data
Worktree: `/home/stefan/repos/lumat-agent-odd-dashboard-chart-seed`
Branch: `odd/dashboard-chart-seed`
Base: `53fef85f` (= `origin/main`, after PR #463)
Source: the owner's review of the merged dashboard (2026-10-01). Everything else was approved; these
three items came out of that same review.
Delivery strategy: `ask-on-risk`
Chain strategy: `stacked-to-main` (owner standing decision)
TDD: Strict TDD ON. Frontend `cd web && npm run test`; backend `bash infra/test-db.sh up` +
`eval "$(bash infra/test-db.sh env)" && uv run pytest tests/` + `down`.

## Objective

Make the "Contactos por día" chart **observable and correct**: give the dev environment real data to
look at, fix the 30-day view that currently breaks, and make the chart and the Motivos card share a
height.

## Why this unit exists

After the visual corrections merged, the owner tried to evaluate the chart and hit three walls:

1. **There is no data to look at.** The dev database has almost nothing, so the chart renders empty and
   the "is this design right?" question cannot be answered for the 7-, 14- and 30-day windows. No demo
   seeder exists in the repository (`app/panel/seed_admin.py` only creates the admin account).
2. **The 30-day view is broken.** `.dashboard__bars` is `display:flex` with `gap:var(--space-2)` and
   every `.dashboard__bar-col` at `flex:1`. At 7 buckets that is comfortable; at 30 the columns leave no
   room for the three-letter day label (`.dashboard__bar-col__day`) or the value above each bar
   (`.dashboard__bar-col__value`), and the labels collide into one unreadable line. The 7-day reference
   is the only state the design covers.
3. **The chart and Motivos do not match heights.** `.dashboard__period { align-items: start }` overrides
   the grid default, so each card takes its own height and a longer Motivos list grows past the chart.

## Root causes (verified)

- `.dashboard__period { align-items:start }` — `primitives.css`. The grid default is `stretch`; the
  override is what breaks parity.
- `.dashboard__bars`, `.dashboard__bar-col`, `.dashboard__bar-col__day`,
  `.dashboard__bar-col__value` — `primitives.css`. No label thinning and no gap adaptation for long
  ranges; the label is always rendered per bucket.
- No demo-data entry point anywhere in `app/`, `scripts/` or `infra/`.

## The decided approach for the heights (owner asked for the correct one)

`align-items: stretch` so both cards share the row height — **and** a bounded scroll on the Motivos
list (`.dashboard__motivos-list { max-height: …; overflow: auto }`). Stretching alone is not enough:
without a cap, a long list would stretch the row and drag the chart to an absurd height. Stretch plus a
cap on the unbounded list is the combination that stays even and stays sane.

## Scope

**In:**
- `app/panel/seed_demo.py` (new) — a dev-only, idempotent demo seeder.
- the `.dashboard*` rules in `web/src/components/primitives/primitives.css`.
- `web/src/components/pages/Dashboard.tsx` (label thinning only) and
  `web/src/components/pages/Dashboard.test.tsx`.

**Out:** `db/seed.sh` and any deploy path — demo data must never reach a deploy; `tokens.css`; the
shared primitives; the shell; every other page; the findings ledger; the KPI row and the shortcut icon
colours (still deferred by the owner).

## Slices

### WU1 — the demo seeder

Add `app/panel/seed_demo.py`, modelled on `app/panel/seed_admin.py` (standalone, runnable as
`python app/panel/seed_demo.py`, `Session` via `app.db.session_scope`, commits its own transaction).

It must produce, spread across the **last 30 days**, enough data that the dashboard is genuinely
populated in every window:

- customers and conversations with inbound messages on many different days, so `contacts` and the
  **trend buckets** are non-zero in the 7-, 14- and 30-day views;
- cases across several `service` values (including the `visita` service the KPI counts) created on
  different days, so `motivos` and `visit_requests` are non-empty;
- some cases with `escalated_at` set, so `derived` is non-zero;
- for the HOY projection: appointments today, at least one unanswered conversation, and at least one
  urgent open case.

Read `app/services/dashboard.py` (`compute_kpis` and `today_projection`) FIRST and make the data satisfy
exactly the predicates those functions count — do not guess the semantics from the field names.

**Safety, non-negotiable:**
- **Dev-only by construction.** Refuse to run unless the resolved database host is local
  (`localhost`/`127.0.0.1`) or an explicit override flag is passed; print why it refused.
- **Idempotent.** Running it twice must not duplicate rows. Use a recognizable marker (a reserved
  customer phone/email prefix, for example) and make the script replace its own previous rows rather
  than blind-inserting.
- **Self-contained.** It must not weaken or bypass any application rule (no direct status hacks that
  the serializers would choke on).
- Document the usage and the safety rule in the module docstring, in the style of `seed_admin.py`.

**Prove it against the test database**, not only by reading: bring up the test DB, run the seeder
against it, call `compute_kpis` for 7 / 14 / 30 days and assert every KPI is non-zero, then tear the DB
down. Add that as a test (e.g. `tests/functional/test_seed_demo.py`) so the seeder cannot silently rot.

### WU2 — the chart fixes

- **Label thinning for long ranges.** With N buckets, render the day label (and the value above the bar)
  only every `ceil(N / 7)`-th bucket, so a 30-day view carries about seven readable labels instead of
  thirty colliding ones. Keep every bar. Decide and report whether the value above the bar follows the
  same thinning.
- **Height parity.** `.dashboard__period` stretches (drop the `start` override) and the Motivos list gets
  a bounded scroll as described above.
- Keep it a **legibility fix, not a redesign** — the owner will judge the result and may ask for a
  redesign afterwards. Do not change the chart's visual language (bar colours, radii, the head row).

## Constraints

- Artifacts in English. Conventional Commits, no AI attribution. Merge commits, never squash. Exactly one
  `type:*` label per PR. Push, PR and merge are the orchestrator's call under the owner's standing
  authorization.
- No new dependency.
- The "Hoy" urgent-case rows keep `navigate("cases")` (AD-HOY-1).
- UI copy stays neutral Chilean Spanish.

## Checks

- `cd web && npm run test`
- `cd web && npx tsc -b --noEmit`
- `cd web && npm run build` ← the only real type check
- `bash infra/test-db.sh up && eval "$(bash infra/test-db.sh env)" && uv run pytest tests/ && bash infra/test-db.sh down`
- `git diff --check`

## Progress

- [x] Graph Check (Step 1) from `/home/stefan/repos/lumat-agent`: nodes consulted across the previous
      units — `Dashboard()`, `Dashboard.tsx`, `primitives.css`, `compute_kpis()`, `today_projection()`,
      `seed_admin()`, `session_scope()`. Report current (8676 nodes, refreshed at the previous unit's
      close).
- [x] Worktree created and provisioned (`rapso worktree create dashboard-chart-seed --yes`, `uv sync`,
      `cd web && npm ci`, `infra/.env` copied from the primary checkout — a fresh worktree does not get
      the gitignored env file).
- [ ] WU1 — demo seeder
- [ ] WU2 — chart fixes
- [ ] verification recorded
- [ ] review measurement

### WU1 record — the demo seeder

- [x] `app/panel/seed_demo.py` + `tests/functional/test_seed_demo.py` — commit `d8de4e78`. Spreads 30
      days of customers, conversations, inbound messages and cases so `contacts`, the trend buckets,
      `motivos`, `derived` and `visit_requests` are non-zero, plus the three HOY projections.
- [x] **Correction `9c041222` — the orchestrator's spot check caught a blocking defect the writer's own
      test could not.** The functional test passed because it builds the environment dict itself, but the
      script was **not runnable at all**: `app/config.py:31` sets `env_file=None`, so nothing loads
      `infra/.env` and a host run died with five missing settings (`app_secret`, `verify_token`,
      `meta_access_token`, `meta_phone_number_id`, `panel_session_secret`); and the "host must be local"
      guard **refused the intended target**, because the dev database lives on the compose service `db`.
      Replaced with an explicit opt-in (`--yes` / `LUMAT_DEMO_SEED=1`) plus a redacted target-url print,
      and the docstring now documents the real invocation.
- [x] **WU1 verification of record** — backend suite **1738 passed**; two opt-in runs against the test DB
      produced the same summary line (idempotent); the inert run exits 1 with the refusal message.
- [x] **How the user actually runs it.** The `infra-api-1` container bind-mounts the repository
      (`- ..:/app`, `working_dir: /app`), so once this lands on `main` the seeder is visible inside it with
      no rebuild: `docker compose exec api python app/panel/seed_demo.py --yes`. The dev database
      (`infra-db-1`) publishes **no host port**, so the container is the only route.

### WU2 record — the chart fixes

- [x] `3e8eb089` — commit `fix(dashboard): keep long-range chart labels readable and level the period
      cards`. Day labels and the value above each bar are thinned to every `ceil(N / 7)`-th bucket, so a
      30-day view carries six readable labels instead of thirty colliding ones; **every bar still
      renders**, and the 7-day view is unchanged because its interval is 1.
- [x] **Height parity** — `.dashboard__period` no longer overrides the grid default, so both cards
      stretch; `.dashboard__motivos-list` is capped at `calc(var(--space-8) * 3)` (96px, the chart plot's
      own height) with `overflow-y: auto`, so a long list cannot stretch the row.
- [x] **WU2 verification of record** — `cd web && npm run test` → **94 files / 951 tests passed**;
      `npx tsc -b --noEmit` → exit 0; `npm run build` → exit 0; `git diff --check` → clean. RED observed
      for the thinning test (`expected length 6, got 30`). The CSS height rules remain owner-verified.

### Carried gaps

- **This is a legibility fix, not a redesign.** The owner judges the 30-day view with real data and may
  ask for a redesign as its own unit.
- The documented `docker compose exec api …` invocation was **not exercised** — the file has to be on
  `main` for the bind mount to see it, so that step happens after merge. The equivalent repo-root form
  was verified against the isolated test database.
- Deferred by the owner from the previous unit and still open: the KPI row presentation, the shortcut
  icon colours, and the app-wide `button { font: inherit }` root cause.

## Recovery

- Base `53fef85f`. The previous unit's worktree and branches are gone.
- `graphify-out/` is gitignored: query from `/home/stefan/repos/lumat-agent`.
- The findings ledger is on `main` (`odd/analysis/findings-ledger.md`).

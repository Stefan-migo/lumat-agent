# ODD: panel-kpi-null

## Objective

Stop a single `NULL` case service from taking the whole admin panel down with a blank screen, by
removing the null from the KPI payload at the source and hardening the one frontend consumer that
crashes on it.

## Problem

Verified against `main` at `77961c29`, reproduced in production with a real session.

- A conversation classified as unknown intent twice escalates, and the escalated case is created
  with `Case.service = NULL` (`app/models.py:334`; the column is nullable).
- `app/services/dashboard.py:45-50` groups by `Case.service` and `:64` emits it raw as
  `[(service, count)]`. With one such case the KPI becomes `{"motivos": [[null, 1]]}`, confirmed live
  against `GET /panel/api/kpis` on the production VPS.
- `web/src/components/pages/Dashboard.tsx:47-51` `motivoAccent(motivo)` loops `motivo.length` with no
  guard, and `:217-218` feeds it straight from the map, so the null throws
  `TypeError: Cannot read properties of null (reading 'length')`.
- There is no `ErrorBoundary` anywhere in the SPA, so that one throw blanks the entire panel.
  Captured with Chrome headless over CDP against the deployed bundle:
  `at V0 (index-D627JZez.js:52:24284)`, called from an `Array.map` in `X0`; the decompiled body of
  `V0` is the `motivoAccent` hash loop.

**This is not a deploy regression.** `git diff cfbefcbd..77961c29 -- web/src` adds no `.length`, so no
release introduced it: it is a latent defect that the first real production data uncovered. It
reached production because the `docs/ops.md` §2.1.2 panel smoke checklist was skipped in `v2026.09.3`.

The contract breach is explicit, not implicit: `web/src/types.ts:168` already declares
`motivos: Array<[string, number]>`. The API violated the type it publishes.

## Scope

**In:** `app/services/dashboard.py` (the `coalesce` in the select and the `group_by`),
`web/src/components/pages/Dashboard.tsx` (the null-safe accent helper, the label fallback, the chip),
`tests/functional/test_api_dashboard.py` (a case whose service is `NULL`),
`web/src/components/pages/Dashboard.test.tsx` (a payload that still carries `null`),
`odd/tasks/panel-kpi-null.md` (this record).

**Out:** any `ErrorBoundary` for the SPA — recorded below as follow-up debt, not done here. Also out:
the escalation/classification path that creates a null service, any schema or migration (the column
stays nullable), `web/src/types.ts` (the type is already correct), any new dependency, and the
`dashboard__chip` styling.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-panel-kpi-null`
- Branch: `odd/panel-kpi-null`
- Base: `77961c29`
- Files: `odd/tasks/panel-kpi-null.md`, `app/services/dashboard.py`,
  `web/src/components/pages/Dashboard.tsx`, `tests/functional/test_api_dashboard.py`,
  `web/src/components/pages/Dashboard.test.tsx`

## Constraints

- **Strict TDD: ON** — `openspec/config.yaml` (`testing.strict_tdd: true`), pytest runner. Observe RED
  before each source change, then GREEN. The frontend half is guarded by Vitest
  (`cd web && npm run test`), also RED first.
- Backend tests need the derived test database: `./infra/test-db.sh up` then
  `eval "$(./infra/test-db.sh env)"` before `uv run pytest`. Tear it down with `./infra/test-db.sh down`.
- Artifacts in English; UI copy stays the panel's existing Spanish register. Conventional commits, no
  AI attribution. No `Co-Authored-By`.
- RDD is **OFF in this clone** (explicit earlier decision): there is no native review. Use an
  independent read-only verifier instead, as was done for `odd/prod-embedder-cache`.
- Work one concern per commit, ≤5 files.

## Decisions

- **D1 — Fix the null at the source, with `func.coalesce(Case.service, "sin clasificar")`, in both the
  `select` and the `group_by`.** A nullable column is not a reason to hand a null to a consumer that
  declared `string`; the aggregate is where the unknown service becomes a named bucket. Coalescing in
  the group key (not in Python after the fact) keeps the counts correct: two null rows stay one group.
  - **`service IS NULL` left as its own bucket was rejected.** It keeps the null on the wire and only
    moves the crash to whoever renders it next.
  - **Not nulling in `to_case_dict`/serializers was rejected.** The KPI aggregate is the surface that
    broke; the serializer is a different contract.
  - **Backfilling `NULL` services in the database was rejected.** It is out of scope, cannot be done
    without a migration, and the panel must survive an unknown service regardless of history.
- **D2 — Guard the frontend too, even though the backend now guarantees a string.** The wire is a trust
  boundary: `motivos` arrives as parsed JSON, so the TS type is an assertion about the server, not a
  runtime check. One unvalidated field blanked the entire SPA because there is no `ErrorBoundary`; the
  guard is the cheap half of that defence and is what makes the panel survive the next unknown shape.
  The fallback label is `sin clasificar`, matching the backend bucket, so a residual null renders a
  readable chip instead of crashing.
  - **The guard is deliberately shallow.** It covers the two places this field is used (the hash and
    the chip text), not a general payload validator — that would be an unrequested abstraction, and the
    `ErrorBoundary` follow-up is the real structural answer.
- **D3 — The frontend test feeds a literal `null`, behind a documented cast.** `types.ts:168` already
  says `string`, so a conforming test could never reproduce the production crash. The cast is the
  point: it encodes "the server can and did send this" at the boundary where the type cannot help, and
  documents why the guard exists at all.
- **D4 — Follow-up debt, recorded not fixed:** there is no `ErrorBoundary` in the SPA, so any future
  render-time throw blanks the whole panel again. That deserves its own unit; it is named here so it
  cannot rot.

## Tasks

- [x] **T1** — RED (backend): extend `tests/functional/test_api_dashboard.py` with a case whose
  `service` is `NULL` and assert the KPI publishes a named bucket with the right count. Follow the
  file's existing seed/fixture shape. Watch it fail on `[null, 1]`.
- [x] **T2** — GREEN (backend): `func.coalesce(Case.service, "sin clasificar")` in the select and the
  `group_by` of `app/services/dashboard.py`. T1 passes; no other KPI value changes.
- [x] **T3** — RED (frontend): extend `web/src/components/pages/Dashboard.test.tsx` with a `motivos`
  payload containing `null` (via the D3 cast) and assert the panel still renders. Watch it fail.
- [x] **T4** — GREEN (frontend): make `motivoAccent` null-safe and give the chip the fallback label in
  `web/src/components/pages/Dashboard.tsx`. T3 passes.
- [x] **T5** — Verification: full `uv run pytest tests/`, `cd web && npm run test`,
  `npx tsc -b --noEmit`, `npm run build`.

## Acceptance criteria

1. A case with `service = NULL` produces a KPI `motivos` entry with the string label `sin clasificar`
   and the correct count — never `null`.
2. `motivoAccent` cannot throw on a `null` motivo, and a residual null renders as a readable chip
   instead of blanking the panel.
3. The existing KPI assertions (`calefont=2, visita=1`, ordering by count then service, empty payload
   → `[]`, no-data-zero counts) are unchanged.
4. `uv run pytest tests/`, `cd web && npm run test`, `npx tsc -b --noEmit` and `npm run build` pass.
5. Only the authorized files change.
6. The missing SPA `ErrorBoundary` remains recorded as follow-up debt rather than silently in scope.

## Checks

- `./infra/test-db.sh up && eval "$(./infra/test-db.sh env)" && uv run pytest tests/`
- `cd web && npm run test`
- `cd web && npx tsc -b --noEmit`
- `cd web && npm run build`
- `git status --short` / `git diff --check`

## Follow-ups (recorded, NOT in scope)

Found by the independent verifier over the delivered diff, deliberately not fixed here. They are the
same latent class — a nullable `Case.service` reaching a consumer that assumes a string — on different
surfaces; folding them into this unit would be a scope change only the human can authorize.

- **F1 — two other endpoints still publish a nullable `service`.** `app/panel/api/serializers.py:151-168`
  (`to_case_dict`) and `:252-260` (today's cases) emit the raw column, while `web/src/types.ts:228-236`
  and `:295-311` declare it as a non-null `string`. Today the consumers degrade quietly instead of
  crashing: `web/src/components/pages/ClientFicha.tsx:116-122` and
  `web/src/components/pages/ConversationThread.tsx:46-50` render the value directly, so a null shows as
  a blank field. It is a contract mismatch, not the white screen — and it is one unguarded `.length`
  away from being this same bug again.
- **F2 — no `ErrorBoundary` in the SPA.** Confirmed by search: no `componentDidCatch`, no
  `ErrorBoundary`, no `errorElement` anywhere under `web/src`. Any future render-time throw blanks the
  whole panel exactly as this one did. This is D4, restated as a finding so it cannot rot.
- **N1 — accepted, not fixed.** The null bucket now shares the label `sin clasificar` with any real
  service literally named that: the two rows would merge into one bucket and share a React `key` (a
  console warning, not a crash). A real service carrying that literal means the same thing, and
  disambiguating it needs a sentinel or a reserved representation — representation churn with no
  observable behaviour change. Both risks are accepted.

## Progress

- [x] Created this ODD record before the first source change.
- [x] Worktree created (`rapso worktree create panel-kpi-null --yes`); `uv sync --frozen` and
  `cp ../lumat-agent/infra/.env infra/.env` done.
- [x] Graph Check (Step 1): `graphify query "panel dashboard KPI motivos case service"` returned
  `services/dashboard.py`, `Dashboard.tsx`, `Case` (`app/models.py:334`), `serializers.py` and
  `test_api_dashboard.py`; `graphify path "compute_kpis" "motivoAccent"` returns no directed path (the
  provider/consumer edge runs through the HTTP boundary, which the graph does not model).
- T1 RED: `eval "$(./infra/test-db.sh env)" && uv run pytest tests/functional/test_api_dashboard.py` —
  failed at `test_kpis_names_null_service_bucket`: expected `["sin clasificar", 1]`, observed `[[null, 1]]`.
- T2 GREEN: `eval "$(./infra/test-db.sh env)" && uv run pytest tests/functional/test_api_dashboard.py` —
  `22 passed`.
- Backend work-unit commit: `be65e6a1` (`fix(panel): bucket NULL case services as sin clasificar`).
- T3 RED: `cd web && npm run test -- --run src/components/pages/Dashboard.test.tsx` — failed at
  `Dashboard operational surface > renders a readable fallback when the API sends a null motivo` with
  `TypeError: Cannot read properties of null (reading 'length')` at `Dashboard.tsx:49:30`.
- T4 GREEN: `cd web && npm run test -- --run src/components/pages/Dashboard.test.tsx` — `1 passed`,
  `7 passed`; existing React `act(...)` warnings remain.
- T5 verification: `eval "$(./infra/test-db.sh env)" && uv run pytest tests/` — `1304 passed`, `2 warnings`.
- T5 verification: `cd web && npm run test` — `79 passed`, `619 passed`; existing React `act(...)` and
  jsdom navigation warnings remain.
- T5 verification: `cd web && npx tsc -b --noEmit` — passed with no output.
- T5 verification: `cd web && npm run build` — passed; Vite transformed 332 modules and emitted the
  production bundle, with the existing chunk-size warning.
- Independent verification (read-only `explore` agent, fresh context, over the diff against
  `77961c29`): confirmed the coalesce removes the null without changing any other KPI, that both new
  tests genuinely fail pre-fix, that the guard covers every `motivo` use in the component, and that no
  other file in the diff is outside the authorized list. It reported `blocked` on execution — no shell
  in its sandbox — so its numbers are read-only claims, not observed runs. It produced F1, F2 and N1.
- Parent re-run of the deciding evidence, after reverting the stray `uv.lock`: `uv run --frozen pytest
  tests/` → exit 0 with **1304 tests and no failure marker in the progress output** (this environment
  did not print pytest's trailing summary line when stdout was redirected, so the count is read from
  the progress rows — 18×72+8 — and the zero exit code). `cd web && npm run test` → **79 files, 619
  passed**. `npx tsc -b --noEmit` → exit 0. Focused spot check: 22 backend tests, 7 frontend tests.
- Corrected writer artifact: the first `uv run pytest` (without `--frozen`) rewrote `uv.lock`
  (`lumatagent` 2026.9.2 → 2026.9.3), because `pyproject.toml` was bumped at `77961c29` without a lock
  refresh. It was reported as a pre-existing change; it was not — `main`'s tree is clean. Reverted, and
  every later run uses `uv run --frozen`.

## Recovery

- Worktree: `/home/stefan/repos/lumat-agent-odd-panel-kpi-null`, branch `odd/panel-kpi-null`.
- On resume: read this file and reconcile the checkbox state against `git log`.
- Original isolation evidence (production repro, CDP transcript, fix scope) lives in Engram
  `handoff/panel-white-screen`.

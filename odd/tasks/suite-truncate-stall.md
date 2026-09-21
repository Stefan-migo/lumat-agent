# ODD: suite-truncate-stall

**Branch**: `odd/suite-truncate-stall`
**Worktree**: `../lumat-agent-odd-suite-truncate-stall`
**Base**: `8ad0e026` (= `origin/main`, includes PR #272)
**Seeded from**: the CI evidence gathered while delivering `odd/versioning-release-process` (PR #273)
**Status**: scoped — not started

## Objective

Make the test suite reliable enough that CI is a trustworthy gate. Today the workflow works and the
suite is what fails: on the GitHub runner the full suite dies by the 120 s `pytest-timeout` ceiling
inside `clean_db`'s TRUNCATE, roughly two runs out of three, on code that is not the cause.

The deliverable is not "CI is green once" — it is "the stall is understood at its root and gone".

## Problem (measured, not assumed)

- **Three CI runs on PR #273**, same workflow, near-identical commits: run 1 **failed**, a re-run of
  the same commit **passed** (`1046 passed, 2 warnings in 84.57s`), the next commit **failed again**.
  Roughly 2 of 3.
- **Where:** `pytest-timeout` fires at 120 s with the main thread inside
  `tests/functional/conftest.py:87` → `clean_db` → `conn.execute(TRUNCATE ...)` → psycopg waiting on
  the socket. It happens after ~145 tests pass, at the first heavy database use.
- **It is pre-existing.** `pyproject.toml` documents it: *"the suite stalls intermittently, unrelated
  to the code under test"* — and that comment is the reason the 120 s ceiling and
  `timeout_method = "thread"` exist at all. CI did not create the stall; it made it visible.
- **It presents as a lock wait, not as slowness.** 120 s of zero progress, once. Not a slow machine:
  the same suite finishes in 85–110 s when it does not stall.

## Refuted hypotheses — do not spend time re-testing these

1. **Missing tmpfs / slow disk.** The runner's `docker create` line includes
   `--tmpfs /var/lib/postgresql/data`; the option is applied. Disk speed is not the mechanism.
2. **Small `/dev/shm`** (the classic Postgres-in-Docker trap). It is 64 MB both on the runner and
   locally, and locally the full suite passes repeatedly against a container created with the very
   same flags (89 s and 107 s).
3. **The CI environment contract** (`TEST_DB_PORT`, `TEST_POSTGRES_PASSWORD`, `TEST_ADMIN_DB_URL`).
   Verified separately and working; without `TEST_ADMIN_DB_URL` the failure is a loud 808-error
   credential failure, not a hang.
4. **The `1046` vs `1044` test-count gap.** Explained: `pull_request` checks run the merge with
   `main`, and `main` gained 2 tests in PR #272. Not a symptom of anything.

## The question to answer

Which connection holds what lock (or otherwise blocks) that the first heavy `clean_db` TRUNCATE waits
on — and why is it timing-dependent rather than deterministic?

## Approach

1. **Instrument rather than guess.** On a throwaway branch, run the suite with a sampler alongside it
   that captures `pg_stat_activity` (including `wait_event_type`, `state`, `query`), `pg_locks`, and
   `pg_blocking_pids()` once per second while pytest runs, and upload the sample as a workflow
   artifact. The stall is a lock wait, so the blocking session is observable during the freeze; the
   artifact survives the ephemeral runner, unlike the container.
2. **Bisect if the sample is inconclusive.** Run directory prefixes (`tests/functional`, then
   `tests/functional/<file>`…) to find the last test that completes before the block, then inspect
   what that path leaves open: session-scoped fixtures, connections from `TestClient` lifespan sweeps
   (`app/main.py` runs four startup sweeps, all of them touching the database), and the SQLAlchemy
   pool's idle-in-transaction behaviour.
3. **Fix the root cause in the tests.** Whatever the culprit is, the fix belongs where the leak is.

## Constraints

- **No papering over it.** No retry wrapper around pytest, no silent re-run, no removing the 120 s
  ceiling or switching `timeout_method`. That ceiling is the diagnosis; hiding a stall converts a
  visible defect into an invisible one.
- **Do not buy speed with coverage.** Truncating fewer tables, skipping suites, or shrinking the reset
  to make the window smaller is not a fix.
- **Application behaviour stays untouched.** If the root cause turns out to live in app code (for
  example a startup sweep that leaks a transaction), stop and bring that finding back before changing
  it — it is a different risk class.

## Out of scope

- The versioning and release work (PR #273) — delivered separately.
- Making the suite faster for its own sake.
- CI for `web/` (vitest + playwright); "the suite" here means pytest.

## Acceptance criteria

1. The blocker is identified **with evidence** — the blocking PID/query and the session holding it,
   captured live — not as another hypothesis.
2. **N ≥ 5 consecutive full local runs** with zero stalls, counts reported.
3. **Consecutive green CI runs on the same commit**, not one lucky green.
4. The 120 s `pytest-timeout` ceiling and `timeout_method = "thread"` remain in place.

## Checks

```bash
export PATH="$HOME/.local/bin:$PATH"
eval "$(infra/test-db.sh env)"
uv run pytest tests/
```

`pyproject.toml` sets `addopts = "-q"` — do not add a second `-q`. No linter, type checker, or
formatter exists; the tests are the verification.

## Progress

- [x] Worktree created and provisioned (base `8ad0e026`, `infra/.env` copied, `.opencode` noise removed).
- [ ] Reproduce or capture the block with live database evidence.
- [ ] Identify the holder and fix it at the root.
- [ ] Five consecutive clean runs; then CI.

## Notes for the executor

- The stall is **intermittent**: it will not necessarily reproduce on demand. Budget for repeated runs,
  and prefer capturing evidence while it happens over trying to make it happen.
- Anything that needs a push to `Stefan-migo/lumat-agent` is a remote operation: ask the human first,
  every time. The pushed-artifact idea (a workflow that uploads the sample) needs that authorization.
- The earlier work unit's records live in `odd/tasks/versioning-release-process.md` on the branch
  `odd/versioning-release-process` — useful context on the CI environment contract, not a dependency.

# ODD: migration-030-existing-rows

## Objective

Prove, in the suite, that `db/migrations/030_memory_visibility_global.sql` applies correctly to a
database that already contains rows with `visibility='project'` — the situation that broke the dev
environment on 2026-09-22, and which no test has ever covered.

## Problem

Every test runs against a database migrated from empty. `migrated_db` is session-scoped and calls
`bash db/migrate.sh` once (`tests/integration/conftest.py:74-80`; the same fixture exists in
`tests/spec/conftest.py:51-79`, `tests/functional/conftest.py:60-81` and `tests/conftest.py:84-105`).

`db/migrate.sh` discovers `*.sql` in `"$SCRIPT_DIR/migrations"` (`db/migrate.sh:21`), sorts them
lexically, skips versions already recorded in `schema_migrations`, and has **no target-version
argument** — it reads only `DATABASE_URL`, `APP_DB_PASSWORD` and `PYTHON` (`db/migrate.sh:13-16`).

So the migration path that matters most — applying 030 to a database that already holds
`visibility='project'` rows — has never run anywhere except once, by hand, as a
`BEGIN; …; ROLLBACK;` against the live dev database during the 030 incident. Manual verification is
not a regression net.

`tests/integration/test_migrations.py` covers the post-030 shape
(`test_schema_migrations_records_version:106`, `test_enums_materialized:323`,
`test_memory_provenance_schema:347`) but never the transition into it.

030 is exactly the class of migration that needs this net: it replaces the coherence CHECK whose
expression carried the enum literal (`026_memory_provenance.sql:12-20` →
`030_memory_visibility_global.sql:19-23`). A wrong replacement, or a rename that misbehaved on a
populated table, would pass every existing test.

## Why

- Item (b) of the three findings left by the 030 incident. The operator hit the failure in the live
  panel; the migration itself was only ever verified manually.
- The class is general: any future migration that replaces a constraint carrying an enum literal has
  the same untested transition. 030 is the concrete instance worth pinning.
- The unit is cheap and self-contained: one test, no production change.

## Scope

**In:**

- One integration test in `tests/integration/test_migrations.py` that builds a scratch database at
  schema 029, seeds pre-030 rows, applies 030 with the real runner, and asserts the transition.

**Out:**

- `db/migrate.sh`: no target-version flag, no production change. The test uses the runner's existing
  behaviour.
- No reimplementation of the migration runner inside the test.
- No change to the memory axis, the enum model, `app/models.py`, or any migration file.
- No change to the shared session fixtures (`migrated_db`, `clean_db`) or to other suites.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-migration-030-existing-rows`
- Branch: `odd/migration-030-existing-rows`
- Base: `2a8bc84f`
- Files: `odd/tasks/migration-030-existing-rows.md`, `tests/integration/test_migrations.py`, and
  `tests/_testdb.py` only if a shared derivation is genuinely needed.

## Constraints

- **Strict TDD: ON** — source: `openspec/config.yaml` (`testing.strict_tdd: true`). Runner:
  `uv run pytest tests/`.
- The test MUST run the real `db/migrate.sh` content, never a reimplementation, and MUST assert the
  copy it executes is byte-identical to the original (`filecmp.cmp(..., shallow=False)`).
- The scratch database MUST be dropped in teardown even when the test fails.
- No pytest-xdist in this repo (verified), so a fixed scratch database name cannot collide.
- `pyproject.toml` sets `addopts = "-q"`; use `-o addopts=""` when the count matters. The per-test
  timeout is 120s (`pyproject.toml:53`), so the scratch build must stay well inside it.
- `memories` NOT NULL columns without defaults: `scope`, `entity_id`, `titulo`, `contenido`,
  `embedding`. Everything else has a default, including `visibility` (`'thread'`).
- One concern, `≤5` files per commit.

## Design decision

**D1 — build a scratch database at 029, then let the real runner apply 030.** Chosen because the
runner has no partial-migration capability and the pre-030 state cannot be recreated on an
already-renamed enum: `ALTER TYPE … RENAME VALUE` is one-way here (adding `'project'` back would
collide with the existing `'global'`), and the 026-era CHECK references a label that no longer exists.

Mechanism: copy `db/migrate.sh` into a temporary directory (asserting the copy is byte-identical),
give it a `migrations/` sibling whose entries are symlinks to `db/migrations/001*.sql` …
`029*.sql`, run that copy against the scratch database so the schema lands exactly at 029, seed the
rows, then run the **real** `db/migrate.sh` against the same scratch database, where only 030 is
pending.

Rejected: adding a `--target` flag to `db/migrate.sh` — a production change made for test
convenience; the runner's semantics are clear and stay untouched.
Rejected: reimplementing the runner inside the test — that tests the test, not the runner.
Rejected: recreating the 026-era enum and CHECK on the migrated database — impossible, as above.

Trade-off accepted: the test depends on `SCRIPT_DIR` remaining the runner's anchor. If someone
refactors `db/migrate.sh`, this test breaks loudly and visibly, and the byte-identity assertion makes
explicit that it executes the real runner.

## Tasks

- [x] **T1** — Harness: scratch database lifecycle plus the 029 scaffold. Create the scratch database
      from the admin URL, copy the runner byte-identical, symlink `001..029`, run it, and drop the
      database in teardown including on failure.
- [x] **T2** — Seed the pre-030 rows and apply 030 with the real runner: one
      `('agent', 'agent:default', visibility='project')` and one
      `('panel', 'thread:<id>', visibility='thread')`.
- [x] **T3** — Assertions: the enum has no `'project'` label; the agent row survives and now reads
      `global`; the panel row still reads `thread`; the replaced CHECK is the 030 expression and still
      rejects `scope='panel'` with `visibility='global'`; the column default is still `'thread'`.
- [x] **T4** — Verify: mutation check, targeted suite, full suite.

## Verification

- `uv run pytest tests/integration/test_migrations.py -o addopts=""`
- **Mutation check** (the load-bearing evidence): with the rename neutered inside a local scratch
  copy of 030 — so the transition does not happen — the test MUST go red. A test that stays green
  there proves nothing. Record the observed failure.
- `uv run pytest tests/ -o addopts=""` (full suite; needs the worktree test database)

## Acceptance criteria

1. The test builds a scratch database at 029 using the real runner content, proving the copy
   byte-identical to `db/migrate.sh`.
2. A row with `visibility='project'` provably exists before 030 runs.
3. After the real runner applies 030: the enum has no `'project'` label, that row is still present
   and now reads `global`, and a `thread` row is unchanged.
4. The replaced CHECK constraint is the 030 expression and still rejects `scope='panel'` with
   `visibility='global'`.
5. The `visibility` column default is still `'thread'`.
6. The scratch database is dropped even when the test fails.
7. The mutation check turns the test red, proving the assertions are not vacuous.
8. The full suite stays green.

## TDD note

This unit changes no production behaviour: 030 already works. Strict TDD's RED has no behaviour to
observe, so the honest equivalent is the mutation check in `## Verification` — neuter the rename and
the test must go red. That observation, not a fabricated RED, is the evidence recorded in the Outcome.

## Outcome

Delivered. Three commits on the branch, plus this record as the closing commit.

| Commit | Subject |
|---|---|
| `1ef028fa` | `test(migrations): prove 030 preserves pre-existing project rows` |
| `9b7a1d61` | `test(migrations): isolate and bound the 030 transition test` |
| `a6a4593b` | `test(migrations): use an unpredictable scratch database and never pre-drop it` |

**Change.** `tests/integration/test_migrations.py` gains `_migration_number()`, `_runner_dir()` and
`test_migration_030_preserves_existing_project_rows()`. The test creates a scratch database, runs the
real `db/migrate.sh` content against a `migrations/` directory of symlinks to `001..029` (asserting
the runner copy byte-identical with `filecmp.cmp(..., shallow=False)`), proves the schema really
landed at 029, seeds an `agent`/`visibility='project'` row and a `panel`/`thread` row, then runs the
real runner against a directory holding **only** 030, and asserts the transition. `db/migrate.sh` and
the migration files are untouched.

**TDD note.** This unit changes no production behaviour, so a RED on changed behaviour is not
observable and none was fabricated. The load-bearing evidence is the permanent in-test 029 assertions
plus the mutation check below.

**Verification.**

- `uv run pytest tests/integration/test_migrations.py -o addopts=""` -> **18 passed in 2.94s**
  (17 before, 18 after).
- `uv run pytest tests/spec/test_memory_spec.py -o addopts=""` -> **26 passed**.
- `uv run pytest tests/ -o addopts=""` -> **1169 passed, 2 warnings in 170.17s**.
- Collection delta measured in this worktree against its own base: **1168 collected at `2a8bc84f`**,
  1169 after, so **+1** — exactly the new test.
- No scratch database is left behind: `SELECT datname FROM pg_database WHERE datname LIKE '%mig030%'`
  returns empty after the suite.
- **One flake observed, and it is pre-existing.** An earlier full-suite attempt tripped the 120s
  `pytest-timeout` ceiling inside a `psycopg` wait. `odd/tasks/pytest-timeout.md:10-19` records this
  exact intermittent stall as undiagnosed and independent of the code under test, with "one pass and
  two hangs (exit 124) around ~74% progress, with the same code both passing and hanging"; the
  ceiling exists so it becomes a named failure instead of an endless hang. Two later full runs passed
  (250.68s and 219.78s). That attempt's output was truncated by my own `tail`, so the test it hit is
  not identified — the record says so rather than guessing.

**Mutation check (verified twice, independently).** With `ALTER TYPE memory_visibility RENAME VALUE
'project' TO 'global';` commented out in the worktree, the test goes RED on the right assertion: 030's
second statement is the replaced CHECK carrying the `'global'` literal, so the migration itself cannot
apply and the run stops at the `migrate(..., "030 migration")` assertion
(`tests/integration/test_migrations.py:170`) with
`psycopg.errors.InvalidTextRepresentation: invalid input value for enum memory_visibility: "global"`.
The file was restored with `git checkout -- db/migrations/030_memory_visibility_global.sql` and
`git status --porcelain` reported it clean.

**Lint: not run.** `ruff` is not installed in this environment and `pyproject.toml` configures no
linter, so there is no lint gate to satisfy.

**Review (native RDD) — three rounds, because two were not enough and the first two rounds' findings
were mine.**

| Round | Lineage | Budget | Outcome |
|---|---|---|---|
| 1 | `review-5b42fc169151c4d4` | 62 | Approved, 5 advisories |
| 2 | `review-19d26e860899cb4f` | 75 | Approved, 2 advisories (same class, correctly re-raised) |
| 3 | `review-7dd5a48364c72039` | 76 | **Approved, zero findings across all four lenses** |

Round 1 advisories: `R3-unbounded-migration-run` (the second subprocess ran the original runner over
the **full** migrations directory, so any later migration would be applied here and could change this
test's outcome), `R1-001` + `R3-concurrent-scratch-db` + `R4-scratch-db-collision` (a predictable
scratch name plus an unconditional `DROP DATABASE IF EXISTS`), and `R3-subprocess-timeout` (no
`timeout=` on either subprocess).

Round 1 fixes: an unpredictable-per-run name, `timeout=45` on both subprocesses, and a final runner
restricted to only 030. Round 2 then re-raised the remaining class — correctly: the PID-derived name
was still predictable **and the destructive pre-drop was still there**. That was a half-fix. Round 2's
fix removed the pre-drop entirely and moved the name to `uuid4().hex`. Round 3 found nothing.

Recorded honestly: the first design's "no xdist, so a fixed name is safe" reasoning only considered
xdist inside one process — never two independent pytest runs, and never a name that might already
exist for another reason. And the round-1 fix addressed the collision symptom while leaving the
destructive pre-drop in place. Both were caught by the review, not by me.

**Graph nodes consulted.** `test_migrations.py`, `test_schema_migrations_records_version()`,
`database_url()`, `_testdb.py`, `admin_conn()`, `clean_db()`, `integration/conftest.py`, `migrate.sh`.
No directed path resolved between `test_migrations.py` and `database_url()`.

**Known coupling.** The test depends on `SCRIPT_DIR` remaining the anchor of `db/migrate.sh`, and on
migration filenames carrying a numeric prefix. Both failures would be loud, and the byte-identity
assertion makes explicit that the runner executed is the real one.

**Remaining backlog.** Item 2 (per-project memory) and item 4 (query-less recall) stay open in
`backlog/memory-cross-thread-followups`, plus the `R3-search-failure-coverage` advisory left by
`odd/read-failure-truthfulness`.

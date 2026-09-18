# ODD Task — Per-worktree test database isolation

**Branch**: `odd/test-db-isolation`
**Worktree**: `../lumat-agent-odd-test-db-isolation`
**Status**: in progress

## Objective

Make the pytest test database per-worktree isolated, so two ODD worktrees can run
their suites concurrently without destroying each other's fixtures.

## Problem (verified, with evidence)

Parallel worktrees share one test database. Root cause is three coupled layers plus
one latent inconsistency:

1. **Fixed host port.** `infra/docker-compose.yml` publishes `db-test` as `"5432:5432"`.
   Two db-test containers cannot coexist on one machine.
2. **Fixed Compose project name.** No `-p` is passed anywhere, so Compose derives the
   project name from the compose file's directory — always `infra`, for every worktree.
   Verified with `docker compose ls`: the only project is `infra`, owning
   `infra-db-test-1` and the named volume `infra_db-test`. Both are literally shared.
3. **Hardcoded connection defaults.** Five conftests hardcode
   `postgresql+psycopg://app:app@localhost:5432/lumat`:
   `tests/conftest.py:43`, `tests/functional/conftest.py:28`,
   `tests/integration/conftest.py:34`, `tests/spec/conftest.py:23`,
   `tests/unit/conftest.py:18`.

The actual interference mechanism is the autouse `clean_db` fixture
(`tests/conftest.py:102-107`): it runs `TRUNCATE ... RESTART IDENTITY CASCADE`
before *every* test. So this is not stale data — a concurrent run destroys the
other run's fixtures mid-test, which is why failures are flaky rather than
deterministic.

**Latent inconsistency.** `tests/functional/conftest.py:49-50` and
`tests/spec/conftest.py:40-41` resolve `TEST_ADMIN_DB_URL` from a *hardcoded*
5432 fallback and do **not** derive it from `DATABASE_URL`. `tests/conftest.py:66`
and `tests/integration/conftest.py:59` do derive it. Exporting only `DATABASE_URL`
(as `README.md:45` instructs) therefore leaves the admin URL pointed at 5432.

**Why this regressed.** Historical verify reports ran against hand-picked ports
(5433, 5434, 5436) by exporting `DATABASE_URL` and `TEST_ADMIN_DB_URL` manually.
The pattern existed but was never encoded in compose or the conftests, so it decayed.
`infra/docker-compose.harness.yml` (present only in the `odd/chat-harness` worktree)
is the same fix done by hand a second time; its own comment documents the collision.

## Why

Two ODD worktrees running pytest concurrently currently interfere. Any future
parallel work re-hits this.

## Scope

In scope:
- One source of truth for the derived test-DB identity (project name + host port).
- Parameterized `db-test` host port in compose.
- All five conftests derive from that single source.
- A unit test guarding the derivation.
- Docs for the new bring-up/teardown path.

Out of scope:
- Managing dev stacks (`api`/`db`) per worktree, other than what already exists.
- Bootstrapping `infra/.env` into fresh worktrees (document the copy, do not automate).
- Rewriting historical verify reports or task docs that reference `localhost:5432`.

## Design decisions (locked — do not invent alternatives)

- **D1 — Single source of truth is Python**: `tests/_testdb.py`, pure stdlib
  (`hashlib`, `os`, `pathlib`). The shell helper calls it; the conftests import it.
  Deriving the port in two languages is the drift that caused the original regression.
- **D2 — Derivation**: identity is the worktree root directory name
  (`Path(__file__).resolve().parents[1].name`).
  - `project = "lumat-test-" + slug(dir_name)` (lowercase, non-alphanumeric → `-`).
   - `port = 5432 + (int(sha256(dir_name).hexdigest(), 16) % 1000)` → range 5432–6431.
   - Deterministic: the same worktree always resolves the same values.
   - For this worktree the derived values are project `lumat-test-lumat-agent-odd-test-db-isolation` and its hash-derived port; no repo-prefix stripping is applied.
- **D3 — Determinism over collision-avoidance.** A collision makes `up` fail loudly
   with "port is already allocated". It must never be resolved by probing for a free
   port, because a probe cannot stay consistent between the shell and Python.
   The harness overlay's `db` service publishes host port 5433, which is inside the
   derived test-port range. By design, D3 does not avoid this by probing: a worktree
   that derives 5433 fails loudly at `up`; use `TEST_DB_PORT=<free port>` to override it.
- **D4 — Escape hatch**: `TEST_DB_PORT` and `TEST_DB_PROJECT` env vars override the
  derivation, and are read by *both* the shell and Python. Explicit
  `DATABASE_URL` / `TEST_ADMIN_DB_URL` still win over everything (preserve the
  existing `os.environ.setdefault` semantics).
- **D5 — Teardown is bound to the worktree lifecycle, not the pytest run.** Do not
  start/stop containers from a pytest fixture. Per-run containers leak on SIGKILL
  and pay boot + migration per run, with no extra isolation (one suite per worktree
  runs at a time).
- **D6 — Misconfiguration must fail loudly, never silently share.** If someone runs
  the old raw `docker compose ... up db-test`, pytest gets connection-refused, not a
  shared database.
- **D7 — Admin credentials** default to `lumat:${TEST_POSTGRES_PASSWORD:-lumat}`,
  matching the compose `db-test` service.

## Tasks

- [ ] **T1** — `tests/_testdb.py`: derivation module per D2/D3/D4/D7. Exposes
  `project_name()`, `host_port()`, `database_url()`, `admin_database_url()`,
  `env()`. `__main__` CLI prints `KEY=value` lines for shell `eval`.
  Add `pythonpath = ["tests"]` to `[tool.pytest.ini_options]` in `pyproject.toml`
  so all conftests can `from _testdb import ...` without path gymnastics.
- [ ] **T2** — `tests/unit/test_testdb_derivation.py`: guards determinism (same dir →
  same values), distinctness (two odd worktree names → distinct ports/projects),
  range 5432–6431, and the `TEST_DB_PORT` / `TEST_DB_PROJECT` overrides.
  This is the regression guard against the drift described in D1.
- [ ] **T3** — `infra/docker-compose.yml`: `db-test` port becomes
  `"${TEST_DB_PORT:-5432}:5432"`. Keep the default so an unparameterized invocation
  still behaves as before.
- [ ] **T4** — `infra/test-db.sh`: `up` | `down` | `env` | `port` | `project`.
  - `up`: `docker compose -p <project> -f infra/docker-compose.yml --profile test`
    with `TEST_DB_PORT` exported, `up -d db-test`.
  - `down`: same project, `down -v` (safe: the volume is namespaced to the test
    project, never the dev/panel volume).
  - `env`: prints `export DATABASE_URL=...` / `export TEST_ADMIN_DB_URL=...`.
  - Missing `infra/.env` must produce a clear actionable message naming the exact
    copy command from the primary worktree, not a raw compose interpolation error.
- [ ] **T5** — Refactor the five conftests to derive from `_testdb`, and fix the
  latent `TEST_ADMIN_DB_URL` inconsistency so all five behave identically.
- [ ] **T6** — `tests/README.md`: replace the raw `--profile test up -d db-test`
  instructions with the helper, and document `up` / `down` / teardown-on-worktree-removal.
- [ ] **T7** — Verify (see Checks).

## Acceptance criteria

1. Two worktrees running a DB-touching suite concurrently both pass, with two
   distinct db-test containers on distinct host ports and distinct named volumes.
2. The same worktree resolves the same project/port on repeated invocations.
3. An explicit `DATABASE_URL` still overrides the derived default.
4. All five conftests resolve a consistent admin URL from the same derivation.
5. `infra/test-db.sh down` removes only that worktree's container and volume.

## Checks

```bash
# setup in the fresh worktree
uv sync
cp ../lumat-agent/infra/.env infra/.env     # gitignored; absent in a fresh worktree

# derivation unit test
uv run pytest tests/unit/test_testdb_derivation.py -q

# derivation is stable across invocations
infra/test-db.sh port && infra/test-db.sh port

# bring up this worktree's test DB, run a DB-touching suite
infra/test-db.sh up
eval "$(infra/test-db.sh env)"
uv run pytest tests/functional -q

# isolation proof is run by the orchestrator (T7), not here:
# two worktrees with concurrent suites + docker ps comparison
```

## Rollback

Revert the branch. The derived port/project are additive; the previous behavior
(project `infra`, port 5432) is restored by reverting `infra/docker-compose.yml`
and the conftests. No data migration is involved. Existing leftover containers:
`docker compose -p infra --profile test down -v` after reverting.

## Progress

- [x] Worktree created, task doc committed.
- [x] T1 — shared stdlib derivation module and pytest import path.
- [x] T2 — derivation regression tests.
- [x] T3 — parameterized Compose test port.
- [x] T4 — lifecycle helper commands.
- [x] T5 — all five conftest refactors and consistent admin URL derivation.
- [x] T6 — isolated test database lifecycle documentation.
- [ ] T7 — cross-worktree isolation proof.

## Verification evidence

- `uv run pytest tests/unit/test_testdb_derivation.py -q`: passed, `4 passed`.
- `infra/test-db.sh port && infra/test-db.sh port`: printed `5939` twice.
- `infra/test-db.sh up && eval "$(infra/test-db.sh env)" && uv run pytest tests/ -q`: completed with no test failures; only the two known warnings were emitted.
- `docker ps --format '{{.Names}}\t{{.Ports}}' | grep -i db-test`: showed `lumat-test-lumat-agent-odd-test-db-isolation-db-test-1` on host port `5939` and `infra-db-test-1` on host port `5432`.
- `infra/test-db.sh down`: removed only the worktree container, network, and `lumat-test-lumat-agent-odd-test-db-isolation_db-test`; `infra-db-test-1`, `infra_db`, and `infra_db-test` remained.
- The worktree test database was brought up again on port `5939`; the primary `infra-db-test-1` remained on port `5432`.

## Next step

Delegate T1–T6 to a single writer, then run the T7 isolation proof.

# ODD Task — Test database isolation: technical debt

**Branch**: `odd/test-db-debt`
**Worktree**: `../lumat-agent-odd-test-db-debt`
**Base**: `745cf0b4`
**Status**: complete

## Objective

Close the four debt items the native reviews and the implementation of
`odd/test-db-isolation` left behind, in the priority order the user fixed:
the unquoted shell export, the explicit-default URL that is mistaken for a derived
one, the ~26 duplicated admin-URL derivations under `tests/`, and the minor items.

This unit removes duplication and one shell-injection vector. It adds no feature and
changes no production code (`app/` is untouched).

## Problem (verified, with evidence)

The per-worktree isolation landed in PR #240. Its reviews flagged four follow-ups, and
none of them reopens that review: the reviewers were explicit that this is separate work.

1. **Shell injection through `eval`.** `tests/_testdb.py:75` prints
   `export {key}={value}` with no quoting, and `tests/README.md:18` tells the developer to
   consume it with `eval "$(infra/test-db.sh env)"`. A `TEST_POSTGRES_PASSWORD` holding
   shell metacharacters is therefore executed. **Reproduced in this worktree** (no side
   effects, `echo` instead of a destructive payload):

   ```console
   $ env -u DATABASE_URL -u TEST_ADMIN_DB_URL TEST_POSTGRES_PASSWORD='$(echo pwned)' \
       .venv/bin/python tests/_testdb.py env
   export DATABASE_URL=postgresql+psycopg://app:app@localhost:5452/lumat
   export TEST_ADMIN_DB_URL=postgresql://lumat:$(echo pwned)@localhost:5452/lumat
   $ bash -c "unset TEST_ADMIN_DB_URL; <that line>; echo \$TEST_ADMIN_DB_URL"
   postgresql://lumat:pwned@localhost:5452/lumat      # ← substituted, not literal
   ```

2. **An explicitly declared default is mistaken for "not declared".**
   `tests/_testdb.py:44-46` compares the *value* of `DATABASE_URL` against
   `_default_database_url()` instead of testing *presence*:

   ```python
   configured = os.environ.get("DATABASE_URL")
   if configured and configured != _default_database_url():
   ```

   Setting `DATABASE_URL` to exactly the derived default falls into the `else` branch and
   demands `TEST_POSTGRES_PASSWORD`, raising `TestDatabaseConfigError` for a variable the
   caller did declare. The information "it was declared" is lost because
   `database_url()` uses `os.environ.get("DATABASE_URL", _default_database_url())`.

3. **~26 duplicated admin-URL derivations.** The isolation change introduced
   `tests/_testdb.py` as the single source, but the test modules were never migrated.
   The literal `postgresql://lumat:lumat@localhost:5432/lumat` survives in **18** files as
   `os.environ.get("TEST_ADMIN_DB_URL", "<literal>")`, plus:

   - 3 files with a divergent derivation
     (`test_h4_worker.py:16`, `test_h4_automations.py:19`, `test_h4_notifications.py:16`):
     `os.environ.get("TEST_ADMIN_DB_URL") or os.environ["DATABASE_URL"].replace(...)`
   - `test_seed.py:29-35` — its own `_seed_admin_db_url` + `SEED_ADMIN_DB_URL`
   - `test_migrations.py:27-29` — `APP_URL`, derived by swapping credentials on the
     `ADMIN_DB_URL` it imports from the integration conftest
   - `test_db.py:203` — a **different** literal, the app-role URL
     (`postgresql://app:app@localhost:5432/lumat`), passed to `psycopg.connect(..., autocommit=True)`

   These are inert today — the helper exports `TEST_ADMIN_DB_URL` and wins over the
   literal — but they are exactly the duplication this change set out to delete, and they
   pin the port to `5432`, which in an isolated worktree is the *wrong* database.

4. **Minor items.** (a) `_slug` is not injective: `foo_bar`, `foo-bar` and `foo.bar` all
   collapse to `foo-bar` and silently share one Compose project and volume. (b) `down`
   requires `infra/.env`. (c) `_slug` uses `char.isalnum()`, which accepts Unicode, so a
   non-ASCII directory name yields a Compose project name Compose rejects. (d) No
   `.gitguardian.yaml`; the secret-scan incident is documented only in commit history.
   (e) `odd/tasks/test-db-isolation.md:5` still reads `**Status**: in progress`.

## Why the obvious fix for 4b does not work (verified, not inferred)

The review suggested requiring `infra/.env` only for `up` and `env`. **That is
insufficient.** Compose interpolates the whole file even for `down`, so the
`${VAR:?…}` declarations still have to resolve. Verified by moving `infra/.env` aside and
running the teardown with none of the variables exported:

```console
$ docker compose -p lumat-test-lumat-agent-odd-test-db-debt \
    -f infra/docker-compose.yml --profile test down -v
error while interpolating services.api.environment.META_ACCESS_TOKEN: required variable META_ACCESS_TOKEN is missing a value: set META_ACCESS_TOKEN in infra/.env
error while interpolating services.api.environment.META_PHONE_NUMBER_ID: required variable META_PHONE_NUMBER_ID is missing a value: set META_PHONE_NUMBER_ID in infra/.env
error while interpolating services.api.environment.PANEL_SESSION_SECRET: required variable PANEL_SESSION_SECRET is missing a value: set PANEL_SESSION_SECRET in infra/.env
error while interpolating services.api.environment.POSTGRES_PASSWORD: required variable POSTGRES_PASSWORD is missing a value: set POSTGRES_PASSWORD in infra/.env
error while interpolating services.api.environment.VERIFY_TOKEN: required variable VERIFY_TOKEN is missing a value: set VERIFY_TOKEN in infra/.env
error while interpolating services.db.environment.POSTGRES_PASSWORD: required variable POSTGRES_PASSWORD is missing a value: set POSTGRES_PASSWORD in infra/.env
exit=1
```

The `:?`-required variables, from `infra/docker-compose.yml`, are:
`POSTGRES_PASSWORD` (`:23`, `:69`), `APP_SECRET` (`:65`), `VERIFY_TOKEN` (`:66`),
`DATABASE_URL` (`:67`), `META_ACCESS_TOKEN` (`:70`), `META_PHONE_NUMBER_ID` (`:71`),
`PANEL_SESSION_SECRET` (`:72`).

## Scope

**In:** quoting the exported shell values; correcting the explicit-default precedence;
migrating every test-side URL derivation onto `tests/_testdb.py`; making the slug
injective and ASCII-only; making `down` independent of `infra/.env`; the status one-liner
in the previous task doc; a regression guard against the duplication returning.

**Out:**

- Any change under `app/`, `db/`, or `infra/docker-compose*.yml`. Production is untouched.
- `.gitguardian.yaml` (item 4d) — see D6.
- `git push`, PR creation, merge, or any remote operation. Local commits only (D7).
- Re-running the native review of `odd/test-db-isolation`. That authority is burned and
  must not be re-created; this is a different candidate.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-test-db-debt`
- Branch: `odd/test-db-debt`
- Files: `tests/_testdb.py`, `tests/unit/test_testdb_derivation.py`, `infra/test-db.sh`,
  `tests/README.md`, every `tests/**/*.py` that derives an admin URL (D3), and
  `odd/tasks/test-db-debt.md`, `odd/tasks/test-db-isolation.md` (status one-liner only).
- **Never touch** `/home/stefan/repos/lumat-agent` (main) or
  `/home/stefan/repos/lumat-agent-odd-memory-axes` (another agent's live worktree).

## Constraints

- **Strict TDD: ON** — source: `openspec/config.yaml` (`testing.strict_tdd: true`);
  runner `.venv/bin/pytest tests/`. Observe RED before each source change, at the
  **assertion** level. A collection `ImportError` is not a RED.
- This worktree's isolated test database is already up: project
  `lumat-test-lumat-agent-odd-test-db-debt`, host port **5452**. Resolve it with
  `eval "$(infra/test-db.sh env)"`. Never `down -v` on `infra` or on any other project.
- `pyproject.toml:45` sets `pythonpath = ["tests"]`, so `from _testdb import …` works from
  every test directory. No conftest adds `tests/` to `sys.path`.
- `addopts = "-q"`: do not add another `-q` (it becomes `-qq` and suppresses the summary).
- No linter, typechecker, pre-commit, or hooks in this repo. The tests are the verification.
- All artifacts are written in English.
- Planning heuristic: ~400 authored changed lines. This unit is expected to land near
  ~300 for code and tests; the ODD doc is the rest. It is a heuristic, not a cap.

## Decisions

- **D1 — `tests/_testdb.py` is the only derivation source.** Every test-side need for an
  admin or app URL calls `admin_database_url()` or `database_url()` from it. No test module
  derives, defaults, or literal-fills a URL again. The pre-existing `__getattr__`-style
  re-export through the conftests stays as-is: `tests/integration/conftest.py:57`,
  `tests/functional/conftest.py:50` and `tests/spec/conftest.py:41` keep exposing
  `ADMIN_DB_URL` for their own fixtures, but the three modules that currently import it
  from a conftest (`test_migrations.py:25`, `test_agent_chat_realtime.py:8`,
  `test_h4_chat.py:9`) import from `_testdb` instead — importing a conftest as a module is
  the very coupling this removes. `test_migrations.py` keeps importing `run_migrate` from it.
- **D2 — One helper for the libpq form.** `admin_database_url()` converts the SQLAlchemy
  driver suffix (`postgresql+psycopg://` → `postgresql://`) inline today, and
  `test_db.py:203` needs the same conversion for its direct `psycopg.connect`. Extract that
  conversion into a named function in `_testdb.py` and use it in both places. This *removes*
  duplication; it does not add a new concept.
- **D3 — Quote at the print boundary.** `main()` is the shell-output boundary, `env()` is a
  data API; quote with `shlex.quote` in `main()` only, so programmatic callers keep raw values.
- **D4 — The slug becomes injective and ASCII, monotonically.** Append a short hex hash of
  the **raw** worktree name **only when the raw name is not already a valid lowercase ASCII
  slug**. Consequences: `lumat-agent-odd-test-db-debt` and every other existing
  `lumat-agent-odd-*` worktree keep their exact project name and port, so no existing test
  database is orphaned; `foo_bar` and `foo-bar` stop colliding; a name with `ñ` or an
  uppercase letter produces a Compose-valid, distinct project name. Do not switch to a
  blanket hash suffix — that would rename every existing project.
- **D5 — The sweep gets a regression guard, and the guard is its RED.** A unit test walks
  `tests/**.py` and fails while any module still contains a self-declared admin-URL literal
  or the divergent `os.environ["DATABASE_URL"].replace(...)` form. It must fail before the
  sweep and pass after. Build the searched pattern so this test file does not match itself.
- **D6 — `.gitguardian.yaml` is deliberately not written.** Writing a scanner-ignore file
  whose schema and effect cannot be verified here risks suppressing real detections for no
  proven benefit. Item 3 already removes the repeated dev literals that motivated the
  incident, shrinking the scanner surface. The decision and its reasoning are recorded here
  for the user to overrule with a documented GitGuardian contract.
- **D7 — Local commits only.** Work-unit commits on `odd/test-db-debt`; no push, no PR, no
  merge. Delivery is a separate human decision, as in every previous unit of this repo.
- **D8 — `down` gets stubs, not a dependency on secrets.** When `infra/.env` is absent,
  `down` exports harmless placeholder values for the seven `:?`-required variables and omits
  `--env-file`, because their values are irrelevant to a teardown. `require_env_file` stays
  mandatory for `up` and `env`. Do not "simplify" this back to requiring the file for `down`
  — that is the state verified as broken above.

## Tasks

- [x] **T1 — RED/GREEN, item 1.** `shlex.quote` in `main()`, plus a test that proves an
  `eval` of the emitted lines preserves the value literally and executes nothing.
- [x] **T2 — RED/GREEN, item 2.** Honour a declared `DATABASE_URL` by presence, plus a test
  that sets it to exactly the derived default and asserts no `TestDatabaseConfigError`.
- [x] **T3 — RED/GREEN, items 4a and 4c.** Injective ASCII slug, plus tests for the
  collisions and for a non-ASCII name; the existing derivation test's inline oracle must be
  updated to the new contract.
- [x] **T4 — RED/GREEN, item 3.** The guard test (D5) first, then migrate all derivation
  sites (D1, D2) and delete the literals.
- [x] **T5 — item 4b.** `down` without `infra/.env` (D8).
- [x] **T6 — item 4e.** Status one-liner in `odd/tasks/test-db-isolation.md`.
- [x] **T7 — Evidence.** Targeted suites per task; the full suite once at the end.

## Acceptance criteria

1. `eval "$(infra/test-db.sh env)"` assigns the exact literal values, for any password,
   including one containing `$`, backticks, quotes, semicolons or spaces.
2. `admin_database_url()` honours a declared `DATABASE_URL` even when its value equals the
   derived default, and still raises loudly when nothing declares it.
3. `_testdb.project_name()` is injective for the names it can receive, ASCII-only, and
   unchanged for every existing `lumat-agent-odd-*` worktree.
4. No file under `tests/` derives, defaults or literal-fills an admin or app URL; the guard
   test fails against the pre-sweep tree and passes after it. No `localhost:5432` URL
   literal for this project survives anywhere under `tests/`.
5. `infra/test-db.sh down` tears down the isolated project when `infra/.env` is absent and
   no variable is exported; `up` and `env` still refuse loudly without it.
6. `odd/tasks/test-db-isolation.md` no longer claims to be in progress.
7. Each task observes RED before its source change and GREEN after, at assertion level.
8. The full suite passes on the isolated database of this worktree.
9. Only the authorized files change; `app/`, `db/` and `infra/docker-compose*.yml` are untouched.

## Checks

Per task (fast, targeted):

- `.venv/bin/pytest tests/unit/test_testdb_derivation.py -q`
- `.venv/bin/pytest tests/integration/test_db.py tests/integration/test_migrations.py tests/integration/test_seed.py -q`

Once at the end (the full suite, ~8-9 minutes, on this worktree's isolated database):

```bash
cp ../lumat-agent/infra/.env infra/.env      # already done for this worktree
infra/test-db.sh up
eval "$(infra/test-db.sh env)"
.venv/bin/pytest tests/
```

Plus:

- `rg -n 'localhost:5432' tests/ -g '*.py'` → no project URL literal remains
- `git status --short` and `git diff --check`
- The `down`-without-`.env` experiment from "Why the obvious fix does not work", re-run and
  its observed output recorded below. **No automated test runs `down`:** it would destroy
  the suite's own database mid-run.

## Progress

- [x] Created this ODD record before the first source change.
- [x] T1 … T7.

## Verification evidence

| Command | Observed result |
| --- | --- |
| `.venv/bin/pytest tests/unit/test_testdb_derivation.py -q` (T1 RED) | `.....F`; assertion observed the evaluated value as `postgresql://lumat:@localhost:5452/lumat` instead of the literal `postgresql://lumat:$(printf pwned >&2)@localhost:5452/lumat`. Exit 1. |
| `.venv/bin/pytest tests/unit/test_testdb_derivation.py -q` (T1 GREEN) | `......` passed. Exit 0. |
| `.venv/bin/pytest tests/unit/test_testdb_derivation.py -q` (T2 RED) | `...F...`; `TestDatabaseConfigError` raised for a declared `DATABASE_URL` equal to the derived default. Exit 1. |
| `.venv/bin/pytest tests/unit/test_testdb_derivation.py -q` (T2 GREEN) | `.......` passed. Exit 0. |
| `.venv/bin/pytest tests/unit/test_testdb_derivation.py -q` (T3 RED) | `.F......`; `_slug("foo_bar")` and `_slug("foo-bar")` both observed as `foo-bar`. Exit 1. |
| `.venv/bin/pytest tests/unit/test_testdb_derivation.py -q` (T3 GREEN) | `........` passed. Exit 0. |
| `.venv/bin/pytest tests/unit/test_testdb_derivation.py -q` (T4 RED) | `..F......`; guard observed 23 offending files, first `tests/integration/test_chat_capture.py`. Exit 1. |
| `.venv/bin/pytest tests/unit/test_testdb_derivation.py -q` (T4 GREEN) | `.........` passed. Exit 0. |
| `.venv/bin/pytest tests/unit/test_testdb_derivation.py -q` (T7) | `.........` passed. Exit 0. |
| `eval "$(infra/test-db.sh env)" && .venv/bin/pytest tests/integration/test_db.py tests/integration/test_migrations.py tests/integration/test_seed.py -q` (T7) | `...........................` passed. Exit 0. |
| `infra/test-db.sh down` with `infra/.env` absent and required variables unset (T5) | `Container lumat-test-lumat-agent-odd-test-db-debt-db-test-1 Stopping` / `Stopped` / `Removing` / `Removed`; `Volume lumat-test-lumat-agent-odd-test-db-debt_db-test Removing` / `Removed`; `Network lumat-test-lumat-agent-odd-test-db-debt_default Removing` / `Removed`; `down_exit=0`. |
| `infra/test-db.sh up` after restoring `infra/.env` (T5) | `restore_verified=0`; network, volume, and container created and started successfully. Exit 0. |
| `infra/test-db.sh up && eval "$(infra/test-db.sh env)" && .venv/bin/pytest tests/` (T7) | `901 passed, 2 warnings in 473.55s (0:07:53)`. Exit 0. |
| `rg -n 'localhost:5432' tests/ -g '*.py'` | No matches. Exit 1 (expected no-match result). |
| `git diff --check` | No output. Exit 0. |

## Graph nodes consulted (Graph Check, Step 1)

`graphify query "test database isolation and worktree derivation in tests/_testdb.py and
infra/test-db.sh"` on this worktree's `graphify-out/` (203 nodes, 63 returned).

- `tests/_testdb.py` — the `integration/conftest.py` community, with `_slug`,
  `project_name`, `host_port`, `_default_database_url`, `database_url`,
  `admin_database_url`, `env`, `main`, `TestDatabaseConfigError`
- `tests/unit/test_testdb_derivation.py` — the derivation contracts
  (`test_explicit_urls_override_derivation`, `test_admin_password_override`,
  `test_missing_password_fails_loudly_instead_of_guessing`, …)
- `tests/integration/conftest.py`, `tests/conftest.py`, `tests/functional/conftest.py`,
  `tests/spec/conftest.py`, `tests/unit/conftest.py` — the communities that consume the
  derivation
- `odd/tasks/test-db-isolation.md` — the unit that introduced the derivation

Directed paths confirmed by reading the wiring: `tests/*/conftest.py → from _testdb import
admin_database_url, database_url`; `pyproject.toml` `pythonpath = ["tests"]` makes the bare
module importable; `infra/test-db.sh → tests/_testdb.py {port,project,env}`.

## Recovery

Resume with `mem_context`, then the project-scoped `mem_search` for this feature, then
`mem_get_observation` for the full document, then read this file. The Engram mirror lives at
topic `odd/test-db-debt/tasks`.

## Next step

Human review and delivery decision. The worktree contains only local work-unit commits; no
push, PR, merge, or rebase was performed.

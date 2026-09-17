# ODD: pytest-timeout

## Objective

Add a timeout ceiling to the pytest suite so an intermittent stall becomes a named failure with a
stack dump instead of hanging forever.

## Problem

The approximately 869-test suite can stall intermittently without a ceiling or diagnostic output.
The underlying stall is not diagnosed. This change is a safety net and diagnostic, not a fix for the
stall itself.

## Why — root cause (verified, not inferred)

The session finding established that the suite takes **519.89s (~8:39)** when green, and that three
full runs produced **one pass and two hangs (exit 124)** around **~74% progress**, with the same code
both passing and hanging. The intermittent behaviour is independent of the code under test. No
`pytest-randomly` was present, the suite had no `pytest-timeout`, and the suspected
`tests/spec/test_memory_spec.py` region passed alone in 8.5s.

The actionable, verified gap is that a stall has no time ceiling and no stack-dump diagnosis. Postgres
contention from suites running in parallel in other worktrees remains an unproven hypothesis and is
out of scope.

## Scope

**In:** the `pytest-timeout` development dependency, pytest timeout configuration, and this ODD
record.

**Out:** diagnosing or fixing the underlying stall; changing application or test code; changing the
database or containers; adding a permanent meta-test for the configuration.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-pytest-timeout`
- Branch: `odd/pytest-timeout`
- Files: `odd/tasks/pytest-timeout.md`, `pyproject.toml`, `uv.lock`
- Dependency command: `uv add --dev "pytest-timeout>=2.3"`

## Constraints

- Work only in the authorized worktree and never push.
- Do not create, delete, start, or stop Docker containers.
- Do not modify tests, application code, `tests/conftest.py`, or unrelated documentation.
- Run the timeout proof once with a throwaway test and delete it afterward; never commit it.
- Run the real suite at most once, with `--durations=10` and the specified test database URL.
- Keep the timeout at 120 seconds if the real suite exposes a genuine timeout.
- Use conventional commits with no AI attribution.

## Tasks

- [x] **T1 — Dependency.** Add `pytest-timeout>=2.3` to the dev dependency group and update `uv.lock`.
- [x] **T2 — Configuration.** Add the requested 120-second per-test timeout and `thread` method under
      `[tool.pytest.ini_options]`, preserving existing keys.
- [x] **T3 — Proof.** Run the throwaway configuration and timeout proof, record its exact output, then
      delete the throwaway file and confirm it leaves no status trace.
- [x] **T4 — Real suite.** Run the full pytest suite once with `--durations=10` and record the exact
      result, wall time, and top durations, or report a genuine timeout/partial run honestly.
- [x] **T5 — Delivery.** Verify the authorized diff, commit dependency/configuration and the ODD record
      as separate reviewable work units, and do not push.

## Acceptance criteria

1. `pyproject.toml` contains `pytest-timeout>=2.3` in the dev dependency group and the requested
   timeout configuration.
2. `uv.lock` records the resolved `pytest-timeout` dependency.
3. The throwaway proof observes the live configuration and the `thread` method fails the 2-second
   sleep with timeout separators and a MainThread stack dump; the file is deleted afterward.
4. The real suite is run no more than once and its result is reported as green, a genuine timeout,
   or partial, without claiming evidence that was not observed.
5. Only the three authorized files are changed and no throwaway proof file is committed.

## Checks

- Dependency: `uv add --dev "pytest-timeout>=2.3"`
- Proof: `uv run pytest tests/unit/test_zz_timeout_proof_tmp.py -q`
- Cleanup: `git status --short`
- Real suite: `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/ -q --durations=10`
- Final review: `git status --short`, `git diff --check`, `git diff --stat`

## Decisions

### `thread` over `signal`

The installed `pytest-timeout` source shows that `timeout_sigalrm` calls `dump_stacks(terminal)` from
the MainThread, while `dump_stacks()` skips the current thread. With one thread, the signal method
therefore provides no useful stack dump and may be swallowed by a C-level block such as the live
libpq database-lock suspicion. `timeout_timer`, used by `thread`, runs in a timer thread, dumps the
hanging MainThread, and calls `os._exit(1)`, guaranteeing the ceiling. The accepted cost is that
teardown does not run and the process dies at the first hang. The rejected alternative is `signal`.

### `session_timeout` dropped

The installed source checks `session_timeout` between tests in `pytest_runtest_protocol`; it cannot
interrupt a stall inside one test. It is a budget check, not a test-stall ceiling, so this option was
considered and rejected.

## Progress

- [x] Task record created before source/configuration changes.
- [x] Dependency and pytest configuration applied.
- [x] Throwaway proof observed and removed.
- [x] Real suite observed and recorded.
- [x] Two reviewable commits created; nothing pushed.

## Verification evidence

The first proof attempt ran with the original `signal` configuration. It produced
`Failed: Timeout (>2.0s) from pytest-timeout` but no `~~ Stack of MainThread` dump. The source-level
reason is that `dump_stacks()` skips `threading.current_thread()`, and the signal handler runs in the
MainThread; with one thread, even the timeout separators are skipped. This observation is why the
method changed to `thread`.

| Check | Command | Result |
|---|---|---|
| Proof A1 | `uv run pytest tests/unit/test_zz_timeout_proof_tmp.py -q` | **1 passed**; the ini values were observed as strings `"120"` and `"thread"` |
| Proof A2 | `uv run pytest tests/unit/test_zz_timeout_proof_tmp.py -q` | **Exit code 1**, hard-exited by `pytest-timeout`; output contained `++ Timeout ++` and `~~ Stack of MainThread` and had no pytest summary |
| Cleanup | `git status --short` | Throwaway file absent; only authorized changes plus pre-existing `.opencode/tools/package-lock.json` remained |
| Full suite | `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/ -q --durations=10` | **869 passed**, 0 failed, 2 pre-existing warnings, real time **6m44.760s**; no pytest-timeout failures |

Top durations from the full suite: 2.79s `tests/spec/test_projects_spec.py::test_project_slug_is_normalized_and_unique`;
2.69s `tests/functional/test_auth.py::test_seed_admin_creates_idempotent_bcrypt_admin`;
2.62s setup `tests/functional/test_api_scheduling.py::test_appointments_range_requires_authentication_and_does_not_mutate`;
2.59s `tests/integration/test_seed.py::test_seed_applies_cleanly_twice`;
2.09s setup `tests/functional/test_api_conversations.py::test_conversations_list_returns_serialized_rows_in_activity_order`.

The diagnosis figures in this record are session findings supplied for this work unit, not
measurements taken during implementation. Remaining verification is pending.

## Next step

The timeout ceiling is installed and verified; the next step is review/merge of the two commits.

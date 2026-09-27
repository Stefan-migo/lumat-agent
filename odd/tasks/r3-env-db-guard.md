# ODD: r3-env-db-guard

**Branch**: `odd/r3-env-db-guard`
**Worktree**: `../lumat-agent-odd-r3-env-db-guard`
**Base**: `0b9f3c2e`
**Status**: merged — PR #259 (`0d8fed79`). Implemented and verified; native review approved and its authority burned.
**Advisory**: `R3-env-database-mismatch` (WARNING, `evidence_class: deterministic`,
`causal_disposition: introduced`, non-blocking) from native review `review-ba9c8a35d22602f6`.

## Objective

Make `_ensure_environment` (`scripts/kb_calibration.py`) do what its docstring promises: refuse to
run unless the harness is pointed at the isolated test database **this worktree provisioned**.

## Problem (verified in code, with corrections to the handoff)

The guard validates its two inputs **separately** and never checks that they name the same database:

- `TEST_ADMIN_DB_URL` must be non-empty (it is exported only by `infra/test-db.sh env`).
- `DATABASE_URL`'s host must be in `_LOCAL_HOSTS` (`localhost`, `127.0.0.1`, `::1`).

A local dev database also has a local host, so it passes the filter, and then
`reset_calibration_documents` (line 480) deletes every `kb_documents` row whose title matches
`[calibration] ` alongside its `kb_chunks`. Blast radius is bounded to that prefix, but the docstring
promises "refuse to touch anything but the isolated test DB" and does not deliver it. A guard that
does not keep its promise is worse than no guard: it lowers vigilance.

Three corrections established by reading the code, which change the handoff's fix directions:

1. **Handoff option 2 is mechanically wrong.** It proposes comparing `DATABASE_URL`'s dbname against
   `infra/test-db.sh project`. But `project` returns the *docker compose project* name
   (`lumat-test-<worktree-slug>`), and the database name is always the literal `lumat`
   (`tests/_testdb.py:44`). Worktree identity lives in the **derived port**
   (`tests/_testdb.py:27-40`), not in the path. The correct anchor is `_testdb.host_port()`.
2. **The reachable blast radius is narrower than the handoff implies.** The dev `DATABASE_URL` in
   `infra/.env:23` uses host `db` (the compose service) and the dev `db` service publishes **no host
   port** (`infra/docker-compose.yml:18`, only `db-test` maps `${TEST_DB_PORT:-5432}:5432`). The
   logical hole is real; the documented workflow does not walk into it.
3. **The guard has zero test coverage, and that is a placement bug.** It sits under the section
   header "I/O shell — real model, real database. Not suite-covered by design" (lines 438-441), but
   it is pure environment parsing. Strict TDD cannot produce a legitimate RED for a function the file
   declares out of coverage, so relocating it above that boundary is part of the fix.

`TEST_ADMIN_DB_URL` is a **sentinel**: the script never connects with it (only `DATABASE_URL` is
used). That is what makes cross-checking the two cheap and meaningful. `scripts/chat_harness.py` has
no equivalent guard; it is out of scope.

## Scope

`scripts/kb_calibration.py` (the guard and its placement) and `tests/unit/test_kb_calibration.py`.
Nothing else.

## Authorized scope

- Human-approved on 2026-09-20: option **A+B** (below) and creation of this worktree.
- The human explicitly accepted the new `scripts/` -> `tests/_testdb.py` import.
- The sibling advisory `R3-empty-corpus-accepted` is **not** in this PR unless the human says
  otherwise later.

## Constraints

- Harness only: `git diff --name-only -- app/ web/ db/ agent/ openspec/` must stay empty.
- Strict TDD is active (`openspec/config.yaml` -> `testing.strict_tdd: true`, runner `uv run pytest`).
  RED first, then GREEN. The guard is pure and model-free: monkeypatch `os.environ`.
- No duplicated environment derivation: `tests/_testdb.py` is the single source of truth
  (`tests/unit/test_testdb_derivation.py:48` enforces it). Resolve the import from `_REPO_ROOT`, never
  from cwd, so it works in any worktree.
- This worktree's derived test-DB port is **5479**; the guard must not hardcode it.
- Do not run the harness for real: this unit needs no database. Unit tests only.
- The change stays uncommitted in the worktree until the native review outcome; delivery
  (commit/push/PR) is a human decision.
- Do not touch other worktrees or their containers.

## Decisions

**A — the two URLs must name the same database.** Compare `hostname`, `port` and `path` of
`urlparse(DATABASE_URL)` against `urlparse(TEST_ADMIN_DB_URL)`. No I/O, no new dependency. This is
literally the invariant the review said was missing.

**B — anchor to this worktree.** `DATABASE_URL`'s port must equal `_testdb.host_port()`, the port
`infra/test-db.sh` derives for this worktree. This is handoff option 2 **corrected**: the identity
lives in the port, not the dbname.

Why both: A alone still passes when the sentinel itself is a local dev URL (both variables agree on
the dev database). B alone still passes when a dev database happens to listen on this worktree's
derived port. Together they close the case the review flagged, for roughly ten lines.

Known residual, accepted: the derived port range is 5432..6431, so a worktree whose derived port is
exactly 5432 could still match a dev database on 5432. Deterministic, rare, and out of proportion to
the cost of closing it (`SELECT current_database()` on the startup path).

## Tasks

- [x] **T1** — `odd/tasks/r3-env-db-guard.md` (this record).
- [x] **T2** — RED: unit tests for `_ensure_environment` in `tests/unit/test_kb_calibration.py`:
      refuses when `TEST_ADMIN_DB_URL` is missing; refuses a non-local `DATABASE_URL` host; refuses
      when the two URLs name different databases (host, port, dbname); refuses when the port is not
      this worktree's derived port; accepts when both agree and the port is the derived one. Expected
      ports come from `_testdb.host_port()` or an explicit `TEST_DB_PORT` override, never a literal.
- [x] **T3** — GREEN: implement A+B in `_ensure_environment`, and move the function above the
      "I/O shell" boundary so its coverage claim is honest.
- [x] **T4** — Verify: unit suite green, RED evidence recorded, production-file diff empty.

## Acceptance criteria

1. `uv run pytest tests/unit/test_kb_calibration.py tests/unit/test_testdb_derivation.py -q` passes
   with **more tests than the 31 baseline**, and the new tests demonstrably fail on the pre-fix code.
2. `git diff --name-only -- app/ web/ db/ agent/ openspec/` is empty.
3. A local dev URL (local host, different port or dbname than the sentinel) is refused; only the
   database this worktree provisioned passes.
4. No environment derivation is duplicated in `scripts/kb_calibration.py`.

## Result

All four acceptance criteria met.

- **RED**: the three tests that pin the new behavior
  (`refuses_different_database_ports`, `refuses_different_database_names`,
  `refuses_a_port_not_derived_for_this_worktree`) failed on the unmodified script with `DID NOT
  RAISE`, before implementation.
- **GREEN**: `uv run pytest tests/unit/test_kb_calibration.py tests/unit/test_testdb_derivation.py -q`
  → **37 passed** (baseline 31; +6 new tests). Independently re-run by the orchestrator: 37 passed.
- `git diff --name-only -- app/ web/ db/ agent/ openspec/` → **empty**.
- `git diff --check` → clean.
- Diff: 45 lines in `scripts/kb_calibration.py`, 59 in `tests/unit/test_kb_calibration.py`.

**Native review** (`review-1afa35fbf13ef67d`, risk `medium`, lens `review-reliability`, 2 files, 104
changed lines): **approved**; acknowledgement consumed revision
`sha256:596498e149b9b8b2ded815f51d49f97280fbc0609054f966db2ce3af3265328a` and returned
`authority: burned`. The candidate excluded untracked paths, so this record is not part of the
reviewed bytes.

**Follow-up left open, deliberately not fixed here** (the review's own envelope classifies it as
non-blocking later work and forbids re-running the review for it):

- `R3-malformed-port` (WARNING, `deterministic`, `introduced`, informational):
  `scripts/kb_calibration.py:466` reads `.port` on both parsed URLs, so a malformed port in either
  variable raises an uncaught `ValueError` instead of the controlled `SystemExit` refusal. Closing it
  means wrapping the port reads (or normalizing a malformed port into the same refusal message).

## Applicable checks

- `uv run pytest tests/unit/test_kb_calibration.py tests/unit/test_testdb_derivation.py -q` →
  **37 passed**
- `git diff --name-only -- app/ web/ db/ agent/ openspec/` → **empty**
- `git diff --check` → clean

## Graph Check (Step 1 of the 5-Step Gate)

Consulted before writing: `database_url()` (`tests/_testdb.py:47`), `_default_database_url()`
(`tests/_testdb.py:43`), `env()` (`tests/_testdb.py:79`), `DATABASE_URL` (`db/migrate.sh:23`).
Dominant community for this area: `_testdb.py`, which owns the test-DB identity and is consumed by
all four conftests. The graph is what confirmed that `tests/_testdb.py` is the single derivation
source and that the calibration guard has no existing edge into it.

# ODD: r3-malformed-port

**Branch**: `odd/r3-malformed-port`
**Worktree**: `../lumat-agent-odd-r3-malformed-port`
**Base**: `26b463a2`
**Status**: implemented and verified; native review approved and its authority burned
**Advisory**: `R3-malformed-port` (WARNING, `evidence_class: deterministic`,
`causal_disposition: introduced`, non-blocking) returned by the native review of PR #259.

## Objective

Keep `_ensure_environment` (`scripts/kb_calibration.py`) inside its own refusal contract: every way of
pointing it at the wrong database must end in the controlled `SystemExit` with the documented message,
never in a bare traceback.

## Problem (verified in code)

The guard introduced by #259 compares the two connection URLs by their parsed identity:

```python
identity = (database.hostname, database.port, database.path)
admin_identity = (admin.hostname, admin.port, admin.path)
```

`urlparse().port` is a **property that parses on access**, and it raises a bare `ValueError` when the
port is not an integer. So a malformed port turns the guard's controlled refusal into a crash:

```
$ uv run python -c "from urllib.parse import urlparse; urlparse('postgresql://u@localhost:abc/db').port"
ValueError: Port could not be cast to integer value as 'abc'
```

Verified reproduction conditions:

- The malformed port must be on a **local** host for the port read to be reached at all. With a
  non-local host (`postgresql://u@host:abc/db`) the existing host check at line 464 fires first and
  the refusal stays controlled. The reachable path is `postgresql://app:app@localhost:abc/lumat`.
- **Correction to the handoff**: the handoff cites line 466, which is the *message* of the
  non-local-host `SystemExit`. The opening reads are at **474** (`database.port`) and **475**
  (`admin.port`), with a redundant third read at **490**.

Both URLs are attacker/copy-paste supplied, so both reads need the same treatment. Blast radius of the
crash is a raw traceback on an operator command — no data loss, which is why the review graded it
advisory and non-blocking.

## Scope

`scripts/kb_calibration.py` (the guard only) and `tests/unit/test_kb_calibration.py`. Nothing else.

## Authorized scope

- Human-approved on 2026-09-20: fix this advisory and create this worktree
  (`rapso worktree create r3-malformed-port --yes`, the `--yes` being the consequence of that
  approval, not a substitute for it).
- Sibling backlog items (`R3-001`, `R3-002`, `kb_scope`, `DEFAULT_MIN_SIM`) are **not** in this unit.

## Constraints

- Harness only: `git diff --name-only -- app/ web/ db/ agent/ openspec/` must stay empty.
- Strict TDD is active (`openspec/config.yaml` -> `testing.strict_tdd: true`, runner `uv run pytest`).
  RED first, then GREEN. The guard is pure and model-free: `monkeypatch` the environment.
- Do not run the harness for real: this unit needs no database and no model. Unit tests only.
- This worktree's derived test-DB port is **5734**; the guard must not hardcode it.
- The refusal message stays the guard's existing shape (`refusing to run: ...` + the `infra/test-db.sh
  env` hint), so operators keep one recognizable contract.
- The change stays uncommitted in the worktree until the native review outcome; delivery
  (commit/push/PR) is a human decision.
- Do not touch other worktrees or their containers.
- `.opencode/tools/package-lock.json` is untracked noise from `rapso worktree create`. Never commit it.

## Decisions

**A — one helper, called for each URL.** A module-private `_url_port(parsed, label)` returns
`parsed.port` and converts `ValueError` into the guard's `SystemExit`, so both reads (474/475) and the
derived-port comparison (490) share one behavior. Requires widening the existing import to
`from urllib.parse import ParseResult, urlparse`.

**B — refuse, do not default.** A malformed port is never coerced to `None` or to a fallback: the run
is refused, exactly as an unknown host or a mismatched database name already is.

## Acceptance criteria

1. `DATABASE_URL` with a malformed port on a local host exits with the controlled `SystemExit` and the
   documented refusal message, not `ValueError`.
2. The same malformed port on `TEST_ADMIN_DB_URL` behaves identically.
3. Every pre-existing guard behavior is unchanged: missing `TEST_ADMIN_DB_URL`, non-local host,
   different ports, different database names, and a port not derived for this worktree all still
   refuse; the matching derived test database still passes.

## Checks

```bash
cd ../lumat-agent-odd-r3-malformed-port
uv run pytest tests/unit/test_kb_calibration.py tests/unit/test_testdb_derivation.py -q
git diff --name-only -- app/ web/ db/ agent/ openspec/   # must be empty
```

## Progress

- [x] Graph check: `graphify query "kb_calibration _ensure_environment test database guard"` ->
      `_ensure_environment()` (`scripts/kb_calibration.py` L442, community 71) and
      `test_kb_calibration.py` (community 32); edge consulted: `kb_calibration` -> `tests/_testdb.py`
      (`host_port()`).
- [x] RED: `uv run pytest tests/unit/test_kb_calibration.py -q` — 2 failures, both leaked
      `ValueError: Port could not be cast to integer value as 'abc'` from `urlparse().port`.
- [x] GREEN: guarded port reads in `_ensure_environment` via `_url_port` for both URLs; focused
      file run passed (`35 passed`).
- [x] Full pure-test run and harness-diff check — `uv run pytest tests/unit/test_kb_calibration.py
      tests/unit/test_testdb_derivation.py -q` → `42 passed`; harness diff command printed nothing.
- [x] Native review, then human decision on delivery

## Review outcome

- Native review lineage `review-2616697131590798`, one consolidated lens (`review-reliability`,
  order 0) because the candidate is `medium` risk: 2 changed files, 40 changed lines.
- Consent relayed to the human and `granted`; the review ran over the frozen candidate tree
  `35988788dd58ca1134041dfe6dfe18ebc5c714d8` (untracked paths excluded, so this task document is
  not part of the reviewed bytes).
- Result: **approved, zero findings**. `authority: burned` on revision
  `sha256:5d3cb57299ab867972d2c0554fa9fa22a5b4ea6baf5a9264b6477e892a93a62a`.
- The reviewed candidate predates this record: the delivery commits below are what carries the
  task document into the PR.

## Delivery

Human decision pending. Reviewed candidate is uncommitted in the worktree as of the review.


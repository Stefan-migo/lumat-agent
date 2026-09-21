# ODD: relations-guard

**Branch**: `odd/relations-guard`
**Worktree**: `../lumat-agent-odd-relations-guard`
**Base**: `06768699`
**Status**: complete — pending review

## Objective

Close the one advisory finding the native review left on `memory-relations` (PR #271): candidate
discovery sits outside the judge's failure-degradation boundary, so a failure there escapes into the
memory write the judge was only supposed to enrich.

## Problem (verified)

`judge_memory_relations` (`app/services/relations.py`) called `find_candidates` **before** the `try`
that degrades judge failures. The function is called inline from three write paths — the agent tool
(`app/chat/assistant/tools/registry.py:275`), the panel route
(`app/panel/api/routes/clients.py:329`), and `close_conversation`
(`app/services/tukulpan.py`) — so anything raised by candidate discovery propagated into a write that
had already succeeded.

Two distinct failure classes, and the second is the one a bare `except` would not have fixed:

1. **Python-level**: a bug or unexpected value in the candidate search raises; the caller sees an
   error for a write that already succeeded.
2. **Database-level**: a real query error aborts the surrounding transaction. Merely catching it
   leaves the session poisoned — the caller's `commit()` then fails with `PendingRollbackError`, so
   the memory write is lost *and* the error surfaces. Catching without a savepoint does not deliver
   the guarantee it appears to deliver.

Origin: native review advisory `R3-judge-search-failure` (`reliability`, WARNING, deterministic,
`introduced`) at `app/services/relations.py:110-113`, registered as
`followup/relations-candidate-search-guard` in Engram.

## Fix

The candidate search now runs inside **its own savepoint, inside the degradation boundary**. Any
failure — Python or database — rolls back to the savepoint, is logged with `exc_info=True`, and the
judge returns no relations. The caller's transaction survives and the judged write still commits.
Control flow is otherwise unchanged: no retry, no re-raise, no new configuration, no new dependency.

This is the same savepoint pattern `upsert()` already uses for its own error recovery, not new
machinery. The documented trade-off carries over: `session.begin_nested()` flushes pending caller
state before taking the savepoint — accepted there and accepted here.

## Authorized scope

- `app/services/relations.py` — the guard.
- `tests/spec/test_memory_relations_spec.py` — the regression tests.
- `odd/tasks/relations-guard.md` — this record.

## Out of scope (do not touch)

- The candidate gate, `REL_MIN_SIM`, `AUTO_JUDGE_CONFIDENCE`, the relation vocabulary, the read
  paths, the human queue, or any other `memory-relations` behaviour.
- Retrying a failed judge or re-attempting after a degraded pass — the write is already done and the
  verdict is enrichment, not a transaction to complete.
- The other open items: H4 outbox runner (handoff `handoff/h4-outbox-runner`), catch-up deploy,
  batch compression, prompt store, memory sync.

## Tasks

- [x] **T1 — Regression tests first.** Two tests: a Python-level candidate failure degrades to no
  relation and the write still commits; a real database error leaves the caller's transaction usable
  and the write still commits. Both assert the warning is logged.
- [x] **T2 — Guard.** Candidate search inside a savepoint inside the degradation boundary.
- [x] **T3 — Verify.** Focused tests, then the full suite, counts measured.

## Acceptance criteria

1. A candidate-search exception writes no relation, logs a warning, and does not abort the judged
   write — proven by a test that forces it.
2. A real database error in candidate discovery leaves the caller able to commit — proven by a test
   that forces one, not by asserting on a mocked exception alone.
3. The full suite is green; the baseline was measured before the change.

## Checks

TDD mode: **strict, enabled** — source `openspec/config.yaml` (`testing.strict_tdd: true`,
`apply.tdd: true`). Runner:

```bash
export PATH="$HOME/.local/bin:$PATH"
eval "$(infra/test-db.sh env)"
uv run pytest tests/
```

`addopts = "-q"` is already set; a second `-q` suppresses the summary line. No linter, formatter, or
type checker for the backend.

## Evidence

- Full suite after the change: **`1044 passed, 2 warnings in 109.40s`**.
- Baseline on this base: **`1042 passed, 2 warnings`**, derived as `1044 − 2`. The test diff adds
  exactly two test functions and the source diff touches nothing else, so the subtraction is sound.
- The baseline was **not** measured directly, and that is stated rather than glossed: running the
  suite with the change stashed was attempted **twice and stalled both times** in the pre-existing,
  undiagnosed flake recorded in `odd/tasks/pytest-timeout.md` (a session left `idle in transaction`
  blocking `clean_db`). The stall reproducing with this change removed is evidence it is not caused
  by this unit — but it is also why the number is derived.
- RED observed: both new tests failed with the fix absent — the mocked `RuntimeError` escaped
  (`test_mem11_candidate_search_failure_degrades_to_no_relation`) and the real `ProgrammingError`
  escaped (`..._leaves_the_transaction_usable`).
- GREEN observed: `4 passed` on the focused selection after the fix.

## Progress

- [x] Worktree created and provisioned (base `06768699`); `.opencode/tools/package-lock.json` removed.
- [x] T1–T3.

## Notes for the executor

- `main` moves in parallel: it advanced during the previous unit and other sessions are active. The
  base above is the merge commit of PR #271; re-measure before relying on it.
- `infra/.env` is not copied by `rapso worktree provision` — copied manually here.
- This unit exists because a native review finding was **not** folded into the frozen candidate it
  came from. Small as it is, it travels its own work unit so the receipt stays honest.

# ODD: kb-calibration-state-restore

**Make `run()` restore the process state it overrides.**

## Objective

`run()` in `scripts/kb_calibration.py` replaces `kb.chunk_text` (when a
chunking override is used) and `kb.EMBED_MODEL` / `kb._embedder` (when
`--model` is used) and never puts them back. Restore all three on every exit
path — normal and exceptional — so a second `run()` in the same process cannot
silently keep a previous run's overrides.

## Problem

This is the deferred `R3-chunker-state-leak` WARNING from the native review of
`odd/kb-chunking-axis` (Engram `debt/r3-kb-chunker-state-leak`, #4750). The
reviewer's claim, verified against the code at `main 77961c29`:

- `scripts/kb_calibration.py:662` captures `original_chunk_text` but uses it
  only as the base for `make_chunker` (`:672`). It is never re-assigned.
- `:674-678` sets `kb.EMBED_MODEL = model` and
  `kb._embedder = TextEmbedding(model_name=model)` with no restore.
  `get_embedder()` (`app/services/kb.py:117`) returns the module-level
  `_embedder` whenever it is not `None`, so after a `--model` run the override
  stays live for the life of the process.

**Impact is low but real.** The harness is a CLI that calls `run()` once per
process (`main` -> `run` -> exit), so the leak never bites the documented use.
It bites a programmatic caller that calls `run()` more than once: a second call
without overrides reports the default chunking and default model while still
using the previous call's overrides — a measurement that lies about what it
measured. That is the same failure class the harness exists to prevent.

## Why this fix

The harness's whole value is that a measurement is trustworthy. Keeping the
overrides after `run()` returns makes a later measurement in the same process
silently wrong, and the wrongness is invisible in the report (it prints the
default values). A restore on the way out is the minimal, native fix; there is
no simpler form that keeps the intended behavior.

## Scope

**In:** `scripts/kb_calibration.py` (extract the override/restore into a small
context manager, use it in `run()`), `tests/unit/test_kb_calibration.py`
(model-free tests for the restore), and this record.

**Out (explicitly):** the CLI surface, the report shape, the chunking math, the
embedder choice, the corpus, and any file outside these three. No production
module is touched. This unit changes only *that the harness cleans up after
itself*, not *what* it measures.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-kb-calibration-state-restore`
- Branch: `odd/kb-calibration-state-restore`
- Base: `a2092b92` (= `origin/main` at branch time; includes PR #318 and release
  v2026.09.4). Verified with `git rev-parse HEAD` inside the fresh worktree.
- Files:
  - `odd/tasks/kb-calibration-state-restore.md` (this record)
  - `scripts/kb_calibration.py`
  - `tests/unit/test_kb_calibration.py`

## Constraints

- **Strict TDD: ON** — `openspec/config.yaml` (`testing.strict_tdd: true`),
  runner `uv run pytest tests/`.
- Model-free: `tests/unit/test_kb_calibration.py` deliberately never imports
  `app.*` (no DB, no network, no `fastembed`). The restore tests stay on that
  side of the line: they drive the context manager with a fake module object
  and, for the embedder path, a stubbed `fastembed` in `sys.modules`.
- The CLI must keep its behavior: `--chunk-size` / `--chunk-overlap` / `--model`
  still change what is measured, and the report still records the *effective*
  model and chunking.

## Decisions

- **D1 — Extract a context manager instead of wrapping `run()`'s body in a bare
  `try/finally`.** The bare version would work, but it would be untestable: the
  unit suite cannot call `run()` (DB + real model). A module-level
  `override_kb(...)` context manager carries the capture/restore logic and
  `run()` only calls it. Same behavior, and the restore is pinned by tests.
- **D2 — Restore in `finally`, always, even when nothing was overridden.** A
  no-op restore is three assignments; the guarantee ("whatever `run()` does,
  the module state is what it was") is worth more than the saved branch.
- **D3 — The report is built inside the override scope.** `model_metadata()`
  reads `kb.EMBED_MODEL`, so building it after the restore would report the
  original model instead of the measured one. The context manager wraps the
  report construction.

## Tasks

- [x] **T1** — this record (before the first source change).
- [x] **T2** — RED: model-free tests for `override_kb` in
      `tests/unit/test_kb_calibration.py` (restore after normal exit, restore
      after an exception, no-op when nothing is overridden, embedder path with a
      stubbed `fastembed`). Observed failure: `override_kb` does not exist yet.
- [x] **T3** — GREEN: add `override_kb` to `scripts/kb_calibration.py` and use
      it in `run()`.
- [x] **T4** — Verify: the focused unit file, the full backend suite, and a
      diff check.

## Applicable checks

- `uv run pytest tests/unit/test_kb_calibration.py -q`
- `uv run pytest tests/` (full suite; read the exit code, not the suppressed
  count line — `pyproject.toml` sets `addopts = "-q"`)
- `git diff --name-only` -> only the authorized files
- `git diff --check` -> no whitespace errors

## Graph Check (Step 1 of the 5-Step Gate)

Consulted before writing, against `graphify-out/graph.json` (7442 nodes /
15496 edges):

- `graphify query "knowledge base retrieval calibration harness and embedding
  model override"` -> community `kb_calibration.py` and its test community
  `test_kb_calibration.py`.
- `graphify path "kb_calibration.py" "app/services/kb.py"` -> 1 hop,
  `kb_calibration.py --imports_from [EXTRACTED]--> services/kb.py`. Confirms the
  harness's only production coupling is the `kb` module whose `chunk_text` /
  `EMBED_MODEL` / `_embedder` it mutates.
- God nodes (`GRAPH_REPORT.md`): none of the top-10 touches this area; the
  harness is a leaf consumer of `kb.py`.

## Progress

- [x] Created this record before the first source change.
- RED: `uv run pytest tests/unit/test_kb_calibration.py -q` failed with four
  `AttributeError` failures because `override_kb` did not exist.
- GREEN: the same command passed (`41 passed`); the full suite reached 100% but
  exited 1 because the test database at `localhost:5529` was unavailable.
- Verification correction: strengthened the exception test to override all three
  attributes and documented the no-op test contract; production code unchanged.

## Recovery

Resume with `mem_context`, then the project-scoped `mem_search` for
`kb-calibration-state-restore`, then `mem_get_observation` for the full record,
then read this file.

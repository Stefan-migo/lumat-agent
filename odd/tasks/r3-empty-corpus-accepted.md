# ODD: r3-empty-corpus-accepted

**Branch**: `odd/r3-empty-corpus-accepted`
**Worktree**: `../lumat-agent-odd-r3-empty-corpus-accepted`
**Base**: `0d8fed79`
**Status**: merged — PR #260 (`f0338c1d`). Implemented and verified; native review approved with no findings and its authority burned.
**Advisory**: `R3-empty-corpus-accepted` (WARNING) from native review `review-ba9c8a35d22602f6`, the
sibling of the `R3-env-database-mismatch` advisory closed by PR #259.

## Objective

Make `load_corpus` refuse a corpus that declares no documents or no queries, so the calibration
harness cannot return a decision-grade report built from zero data.

## Problem (verified by running the loader)

`load_corpus` (`scripts/kb_calibration.py:156`) promises "Raises ValueError on any violation", but
an absent or empty section is silently accepted:

- line 158: `raw = yaml.safe_load(...) or {}` turns an empty file into `{}`;
- line 161: `for entry in raw.get("documents") or []` — a missing key or an empty list iterates zero
  times;
- line 181: the same shape for `queries`.

Measured with the shipped code (empty temp file, no database, no model):

```
empty file      -> accepted: docs=0 queries=0
   summarize([]) -> balanced_accuracy: 0.5 for absolute, margin and relative;
                    best_absolute.threshold: 0.0
   compare_rules([]) -> the same three rules, all 0.5, all totals 0
```

Nothing raises, nothing warns, and `main()` would exit 0. The report is well formed and every
number in it is meaningless: `balanced_accuracy: 0.5` is the empty-set value, and
`threshold: 0.0` reads like a result. That matters more here than in an ordinary script, because this
harness exists to decide the production `DEFAULT_MIN_SIM` rule: it would hand a reviewer a decision
number derived from no queries at all.

A second malformed shape was checked while exploring: a non-empty but non-list section (for example
`documents: "abc"`) reaches the entry loop and raises `TypeError`, not `ValueError`. That is loud
rather than silent, and the review flagged emptiness — see D2.

## Scope

`load_corpus` in `scripts/kb_calibration.py`, and its tests in `tests/unit/test_kb_calibration.py`.
Nothing else.

## Authorized scope

- Human instruction on 2026-09-20: continue with the next backlog item, `R3-empty-corpus-accepted`.
- Worktree and branch created with that authorization, same scheme as PR #259.

## Constraints

- Harness only: `git diff --name-only -- app/ web/ db/ agent/ openspec/` must stay empty.
- Strict TDD is active (`openspec/config.yaml` -> `testing.strict_tdd: true`, runner `uv run pytest`).
  These tests are pure and use `tmp_path`: no database, no model.
- Do not run the harness against a database.
- The shipped corpus must keep loading unchanged (24 documents, 52 queries).
- The change stays uncommitted until the native review outcome; delivery is a human decision.
- Do not touch other worktrees or containers. This worktree's derived test-DB port is 5598; it is not
  needed for this unit.

## Decisions

**D1 — both sections must be present and non-empty.** `load_corpus` raises `ValueError` when
`documents` is missing or empty, and when `queries` is missing or empty, with a message that names
the section. Absent and empty collapse to the same refusal: neither carries data, and the pathology
the review described does not distinguish them.

**D2 — a wrong-typed section stays out of scope, deliberately.** `documents: "abc"` iterates as
characters and fails on `entry["id"]` with `TypeError`. It is a real edge, but it is a loud crash
rather than a silent empty report, and the advisory is specifically about required/non-empty
sections. Recorded here as a candidate follow-up; not bundled, so the diff stays about the flagged
pathology.

**D3 — do not tighten `Corpus`.** The dataclass keeps accepting empty tuples; the refusal belongs at
the loader, which is where the promise lives, and where the tests can reach it without a database.

## Tasks

- [x] **T1** — `odd/tasks/r3-empty-corpus-accepted.md` (this record).
- [x] **T2** — RED: unit tests in `tests/unit/test_kb_calibration.py` pinning the refusals with
      `tmp_path`: empty file; `documents` missing; `queries` missing; `documents: []`; `queries: []`.
      Each asserts `ValueError` and that the message names the section. These must fail on the
      current loader.
- [x] **T3** — GREEN: require both sections in `load_corpus`, keeping the existing per-entry
      validation untouched.
- [x] **T4** — Verify: unit suite green, RED evidence recorded, the shipped corpus still loads,
      production-file diff empty.

## Progress

- RED observed before implementation: the five new tests each failed with `Failed: DID NOT RAISE ValueError`.
- GREEN observed: `uv run pytest tests/unit/test_kb_calibration.py tests/unit/test_testdb_derivation.py -q -rA` — 42 passed.
- Corpus check observed: the pure loader printed `24 52`.
- Scope and whitespace checks observed: both commands produced no output.

## Acceptance criteria

1. `uv run pytest tests/unit/test_kb_calibration.py tests/unit/test_testdb_derivation.py -q` passes
   with **more tests than the 37 baseline**, and the new tests demonstrably fail on the current code.
2. `git diff --name-only -- app/ web/ db/ agent/ openspec/` is empty.
3. Every empty or missing-section corpus is refused with `ValueError`; no path returns an empty
   `Corpus` that later produces a report.
4. The shipped `scripts/kb_calibration_corpus.yaml` still loads with 24 documents and 52 queries.

## Result

All four acceptance criteria met.

- **RED**: the five new tests failed on the unmodified loader with `Failed: DID NOT RAISE ValueError`.
- **GREEN**: `uv run pytest tests/unit/test_kb_calibration.py tests/unit/test_testdb_derivation.py -q`
  → **42 passed** (baseline 37; +5). Independently re-run by the orchestrator: 42 passed.
- Shipped corpus still loads: the pure loader prints `24 52`.
- `git diff --name-only -- app/ web/ db/ agent/ openspec/` → **empty**; `git diff --check` → clean.
- Diff: 4 lines in `scripts/kb_calibration.py`, 60 in `tests/unit/test_kb_calibration.py`.
  The positive control is an addition to the existing `test_corpus_loads_and_ids_are_unique`
  (24 documents / 52 queries) rather than a new test.

**Native review** (`review-6a0f5a17b6d15bb8`, risk `medium`, lens `review-reliability`, 2 files, 64
changed lines): **approved with no findings**. Acknowledgement consumed revision
`sha256:8a5258136ddc033f3d0089cac8f0c45abb3a4163a485f1a490e43a47671e459c` and returned
`authority: burned`. The candidate excluded untracked paths, so this record is not part of the
reviewed bytes.

The only follow-up this unit leaves is the one already recorded in D2: a wrong-typed section
(`documents: "abc"`) still fails with `TypeError` instead of a clear `ValueError`. It is loud rather
than silent, and it was deliberately not bundled.

## Applicable checks

- `uv run pytest tests/unit/test_kb_calibration.py tests/unit/test_testdb_derivation.py -q` →
  **42 passed**
- `uv run python -c "import sys; sys.path.insert(0,'scripts'); import kb_calibration as c; k=c.load_corpus(); print(len(k.docs), len(k.queries))"` → `24 52`
- `git diff --name-only -- app/ web/ db/ agent/ openspec/` → **empty**
- `git diff --check` → clean

## Graph Check (Step 1 of the 5-Step Gate)

Consulted before writing: `load_corpus()` (`scripts/kb_calibration.py:156`), `Corpus`
(`scripts/kb_calibration.py:133`), `ingest_corpus()` (`scripts/kb_calibration.py:496`), `run()`
(`scripts/kb_calibration.py:611`), `summarize()`/`compare_rules()`
(`scripts/kb_calibration.py:429`). Dominant community for this area: `kb_calibration.py`, with the
only consumer edge being `run()` and the test module. The graph is what confirmed that `load_corpus`
has a single call site, so tightening it cannot change behavior anywhere else.

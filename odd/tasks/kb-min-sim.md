# ODD: kb-min-sim

**Branch**: `odd/kb-min-sim`
**Worktree**: `../lumat-agent-odd-kb-min-sim`
**Base**: `cdda793c`
**Status**: implemented and verified; native review approved and its authority burned
**Source**: the last open item of the KB backlog (handoff Engram #4467) — the `DEFAULT_MIN_SIM` decision.

## Objective

Move the production relevance threshold off a value the benchmark proved wrong in both directions,
choosing a point on the measured trade-off **deliberately** and recording why that point and not the
fitted optimum.

## What the decision rests on (measured, real model, this worktree)

Re-ran the harness on current `main` and reproduced slice 1 exactly (separation `−0.335`, best absolute
`0.4752` → balanced `0.791`/`0.801`, margin `0.797`/`0.804`, relative `0.882`/`0.848`). The instrument
is reproducible, so the numbers below are decision-grade.

**The reframe that was not in the handoff: `min_sim` is the escalation trigger, not just a retrieval
gate.** `app/chat/nodes/respond.py:141-152` — `if not chunks` replies `CANNOT_ANSWER_REPLY`, logs the
question as unresolved (CM-6) and sets `escalate=True` with `escalate_reason="kb_miss"`, with no LLM
spend. So the shipped `0.65` does not merely drop context: it **escalates 20 of 30 answerable queries
to a human advisor**, and 15 of those have the correct document **at rank 1** (F1). The measured cost
of the current value is a human queue that is roughly two-thirds false positives.

| threshold | recall (answerable) | false accept (irrelevant) | balanced | false escalations |
|---|---|---|---|---|
| **0.65 (shipped)** | 0.333 / 0.321 | 0.136 / 0.125 | 0.598 | **20 of 30** |
| ~0.55 | ~0.700 | ~0.227 | ~0.736 | ~9 of 30 |
| **0.4752** (harness optimum) | 0.900 / 0.893 | 0.318 / 0.292 | **0.791 / 0.801** | ~3 of 30 |
| floor + `top_k=5` | recall@5 = 0.967 / 0.964 | everything passes | — | 0 |

**The optimum is a knife edge, not a plateau** (measured in this run): within 0.5 points of the maximum
balanced accuracy there is a **single** threshold value. Moving ±0.025 costs 3–4 balanced points
(`0.45 → 0.779`, `0.4752 → 0.824`, `0.50 → 0.791`, `0.55 → 0.736`). That is the signature of fitting 52
queries, so the harness's own argmax is **not** defensible as a production constant.

## Decision (human-approved, 2026-09-20)

**Retune `DEFAULT_MIN_SIM` from `0.65` to `0.50`.** Chosen over the two alternatives:

- **Not the fitted optimum (`0.4752`)**: it is the argmax of a knife-edge curve computed from 52
  queries. `0.50` sits on the same balanced level (`0.791`/`0.801` measured at `0.4752`) while being a
  round, conservative value and not a data-fitted one.
- **Not the floor (`-1`, rely on `top_k=5`)**: it measures best on recall@5 (`0.967`/`0.964`) and its
  cost is bounded by `top_k`, but `if not chunks` is simultaneously the refusal **and** the
  deterministic escalation trigger. A floor removes both: uncovered questions would stop escalating
  deterministically and that decision would move to the LLM. That is a design change with a KB-2 spec
  delta, not a constant change, so it is a **separate unit**.

This keeps the mechanism unchanged: gate, deterministic escalation, and the no-LLM cost guardrail all
stay. No spec delta is needed — KB-2 requires "a configured top-k and relevance threshold", and its
mechanism is untouched.

**Honest framing:** F2 stands (no absolute threshold separates the classes; the worst irrelevant scores
`0.6976` and beats 24 of 30 answerables). This unit is **harm reduction, not a fix**, and the record
says so rather than pretending the threshold question is closed.

## Scope

`app/services/kb.py` (the constant and the module docstring that quotes it),
`tests/integration/test_kb.py` (the behaviour test), `scripts/kb_calibration.py` (the instrument defect
below, which had to be fixed before this unit's own end-to-end criterion could be met), and this record.
Nothing else.

## Instrument defect found while verifying (and fixed here)

The end-to-end check exposed a defect in the decision instrument itself. `scripts/kb_calibration.py`
built its per-query production acceptance with a **hardcoded `0.65`** and only *labelled* it with the
constant:

```python
"accepted_at_production_0_65": accept_absolute(o.scores, 0.65)   # before
...
print(f"  at the shipped 0.65: {production} ...")               # before
```

`production_threshold` in the same report *does* read `kb.DEFAULT_MIN_SIM`, so after the retune the
report contradicted itself: `production min_sim: 0.5` on one line, `at the shipped 0.65` on the next.
The metric had never followed the constant — in slice 1 it was right only by coincidence, because
production was `0.65` at the time. It is a blind instrument, not a stale label.

Fixed by reading the constant (`accept_absolute(o.scores, kb.DEFAULT_MIN_SIM)`), renaming the field to
`accepted_at_production_threshold`, and printing the actual value (taken from the report it already
carries). No test depended on the field name or on the literal. The harness docstring's stale
`min_sim=0.65` problem statement was updated in the same pass.

**The decision is not contaminated by this**: the knife-edge curve, the best-absolute figures and the
recall@5 numbers all come from the pure core (`accept_absolute` / `metrics_at` / the sweeps) and the
per-query score lists, never from the hardcoded field. This defect is recorded here rather than in
`odd/tasks/kb-retrieval-calibration.md`, which is frozen by the repo's receipt policy.

## Explicitly out of scope

- The floor option and any escalation redesign (separate unit, KB-2 spec delta).
- The relative/margin rule shapes (measured: the relative rule's edge collapses from `+0.091` to
  `+0.022` once the title axis shifts the distribution, and its grid is data-derived).
- The title/embedding axis (slice 2, already measured; its naked-title micro-chunk is its own finding).
- `odd/tasks/kb-retrieval-calibration.md` — **frozen by the repo's receipt policy**; that unit's
  outcome lives in its PR body and Engram, not in the document.

## Constraints

- Strict TDD is active (`openspec/config.yaml` -> `testing.strict_tdd: true`), runner `uv run pytest`.
  RED before GREEN, observed.
- Test DB for this worktree: derived port **5875**, project
  `lumat-test-lumat-agent-odd-kb-min-sim`; already up with migrations applied. Run
  `eval "$(bash infra/test-db.sh env)"` before any test or migration.
- The `fake_embedder` fixture (`tests/integration/conftest.py:97`) builds **multi-hot char-trigram**
  vectors, so cosine similarity takes intermediate values and a controlled band is constructible. A
  test that pins a band must assert the band itself, so it fails loudly if the fixture changes instead
  of passing vacuously.
- Run the **whole** suite, not just the KB files: a constant consumed by `respond`, `research_triage`
  and the panel probe can ripple.
- Nothing is committed until the review outcome; delivery is a human decision.
- `.opencode/tools/package-lock.json` is untracked noise; never commit it.

## Acceptance criteria

1. A test proves the behaviour change at the default threshold: with a query whose fake-embedder
   similarity to the seeded document is asserted to lie in `[0.50, 0.65)`, `kb.retrieve(...)` returns
   that document. It fails against the shipped `0.65` and passes at `0.50`.
2. The existing "unrelated query → `[]`" threshold test still passes: unrelated text scores far below
   both values, so the refusal path stays covered.
3. `uv run pytest tests/ -q` is green, with no test asserting the old constant.
4. The module docstring no longer quotes a stale threshold.
5. A real-model harness re-run reports the **new** shipped threshold and the predicted behaviour at it
   (`~0.900` recall, `~0.318` false accept), confirming end-to-end that the retune did what the evidence
   said it would.

## Checks

```bash
cd ../lumat-agent-odd-kb-min-sim
eval "$(bash infra/test-db.sh env)"
uv run pytest tests/ -q
uv run python scripts/kb_calibration.py --json /tmp/kb-min-sim-after.json
git diff --name-only -- web/ db/ agent/ openspec/   # must be empty
```

## Progress

- [x] Graph check: `graphify query` over the KB area in earlier units; consumers of the constant
      confirmed by reading: `app/chat/nodes/respond.py:135`, `app/chat/subgraphs/research_triage.py:97`,
      `app/panel/api/routes/kb.py:82`, `retrieve()` default (`app/services/kb.py:326`), and the harness
      report field `production_threshold` (`scripts/kb_calibration.py:687`).
- [x] Measurement: harness re-run on current `main`, slice 1 reproduced exactly; knife-edge curve and
      recall@5 computed from the report (`/tmp/kb-min-sim.json`).
- [x] RED: `uv run pytest tests/integration/test_kb.py::test_kb2_default_threshold_returns_intermediate_similarity_hit -q`
      failed against `0.65` with `assert [] == [1]`; the fixture pair was
      `manual calefont revision anual seguridad mantenimiento precio visita tecnica` /
      `calefont seguridad`, cosine `0.5121475197`.
- [x] GREEN: changed `DEFAULT_MIN_SIM` and the module docstring to `0.50`; the focused
      test passed.
- [x] Full suite green — run as two non-overlapping invocations of the whole `tests/` tree:
      `tests/integration` -> **495 passed, exit 0**; `tests/functional tests/unit tests/spec` ->
      **522 passed, exit 0**. The single combined invocation stalled in the environment, not in a test
      (see the environment note below).
- [x] Real-model re-run confirms the prediction — after fixing the instrument (above) the harness
      reports `at the shipped 0.5: 34 of 52 queries accepted; 30 should have been answered` (unscoped)
      and `32 of 52; 28` (customer), matching the harness's own best-absolute recall of `0.900`/`0.893`
      exactly. The retune landed on the measured optimum level.
- [x] Instrument defect found, fixed and re-verified: `accepted_at_production_0_65` was built from a
      hardcoded `0.65`; it now reads `kb.DEFAULT_MIN_SIM`.
      `tests/unit/test_kb_calibration.py` (the harness's only importer) -> **35 passed, exit 0**.
- [x] Native review, then human decision on delivery

## Review outcome

- Native lineage `review-5391d256d8921f1a`, `medium` risk, one consolidated lens
  (`review-reliability`), 3 files / 65 changed lines. Consent relayed to the human and `granted`.
- **Approved.** `authority: burned` on revision
  `sha256:795ef405b14c3583a620d96fb8ce31800d08e2c32ab265fbbbd81a58b7614884`.
- One **advisory** finding arrived with the approval — non-blocking, informational, and explicitly not
  a reason to re-run this review:

  > **R3-001** (WARNING, `inferential`, `introduced`) at `app/services/kb.py:40`: "Lowering the
  > default similarity threshold to 0.50 is covered only for an intermediate positive match; no
  > changed test proves that irrelevant queries remain rejected at the new threshold."

  **Assessed: the coverage claim does not hold.** The reviewer sees only the diff, and the rejection is
  proven by a test the candidate did not touch: `tests/integration/test_kb.py:289-298`
  (`test_kb2_retrieval_threshold_miss`) calls `kb.retrieve(...)` **without** `min_sim`, so it exercises
  the new default, and it was run green against `0.50` (`exit 0`). Acceptance criterion 2 is met.

  **What the finding does point at, smaller and real:** that same test's trailing comment still reads
  `# unrelated -> below min_sim 0.65`, naming a default that no longer exists. That is a one-word doc
  drift, not a coverage gap. It is deliberately **not** fixed here: changing a reviewed file after the
  receipt would deliver bytes the review never saw. It belongs to a later unit.


## Environment note (honest, not a test result)

The first whole-suite attempt stalled at 27% inside `functional/conftest.py::clean_db` (the
`TRUNCATE`-per-test fixture). The database was healthy when checked — no stale connections, no locks —
and the container logs show the real cause: checkpoints taking ~55 s and syncing 141,340 files, plus
autovacuum `skipping analyze ... lock not available`. That is a slow-storage environment, not a failing
test. The suite passes with the tree split into two invocations, and the two invocations cover it
without overlap.

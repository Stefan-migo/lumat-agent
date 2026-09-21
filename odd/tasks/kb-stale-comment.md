# ODD: kb-stale-comment

**Branch**: `odd/kb-stale-comment`
**Worktree**: `../lumat-agent-odd-kb-stale-comment`
**Base**: `bd50b18c`
**Status**: implemented and verified; native review approved and its authority burned
**Origin**: residue of PR #268 (`DEFAULT_MIN_SIM` `0.65` -> `0.50`). Left out of that PR on purpose:
editing an already-reviewed file after the receipt delivers bytes the review never saw.

## Objective

The comment on `test_kb2_retrieval_threshold_miss` must state the threshold actually in force, so the
test documents reality instead of a retired default.

## Problem (verified in code)

`tests/integration/test_kb.py:297` read `# unrelated -> below min_sim 0.65`, while
`app/services/kb.py:40` says `DEFAULT_MIN_SIM = 0.50` since #268. The assertion itself was already
correct: the file is green before and after the edit. This is comment drift of one line, not a
behavior bug.

## Scope

`tests/integration/test_kb.py` (one comment). Nothing else.

## Authorized scope

- Human-approved on 2026-09-20: fix this stale comment and create this worktree
  (`rapso worktree create kb-stale-comment --yes`, the `--yes` being the consequence of that
  approval, not a substitute for it).
- Sibling backlog items are **not** in this unit: the coverage unit (`min_sim` as floor + `top_k`,
  with the KB-2 escalation delta) and the optional graphify label refresh.

## Constraints

- Harness only: `git diff --name-only -- app/ web/ db/ agent/ openspec/` must stay empty.
- There is no RED/GREEN pair: a comment cannot fail a test. The proportional check is the focused
  file, green before and after by construction.
- The change stays uncommitted until the native review outcome; delivery (commit/push/PR) is a human
  decision.
- Do not touch other worktrees or their containers.
- `.opencode/tools/package-lock.json` is untracked noise from `rapso worktree create`. Never commit it.

## Checks

```bash
cd ../lumat-agent-odd-kb-stale-comment
eval "$(bash infra/test-db.sh env)"
uv run pytest tests/integration/test_kb.py -q
git diff --name-only -- app/ web/ db/ agent/ openspec/   # must be empty
```

## Progress

- [x] Graph check: `graphify query "kb retrieval min_sim threshold test_kb"` ->
      `test_kb2_retrieval_threshold_miss()` (`tests/integration/test_kb.py` L289, community 42),
      `retrieve()` (`app/services/kb.py` L322), community `min_sim as Escalation Trigger`
      (`odd/tasks/kb-min-sim.md`). Graph fresh at `bd50b18c`.
- [x] Baseline: `uv run pytest tests/integration/test_kb.py -q` -> 21 passed.
- [x] Fix: comment `0.65` -> `0.50`; one line, `tests/integration/test_kb.py` only.
- [x] Verify: `uv run pytest tests/integration/test_kb.py -q` -> 21 passed; production diff empty.
- [x] Native review, then human decision on delivery

## Review outcome

- Native review lineage `review-51abe8b850bf71b2`, one consolidated lens (`review-reliability`,
  order 0) because the candidate is `medium` risk: 1 changed file, 2 changed lines.
- Consent relayed to the human and `granted`; the review ran over the frozen candidate tree
  `9e7e6a5c56e52269fcbe711766db309028fdf794` (untracked paths excluded, so this task document is not
  part of the reviewed bytes).
- Result: **approved, zero findings**. Reviewer evidence: the change edits only an explanatory
  comment, so it introduces no behavioral or test-reliability regression.
- `authority: burned` on revision
  `sha256:d474c3440e97e09ed6880d509d98634dc2ffece5b340b96385923e03373f61a1`.
- The reviewed candidate predates this record: the delivery commit carries this task document into
  the PR.

## Delivery

Human decision pending. The reviewed candidate is uncommitted in the worktree.

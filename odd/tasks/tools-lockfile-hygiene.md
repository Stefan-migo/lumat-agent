# ODD: tools-lockfile-hygiene

**Branch**: `odd/tools-lockfile-hygiene`
**Worktree**: `../lumat-agent-odd-tools-lockfile-hygiene`
**Base**: `28b72cf4` (= `main` at branch time)
**Status**: complete — implementation verified; the native review never closed (see Review)

## Objective

Stop `.opencode/tools/package-lock.json` from appearing as an untracked file that dirties the review
candidate of every new worktree.

## Problem (verified)

- `.opencode/tools/package.json` is tracked, and `.opencode/.gitignore:1` ignores `node_modules/`.
- The lockfile was **neither tracked nor ignored**: `git check-ignore -v .opencode/tools/package-lock.json`
  reported nothing, and it did not appear in `git ls-files`.
- `rapso worktree create` provisions the tools install root (npm install), so the lockfile materialises
  untracked in **every** new worktree.
- Consequence, already experienced: the RDD candidate carries an unrelated untracked path, forcing
  `--untracked-scope=exclude --expected-untracked-inventory=<digest>` on every `assess` / `status`; and it
  caused a real incident when a `git add -A` swept it into a commit.

## Why commit it, not ignore it

The repository already answers this:

- `.opencode/package-lock.json` **and** `web/package-lock.json` are both tracked.
- `.opencode/.gitignore` ignores only `bun.lock`, deliberately: npm is the chosen package manager, and
  `package-lock.json` is the file that is meant to be committed.

Committing it also pins the resolved `@opencode-ai/plugin` version for this install root (1.18.32 at this
base) and removes the recurring dirty path.

**Known ceiling, declared:** `.opencode/tools/package.json` declares `"@opencode-ai/plugin": "latest"`, so
the lockfile will legitimately change when a newer plugin version is published. That change then arrives as
one real, reviewable commit instead of as permanent untracked noise on every worktree.

## Scope

- **IN**: add `.opencode/tools/package-lock.json` to the repository.
- **OUT**: no `.gitignore` change (the tracked-lockfile convention is the intended one, and `node_modules/`
  is already ignored). W3 (the 22-vs-20 tool-count comment) remains a separate decision.

## Constraints

- One commit for this concern (`af948a5c`); the record commits are documentation only.
- No push, no PR, no merge without an explicit request — honored throughout implementation; the push and
  PR follow an explicit later request.

## Resolved execution config

- **TDD**: strict TDD is active (`openspec/config.yaml:38`), but this change adds a **generated artifact**
  and alters no behavior, so there is no RED to observe and no test can cover it. Stated rather than faked.
- **Test runner**: `uv run pytest tests/` (not applicable to this change; no source file is touched).
- **Graph Check**: not applicable — no module is edited and no edge changes. Recorded explicitly instead of
  claiming a query that would carry no information.

## Checklist

- [x] **T1**: commit `.opencode/tools/package-lock.json` — `af948a5c`.
- [x] **T2**: confirm the lockfile is in sync with `package.json` and is valid JSON.
- [x] **T3**: confirm `node_modules/` is still ignored and the lockfile is now tracked.
- [ ] **T4**: assess the branch and follow the returned RDD transition. — **blocked, not closed.**
      The review never captured; see Review.

## Acceptance criteria

- `.opencode/tools/package-lock.json` is tracked and identical to what the provisioner generates.
- No `.gitignore` change; `node_modules/` stays ignored.
- A freshly provisioned worktree no longer shows that path as untracked.

## Verification evidence

All observed on the final candidate (`29ab8461`), tree clean before and after each check.

| Task | Command | Observed |
|---|---|---|
| T3 | `git ls-files .opencode/tools/package-lock.json` | `.opencode/tools/package-lock.json` |
| T3 | `git check-ignore -v .opencode/tools/node_modules/` | `.opencode/.gitignore:1:node_modules/` |
| T2 | `npm install --package-lock-only` in `.opencode/tools` | `up to date, audited 33 packages`, **zero diff** |
| T2 | `JSON.parse(package-lock.json)` | valid JSON |
| T3 | `git status --porcelain` | empty |

No Python test is run or applicable: no source or test file is touched, so the suite result is identical
to the base by construction. CI (`.github/workflows/tests.yml`) runs it on the pull request.

## Review

**Not closed — no receipt covers these bytes.** Declared rather than hidden.

- Lineage `review-1b9c767070551227`, risk `medium`, one lens (`review-reliability`), 2 paths / 480 lines.
- Typed refusal, identical 4/4 attempts:
  `opencode_reviewer_result_refused: OpenCode Task transport did not produce a capturable reviewer result`.
- Cause established afterwards: the transaction was **created** by a `review start` that did not carry
  `--agent=opencode`, and a replay that adds the flag does not repair the binding. The two reviews that
  did close in this repository (`review-ec730c06ffe3d86e`, `review-1a55a58e93152714`) were created with it.
- By explicit human decision, receipt-driven development is off for this clone
  (`review mode disable --scope clone`) and this branch is delivered under ordinary repository policy.

## Next step

None on this branch. Delivery is a human decision. Separate follow-up: W3, the 22-vs-20 tool-count
comment in `tests/integration/test_assistant_harness_guardrails.py:301`.


# ODD: tools-lockfile-hygiene

**Branch**: `odd/tools-lockfile-hygiene`
**Worktree**: `../lumat-agent-odd-tools-lockfile-hygiene`
**Base**: `28b72cf4` (= `main` at branch time)
**Status**: in progress

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

- One commit for this concern.
- No push, no PR, no merge without an explicit request.

## Resolved execution config

- **TDD**: strict TDD is active (`openspec/config.yaml:38`), but this change adds a **generated artifact**
  and alters no behavior, so there is no RED to observe and no test can cover it. Stated rather than faked.
- **Test runner**: `uv run pytest tests/` (not applicable to this change; no source file is touched).
- **Graph Check**: not applicable — no module is edited and no edge changes. Recorded explicitly instead of
  claiming a query that would carry no information.

## Checklist

- [ ] **T1**: commit `.opencode/tools/package-lock.json`.
- [ ] **T2**: confirm the lockfile is in sync with `package.json` (regenerate with
      `npm install --package-lock-only` in `.opencode/tools` and observe zero diff) and is valid JSON.
- [ ] **T3**: confirm `node_modules/` is still ignored and the lockfile is now tracked.
- [ ] **T4**: assess the branch and follow the returned RDD transition.

## Acceptance criteria

- `.opencode/tools/package-lock.json` is tracked and identical to what the provisioner generates.
- No `.gitignore` change; `node_modules/` stays ignored.
- A freshly provisioned worktree no longer shows that path as untracked.

## Verification evidence

- (pending)

## Next step

Implement T1 → T3, then run the RDD assessment.

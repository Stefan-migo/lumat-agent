# ODD: r3-duplicate-tools

**Branch**: `odd/r3-duplicate-tools`
**Worktree**: `../lumat-agent-odd-r3-duplicate-tools`
**Base**: `c6f7b534`
**Status**: implemented and verified (native review pending)

## Objective

Make the assistant capabilities contract test detect a tool listed twice in the API response,
closing the `R3-duplicate-tools` advisory that the native review of PR #248 left as later work.

## Problem (verified)

PR #248 (WU#8 `tool-name-honesty`) replaced a hardcoded `== 19` tool count with a surface derived
from `TOOL_REGISTRY`. Its native review (`review-00410cb796e65edb`, lens `review-reliability`) left
one non-blocking advisory: the set comparison at
`tests/functional/test_api_assistant_capabilities.py:40` no longer detects duplicate entries in the
API response.

The path from a duplicated configuration entry to a silently passing test is real, not theoretical:

1. `_coerce_str_list` (`app/agent_registry.py:93-101`) returns `tuple(value)` with **no duplicate
   check**, so a repeated entry in `assistant.tools_whitelist` survives registry validation.
2. The endpoint (`app/panel/api/routes/chat.py:246-254`) builds `tools` by iterating that same
   whitelist, so the repeated entry appears twice in the payload.
3. The assertion builds a `set`, which collapses the duplicate, so
   `{tool["name"] for tool in payload["tools"]} == set(TOOL_REGISTRY)` still holds and the test
   passes on a payload it should reject.

One more fact shapes the fix: the payload order follows the YAML whitelist order, not
`TOOL_REGISTRY` order, so an order-sensitive list comparison would be fragile.

## Decisions

- Compare the two surfaces as a **multiset**:
  `sorted(tool["name"] for tool in payload["tools"]) == sorted(TOOL_REGISTRY)`. It detects
  duplicates and missing/extra names in one line, and stays order-independent.
- Leave the subset assertion on lines 41-43 untouched. It documents which tools matter and is
  already implied by the equality, so removing it is out of scope for this unit.

## Authorized scope

- `tests/functional/test_api_assistant_capabilities.py` — the single assertion.
- `odd/tasks/r3-duplicate-tools.md` — this record.

## Out of scope

- No production change (`app/` untouched) and no behavior change: this hardens a regression guard.
- Making `_coerce_str_list` reject duplicates is a separate question. If the loader ought to fail
  fast on a repeated whitelist entry, that is its own unit with its own evidence.
- `tests/unit/test_agent_registry.py` already received its WU#8 tail assertion and is not touched.

## Constraints

- Test-only change; strict TDD is active (`apply.tdd=true`, runner `pytest tests/`). The artifact
  *is* a test, so RED must be shown honestly: a payload carrying a duplicated tool that the new
  assertion rejects and the old one accepted.

## Tasks

- [x] T1. Replace the set comparison with the multiset comparison.
- [x] T2. Prove RED with a duplicated whitelist entry, then revert to GREEN.
- [x] T3. Run the focused capabilities test and the full unit + integration suite.

## Acceptance criteria

- The capabilities contract fails when the response lists a tool twice.
- The capabilities contract still passes against the real registry.
- No production file changes: the diff is the test assertion and this record only.

## Checks

- `eval "$(infra/test-db.sh env)" && uv run pytest tests/functional/test_api_assistant_capabilities.py -q`
- `eval "$(infra/test-db.sh env)" && uv run pytest tests/unit tests/integration -q`
- `git diff --check`

## Progress

- [x] ODD record created before the first source change.
- [x] Worktree created (`rapso worktree create r3-duplicate-tools`, base `origin/main` `c6f7b534`).
- [x] Provisioned: `infra/.env` copied, `uv sync`, test DB up.
- [x] Graph Check: `graphify query "assistant capabilities endpoint tool registry payload"` and
      `graphify path "registry.py" "chat.py"` run; nodes consulted `registry.py`,
      `assistant_capabilities` (`chat.py:241`), `_coerce_str_list` (`agent_registry.py:93`),
      `test_api_assistant_capabilities.py`.
- [x] T1 applied: the set comparison became a sorted multiset comparison in
      `tests/functional/test_api_assistant_capabilities.py`, with a comment recording why a set
      would silently accept the duplicate.
- [x] T2 RED proven on the real endpoint, not by argument: a duplicate `- kb.retrieve` injected
      into `assistant.tools_whitelist` (`agent/registry.yaml`) produced a payload with one tool too
      many, and the run showed the OLD set assertion passing while the NEW assertion failed with
      `Left contains one more item: 'web.search'`. The injection was reverted with
      `git checkout -- agent/registry.yaml`.
- [x] T3 verification: `tests/functional/test_api_assistant_capabilities.py` -> 4 passed;
      `tests/unit tests/integration` -> **674 passed, 0 failed** (94.87s); `git diff --check` clean.
- [x] Diff is the test assertion plus this record only; `app/` is untouched.

## Review (native RDD)

_Not started. Filled in at the delivery boundary._

## Next step

Implemented and verified. Native review runs on the committed candidate; the outcome is recorded in
the PR body and in Engram (`odd/r3-duplicate-tools/outcome`), never as a post-freeze commit on this
branch (`pattern/rdd-receipt-policy`).

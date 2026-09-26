# ODD: assistant-closeout

**Branch**: `odd/assistant-closeout`
**Worktree**: `/home/stefan/repos/lumat-agent-odd-assistant-closeout`
**Base**: `50bce481` (= `main` = `origin/main` at branch time, merge of PR #382)
**Status**: complete — implementation and checks green; push and PR are the owner's decision.

## Objective

Close the remaining open lanes of the Lumat panel-assistant thread (`app/chat/assistant/`) so the thread
stops carrying unresolved follow-ups: the `R3-marker-boundary` advisory, the Brave rate-limit backoff, the
post-U2 tool-catalog cost (measured but never recorded), and the two `Status` lines that PR #379 itself
left stale.

## Problem (verified)

The lanes come from the 2026-09-26 handoff
(`.rapsodia-code/handoffs/2026-09-26-asistente-lumat-thread.md`) and were verified against the repository,
not read from memory.

### Lane A — `R3-marker-boundary` is a verified false positive

The advisory is real as a finding, but its detail lives only in the **PR #344 body**, not in any repo doc —
which is why a repo-only grep finds nothing:

> the fit check reserves the marker for the currently considered omitted count, but breaking at that index
> actually omits one more. If that crosses a digit boundary the marker can be one character short.
> **Unreachable today** — `MAX_ASSISTANT_TOOL_STEPS = 2` bounds `omitted` to `≤ 1` — ... (the fix is
> reserving `older + 1`).

Verified in `_render_tool_evidence` (`app/chat/assistant/nodes.py:778-810`, reserve at `:795`):

- The reserve deficit is real (`older` vs `older + 1`) but **cannot manifest**:
  - unreachable — a digit boundary needs `omitted ≥ 10`, i.e. ≥11 rendered results; the bound is 2;
  - harmless even if reached — `used` counts one separator per item while `body = "\n".join(...)` uses
    `len(kept) - 1` separators, so the render always carries exactly one spare character, the deficit.
- The prescribed fix was measured against the real function over ~14k configurations:
  - unguarded `_omission_marker(older + 1)`: **fixes 0, breaks 2**, changes 289 outputs;
  - guarded variant (keep `if older else 0`): **fixes 0, breaks 0**, changes 3 outputs — a no-op.
- The residual behaviour (the newest result is truncated when the newest plus its marker alone exceeds
  `_TOOL_EVIDENCE_LIMIT`) is the documented fallback at `:807-810`, not a boundary off-by-one.

**Decision: do not apply the prescribed fix.** It would regress two reachable configurations (`n = 2`,
newest ≈ 3934) by dropping a result that fits, and it fixes nothing. Lane A closes as a verified false
positive with no source change.

### Lane B — the search adapter ignored the provider's rate limit

`app/chat/assistant/tools/search.py` issued one GET and mapped **every** non-timeout `httpx.HTTPError`
(401/403/429/500) to the same `SearchFailure("search provider request failed")`. Brave's free tier allows
one request per second, so a burst failed the turn's search instead of waiting it out.

### Lane C — post-U2 catalog cost, previously unmeasured

Measured at `50bce481` with `_planner_tool_catalog(list(TOOL_REGISTRY))` (`nodes.py:484-492`), same method
as the recorded U1 baseline (chars/4):

| | U1 baseline | Now |
|---|---|---|
| tools | 23 | **24** |
| chars | — | 10.587 |
| tok/turn | ~2.471 | **~2.647** (+176, +7%) |
| tok/tool | ~112 | ~110 |

The `memory.*` family is **40% of the catalog** (1.063 of 2.647 tok) with descriptions of 19–47 chars, so
the weight is the argument JSON schemas, not the prose. Top: `memory.search` 337, `memory.read` 333,
`memory.write` 172, `automation.create_rule` 166, `memory.update` 158.

The pinned hash (`tests/unit/test_assistant_delegation.py:39-44`) pins catalog **bytes**, not tokens: it
detects shape change and cannot measure cost. Trimming aliases or schemas would move both the whitelist
invariant (`tests/unit/test_agent_registry.py:281-286`) and that hash — an **owner decision, not applied
here**.

### Lane D — the `Status` debt PR #379 fixed regenerated

`odd/tasks/docs-status-reconciliation.md` and `odd/tasks/customers-search-pii.md` both said "merge is the
owner's decision" while already merged (`d2546396`, `50bce481`) — the two docs that work itself created.

## Scope

**In**: lane A record, lane B fix, lane C record, lane D reconciliation.
**Out**: trimming the tool catalog (owner decision), deep research (a composition of U1+U2+U3, not a unit),
reopening `R3-dns-rebinding` (accepted on purpose and documented), any change to the bounds
(`_TOOL_EVIDENCE_LIMIT`, `MAX_ASSISTANT_TOOL_STEPS`, `MAX_ITEMS`).

## Decisions

- **D1 — Lane A gets no code change.** The advisory's prescribed fix is a measured regression and fixes
  zero failing configurations; the finding closes as a false positive (evidence above). No test was added
  for a non-defect.
- **D2 — Lane B retries once, bounded, and only on 429.** Honour `Retry-After` seconds, capped at
  `_RATE_LIMIT_RETRY_CAP_SECONDS = 2.0` (default `1.0` when the header is absent or not a number). A
  persistent 429 raises `SearchFailure("search provider rate-limited the request")` so the responder is
  honest instead of generic. Non-429 failures never retry.
- **D3 — Lane C is recorded, not acted on.** The measurement exists now; the trim moves a pinned hash and
  the whitelist invariant, so it stays an owner decision.

## TDD

Strict TDD ON (`openspec/config.yaml` → `testing.strict_tdd: true`). Runner: `uv run pytest tests/`.

## Tasks

| ID | Task | Route | Status |
|---|---|---|---|
| T1 | Lane B RED: rate-limit tests (wait, cap, default wait, persistent 429, non-429 no-retry) | direct inline | done |
| T2 | Lane B GREEN: bounded 429 retry honouring `Retry-After` | direct inline | done |
| T3 | Lane A: verify the advisory against the real function and record the false positive | direct inline | done |
| T4 | Lane C + D: record the measurement and reconcile the two `Status` lines | direct inline | done |
| T5 | Full checks: assistant suites, full suite, `git diff --check` | direct inline | done |

## Checks

```bash
eval "$(bash infra/test-db.sh env)"      # test DB on port 6015

uv run pytest tests/unit/test_assistant_tools.py -k "rate_limit or non_rate_limit" -q
uv run pytest tests/unit/test_assistant_tools.py -q
uv run pytest tests/unit/test_assistant_tool_loop.py tests/unit/test_agent_registry.py tests/unit/test_assistant_delegation.py -q
uv run pytest tests/ -q
git status --short && git diff --check
```

- Lane B RED observed: 4 new rate-limit tests failed with `search provider request failed` and a single
  request; the non-rate-limit guard passed.
- Lane B GREEN observed: 12 selected tests pass; `tests/unit/test_assistant_tools.py` 83 passed.
- Assistant scoped suites green, exit 0: `tests/unit/test_assistant_tools.py tests/unit/test_assistant_tool_loop.py tests/unit/test_agent_registry.py tests/unit/test_assistant_delegation.py` → 151 passed; `tests/integration/test_assistant_harness_guardrails.py tests/integration/test_assistant_chat.py` → 90 passed.
- Full suite green, exit 0, reached `[100%]` with zero `F`/`E` markers. The first attempt stalled at the
  first heavy database use — the repository's documented pre-existing stall (`pyproject.toml:48-52`,
  `odd/tasks/suite-truncate-stall.md`); a restart of this worktree's own test DB cleared the stale lock and
  the identical tree passed. Not a regression from this unit.
- `git diff --check` clean; `uv.lock` restored after every `uv run`.
- Lane A probe: length model validated against the real renderer (0 mismatches / 300 random
  configurations); the fix counts above come from that validated model plus the real function.

## Progress

- 2026-09-26 — **T1 + T2 done.** Rate-limit retry with tests, strict TDD RED→GREEN.
- 2026-09-26 — **T3 done.** Advisory verified false positive; decision D1 recorded.
- 2026-09-26 — **T4 done.** Catalog cost measured and recorded; the two `Status` lines reconciled.
- 2026-09-26 — **T5 done.** Scoped assistant suites and the full suite green; `git diff --check` clean.

## Next step

Push and open the PR, then merge — all three are the owner's decision. Nothing else is outstanding in this
unit.

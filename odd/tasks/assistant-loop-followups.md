# ODD: assistant-loop-followups

**Branch**: `odd/assistant-loop-followups`
**Worktree**: `/home/stefan/repos/lumat-agent-odd-assistant-loop-followups`
**Base**: `1d57f516` (= `main`, PR #343 merged)
**Status**: complete — waiting on the native review and the PR decision
**Origin**: Engram `handoff/slice2-assistant-tool-chaining` (#4932), open follow-ups after U1.

This is a **follow-up unit**, not a start of U2 or U3. U2 (local page reader + SSRF) and U3
(panel sub-agent delegation) stay unstarted. `panel_subagents` stays `not_implemented`.

## Objective

Close the two follow-ups U1 (`assistant-tool-chaining`) left open. Both live in
`app/chat/assistant/nodes.py`, so they ship as two commits on one branch and one PR.

## Problem — measured, not inferred

### P1 — the omission marker can cut the newest result (`R3-evidence-marker-overflow`)

`_render_tool_evidence()` budgeted the accumulated results first and prepended the
`[N earlier tool result(s) omitted]` marker **afterwards**. When the kept results nearly filled
`_TOOL_EVIDENCE_LIMIT` (4,000), the marker pushed the rendering over the limit and the final
tail cut (`rendered[:LIMIT-1] + "…"`) removed the **newest** result — the one the planner
decides from, and the one the marker exists to protect.

Reproduced by measurement, not by reading: three results, the middle padded to fill the budget,
the oldest dropped. Old code: `len=4000, newest present = **False**`, rendering starting with
`[1 earlier tool result(s) omitted]` and ending in the middle result. The marker is what
overflowed; the newest result paid for it.

### P2 — an autonomous write at step 1 can chain into a read-only step 2

`AUTONOMOUS_WRITE_ALLOWLIST = {memory.write, memory.update, memory.delete}` (`registry.py:32`).
An autonomous write needs no approval (`nodes.py:612`), and the step ≥ 2 write refusal only fires
from step 1 onward (`nodes.py:603`). So a step-1 autonomous write with `follow_up: true` executed
and then took the back-edge: the planner re-planned and could run a read-only step 2. A turn could
**act → discover**, while the loop's own contract says chaining is read-only (D3) and its router
docstring says "bounded read-only follow-up".

Reproduced by measurement: plan 1 = `memory.write` with `follow_up: true`, plan 2 = `memory.search`.
Observed handler calls: `['memory.write', 'memory.search']`.

## Decisions (owner-confirmed, 2026-09-24)

**D1 — A write ends the turn (rule A).**

- A write is an **action, not evidence**. The loop exists to gather evidence for the answer, so a
  turn that wrote is done: it answers with what it has. Only the read-only tools (`read_only=True`)
  may chain.
- **Consequence, stated plainly.** An autonomous write (no approval, panel-scoped memory) no longer
  chains. The write itself is unchanged; only the follow-up step is dropped.
- *Rejected* — **B, leave it as is**: the loop's "read-only" contract would carry an invisible
  exception that has to be documented and tested anyway. *Rejected* — **C, refuse the write when
  `follow_up` is set**: it punishes a legitimate autonomous write for a planner flag, and it is the
  hardest of the three to explain to a user.
- **Measured cost of A:** zero on tool count and planner calls for every read-only turn; the only
  affected turns are autonomous writes that asked for a follow-up, which now simply end.

**D2 — The marker is budgeted with the results.**

- Reserve the marker's length inside `_TOOL_EVIDENCE_LIMIT` while keeping results, newest first.
  The newest result can therefore never be the part a final cut removes. A single result larger than
  the whole budget is still truncated, exactly as before.
- Conservative by design: when the budget is tight, the fix drops one more **older** result to keep
  the marker honest rather than silently squeezing it out.

## Contract

1. The newest tool result is present in the planner/responder rendering whenever it is rendered at
   all, independent of the omission marker.
2. The omission marker stays: a dropped older result is never silent.
3. The combined rendering never exceeds `_TOOL_EVIDENCE_LIMIT`.
4. A non-read-only plan never chains; a read-only plan with `follow_up` still does.
5. `_TOOL_EVIDENCE_LIMIT` is not raised. Bounds stay bounds.

## Tasks (strict TDD — observed RED before each source change)

- [x] **T1 — RED + GREEN, evidence marker.** RED observed: `assert 'NEWEST_RESULT_MARKER' in
  '[1 earlier tool result(s) omitted]\n[{"evidence": "customers.search", ...` — the newest result
  was gone. GREEN: `1734f793`.
- [x] **T2 — RED + GREEN, autonomous write ends the turn.** RED observed:
  `assert ['memory.write', 'memory.search'] == ['memory.write']`. GREEN: `3594bc96`.
- [x] **T3 — Scope guard.** `test_read_only_tool_with_follow_up_still_chains` asserts the read-only
  chain is untouched, so D1 cannot be implemented by over-refusing.
- [x] **T4 — Suite.** Targeted: 27 passed in the loop file; 216 passed across the assistant, cortex
  and SDB-recovery files (SDB is untouched, which is the blast-radius check). Full suite:
  **1358 passed, 2 warnings in 359.97s** — no stall this run.

## Acceptance criteria

1. Three new tests, all RED before their source change; every pre-existing assertion still holds.
2. Full suite green.
3. `_TOOL_EVIDENCE_LIMIT` unchanged; no bound raised.
4. The approval mechanism, `resume_thread` and SDB untouched.
5. U2 and U3 untouched; `panel_subagents` still `not_implemented`.

## Verification

```bash
cp ../lumat-agent/infra/.env infra/.env     # a fresh worktree starts without it
uv sync                                     # test-db.sh needs .venv/bin/python
bash infra/test-db.sh up                    # port 5528 for this worktree
eval "$(bash infra/test-db.sh env)"

uv run pytest tests/unit/test_assistant_tool_loop.py
uv run pytest tests/unit/test_cortex_session_loop.py tests/unit/test_assistant_planner.py \
  tests/unit/test_assistant_tools.py tests/integration/test_assistant_harness_guardrails.py \
  tests/integration/test_assistant_chat.py tests/spec/test_sdb_recovery.py
uv run pytest tests/
```

`uv run` rewrites `uv.lock`; it was clean at both commits.

## Scope

**In scope** — `app/chat/assistant/{nodes.py}` and `tests/unit/test_assistant_tool_loop.py`.

**Out of scope** — U2, U3, `resume_thread` cost/freshness re-checks, tool-catalog cost hygiene,
the Brave Free production deploy, any bound increase, the approval mechanism, `resume_thread`, SDB.

## Authorized scope

- Branch `odd/assistant-loop-followups` in `/home/stefan/repos/lumat-agent-odd-assistant-loop-followups`.
- Writes limited to the in-scope files plus this record and its Engram mirror.
- `main` was fast-forwarded from `66cc868a` to `1d57f516` before branching, so the base carries the
  merged slice 2. No other worktree was touched.

## Constraints

- **Strict TDD: ON** — `openspec/config.yaml:38`, runner `uv run pytest tests/`.
- No linter, typechecker, pre-commit or hooks exist. **The tests are the verification.**
- One concern per commit, ≤5 files per commit, Conventional Commits.
- **No `Co-Authored-By` and no AI attribution in commits.**
- English artifacts.
- Graph Check (Step 1) before each task.

## Graph nodes consulted (Graph Check, Step 1)

- `graphify query "assistant tool evidence rendering and tool loop routing"` → `nodes.py`,
  `assistant/evidence.py`, `assistant/graph.py`, `registry.py`, `get_tool()`, `execute_tool()`,
  `AssistantState`, `issue_approval`, `test_assistant_harness_guardrails.py`, and the U1 record's
  `Loop Write Refusal (D2)` / `U1 Bounded Multi-Step Tool Execution` nodes.
- `graphify path _render_tool_evidence tool_loop_head` → **no directed path** (same shape the U1
  record hit for `execute respond_stream`: the graph's edges are call-based, so graph-node routing
  is not represented). Same for `graphify path plan_llm tool_loop_head`.
- `graphify-out/GRAPH_REPORT.md` hubs: `nodes.py`, `agent_chat.py`, `assistant/graph.py`,
  `assistant/state.py`, `registry.py`, `issue_approval`.
- Graph inherited from `main` at `1d57f516` (`graphify-out/` is gitignored, so a new worktree does
  not get it). Refresh once at session close.

## Review workload

107 authored lines excluding this record (`26/+9` in `nodes.py`, `72/+0` in the test file), well
under the 400-line budget → **single PR**, no chaining.

## Progress

- 2026-09-24 — Handoff read; `main` fast-forwarded to `1d57f516`; worktree created with owner
  consent (base `1d57f516`), env and test-db (port 5528) provisioned; Graph Check run.
- 2026-09-24 — P1 diagnosed by measurement and reproduced end to end through `plan_llm`.
- 2026-09-24 — D1 (rule A) and D2 decided with the owner before the first source write.
- 2026-09-24 — **T1 done** (`1734f793`): marker budgeted with the results; newest result survives
  the overflow. 25 passed in the loop file.
- 2026-09-24 — **T2 done** (`3594bc96`): a non-read-only plan ends the turn; read-only chaining
  preserved. 27 passed in the loop file; 216 passed across the assistant/cortex/SDB files.
- 2026-09-24 — **T4 done**: full suite 1358 passed, 2 warnings, 359.97s. No stall.

## Next step

The native review on the frozen candidate, then the PR decision (single PR, 107 authored lines).

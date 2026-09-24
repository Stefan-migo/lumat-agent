# ODD: assistant-tool-chaining

**Branch**: `odd/assistant-tool-chaining`
**Worktree**: `/home/stefan/repos/lumat-agent-odd-assistant-tool-chaining`
**Base**: `e16b3ff8` (= `main` at branch time)
**Status**: scoped — not started
**Origin**: `.rapsodia-code/sessions/ready-for-odd/2026-09-24-panel-agency-and-web-grounding/`
(Engram `handoff/panel-agency-to-u1-tool-chaining`)

> Base note: the handoff named `main = 59034858`. At branch time `main` had advanced to `e16b3ff8`
> (PR #336, `odd/panel-visual-foundation`). `git diff --name-only 59034858..e16b3ff8` touches only
> `web/`, `odd/tasks/` and `openspec/specs/` — **zero backend files** under `app/`, `agent/` or
> `tests/`. The target area is byte-identical; the base drifted harmlessly forward.

## Objective

Give the panel assistant **bounded multi-step tool execution**: after a tool result, re-plan instead of
terminating. Today a turn runs **at most one tool** and then answers. This unit lets a turn chain at
least two tools and answer from the combined evidence, under a hard iteration cap, with the cost gate
counting each iteration and an explicit, tested policy for write tools inside the loop.

This is **U1 of three**. **U2** (local page reader) and **U3** (panel sub-agent delegation) are **not**
started by this unit, and the deep-research composition of all three is explicitly not a unit.

## Problem — measured, not inferred

| Symptom | Evidence |
|---|---|
| A second tool execution can never happen | `execute()` (`app/chat/assistant/nodes.py:652-676`): `tool_already_ran = state.get("tool_result") is not None`, and the execution branch is gated by `if tool_name and not tool_already_ran:`. |
| The graph has no path back to planning | `app/chat/assistant/graph.py:147` — `execute_tool → respond_stream`; then `respond_stream → evidence → END` (`graph.py:148-149`). |
| State carries exactly one tool result | `AssistantState` (`app/chat/assistant/state.py:154-193`) has a singular `tool_result: dict \| None`. There is no accumulating tool-result list. |
| The old contract is codified in tests | `tests/unit/test_assistant_tool_loop.py:40-45` asserts `("respond_stream", "execute_tool") not in edges` and `:48-70` asserts the handler runs **once**. |
| Delegation stays unimplemented | `extension_hook_metadata()` → `"panel_subagents": "not_implemented"` (`nodes.py:69-71`). U1 does not touch it. |
| The catalog is re-sent on every planning call | `_planner_tool_catalog()` (`nodes.py:440-448`): 9,883 chars ≈ 2,471 tokens per call. |

**Why this is the ceiling worth breaking.** The orchestrating infrastructure this unit needs already
exists and runs live on the customer path (`webhook/ingest.py` → `run_conversation()` → `orchestrate` →
`research_triage`). The panel assistant simply never got it. "One tool per turn" is a deliberate
cost/safety choice, not a technical limit — and it is now a ceiling for the stated needs.

**Consequence to keep in view.** Adding a re-plan step changes the shape of **every** tool turn, not
only research turns: `execute tool → respond` becomes `execute tool → re-plan → (another tool | respond)`.
That extra planner call carries the ~2,471-token catalog. It is the cost this unit actually introduces,
and it is measured (see Checks).

## Decisions (owner-confirmed, 2026-09-24)

**D1 — Iteration cap: per turn, `MAX_ASSISTANT_TOOL_STEPS = 2`, one module constant, with the cost gate
re-evaluated at each iteration, and cap truncation recorded.**

- **Per turn, not per conversation.** The conversation and daily budgets already exist and already work:
  `panel_cost_gate` (`nodes.py:407-437`) measures `internal_thread_cost_state(session, thread_id)` and
  `daily_cost_state(session)`. A second budget inside the loop would leave two spend counters that never
  talk to each other.
- **Value 2 matches the house precedent.** The only bounded loop in the repo is
  `MAX_TRIAGE_RETRIES = 1` (`app/chat/subgraphs/research_triage.py:47`) → two attempts.
- **Raise on data, not intuition.** When the cap — and not the planner's own decision — ends a turn, that
  truncation is recorded (`cap_reached`). If production shows the cap being hit routinely, raising it is a
  one-line change. The cap bounds the worst case; it does not raise the cost of a non-chaining turn.
- *Rejected*: per-conversation cap (duplicates an existing budget); free/unbounded iteration (burns tokens
  with no ceiling); value ≥ 4 up front (raises the worst case with no measurement to justify it).

**D2 — Write tools: refused after planning step 1. Explicit and tested, never implicit.**

- **Why refuse rather than re-issue per iteration.** The post-approval path does **not** re-enter the
  graph: `resume_thread()` calls `execute()` **directly** with the frozen `thread.current_plan`
  (`app/services/agent_chat.py:1144-1177`). It is built for *one plan → one execution → done*. An approval
  mid-loop would require persisting the loop position, re-entering the graph at the right node, re-running
  the cost gate and re-validating — a redesign of the recovery path, which has its own audit suite
  (`tests/spec/test_sdb_recovery.py`).
- **The refusal also closes a real hole.** Without an explicit rule, `guardrails` (`nodes.py:543-577`)
  would emit a *new* approval for a step-2 write, and that approval could never be consumed correctly —
  a dangling approval.
- **An approval must be able to see what it authorizes.** In a chain, step 2 depends on step 1's result,
  so a human approving step 2 would be approving steps they cannot see. That defeats the approval.
- *Rejected*: re-issuing approval per iteration (touches the single-use mechanism in `approval.py:157-172`,
  the resume path, and the audit suite). Deferred to a future unit if the need is ever proven.

**D3 — Loop scope: read-only.**

- Chained steps are read-only by construction. The write-with-approval turn stays **exactly** as today:
  one tool, one approval, no chain.
- The operational domain — `customers`, `conversations`, `appointments`, `cases` — has **zero** write
  tools, so almost nothing is refused in practice. The only writes are `memory.*`, `automation.create_rule`
  and `project.*`.
- Leaves the approval mechanism, the `resume_thread` path and the SDB audit suite **untouched**: U1's blast
  radius is planner + guardrails + graph.
- **Honest limitation, recorded deliberately**: "discover and then act" write chains (e.g. search a
  customer → `memory.write`) are **not possible** in U1.

## Contract

Observable behavior this unit must produce. Implementation shape is the implementer's choice within it.

1. **Accumulating state.** Add an ordered, bounded list of tool results (e.g. `tool_results: list[dict]`)
   plus a step counter (e.g. `tool_steps: int`). Keep the singular `tool_result` working: the responder
   path and `_render_tool_evidence()` (`nodes.py:580-588`) depend on it, and
   `tests/unit/test_assistant_tool_loop.py:48-95` covers it.
2. **Bounded back-edge.** A conditional edge returns from tool execution to planning. The router is
   deterministic and returns the finish path when: the step budget is exhausted, the plan is no longer a
   tool, the cost mode is not `normal`, or step ≥ 2 proposes a write.
3. **The back-edge must not re-enter `assemble_context`, `cortex_session_gate` or `sdb_trigger_gate`.**
   Those are per-turn gates; re-running them inside a loop changes unrelated behavior.
4. **The planner must see prior results.** After a tool result the planner needs a bounded rendering of
   the accumulated results to decide "I have enough" vs "I need another tool". Today only the responder
   receives `<tool_evidence>`.
5. **Cost gate per iteration.** A non-`normal` cost mode (`conservative` or `blocked`) **stops the loop**
   and the turn answers with what it already gathered. Never keep spending in a non-normal mode.
6. **Write refusal at step ≥ 2.** A write plan after step 1 is refused with a visible reason: no
   execution, no approval issued, no auto-approval.
7. **Evidence budget across N results.** `_TOOL_EVIDENCE_LIMIT = 4_000` (`nodes.py:37-39`) truncates
   **one** result. With N results the combined rendering must stay bounded — otherwise the planner and
   responder prompts grow without control as iterations accumulate.
8. **Observability.** Record per-run `tool_steps` and `cap_reached`, and publish a stage event per
   iteration through the existing `on_stage` / `publish_live` path so the extra planner call does not read
   as silence to the user.
9. **A single-tool turn is unchanged in cost and shape.** One tool, no extra planner call, same response.

## Scope

### In scope

- The panel assistant path only: `app/chat/assistant/{graph,state,nodes}.py` and its tests.
- A bounded re-plan cycle, accumulating state, per-iteration cost gate, write refusal, bounded evidence
  rendering, and cap observability.
- Measurement of cost and latency before and after.

### Out of scope

- **U2** — local page reader / `web.fetch`, SSRF hardening. **Do not start.**
- **U3** — panel sub-agent delegation. **Do not start.** `panel_subagents` stays `not_implemented`.
- Deep research as a unit; any domain allow/deny filter.
- Making read-only tools writable, or adding any new tool. U1 is provable with the 22 tools that exist.
- Tool **catalog** cost hygiene (schemas are ~81% of the payload). Own lane, requires a live A/B first.
- Lazy loading of tool schemas — already evaluated and rejected on 2026-09-17; that decision stands.
- Any change to the approval mechanism, the `resume_thread` recovery path, or SDB.

## Authorized scope

- Branch `odd/assistant-tool-chaining` in `/home/stefan/repos/lumat-agent-odd-assistant-tool-chaining`.
- Writes limited to the in-scope files above plus this record and its Engram mirror.
- Protected: `lumat-agent` main worktree, `lumat-agent-odd-panel-visual-foundation`, and
  `lumat-agent-odd-assistant-web-context` (dead unit — a separate cleanup decision, not this branch).

## Constraints

- **Strict TDD: ON** — `openspec/config.yaml:38`, runner `uv run pytest tests/`. Observe RED before each
  source change, then GREEN.
- **`tests/unit/test_assistant_tool_loop.py` codifies the contract being replaced.** Line `:40-45` asserts
  there is no cycle back to tool execution, and `:48-70` asserts one execution per state. Both MUST be
  **rewritten** to assert the new bounded cycle — never deleted to make the change fit, and no assertion
  may be silently weakened. Note the literal edge assertion may still pass if the back-edge routes through
  a loop-head node rather than directly to `execute_tool`; the **intent** changes regardless, so the test
  name and assertions must reflect a cycle that exists and is bounded.
- `_TOOL_EVIDENCE_LIMIT`, `_KB_EVIDENCE_LIMIT` and the SDB limits (`nodes.py:37-39`, `301-303`) are not
  raised to make the loop fit. Bounds stay bounds.
- No linter, typechecker, pre-commit or hooks exist. **The tests are the verification.**
- One concern per commit, ≤5 files per commit, Conventional Commits.
- **No `Co-Authored-By` and no AI attribution in commits.**
- English artifacts.
- Graph Check (Step 1) before each task: `graphify query` / `graphify path`, recording the nodes consulted.

## Tasks (strict TDD — observed RED before each source change)

- [ ] **T1 — Baseline measurement, before any source change.** Record, for the **current** code: the
  planner call count, the catalog payload size, the character/token cost and the wall latency of (a) a
  single-tool turn and (b) a two-tool scenario. Static baseline already known: catalog 9,883 chars ≈
  2,471 tokens/turn (Engram #4899, #4901). This is the "before" of the required before/after comparison.
- [ ] **T2 — RED + GREEN, bounded cycle and accumulating state.** RED: a turn whose planner asks for a
  second tool executes both and answers from the combined evidence; a third is refused at the cap; a
  single-tool turn is byte-for-byte unchanged in behavior. Rewrite
  `tests/unit/test_assistant_tool_loop.py:40-45` to assert the bounded cycle exists. GREEN: accumulate
  results, add the counter, add the back-edge through a loop-head node that does not re-enter the
  per-turn gates.
- [ ] **T3 — RED + GREEN, cost gate per iteration.** RED: a turn that would chain is stopped when the cost
  mode turns `conservative` or `blocked` mid-loop, and answers with what it has. GREEN: re-evaluate the
  cost mode at the loop head.
- [ ] **T4 — RED + GREEN, write refusal at step ≥ 2.** RED: a step-2 plan for a non-read-only tool is
  refused with a visible reason, executes nothing, and issues no approval. GREEN: explicit guardrails
  rule. Assert the *absence* of an approval, not only the absence of execution.
- [ ] **T5 — RED + GREEN, planner sees prior results, bounded.** RED: the planner prompt carries a
  bounded rendering of accumulated results and the combined rendering stays within budget across N
  results. GREEN: extend the planning prompt with the bounded rendering.
- [ ] **T6 — Observability.** `tool_steps` and `cap_reached` reach the persisted run state; a per-iteration
  stage is published. Proved by test, not by comment.
- [ ] **T7 — Harness end-to-end.** An integration turn that chains `web.search → kb.retrieve` and answers
  from combined evidence, plus a turn that stops at the cap with the truncation recorded.
- [ ] **T8 — After measurement.** Re-run T1's measurement against the new code and report the delta,
  including the extra planner call per tool turn.
- [ ] **T9 — Suite and spec check.** Full suite green; every pre-existing assistant assertion still holds;
  the pre-existing `tool_result` and `<tool_evidence>` contracts are intact.

## Acceptance criteria

1. A turn chains **at least two** tools and answers from the combined evidence.
2. The iteration cap is **observable** — proven by a test, and recorded per run as `cap_reached`.
3. A normal **single-tool** turn is unchanged in cost and shape: no extra planner call, same response.
4. The write-tool policy inside the loop is **explicit and tested**: a write after step 1 is refused with a
   visible reason, executes nothing and issues no approval.
5. A non-`normal` cost mode stops the loop mid-chain.
6. The combined evidence rendering stays bounded as results accumulate.
7. Cost and latency before vs. after are **measured and reported**.
8. Full suite green; no previously-green assistant assertion weakened.
9. U2 and U3 are untouched; `panel_subagents` still reads `not_implemented`.

## Checks

```bash
cp ../lumat-agent/infra/.env infra/.env     # a fresh worktree starts without it
bash infra/test-db.sh up
eval "$(bash infra/test-db.sh env)"
# run pytest WITHOUT -q: pyproject.toml already sets addopts = "-q", so -q yields -qq
# and suppresses the pass summary

uv run pytest tests/unit/test_assistant_tool_loop.py
uv run pytest tests/unit/test_assistant_graph.py tests/unit/test_cortex_session_loop.py
uv run pytest tests/integration/test_assistant_harness_guardrails.py
uv run pytest tests/integration/test_assistant_chat.py
uv run pytest tests/spec/test_sdb_recovery.py
uv run pytest tests/

git status --short
git diff --check
```

Worktree notes already applied for this branch: `infra/.env` copied, test-db up on **port 5719**
(`lumat-test-lumat-agent-odd-assistant-tool-chaining`), own `.venv` created by `uv sync`. `uv.lock` is
rewritten by every `uv run` — `git checkout -- uv.lock` before committing. `graphify-out/` was inherited
from main (built at `59034858`, `cluster-only`); it is gitignored, so a **new** worktree does not get it
for free.

## Progress

- 2026-09-24 — Handoff read; repo state verified against `main` (`uv.lock` drift only; RDD `off` for this
  clone, `clone_local`).
- 2026-09-24 — Code map taken: one-tool gate, missing back-edge, singular `tool_result`, the
  per-turn-only cost gate, the single-use approval path, and the `resume_thread` non-resuming execution
  path.
- 2026-09-24 — The three open design questions (cap, approvals in the loop, loop scope) resolved with the
  owner and recorded above as D1–D3.
- 2026-09-24 — Worktree created with explicit owner consent: base `e16b3ff8`, branch
  `odd/assistant-tool-chaining`; environment set up; Graph Check run. **This record created before the
  first source change.**

## Graph nodes consulted (Graph Check, Step 1)

- `graphify query "assistant tool execution and planner loop"` → `nodes.py`, `agent_chat.py`,
  `assistant/graph.py`, `assistant/state.py`, `registry.py`, `build_assistant_graph()`, `get_tool()`,
  `execute_tool()`, `issue_approval` community, `test_assistant_harness_guardrails.py`.
- `graphify path execute respond_stream` → **no directed path** (confirms the missing back-edge).
- `graphify-out/GRAPH_REPORT.md` community hubs: `nodes.py`, `agent_chat.py`, `chat.py`,
  `assistant/state.py`, `registry.py`, `issue_approval`, `test_assistant_chat.py`.
- Graph staleness: built from `59034858`; base is `e16b3ff8`. The diff touches no backend file, so the
  map is valid for this area. Refresh once at session close (`graphify <path> --update` **and**
  `graphify cluster-only <path>`).

## Next step

T1 — take the baseline measurement before touching source. Then T2 (RED first) begins the loop.

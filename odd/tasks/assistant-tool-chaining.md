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

**D4 — The loop is opt-in per turn, never automatic.** *(Added after the T1 baseline measurement exposed
a contradiction between the two requirements it inherited.)*

- The handoff's definition of done requires that **a normal single-tool turn is unchanged in cost and
  shape**. An unconditional re-plan after every tool would contradict it: measured (T1), that re-plan costs
  **~12,150 prompt chars ≈ 3,037 tokens and one provider round-trip on *every* tool turn** — the exact
  central risk the source session flagged ("U1 changes cost and latency of ALL turns").
- Therefore the **planner declares, in its own plan, that the turn needs a follow-up step**. Only then does
  the graph take the back-edge and re-plan. A turn whose planner does not ask for a second step behaves
  exactly as today: one planner call, one tool, one responder.
- Consequence: the cost delta is paid **only on turns that actually chain**. A single-tool turn's cost is
  unchanged by construction, not by hope.
- Mechanism: an explicit field on the planner output (`PlannerOutput`, `state.py:27-38`, `extra="forbid"`)
  documented in `agent/prompts/assistant_plan.md` so the planner can emit it. The field is part of the
  planner contract, so it is validated and refused if malformed like every other plan field.
- *Rejected*: an unconditional back-edge (violates the DoD and taxes every tool turn); inferring "needs
  another step" from the tool result (a hidden policy, not agency, and untestable as a rule).

## Contract

Observable behavior this unit must produce. Implementation shape is the implementer's choice within it.

1. **Accumulating state.** Add an ordered, bounded list of tool results (e.g. `tool_results: list[dict]`)
   plus a step counter (e.g. `tool_steps: int`). Keep the singular `tool_result` working: the responder
   path and `_render_tool_evidence()` (`nodes.py:580-588`) depend on it, and
   `tests/unit/test_assistant_tool_loop.py:48-95` covers it.
2. **Bounded back-edge, opt-in (D4).** A conditional edge returns from tool execution to planning **only
   when the plan asked for a follow-up step**. The router is deterministic and returns the finish path
   when: the step budget is exhausted, the plan is no longer a tool, the cost mode is not `normal`, the
   plan did not opt in, or step ≥ 2 proposes a write.
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

- [x] **T1 — Baseline measurement, before any source change.** Recorded against unmodified `main`-derived
  code, before the first source edit. See *Baseline measurement (T1)* below.
- [x] **T2 — RED + GREEN, bounded opt-in cycle and accumulating state.** Done in `83218556` + correction
  `b99646fe`. RED for the opt-in field was an `ImportError` (weak — it proves the symbol was missing, not
  the behavior); the correction's REDs were behavioral (`assert 2 == 1` on the duplicated evidence,
  `KeyError: 'approval'` on the silent drop). GREEN: 124 tests across the four assistant test files, full
  suite 1,339 passed.
- [x] **T3 — RED + GREEN, cost gate per iteration.** Done in `9f77520b`. Behavioral RED:
  `assert ['customers.search', 'memory.search'] == ['customers.search']` — the stale gate let the second
  tool run. GREEN: `test_cost_mode_flip_stops_loop_before_second_planner` is parametrized over
  `conservative` and `blocked`, drives the real graph, and asserts one tool, one planner call, the answer
  from the gathered evidence, and the visible `loop_cost_stopped` decision.
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

## Baseline measurement (T1)

Taken **before the first source change**, against the unmodified branch head. Instrument: a throwaway
script that patches `app.chat.assistant.nodes._assistant_client` and `execute_tool`, so it makes **no
network call and touches no database** (`session=None` short-circuits `panel_cost_gate` and
`assemble_context_node`). It counts LLM calls and sums prompt characters; tokens are `chars / 4`.

| Vector | Measured |
|---|---|
| Whitelisted tools | 22 |
| Planner catalog payload | **9,883 chars** ≈ 2,471 tok — reproduces the handoff's figure exactly (Engram #4899) |
| Persona (system prompt) | 1,448 chars |
| **Single-tool turn** (`customers.search`) | 1 planner call + 1 tool execution + 1 responder call |
| Planner prompt | **12,150 chars** ≈ 3,037 tok (the catalog is 81% of it) |
| Responder prompt | 2,497 chars ≈ 624 tok |
| Single-tool turn total | **14,647 prompt chars** ≈ 3,661 tok |
| `respond`-plan turn | 1 planner call, no responder — see caveat |

**What U1 costs, corrected by D4.** Because the loop is **opt-in**, a tool turn that does *not* ask for a
follow-up step keeps its baseline shape exactly: **1 planner + 1 tool + 1 responder = 14,647 prompt chars**,
unchanged. A turn that *does* chain pays **one extra planner call of ~12,150 prompt chars (≈3,037 tok) plus
one provider round-trip** — that is the price of the second step, paid only when the planner asks for it.
Planner calls: **1 → 2 on chaining turns only; 1 → 1 on normal turns.**

An earlier draft of this record claimed the extra planner call landed on *every* tool turn. The measurement
and the DoD contradicted each other; **D4 resolves it in favour of the DoD**, and T8 must verify that a
non-chaining tool turn is byte-for-byte identical in call count and prompt characters.


**Honest gaps in this baseline:**

- **Wall latency is NOT measured.** It needs a live provider call. The mocked run's wall time is
  meaningless and is deliberately not reported. Live before/after latency must be taken against the dev
  panel, or recorded as an explicit unrun row — never inferred.
- The `respond`-plan run read `degraded` ("knowledge base unavailable") because `session=None` leaves
  `retrieve_kb` with no data source. That row is an artifact of the instrumentation, **not** a measured
  production path; only the tool-turn row is a production-shaped baseline.
- Token figures are `chars / 4` estimates, not provider-reported usage. `_record_usage()` no-ops without
  a session (`nodes.py:278-292`), so real usage needs the DB-backed path.

## Ledger of measured change (T1 → T2)

Re-measured with the same instrument after T2, on the **non-opted-in single-tool turn** (the path D4
guarantees is unchanged):

| Vector | T1 baseline | After T2 | Delta |
|---|---|---|---|
| Planner calls | 1 | 1 | **0** |
| Tool executions | 1 | 1 | **0** |
| Responder calls | 1 | 1 | **0** |
| Responder prompt chars | 2,497 | **2,497** | **0** |
| Planner prompt chars | 12,150 | 12,513 | **+363** |
| Total prompt chars | 14,647 | 15,010 | +363 (+2.5%) |

The only remaining delta on a normal tool turn is **+363 chars (~91 tokens) on the planner prompt**: the
`follow_up` contract added to `agent/prompts/assistant_plan.md`. It is the unavoidable price of publishing
the opt-in field to the planner — without it the planner cannot ask for a second step. Recorded, not hidden.

Two defects found by the parent's readback of the first T2 attempt, both fixed before the task closed:

1. **Tool evidence leaked into the responder prompt.** `_context_text()` was patched to append prior tool
   evidence, but the responder consumes `_context_text()` too, so every tool turn carried the evidence
   **twice** — measured +47 chars on the synthetic turn, bounded at up to 4,000 duplicated chars on a real
   one. Fixed with a planner-only `_planner_context_text()`; the responder prompt returned to exactly 2,497.
2. **A step-2 write exited silently.** The `follow_up` exit ran *before* the write guard, so a step-2 write
   plan with `follow_up` false was dropped with no decision and no reason — the implicit behavior D2 exists
   to forbid. The guard now evaluates the plan independently of `follow_up` and always refuses with a
   visible `loop_write_refused` decision.

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
- 2026-09-24 — **T1 done.** Baseline measured on the unmodified branch: 9,883-char catalog, 14,647 prompt
  chars per single-tool turn, 1 planner call per tool turn. Predicted U1 delta: +1 planner call
  (~12,150 chars) per tool turn.
- 2026-09-24 — **D4 added.** T1's measurement contradicted the handoff's "a single-tool turn is unchanged"
  requirement: an unconditional re-plan taxes every tool turn. The loop is now opt-in by the planner.
- 2026-09-24 — **T2 done** (`83218556 feat(assistant): add bounded opt-in tool chaining`). Planner
  `follow_up` field + prompt contract, accumulating `tool_results`/`tool_steps`, `tool_loop_head`, and a
  bounded back-edge that bypasses the per-turn gates. `test_assistant_tool_loop.py:40-45` and `:48-70`
  rewritten (not deleted) to assert the bounded cycle; six new tests cover the opt-in, the cap, the
  combined-evidence answer, the per-turn-gate bypass, the write refusal, and the evidence budget.
- 2026-09-24 — Parent readback of T2 found two defects and one bounded correction fixed both
  (`b99646fe fix(assistant): keep tool evidence planner-only and refuse looped writes`). Re-verified by
  measurement, not by report: responder prompt back to exactly 2,497 chars; write guard now evaluated
  independently of the opt-in flag.
- 2026-09-24 — After-measurement of the normal tool turn recorded in the ledger above: call counts
  unchanged, responder prompt unchanged, planner prompt +363 chars from the new prompt contract.
- 2026-09-24 — **T3 done** (`9f77520b feat(assistant): re-evaluate the cost gate on every loop step`).
  Extracted a side-effect-free `_cost_snapshot(session, thread_id)` shared by `panel_cost_gate` and
  `tool_loop_head`; the loop head now reads the **live** cost mode instead of the value frozen at turn
  start, so a chain that itself pushes the thread past a threshold stops spending. `panel_cost_gate`
  keeps its exact return shape and its two owner alerts — the loop head emits none.
- 2026-09-24 — T3 verification: `cost_allowed` is consumed downstream at `nodes.py:770` →
  `execute_tool(..., cost_allowed=...)` → `registry.py:555`. A `blocked` loop-stop therefore sets
  `cost_allowed=False`, but the stop routes to `respond_stream`, where `tool_already_ran` is already true,
  so the tool branch (and that check) is never reached. Confirmed rather than assumed. 131 tests pass
  across the five assistant/chat test files; full suite 1,342 passed.

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

## Delivery — chained PRs, `stacked-to-main` (owner-decided 2026-09-24)

The running authored count crossed the review budget (~400 changed lines) while T4/T6/T7 were still
outstanding, so the delivery decision was taken **before** the next commit, as the rule requires. Owner
chose **Stacked PRs to main**: each slice lands on `main` in order, independently reviewable.

```
main ──●────────────●────────────▶
       │            │
       └ PR #1 ─────┘  (slice 1: the bounded loop)
                    │
                    └ PR #2 ──▶  (slice 2: observable + proven)
                        📍 next
```

| Slice | PR | Tasks | Content | Status |
|---|---|---|---|---|
| 1 | #1 → `main` | T1, T2, T3 | The loop exists and is safe: baseline measurement, planner opt-in, accumulating state, bounded back-edge, cap, write refusal, per-iteration cost gate | ready |
| 2 | #2 → `main` after #1 | T4, T6, T7, T8, T9 | The loop is observable and proven: user-visible write refusal, persisted `cap_reached`/`tool_steps`, end-to-end chained turn, chaining-cost delta | not started |

**Slice 1 review budget** (additions + deletions, unit record excluded), measured with
`git diff --numstat e16b3ff8..HEAD -- . ':(exclude)odd/tasks/'`:

| File | +/- | Lines |
|---|---|---|
| `app/chat/assistant/nodes.py` | +109 / −16 | 125 |
| `tests/unit/test_assistant_tool_loop.py` | +200 / −21 | 221 |
| `app/chat/assistant/graph.py` | +20 / −3 | 23 |
| `agent/prompts/assistant_plan.md` | +7 / −1 | 8 |
| `app/chat/assistant/state.py` | +4 / −0 | 4 |
| **Total** | | **381** |

**Out of scope for both slices**: U2, U3, deep research, any new tool, tool-catalog cost hygiene, lazy
tool loading.

## Next step

T4 (narrowed) — the looped-write refusal is enforced and tested, but the reason never reaches the user:
the refusal sets a canned `response`, and `respond_stream` overwrites it with the model's answer, so a turn
that asked to act finishes silently with text. Surface it honestly. Then T6 (persisted `cap_reached` /
`tool_steps`), T7 (harness end-to-end chain), T8 (chaining-turn delta), T9 (suite + PR).

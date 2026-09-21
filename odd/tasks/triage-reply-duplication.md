# ODD: triage-reply-duplication

**Stop the customer from receiving the CM-1 menu twice.**

## Objective

The `research_triage` sub-graph duplicates every reply the parent graph accumulated before it
ran. On a first-contact turn the customer receives the greeting and the 8-category menu **twice**,
followed by the actual reply. This unit fixes the graph wiring that causes it.

## Problem

Found and measured by the sibling unit `odd/kb-answer-fidelity.md` (F9).

`build_graph` adds the compiled `research_triage` sub-graph as a node with no explicit input schema
(`app/chat/graph.py:192`), and the sub-graph is compiled over the **same** `ConversationState`
(`app/chat/subgraphs/research_triage.py:152`). `ConversationState.replies` carries an `add` reducer
(`app/chat/state.py:175`, `Annotated[list, add]`), so LangGraph hands the sub-graph the parent's
`replies` — already holding the CM-1 greeting — and merging the sub-graph's final state back into
the parent re-adds them.

Measured, after the KB scope fix: **7 of 52** turns returned `[greeting, greeting, reply]`, of which
**5 were answers**. Before that fix it was **8 of 8** `kb_miss` turns, because only the miss path
reached the sub-graph often enough to show it. The KB fix made this **more visible on the happy
path**: a customer asking a price now gets the menu twice and then the price.

`receive` was instrumented during that investigation and runs **once**, so this is not node
execution — it is the state merge.

### Minimal reproduction (no LLM, no database)

```python
@dataclass
class S:
    replies: Annotated[list, add] = field(default_factory=list)
    intent: str = ""

sub = StateGraph(S); sub.add_node("respond", sub_respond); ...   # same schema as the parent
parent.add_node("research_triage", sub.compile())                 # no input schema
```

| | result |
|---|---|
| as shipped | `['GREETING', 'GREETING', 'ANSWER']` |
| with the fix | `['GREETING', 'ANSWER']` |

The reproduction matches the production symptom exactly, which is what makes the mechanism a
finding rather than a guess.

## Why now

It is user-visible on the path that now works. Every `valores`/`postventa` answer — the intents the
previous unit just made reachable — arrives with a duplicated menu in front of it.

## Scope

**In:** `app/chat/graph.py` (the sub-graph node wiring), one regression test, and this record.

**Out (explicitly):**

- **The sub-graph's internals.** AO-5 requires sub-graphs to wrap the vetted nodes; `respond` and
  `handoff` are reused unchanged. This unit changes how the parent invokes the sub-graph, not what
  the sub-graph does.
- **The `replies` accumulator and the CM-1 greeting.** Both are correct as designed; the defect is
  the boundary between them.
- The other KB pendings (F3/F4/F5, the panel assistant, the audience label). Each is its own unit.

## Spec constraints (binding — do not violate)

- `openspec/specs/agent-orchestration/spec.md` — **AO-5** (sub-graphs wrap vetted nodes) and
  **AO-3** (deterministic orchestrator dispatch). The dispatch and the reuse contract are unchanged;
  only the invocation boundary moves.
- `openspec/specs/conversation-manager/spec.md` — **CM-1** (single-agent flow with menu). The
  requirement is that first contact gets the greeting and menu; receiving it twice violates the
  intent of the requirement without any test catching it.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-triage-reply-duplication`
- Branch: `odd/triage-reply-duplication`
- Base: `53bbe320` (= `origin/main`, includes PR #277). Verified with `git merge-base HEAD origin/main`
  **before** writing this record.
- Files:
  - `odd/tasks/triage-reply-duplication.md`
  - `app/chat/graph.py`
  - `tests/integration/test_triage_reply_duplication.py`

## Constraints

- **Strict TDD: ON** — `openspec/config.yaml` (`testing.strict_tdd: true`); runner `uv run pytest`.
- Test DB: `eval "$(bash infra/test-db.sh env)"` is required before pytest, and a fresh test database
  needs `bash db/migrate.sh` first (the pytest conftest owns migrations; a standalone script does not
  inherit them).
- A fresh worktree has no `.venv`: `uv sync` before anything else.
- Known worktree artifact: `rapso worktree create` leaves `.opencode/tools/package-lock.json`
  untracked. Declare it to the review preflight, never commit it.
- No commit, push, or PR from a delegated phase unless the orchestrator authorizes it.

## Decisions

- **D1 — A wrapper node that clears the accumulator, NOT a partial `input_schema`.** LangGraph 1.2.11
  exposes `input_schema` on `add_node`, which looks like the obvious lever, and it is the wrong one
  here. The sub-graph reads 12 of `ConversationState`'s 21 fields; a partial schema would make the
  other 9 invisible inside the sub-graph, **including `memory_context`** — which `respond` injects
  into the prompt for CM-7. That is a silent regression of exactly the kind this session has been
  hunting, traded for four lines of saved code. Enumerating all 20 non-`replies` fields would work
  but drifts the moment a field is added to `ConversationState`.

  The wrapper has neither problem: it copies the state, clears one field, and invokes the sub-graph.
  Verified in the minimal reproduction above, including an assertion inside the sub-graph that
  `memory_context` survives.

- **D2 — The wrapper forwards `config`.** Invoking the compiled sub-graph manually would otherwise
  drop the `RunnableConfig`, losing callback and tracing propagation that LangGraph's sub-graph
  node normally carries. The node signature `(state, config)` and `invoke(state, config)` keep it.

- **D3 — The sub-graph's internals are untouched.** `build_research_triage_subgraph` and its nodes
  keep emitting `replies` exactly as they do now; the fix is at the parent's invocation boundary.
  This preserves the AO-5 reuse contract and keeps the change reviewable as one idea.

- **D4 — The regression test asserts the customer-visible reply list, not internal state.**
  Asserting `state.replies == [...]` would pin the wiring; asserting the returned replies pins the
  behaviour the customer experiences, which is what broke. The test also covers a non-sub-graph turn
  so the fix cannot be "verified" by a change that flattens every path.

## Tasks

- [x] **T1** — `odd/tasks/triage-reply-duplication.md` (this record).
- [x] **T2** — RED: `tests/integration/test_triage_reply_duplication.py`. Observed failure:
      `['greeting', 'greeting', 'answer']` — the duplicated greeting, with the answer present. The
      control test passed before the fix, as designed.
- [x] **T3** — `app/chat/graph.py`: `_triage_node` and the wiring change.
- [x] **T4** — GREEN: focused suites and the full suite pass.
- [x] **T5** — Re-ran the sibling fidelity harness: **7 duplicated-greeting turns → 0**, all 52
      queries.

## Findings

### The fix works, measured on the real path

Same corpus, same threshold, same model (`deepseek/deepseek-flash`), real provider, all 52 queries.
The only difference is this unit's wiring change.

| | before | after |
|---|---|---|
| turns with a duplicated greeting | **7** | **0** |
| of those, answers | 5 | — |
| of those, handoffs | 2 | — |

The regression test also pins the shape: exactly two replies on a first-contact `valores` turn
(greeting + answer), which fails if a future change drops the sub-graph's reply instead of
correcting the merge.

### The rejected alternative, recorded so it is not re-proposed

LangGraph 1.2.11 exposes `input_schema` on `add_node`, and it is the obvious lever for this bug.
It is the wrong one: the sub-graph reads 12 of `ConversationState`'s 21 fields, so any partial
schema makes the other 9 invisible inside it. `memory_context` is one of them, and `respond`
injects it into the prompt for CM-7 — the fix would have silently removed customer memory from
every `valores`/`postventa` answer. The wrapper has no such surface.

### Run-to-run variance, stated rather than smoothed

The answerable `answered` count moved from 4 to 5 between the pre-fix and post-fix runs. That is
intent-classification variance in the mocked-then-real path, not a second effect of this fix: the
change touches only the reply list, not retrieval, routing or the model. The duplicate-greeting
count is the number this unit owns, and it moved 7 → 0 deterministically.

## Acceptance criteria — result

1. RED observed before T3 (`['greeting', 'greeting', 'answer']`), GREEN after.
2. The eight focused suites → **110 passed**.
3. `uv run pytest tests/` → **exit 0, 100%**, no failures or errors.
4. The fidelity harness reports **0** turns with a duplicated greeting, where it previously
   reported **7**.
5. `git diff --name-only` shows only the authorized files plus the known untracked
   `.opencode/tools/package-lock.json`.

## Applicable checks

- `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/integration/test_triage_reply_duplication.py -q`
- `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/ -q`
- `git diff --name-only` → only the authorized files
- `git diff --check` → no whitespace errors

## Graph Check (Step 1 of the 5-Step Gate)

Consulted before writing: `build_graph` and the sub-graph node wiring (`app/chat/graph.py:171-232`),
`_route_path`, `_after_respond`, `ConversationState` and its `replies` reducer
(`app/chat/state.py:174-175`), `build_research_triage_subgraph` and its conditional edges
(`app/chat/subgraphs/research_triage.py:150-168`), and the three reused nodes' field reads
(`_kb_check`, `respond`, `handoff`). `graphify query "knowledge base retrieval and calibration"`
(depth 2, 407 nodes) previously confirmed the sub-graph has exactly one parent entry point and no
other caller.

# ODD: compaction-rotation-cue

## Objective

Render a harness metadata cue into the assistant prompt when the panel thread's history reached the
compaction threshold, so the agent learns that a recap was persisted as thread memory and that it must
**pull** it explicitly with `memory.read`. Render a distinct, more urgent cue when the recap write
**failed**, so the agent does not claim to remember history that no memory row holds.

This is decision **D5** from the Tukulpan/Engram session
(`.cortex-sessions/ready-for-odd/2026-09-17-memoria-tukulpan-vs-engram/report.md:80-87`), split out of
work unit #2 (`odd/tasks/remove-panel-memory-push.md`).

## Problem

Work unit #2 removed the automatic memory push from the panel prompt. The recap row still exists
(`app/services/tukulpan.py:330-340`: `scope="panel"`, `entity_id=f"thread:{thread_id}"`,
`MemoryType.SUMMARY`), and `memory.read` can still fetch it — but **nothing tells the agent it is
there**. Without a cue the agent silently cannot know its earlier turns were compacted away, so it may
either claim to remember them or fail to pull the recap when it needs them.

That makes D5 the missing half of the pull contract: after the push removal, the cue is the only
harness signal that connects rotation to an explicit scoped read.

### Premise correction (verified by reconnaissance, not inferred)

The original D5 wording said "the already-computed `meta["truncated"]` is rendered so the agent learns
its history rotated". **That is wrong — rendering `meta["truncated"]` would be a bug.**

- `meta["truncated"]` (`app/services/agent_chat.py:452`) means **injection-budget loss**: a context
  row or attachment did not fit `injection_budget`. It is set at `:459`, `:480`, `:493`, `:498`.
- The rotation signal is a different field: `compaction["rotated"]` from `compact_session()`
  (`app/services/agent_chat.py:359-423`).
- `compact_session()` also computes its own local `truncated = len(retained) != len(messages)`
  (`:378`) and passes it to `write_recap` (`:397`). **Three different things share the name
  "truncated".**

Rendering `meta["truncated"]` as rotation would fire a false "a recap is waiting" message every time
an attachment exceeds the budget.

### The `failed` trap (verified)

`rotated` and `failed` are **mutually exclusive**, and the worse case arrives with `rotated=False`:

```python
# app/services/agent_chat.py:400-406 — the recap write failed
return {..., "flushed": False, "rotated": False, "failed": True, ...}
```

A cue that checks only `compaction.get("rotated")` **silently swallows the failed case** — exactly when
the agent must know that no memory row holds the history. The cue must check `rotated or failed` and
branch.

### What compaction actually does (verified)

`compact_session()` does not delete thread history. `retained_message_ids` is **not consumed** at its
call site (`app/services/agent_chat.py:651-657`). It computes a bounded retained window and persists a
recap through `flush_panel_session` → `write_recap`. The component that actually narrows the prompt is
`assemble_context()`'s injection budget, and that is signalled by `meta["truncated"]`.

Therefore the honest cue semantics are: *"a recap was just saved to thread memory; pull it if you need
earlier context"* — not *"your history rotated away"*.

## Scope

**In:**

- Render the rotation cue in `_context_text()` (`app/chat/assistant/nodes.py:190-197`) — the single
  renderer already called by **both** the planner (`nodes.py:388`) and the responder (`nodes.py:563`),
  so one change covers both prompts with zero new plumbing.
- Two mutually exclusive branches: recap **saved** (`rotated`) and recap **unavailable** (`failed`).
- Unit tests for both branches plus the no-rotation case.
- Spec delta on `HL-3` (`openspec/specs/harness-lumat/spec.md:54-68`), which owns
  `compact_session()`/recap/rotation and already requires that failed writes not be reported as
  successful.

**Out:**

- `meta["truncated"]` (injection-budget loss) — a real but **different** signal, not part of D5. It
  stays visible through `AssistantState.context_meta` in evidence.
- Any change to `compact_session()`, `assemble_context()`, `write_recap()`, the tool registry, or the
  prompts (`agent/prompts/*.md`). None of them need to change.
- WhatsApp's independent customer-memory push (scoped out since the original Tukulpan proposal).
- `hybrid_search()`, relations, lifecycle decay, sessions-as-entity, sync.

## Why the cue lives in `_context_text()`

`AssistantState.compaction` **already exists and already travels**:

- Declared: `app/chat/assistant/state.py:168` (and in `ASSISTANT_STATE_KEYS`, `:16`).
- Populated: `run_assistant(compaction=...)` (`app/chat/assistant/graph.py:119`) → graph state
  `"compaction": compaction or {}` (`graph.py:141`), fed from `app/services/agent_chat.py:671` and
  persisted to the thread at `:697`.
- Consumed today only by `collect_evidence` for the `failed` case (`nodes.py:617-627`), which reaches
  UI evidence — **not** the model prompt.

So the cue needs **no new state field, no new node, no prompt placeholder, no template change**. It is
a local read of a field that is already in scope.

The cue is harness metadata, not memory content: it carries no memory payload and preserves `HL-1`'s
"no memory content" guarantee while serving its "explicit scoped memory reads" clause.

## Acceptance criteria

1. `_context_text(state)` renders a recap-saved cue when `state["compaction"]["rotated"]` is truthy.
2. `_context_text(state)` renders a recap-unavailable cue when `state["compaction"]["failed"]` is
   truthy, and **never** the saved cue in that case.
3. `_context_text(state)` renders no cue when compaction is absent, empty, or reported as not rotated
   and not failed.
4. The cue names the pull path (`memory.read`) and the conversation identity that is already rendered
   immediately above it.
5. Existing `_context_text` tests (`tests/unit/test_assistant_planner.py:259-273`) keep passing
   unchanged.
6. `HL-3` states the prompt-side rotation cue contract and its failed-write counterpart.
7. Full suite green with `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat`.

## Tasks

- [x] T1 — RED: unit tests for the two cue branches and the no-rotation case.
- [x] T2 — GREEN: render the cue in `_context_text()`.
- [x] T3 — Spec delta on `HL-3`.
- [x] T4 — Verify: targeted tests, then the full suite.
- [x] T5 — RDD review cycle on the frozen candidate.

## Verification

- `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/unit/test_assistant_planner.py -v`
- `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/`

Strict TDD is active (`openspec/config.yaml`): RED must be observed before the implementation.

## Graph nodes consulted

- `_context_text()` — `app/chat/assistant/nodes.py` community
- `compact_session()` — `app/services/agent_chat.py` / `test_assistant_harness_session.py` community
- `assemble_context()` — `assemble_context` community
- `harness_limits()` — `test_assistant_harness_session.py` community
- `test_compaction_records_rotation_metadata()` / `test_compaction_fires_once_the_thread_window_fills()`
- `Harness Lumat Specification` (HL-1, HL-3), `Harness Lumat Design`, `Planner Tool Catalog`
- Graph: `graphify-out/GRAPH_REPORT.md` built from `2c3d3936` (5534 nodes / 12193 edges / 576
  communities); traversal BFS depth=2 over "assistant compaction rotation context rendering planner".

## Status

**complete, verified, RDD-approved, uncommitted.** Worktree
`../lumat-agent-odd-compaction-rotation-cue`, branch `odd/compaction-rotation-cue`, base `2c3d3936`.

### Verification evidence

- RED (before implementation): `2 failed, 15 passed` — both new cue tests failed with
  `assert 'recap saved' in ...` and `assert 'unavailable' in ...`; the two pre-existing
  `_context_text` tests passed unchanged.
- GREEN (targeted file): `17 passed`.
- Full suite: `877 passed, 2 warnings in 448.00s (0:07:28)`.

### RDD review

- Lineage `review-e84822d8086939a8`, target
  `sha256:1721da78f4f3469766d06ab71239005444a75b97ae6592c31be59eb9adcc3f20`.
- Candidate: 3 tracked paths, 62 changed lines, tier `medium`, correction budget 31.
- Lenses: one — `review-reliability`. **0 findings.** Result hash
  `sha256:b6f7b79f350e16f1f9694d056c27ef545e9af3bacdd536e621e6d7e319dec995`.
- Acknowledgement consumed revision
  `sha256:67143fa2ceff90428711fc77605cfdb6c08fa69191fe65d980d1967b1842882f`; authority `burned`.
- The ODD task document was deliberately excluded from the candidate
  (`--untracked-scope=exclude`), so updating it after the burn did not touch the frozen bytes.

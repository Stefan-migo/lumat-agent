# ODD: assistant-planner-contract

## Objective

Make the two orphaned defects from the `2026-09-17-lazy-loading-tools-asistente` session real fixes,
so a scoped `memory.read` call from the panel assistant either succeeds with valid arguments or fails
loudly — instead of silently returning empty memory that reads to the user as "no tengo memoria".

## Problem

The session left two defects unowned (its #1 went to `odd/compaction-window-gate`; its #6 collides
with that worktree's `state.py`). Both sit in files that worktree does not touch.

**Defect A — `_context_text` discards `context.meta`.** `assemble_context`
(`app/services/agent_chat.py:466-474`) returns `meta: {"scope": "panel", "entity_id": "thread:{id}"}`.
`_context_text` (`app/chat/assistant/nodes.py:205-206`) renders only `items[].content` and drops
`meta` entirely. The one value the model needs to build valid scoped arguments is computed and
discarded one line before the planner prompt is built.

**Defect B — `MemoryArgs` fails open.** `scope: str` (`app/chat/assistant/tools/registry.py:73`)
with a validator (`:78-87`) that only checks the two known scopes. Any other value passes:

```
MemoryArgs.model_validate({"scope": "banana", "entity_id": "whatever"})   # PASSES today
```

A wrong-but-plausible scope clears the guardrail, sets `decision: "execute"`, and returns an empty
list. The user reads that as "no memory" instead of "your argument was invalid".

## Why — verified evidence, not inference

From the session's live run (13 real provider calls, `deepseek-flash`, the real `plan_llm` +
`guardrails` path; scripts `/tmp/opencode/live_plan_probe2.py`, `live_plan_stability.py`):

| Variant | Tools block | Thread id in context | Valid args |
|---|---|---|---|
| A (production today) | names only | no | **0/3** |
| D | schemas + precise doc | yes | **3/3** |

`MemoryArgs` scope as the model sees it: `{"type":"string","minLength":1,"maxLength":100}` — a
generic string. The contract (`scope="panel"` ⇒ `entity_id` must start with `thread:`) lives only in
the Pydantic validator, which is invisible to the model. So the schema under-specifies what the
validator over-enforces.

Variant D's precise doc, verbatim (`live_plan_probe2.py:75-79`):

```
Read stored memory entries. For the memory of the CURRENT CONVERSATION THREAD
use scope="panel" and entity_id="thread:<thread id>". For a customer use
scope="customer" and entity_id="customer:<customer id>".
```

and the thread id arrived as a context entry (`:122-124`): `Conversation thread id: 4242`.

**Honest limit on this evidence.** Variant D carried its contract in the *tool description*, which
only reaches the model when a tool block is sent. Production sends **names only**
(`nodes.py:385`: `", ".join(config.tools_whitelist)`), so neither C nor D reproduces production
exactly, and the combination this change creates — names only + identity + a prompt-stated
convention — was **never probed**. That gap is closed by T6, not asserted away.

Two variants were never tabulated (B, C ran once each; their output was not saved), so the
attribution between "identity alone" and "explicit contract" is not settled by the recorded data.
This change takes the conservative path: supply both.

## Scope

### T1 — RED then GREEN: `MemoryArgs` fails closed

`scope: Literal["panel", "customer"]`. Observable: an unknown scope raises `ValidationError`, and
`model_json_schema()["properties"]["scope"]` carries the closed `enum` — so the contract stops
living only in the validator.

### T2 — RED then GREEN: the planner sees the conversation identity

`_context_text` renders the conversation identity from `context.meta` after the items, only when
`scope` and `entity_id` are both present (`meta` is `{}` on the session-less path,
`nodes.py:421-423`, so the guard is required). This feeds both prompt builds (`:385` planner,
`:561` respond) — accepted deliberately: it is true context for the conversation, and one function
with one behaviour is smaller than a parameter with two.

### T3 — The prompt states the scoped-read convention

`agent/prompts/assistant_plan.md` gains one sentence naming the convention and pointing at
`<context>` for the value — the piece variant D proved necessary. Prompts are file-backed
(`app/services/prompts.py:143`, `prompts={name: load(path) ...}`), so no reseed is involved.

Also correct the `memory.read` tool description, today `"Read scoped customer memory."`
(`registry.py:255`), which is factually wrong: the tool serves `panel` and `customer` scope.

### T4 — Spec sync

`openspec/specs/assistant-tools/spec.md` mentions `memory` zero times. State the scope/entity
contract and the closed scope domain.

### T5 — Suite green.

### T6 — Live verification of the real production shape

Re-run the probe with production's actual composition (names-only tools + the new identity and
prompt convention) and record the tally. This is the only check that proves the effect rather than
the wiring, and it is what the session's own F5 limit demands.

## Out of scope (do not expand)

- `compact_session` / the compaction gate — owned by `odd/compaction-window-gate` in
  `/home/stefan/repos/lumat-agent-odd-compaction-window-gate`. **Do not touch
  `app/services/agent_chat.py`, `app/chat/assistant/state.py` or `app/config.py`.**
- `PlannerOutput.summary max_length=200` (session defect #6) — `state.py` is that worktree's file.
- Sending tool schemas or descriptions to the model (the session's pending eager/lazy/hybrid
  tradeoff). Not needed for this fix and it would add ~1.1k tokens/turn.
- `record_milestone` dead code (session defect #5).
- A thread↔customer binding, which is what `scope="customer"` would need to become reachable from
  the panel (session defect #4 — a product decision, not a fix).

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-planner-contract`
- Branch: `odd/planner-contract` (base `main` @ `366a4aae`)
- Files:
  - `app/chat/assistant/nodes.py`
  - `app/chat/assistant/tools/registry.py`
  - `agent/prompts/assistant_plan.md`
  - `openspec/specs/assistant-tools/spec.md`
  - `tests/unit/test_assistant_tools.py`
  - `tests/unit/test_assistant_planner.py`
  - `tests/integration/test_assistant_harness_context.py`
  - `odd/tasks/assistant-planner-contract.md`

## Constraints

- **TDD: ON** — source: project config `openspec/config.yaml` (`apply.tdd: true`,
  `strict_tdd: true`). Runner: `uv run pytest tests/`. Observed RED is required before each
  implementation step; never invent RED evidence.
- Integration tests need `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat`.
- `assemble_context` keeps its deterministic injection budget and truncation metadata (HL-1). This
  change consumes `meta`; it does not alter it.
- Conventional commits, no AI attribution.
- Planning heuristic: ~400 authored changed lines. This is expected to be far smaller.

## Acceptance criteria

1. `MemoryArgs` rejects an unknown scope and its JSON schema exposes the closed scope domain.
2. `_context_text` includes the conversation identity when `meta` carries it, and omits it cleanly
   when `meta` is empty.
3. The planner prompt states the scope/entity convention and points at `<context>` for the value.
4. Each acceptance criterion above fails against the pre-change code (RED observed) and passes after.
5. The full suite passes.
6. The live probe on production's real composition is run and its tally recorded honestly, including
   any run where the model still produces invalid arguments.

## Checks / verification commands

- Targeted: `uv run pytest tests/unit/test_assistant_tools.py tests/unit/test_assistant_planner.py tests/integration/test_assistant_harness_context.py -q`
- Full: `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/ -q`

## Graph nodes consulted

`graphify query "assistant planner context assembly and tool args validation"` on `main` @ `366a4aae`
(graph `graphify-out/graph.json`, built 2026-09-17 15:48):

- `assemble_context()` — `app/services/agent_chat.py:393` (community `test_assistant_harness_context.py`)
- `_context_text` via `nodes.py` — `app/chat/assistant/nodes.py:1` (community `nodes.py`)
- `MemoryArgs` / `RuleArgs` — `app/chat/assistant/tools/registry.py:96` (community `registry.py`)
- `ToolValidationError` — `app/chat/assistant/tools/registry.py:30`
- `execute_tool()` / `get_tool()` — `app/chat/assistant/tools/registry.py:279,268`
- `PlannerOutput` / `.require_tool_for_tool_kind()` — `app/chat/assistant/state.py:31,45` (read-only)
- `plan_llm` → `parse_planner_output()` — `app/chat/assistant/nodes.py:156`
- `test_assembly_does_not_search_and_reports_fixed_budget_metadata()` —
  `tests/integration/test_assistant_harness_context.py:104`

## Progress

- [x] **T1** — `MemoryArgs.scope` is `Literal["panel", "customer"]`; RED observed, GREEN observed.
- [x] **T2** — `_context_text` renders the conversation identity from `context.meta`, guarded; RED observed, GREEN observed.
- [x] **T3** — `assistant_plan.md` states the scoped-read convention; `memory.read` description corrected.
- [x] **T4** — AT-8 added to `openspec/specs/assistant-tools/spec.md`.
- [x] **T5** — 866 tests collected, full suite green.
- [x] **T6** — live probe on production's real composition: **3/3 valid arguments**.

### Parent correction applied during readback

The delegated writer rendered the identity as
`Conversation thread id: {meta['entity_id'].removeprefix('thread:')}`. `_context_text` is generic
over `meta`, but `removeprefix('thread:')` hardcodes the panel prefix: under any other scope the
function would emit a line labelled "thread id" carrying a non-thread entity — a silent falsehood to
the model. Replaced with both values rendered verbatim,
`Conversation identity: scope={scope} entity_id={entity_id}`, which also removes the inference step
(the model copies the literal `entity_id` instead of concatenating `thread:` + id). Test updated to
match.

## Verification evidence

### RED (observed before implementation, and independently reproduced by the orchestrator)

`git stash push app/chat/assistant/nodes.py app/chat/assistant/tools/registry.py` then:

```
FAILED tests/unit/test_assistant_tools.py::test_memory_args_reject_unknown_scope_and_expose_closed_scope_schema
FAILED tests/unit/test_assistant_planner.py::test_context_text_includes_conversation_identity_when_available
E  Failed: DID NOT RAISE ValueError
E  AssertionError: assert 'Pinned fact\nRecent message' == 'Pinned fact\nRecent message\nConversation identity: scope=panel entity_id=thread:42'
```

### GREEN

```
TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat \
  uv run pytest tests/unit/test_assistant_tools.py tests/unit/test_assistant_planner.py \
  tests/integration/test_assistant_harness_context.py -q
................................................                         [100%]
```
48 passed.

Full suite: `866 tests collected`; observed green (no failures, no errors).
Two pre-existing warnings are unrelated to this change: an unawaited `_publish_all` coroutine in
`tests/integration/test_webhook_ingest.py` and the fastembed mean-pooling warning from `app/services/kb.py`.

`ruff` is not available in this environment (`Failed to spawn: ruff`); `openspec/config.yaml` declares
`quality.linter: false`, so no lint gate applies. `git diff --check` passes.

### T6 — live probe, production composition (`/tmp/opencode/planner_contract_probe.py`)

Reproduces production exactly: names-only `<available_tools>` (19 tools), the real prompt file, a
real `assemble_context`-shaped context. Credentials from the main worktree's gitignored
`infra/.env`; code from this worktree. 3 real `deepseek-flash` calls; no DB or repo writes
(`session=None`).

Wiring, as actually delivered to the provider:

```
[OK ] tools block is names only (production shape, no schemas)
[OK ] prompt states the scoped-read convention
[OK ] context carries the conversation identity
```

Delivered `<context>`:

```
Hola, necesito revisar el caso de Ana.
Listo, ¿querés que busque algo en particular?
Conversation identity: scope=panel entity_id=thread:4242
```

Tally:

| Measure | Result |
|---|---|
| proposed `memory.read` | **3/3** |
| `PlannerOutput` PASS | **3/3** |
| `MemoryArgs` PASS | **3/3** |
| used `scope="panel"` | **3/3** |
| used `entity_id="thread:4242"` | **3/3** |

Every run produced exactly `{"scope": "panel", "entity_id": "thread:4242"}`.

**This closes the gap the task doc flagged as unprobed.** The session measured 0/3 on production's
composition (names only, no identity) and 3/3 only on variant D, which carried its contract in a tool
description that production never sends. The composition this change creates — names only + identity
+ a prompt-stated convention — was never probed before and is now 3/3, with all three runs agreeing.

### Honest limits

- n=3 on one provider (`deepseek-flash`) and one user turn. It is a stability check, not a
  distribution.
- Variants B and C from the session remain untabulated, so how much of the gain comes from the
  identity versus the prompt convention is not isolated by this probe. This change supplies both
  deliberately; the split is not claimed.
- The local Postgres is a fresh database, so no production memory rows were read end to end. The
  probe verifies argument validity, not the memory read itself.
- Session defect #6 (`PlannerOutput.summary max_length=200`) is untouched: all three runs produced
  summaries of 95-141 chars and passed, consistent with the session's finding that it is intermittent
  and needs measurement against real traffic.

## Recovery

Resume with `mem_context`, then the project-scoped `mem_search` for this feature, then
`mem_get_observation` for the full document, then read this file. Continue from the first
unchecked task.

## Next step

All six tasks are closed. Remaining: native review of the candidate, then commit and PR. The open
follow-ups this change deliberately did not take are listed under "Out of scope"; the largest is the
thread↔customer binding that `scope="customer"` would need to become reachable from the panel.

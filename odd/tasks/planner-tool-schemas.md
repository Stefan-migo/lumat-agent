# ODD: planner-tool-schemas

## Objective

Give the panel assistant planner the real tool catalog — name, description, and JSON Schema of the
arguments — from the single registry that already owns it, instead of a comma-separated list of bare
tool names.

## Problem

`plan_llm` interpolates `", ".join(config.tools_whitelist)` into `<available_tools>`
(`app/chat/assistant/nodes.py:391`). The planner receives 19 bare names and zero argument schemas.

**Consequence.** A tool whose arguments are non-trivial is effectively non-invocable. `memory.read`
requires `scope` and `entity_id` (`MemoryArgs`, `app/chat/assistant/tools/registry.py:71-87`) and the
model is never told those argument names exist; any future memory tool is born dead the same way. The
hand-written hint at `agent/prompts/assistant_plan.md:7` is a manual duplicate of what the registry
already knows and **has already drifted** — it documents "reading **or writing** memory" for a write
tool that was never built.

## Why — root cause (verified, not inferred)

- The registry already carries the whole contract: `ToolDefinition(name, args_model, read_only,
  handler, description)` with `.schema()` returning `args_model.model_json_schema()`
  (`registry.py:229-243`).
- `tool_schemas()` already exists (`registry.py:275-276`) and is called **only by tests**
  (`tests/unit/test_assistant_tools.py:16,25,49`). Production never calls it.
- So the defect is not missing data, it is an **unused source of truth**: the planner is fed a lossy
  projection (names) of a registry that holds the full contract.
- Registry lookup is safe for every whitelisted name: `_build_assistant` rejects any
  `tools_whitelist` entry outside `KNOWN_TOOLS` at load time (`app/agent_registry.py:149-153`), and
  the assistant block declares exactly 19 entries (`agent/registry.yaml:56-86`).

## Why not the LangGraph tool-calling path (investigated first, as the handoff required)

The prior session's handoff asked whether LangGraph's native tool-calling replaces the hand-rolled
`plan_llm -> guardrails -> execute` triad. Investigated before writing code. **Verdict: no.**

- The graph is `StateGraph(AssistantState)` over a plain state dict with **no checkpointer**
  (`app/chat/assistant/graph.py:73-74`), not the message state `ToolNode` expects.
- There is **no planner/tool loop**: `execute_tool -> evidence -> END` (`graph.py:112-115`). One shot.
- `create_react_agent` is **deprecated** in the resolved `langgraph` 1.2.11 (`uv.lock:708-723`;
  `langgraph-prebuilt` 1.1.0).
- There is no LangChain `ChatModel`: `plan_llm` calls the raw `openai` SDK
  (`nodes.py:397-402`, `app/services/llm.py:31-54`), so `.bind_tools()` does not exist without
  writing an adapter.
- `ToolNode` executes tool calls itself, which would bypass `guardrails` (`nodes.py:435-463`):
  whitelist enforcement, argument-model validation, `validate_execution` approval + consumption, cost
  gate, audit trail, project authorization.

The framework path **replaces** the guards instead of nesting inside them. Rejected.

## Scope

**In:** build the catalog in `plan_llm` from `TOOL_REGISTRY` filtered by `config.tools_whitelist`;
explain the catalog format in the prompt and repair the drifted hint; unit coverage for the catalog
contract.

**Out:** the responder's identical `", ".join` (`nodes.py:566`) — that is the DSML leak, work unit #6;
`registry.py` changes; `guardrails` or approval semantics; `ToolNode` / `create_react_agent`; memory
tools; push-channel removal; the `legacy_compat` branch.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-planner-tool-schemas`
- Branch: `odd/planner-tool-schemas`
- Base: `1d3e4396`
- Files: `odd/tasks/planner-tool-schemas.md`, `app/chat/assistant/nodes.py`,
  `agent/prompts/assistant_plan.md`, `tests/unit/test_assistant_planner.py`

## Constraints

- **Strict TDD: ON** — source: `openspec/config.yaml` (`testing.strict_tdd: true`). Runner:
  `uv run pytest tests/`. Observe RED before the source change; never invent RED evidence.
- Integration commands require `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat`.
  Without it, `tests/integration/conftest.py` falls back to the least-privilege `app` role and fails
  with `InsufficientPrivilege` — a known environment condition, not a defect.
- The catalog must contain exactly the whitelist, never the full registry. Advertising a tool the
  whitelist excludes would invite plans that `guardrails` then rejects.
- Token cost is accepted (decision D3a, ~1.1k tokens/turn already measured). Keep the payload compact;
  do not restate registry data in prose.
- `guardrails` and `execute_tool` must remain the single enforcement boundary and must not change.
- Planning heuristic: ~400 authored changed lines; this change is expected to be far smaller.
- No commits, no push, no PR from this session unless separately authorized.
- All artifacts are written in English.

## Tasks

- [x] **T1 — RED.** Unit coverage: the planner prompt carries, for each whitelisted tool, its name,
      description, and the JSON Schema of its arguments; it never carries a tool outside the whitelist.
- [x] **T2 — GREEN.** Build the catalog in `plan_llm` from `TOOL_REGISTRY` filtered by the whitelist and
      inject it into `<available_tools>`; update `assistant_plan.md` to describe the format and remove
      the drifted memory hint.
- [x] **T3 — Evidence.** Run the required checks, record exact RED/GREEN output and honest limits.

## Acceptance criteria

1. The planner prompt contains, for every whitelisted tool, its name, its description, and the JSON
   Schema of its arguments.
2. No tool outside `config.tools_whitelist` appears in the payload.
3. `memory.read`'s required `scope` and `entity_id` are visible to the planner.
4. Each criterion fails against the pre-change code (RED observed) and passes after.
5. Only the four authorized files change and the required suites meet the baseline.

## Checks

- `uv run pytest tests/unit/test_assistant_planner.py -q`
- `uv run pytest tests/unit/test_assistant_tools.py -q`
- `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/unit tests/integration/test_assistant_harness_guardrails.py tests/integration/test_assistant_harness_production.py tests/integration/test_assistant_chat.py -q`
- `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/ -q`
- `git status --short`
- `git diff --check`

Prerequisite for the integration commands: `docker compose -f infra/docker-compose.yml up -d db`.
Never `down -v` — it deletes panel data.

## Decisions

- **Serialize the registry instead of extending the hand-written hint.** The hint is a duplicate that
  already drifted once; a second manual copy would drift again. Rejected alternative B from the prior
  session's report.
- **Filter by the whitelist rather than emitting `tool_schemas()` wholesale.** The prompt must match
  what `guardrails` will allow, or the planner is invited to propose plans that get rejected.
- **Investigate the framework path before building.** It would have been the smaller writer's first
  instinct to reach for `ToolNode`; verifying that it deletes the guards is what made variant A the
  obvious choice.
- **Leave `nodes.py:566` alone.** Same shape, different defect (the responder is handed tools it
  cannot call). Mixing it in would make this unit unreviewable and is explicitly work unit #6.

## Progress

- [x] Created this ODD record before the first source change.
- [x] T1 — RED observed before the source change: the new planner catalog test attempted to parse the bare-name payload and failed with `json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)`.
- [x] T2 — GREEN: `plan_llm` now serializes the whitelist-filtered registry catalog in whitelist order; the prompt documents the JSON contract and the memory hint describes reading only.
- [x] T3 — Required verification completed; exact results are recorded below.

## Verification evidence

| Command | Observed result |
| --- | --- |
| `uv run pytest tests/unit/test_assistant_planner.py -q` (RED, before source change) | `__________ test_plan_llm_includes_whitelisted_tool_catalog_in_prompt __________`; `E           json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)`; `1 failed, 13 passed` was not printed by the configured quiet runner. |
| `uv run pytest tests/unit/test_assistant_planner.py -q` (GREEN) | `..............                                                           [100%]` — 14 tests passed. |
| `uv run pytest tests/unit/test_assistant_tools.py -q` | `................................                                         [100%]` — 32 tests passed. |
| `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/unit tests/integration/test_assistant_harness_guardrails.py tests/integration/test_assistant_harness_production.py tests/integration/test_assistant_chat.py -q` | `........................................................................ [ 36%]`, `........................................................................ [ 73%]`, `....................................................                     [100%]` — 196 tests passed. |
| `TEST_ADMIN_DB_URL=postgresql://lumat:lumat@localhost:5432/lumat uv run pytest tests/` | `877 passed, 2 warnings in 479.47s (0:07:59)`. Warnings: `_publish_all` coroutine was never awaited in `tests/integration/test_webhook_ingest.py::test_startup_sweep_reprocesses_received`; fastembed model pooling warning in `tests/spec/test_projects_spec.py::test_project_slug_is_normalized_and_unique`. |
| `git status --short` | `M agent/prompts/assistant_plan.md`; `M app/chat/assistant/nodes.py`; `M tests/unit/test_assistant_planner.py`; `?? odd/tasks/planner-tool-schemas.md`. |
| `git diff --check` | No output; passed. |

**Graph nodes consulted (Graph Check, Step 1):** the worktree contains no `graphify-out/` report or graph
at base `1d3e4396`; the graph evidence recorded in this task document was consulted instead. Although
the `graphify` executable is present, no query was run because there is no graph to query and rebuilding
would modify unauthorized artifacts:

- `app_chat_assistant_nodes_plan_llm` — community `nodes.py`
- `app_chat_assistant_nodes_execute` — community `nodes.py`
- `registry.py` — community `assistant/tools`
- `AssistantState` — community `assistant/state.py`
- "Panel assistant cost-gate flow" and "Harness Lumat Design" communities (`GRAPH_REPORT.md:773-775`,
  `:801-803`)

The directed path `plan_llm -> cortex_session_gate -> sdb_trigger_gate -> guardrails` is confirmed
directly by the graph wiring (`graph.py:95-113`); the defect lives on the `plan_llm` side of that edge.

**Payload cost (parent measurement, not a required check).** `_planner_tool_catalog` over the declared
19-tool whitelist produced 6,437 characters (~1,609 tokens) against 314 characters (~78 tokens) for the
previous comma-separated name list — a delta of ~1,531 tokens per planner turn. This is consistent with
the cost already accepted in decision D3a and is recorded here rather than treated as a finding.

**Native RDD review.** The candidate was frozen with `--untracked-scope=exclude`, so this untracked
record is deliberately outside the reviewed scope: the candidate is exactly the three code files.
Tier `medium`, 3 files, 59 lines, one lens (`review-reliability`), correction budget 30, lineage
`review-99278ecc67395081`, target identity
`sha256:a41ca6562d91af79288b8d4604c2696d346d9364ec715bdb29728883bb26d214`. Result: **approved with zero
findings**, result hash `sha256:1320bec351a32d9328c8847dddf357c5fcc7d542a4f9afb4a2485ce7bd2da247`;
acknowledgement consumed (`gentle-ai.review-acknowledged/v1`, `authority: burned`). No correction round
was requested, so the frozen candidate bytes are exactly the bytes that were approved.

## Recovery

Resume with `mem_context`, then the project-scoped `mem_search` for this feature, then
`mem_get_observation` for the full document, then read this file. Continue from the first unchecked
task.

## Next step

The work unit is implemented, verified, and reviewed (approved, authority burned). Nothing has been
committed, pushed, or opened as a PR, so delivery is the next human decision. The responder's tool list
(`nodes.py:566`) remains a separate, deliberate follow-up.

# Exploration: harness-lumat

## Current State

The panel assistant already has a durable LangGraph boundary, but it is a thin
single-turn execution graph rather than a session-aware harness:

```text
START -> plan (keyword approval heuristic) -> approval -> execute -> evidence -> END
```

`app/chat/assistant/nodes.py::plan` only detects `create`, `delete`, `change`,
and `send`; it does not call an LLM, select a tool, classify complexity, or
consume the assistant registry. The response path sends only the current user
content and attachment context to the model and still uses the hardcoded system
prompt `You are Lumat's internal operations assistant.`. The existing
`agent/prompts/assistant_{plan,respond,classify}.md` files and
`agent/personas/assistant.md` are validated and exposed as capability metadata,
but are not used to assemble runtime prompts.

The persistence boundary is real and should be retained. `agent_chat.py`
persists `InternalChatThread`, `InternalChatMessage`, `current_plan`,
`active_run_id`, `assistant_state`, ordered events, audit entries, and recovery
claims through `claim_execution`. `routes/chat.py` exposes thread creation,
read/recovery, message submission, approvals, SSE replay, attachments, and a
read-only capability endpoint. However, thread messages are not read by the
assistant graph when planning or responding, so the runtime remains stateless
with respect to conversation history despite durable storage.

The existing tool registry is typed, bounded, and directly service-backed. It
contains read tools plus the single write tool `automation.create_rule` and
enforces argument validation and exact approval for writes. The assistant graph
does not yet enforce `assistant.tools_whitelist` at its dispatch boundary; the
registry is used by the capability endpoint and by the WhatsApp H2 router's
sub-agent path, not by the panel assistant planner.

`app/chat/graph.py` provides the relevant deterministic safety precedent for the
WhatsApp runtime: `emergency_gate -> cost_gate -> handoff_gate` runs before LLM
work, with deterministic routing, audit, and bounded cost behavior. This is a
pattern to adapt, not a graph to merge with the panel assistant: WhatsApp and
panel state must remain separate.

Memory is implemented as `app/services/memory.py` over migration `009_memory.sql`:
typed memories, pins, review status, pgvector/FTS hybrid search, customer
context loading, per-turn persistence, close-time memo, and observations. Its
production consumers are the WhatsApp graph, customer ficha, and `memory.read`;
the panel assistant does not inject memory. There is no existing panel-scoped
injection contract, token measurement, rolling-thread compaction, pre-compaction
flush, or invisible session rotation. Attachment context has a configured
character limit, but that is not a general token budget.

The database is already the source of truth for panel thread state:
`InternalChatThread` stores `assistant_state`, `current_plan`, and
`active_run_id`; `InternalChatMessage` stores the chronological conversation
and per-run metadata. No LangGraph checkpointer is present or needed.

## Affected Areas

- `app/chat/assistant/graph.py`, `app/chat/assistant/nodes.py`,
  `app/chat/assistant/state.py` — evolve the graph to context assembly, LLM
  planning, deterministic guardrails, tool/response branches, persistence
  evidence, and extension hooks without rewriting the runtime.
- `app/services/agent_chat.py`, `app/panel/api/routes/chat.py`,
  `app/chat/assistant/recovery.py` — load chronological thread context, keep DB
  recovery authoritative, and preserve approval/SSE/API compatibility.
- `app/models.py` and migrations only if the design proves new durable fields are
  required; current `assistant_state` JSONB is intentionally sufficient for the
  session contract until design establishes otherwise.
- `agent/registry.yaml`, `agent/personas/assistant.md`,
  `agent/prompts/assistant_{plan,respond,classify}.md`, and
  `app/services/prompts.py` — assemble the assistant persona, prompt templates,
  declared tools, and memory scope. The existing generic prompt loader is wired
  to WhatsApp prompts, not these assistant entries.
- `app/chat/assistant/tools/registry.py` — add the narrow assistant dispatch
  whitelist boundary; do not duplicate tool handlers or call panel HTTP routes.
- `app/services/memory.py`, `db/migrations/009_memory.sql`, and memory specs —
  consume existing memory primitives through a panel/pinned injection contract;
  do not implement Tukulpan internals or rename the service in this change.
- `app/chat/graph.py` and deterministic gate services (`emergency`, `costs`,
  `handoff`, `audit`) — provide approval/cost/audit design precedent and
  reusable guardrail concepts, while preserving WhatsApp semantics.
- `agent/skills/sdb.md`, `agent/README.md`, `openspec/specs/agent-config/`, and
  all grep consumers — rename Lumat's old “SDB (Deterministic Behavior
  Database)” terminology to “Gates deterministas / Guardrails”. Do not add the
  seven-phase Spec Driven Behavior subgraph here.

## Prior-Art Audit

### `2026-08-21-config-agente-lumat`

Already shipped the declarative `agent/` tree, `app/services/prompts.py`
loader/strict renderer, fallback behavior, reference-only skills, and initial
registry shape for WhatsApp prompt extraction. Its design explicitly left the
registry as data-only and deferred a runtime registry consumer to H2. It does
not wire the assistant-specific persona or three assistant prompt files into
the panel graph. The current loader's fallback literals are WhatsApp
orchestrator/classify/summary prompts, not the panel assistant prompt set.

### `2026-08-24-h2-router-langgraph`

Already shipped the five-agent roster, cached read-only registry validation,
deterministic `orchestrate` dispatch, the `research_triage` subgraph, scoped KB
retrieval, bounded retry, and cost coverage for the WhatsApp multi-agent path.
The other four sub-agents remain data-only. The archive explicitly enforced no
checkpointer, no panel endpoints, no new DB tables, no assistant harness, and no
gate-envelope redesign. Its dispatch and gates are useful precedent but are
not a panel assistant planner.

### `2026-09-07-panel-ai-agent-grammar`

Already shipped frontend presentation grammar for the panel shell, conversation
views, and `AgentChat` states. It changed no backend, endpoint, streaming, or
runtime behavior. It supplies UI constraints only; harness behavior remains
backend work.

### `2026-09-09-panel-asistente-lumat`

Already shipped the separate panel `AssistantState` graph, typed tools, exact
argument approval, audit/evidence events, durable recovery, admin-only SSE,
read-only capability view, validated assistant registry references, automation
write support, and attachment/multimodal handling. These are foundational
contracts to preserve, not to duplicate. The archive's design left assistant
per-run/token budgets as an open question and deliberately implemented a
planner/approval/execution graph rather than a session-aware agent harness.
The current source confirms the remaining gap: keyword planning and a hardcoded
assistant system prompt, no thread-history context, no panel memory injection,
and no registry prompt wiring.

### `2026-08-20-memoria-persistente-lumat`

Already shipped the memory schema, CRUD, pins/status, hybrid search,
customer-scoped context, WhatsApp per-turn persistence, close-time memo and
observations, panel customer-memory management, and `memory.read`. It explicitly
deferred batch compression, decay, automatic conflict judgment, cross-project
search, and a memory ToolNode. It does not provide the panel thread injection
contract, rolling session compaction, or pre-compaction flush required here.

### Existing canonical capabilities

`openspec/specs/internal-agent-chat`, `assistant-operations`,
`assistant-tools`, and `agent-config` describe the delivered durable graph,
approval, tool, attachment, registry, and read-only capability contracts. The
new harness MUST extend these contracts without weakening admin authorization,
exact-argument approval, audit/evidence ordering, recovery, or the no-checkpointer
decision. `agent-orchestration` applies to WhatsApp and its four data-only
sub-agents; it is not a license to implement panel sub-agents in this change.

## Approaches

1. **Evolve the existing panel assistant graph** — replace the keyword planner
   with a structured-output LLM planner, add deterministic guardrails and
   context assembly nodes, and retain the current DB persistence, approval,
   tools, evidence, SSE, and recovery seams.
   - Pros: smallest architectural delta; preserves shipped security and API
     contracts; aligns with the Cortex decision and current LangGraph topology.
   - Cons: context/compaction and failure semantics require careful new state
     contracts; structured-output failures need a deterministic fallback.
   - Effort: Medium/High.

2. **Create a new generic agent loop beside the current graph** — implement a
   separate runtime and migrate panel chat to it later.
   - Pros: unconstrained design space.
   - Cons: duplicates persistence, approval, recovery, tool execution, and SSE;
     creates competing sources of truth and a risky migration boundary.
   - Effort: High.

## Recommendation

Choose Approach 1. The shipped assistant graph is already the correct durable
boundary; the work is to make its per-turn planning and context truthful, not to
replace its runtime. The design should introduce only the minimum new state
needed for assembled context, planner output, guardrail decisions, and
compaction evidence, and should keep DB persistence authoritative with no
LangGraph checkpointer. Use the existing approval, tool registry, audit, SSE,
attachment, and recovery contracts as seams.

The harness SHOULD expose extension hooks for future panel sub-agents and the
future SDB Spec Driven Behavior subgraph, but MUST NOT implement either here.
It MUST leave the exact SDB trigger out of scope. Design MUST resolve the exact
Tukulpan injection budget, compaction threshold/window, token measurement
method, and per-run/cost budgets before implementation.

## Ponytail Review

- Section "Scope": `delete:` panel sub-agents, SDB seven-phase internals, and
  Cortex-session loop; retain only explicit extension hooks.
- Section "Runtime": `native:` use the existing LangGraph graph, SQLAlchemy
  thread history, approval helpers, tool registry, audit, and SSE; do not add a
  second loop or checkpointer.
- Section "Context": `yagni:` entity-resolution machinery and automatic
  semantic search on every turn; inject deterministic `panel` plus pinned
  entries, leaving `hybrid_search` as an explicit tool call.
- Section "Persistence": `shrink:` prefer `assistant_state` JSONB and existing
  message rows before adding migrations; add columns only if a concrete query or
  recovery invariant cannot be represented safely.
- Section "Configuration": `yagni:` panel editing and unapproved versions;
  expose the validated registry read-only and run only approved configuration.

## Graph Check Consulted

The graph was present and fresh per the session preflight. `GRAPH_REPORT.md`
was read for god nodes and communities. Consulted nodes included:
`assistant/graph.py`, `nodes.py`, `agent_chat.py`, `chat.py`, `agent_registry.py`,
`registry.py`, `execute_tool()`, `memory.py`, `InternalChatThread`,
`InternalChatMessage`, `test_assistant_chat.py`, and `test_cost_guardrails.py`.
Consulted edges/paths included:

- `assistant/graph.py <--imports_from-- agent_chat.py` (DB persistence boundary
  imports and invokes the assistant runtime).
- `agent_registry.py -> registry.py -> execute_tool()` (registry/tool
  declaration and executor relationship).
- `chat/graph.py -> llm.py <- nodes.py <- assistant/graph.py` (shared LLM
  dependency and separation from the WhatsApp graph).
- BFS query for panel assistant harness, planner, registry, persistence, tools,
  guardrails, context, and memory; key communities were panel `chat.py`,
  assistant `nodes.py`, `agent_registry.py`, `memory.py`, `costs.py`, and
  `chat/graph.py`.

## Risks

- LLM structured output may be invalid or unsafe; validate schema and fall back
  to a bounded direct response with audit evidence, never to unchecked execution.
- A planner could select a declared but unauthorized tool; enforce the assistant
  whitelist immediately before dispatch and preserve exact approval for writes.
- Context compaction may lose operational facts; flush durable memory before
  compaction and persist compaction evidence in the thread state.
- Unbounded history or memory injection can exceed model limits or increase
  cost; DESIGN MUST establish deterministic budgets and token measurement.
- Renaming SDB terminology may miss docs/specs/README consumers; the apply phase
  requires a repository-wide grep with an explicit consumer inventory.
- Extending assistant state may conflict with existing recovery/API clients;
  preserve current fields and event ordering, and add compatibility tests before
  changing serialized shapes.
- The current graph report was built at commit `ce02d3b7`; query results are
  structural navigation evidence, while exact behavior was verified against the
  source files read above.

## Ready for Proposal

Yes. The architectural gap and shipped boundaries are clear. The proposal can
be written after DESIGN resolves token/context measurement, injection and
compaction budgets, fallback semantics for invalid planner output, and the
minimal `assistant_state` contract. It must explicitly state that Tukulpan,
SDB internals, Cortex-session mode, and panel sub-agents are deferred.

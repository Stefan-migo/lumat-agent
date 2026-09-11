# Exploration: tukulpan

## Current State

The persistent memory layer is implemented in `app/services/memory.py` (506
lines) over `db/migrations/009_memory.sql`. Its API is a caller-committed
SQLAlchemy service exposing `upsert`, `get_by_key`, `list_for_entity`,
`delete`, `set_mark`, `hybrid_search`, `load_customer_context`,
`persist_memory_session`, and `close_conversation`. It embeds through
`app.services.kb.embed_texts`, restricts writes to `proyecto='default'`, and
stores typed `memories`, schema-only `memory_relations`, and typed
`memory_observations`. The existing memory spec covers CRUD, hybrid recall,
customer-close memo/observations, and customer-ficha management.

Runtime consumers are split across two lifecycles:

- WhatsApp/conversation flow: `app/chat/state.py` loads customer-scoped
  context during `ConversationState.from_db()`, `app/chat/graph.py` flushes
  the current inbound turn before returning, and `set_conversation_state()`
  calls `close_conversation()` when a conversation closes.
- Panel assistant: `app/chat/assistant/nodes.py` already provides
  `load_panel_context()` and `flush_panel_session()` seams. The former reads
  `scope='panel'`, `entity_id='thread:{id}'`, puts pinned rows first, and
  bounds the result to 4,000 estimated tokens. The latter writes a synthetic
  `assistant-compaction` session memory. `app/services/agent_chat.py` calls
  `load_panel_context()` from `assemble_context()` before history and
  attachments, and `compact_session()` calls the flush seam at the 4,000-token
  threshold.

The harness seams are therefore real, not stubs, but the write seam is still a
placeholder lifecycle record rather than a meaningful recap/evidence write.
There is no automatic `hybrid_search()` in panel turn assembly; that remains
an explicit `memory.read`-adjacent service/tool concern, matching the existing
YAGNI boundary. The panel assistant graph is already
`START -> assemble_context -> plan_llm -> guardrails -> execute/respond ->
evidence -> END`, with DB thread history authoritative and no checkpointer.

The database schema should not be renamed: table/type names (`memories`,
`memory_observations`, `memory_type`, etc.) are persisted contracts. The
existing model and migration contain no Tukulpan-specific schema gap.

### Consumer and rename inventory

There are 5 production modules importing or calling the service directly:
`app/chat/assistant/nodes.py`, `app/chat/assistant/tools/registry.py`,
`app/chat/graph.py`, `app/chat/state.py`, and
`app/panel/api/routes/clients.py`. Seven test modules import the module
directly, including the memory spec, pipeline/observation/chat-state tests,
client/API tests, and assistant-tool tests. Repository-wide search finds 17
files with the concrete `app/services/memory.py` path and 39 files with
memory/Tukulpan references across application, specs, tests, docs, and agent
artifacts. The blast radius includes historical OpenSpec artifacts, so a
literal replacement would damage the audit trail without changing behavior.

## Affected Areas

- `app/services/memory.py` — current implementation and public API to reshape
  under the Tukulpan concept.
- `app/chat/assistant/nodes.py` — panel/pinned read and compaction write seams;
  current budget/order behavior lives here.
- `app/services/agent_chat.py` — `assemble_context()` is the per-turn
  injection point; `compact_session()` owns the preflight threshold and
  retention window.
- `app/chat/assistant/state.py` — authoritative 4,000-token injection budget
  and deterministic UTF-8/4 token estimate.
- `app/chat/assistant/graph.py` — existing harness topology; no new graph or
  checkpointer is needed.
- `app/chat/graph.py`, `app/chat/state.py` — existing WhatsApp turn persistence
  and close lifecycle that must remain separate from panel Tukulpan scope.
- `app/chat/assistant/tools/registry.py` — explicit `memory.read` consumer;
  preserve as a bounded tool rather than turning search into implicit recall.
- `app/models.py`, `db/migrations/009_memory.sql` — persisted names and typed
  rows; likely no migration change.
- `app/panel/api/routes/clients.py`, serializers, and `ClientFicha` — customer
  memory management surface; preserve its customer scope and audit behavior.
- `openspec/specs/memory/`, `openspec/specs/harness-lumat/`, and the related
  conversation/customer specs — update canonical terminology/contracts only;
  retain archived artifacts unchanged.
- `tests/spec/test_memory_spec.py`, memory integration/API tests, and assistant
  harness context/session tests — compatibility and lifecycle coverage.

## Approaches

1. **Literal module rename** — rename `memory.py` to `tukulpan.py` and update
   every import, test, documentation reference, and canonical spec.
   - Pros: clean final naming and no duplicate implementation.
   - Cons: broad mechanical diff, unnecessary historical-artifact churn, and
     avoidable compatibility risk for external/internal imports.
   - Effort: Medium.

2. **Tukulpan façade with a compatibility alias** — expose the reshaped
   Tukulpan API from a new canonical service boundary while keeping
   `app.services.memory` as a thin compatibility import during migration; move
   only active consumers/specs to Tukulpan terminology and leave archived
   records untouched.
   - Pros: satisfies the conceptual rename, preserves existing imports and
     persisted contracts, supports incremental consumer migration, and keeps
     the diff focused on behavior/lifecycle.
   - Cons: temporary two-name surface and a small risk of adding new calls to
     the legacy alias.
   - Effort: Medium.

3. **Keep `memory.py` and rename only the concept/docs** — treat Tukulpan as
   the product name while retaining the implementation module and API.
   - Pros: smallest diff and lowest regression risk.
   - Cons: leaves a misleading implementation boundary and makes future
     Tukulpan-specific lifecycle work harder to discover.
   - Effort: Low.

## Recommendation

Choose Approach 2, but keep the alias deliberately thin and temporary. Tukulpan
should own the narrow contracts needed by this change: deterministic panel
scope plus pinned read, fixed injection budget, explicit search (no automatic
semantic recall), and milestone/decision writes. `hybrid_search()` should stay
an explicit operation. Migrate active panel and harness consumers first; retain
`memory.py` compatibility for WhatsApp, API, tests, and downstream imports, and
do not rewrite archived SDD artifacts or database identifiers.

The per-turn read plugs into the existing `agent_chat.assemble_context()` seam:
call a Tukulpan panel projection with `entity_id=thread:{thread_id}`, append
pinned entries before non-pinned entries, then apply the existing deterministic
budget and history/attachment ordering. The panel projection should return
source IDs and truncation metadata so `assistant_state.context_meta` remains
the evidence boundary. `hybrid_search()` must not be called implicitly.

Writes should be event-driven and minimal: save explicit Cortex-session
decisions and durable milestones, flush a meaningful bounded compaction recap
before rolling-session rotation, and preserve the already-correct WhatsApp
per-turn, close-time memo, and typed-observation paths. Do not invent a generic
every-message write path or a second event bus. The current synthetic
`assistant-compaction` row is the clearest seam to replace with a bounded recap
or milestone payload in a follow-up design.

## Risks

- A full rename can break imports, monkeypatch paths, capability tests, and
  undocumented consumers; the alias is the safer migration boundary.
- Archived OpenSpec artifacts are audit history and should not be mass-renamed.
- The current panel flush records token counts but not useful conversation
  evidence; changing it requires a precise recap source and idempotency rule.
- Mixing panel `thread:{id}` scope with WhatsApp `customer:{id}` scope could
  leak context; scope/entity filters must remain explicit and tested.
- A fixed budget can starve history or attachments if pinned memories consume
  it; preserve deterministic ordering and truncation evidence.
- Embedding every milestone write is synchronous and can fail a turn; the
  proposal must define whether writes are required, degradable, or retried
  without weakening data-loss guarantees.

## Ready for Proposal

Yes. The existing service, schema, consumers, and harness seams are concrete.
The proposal should scope a compatibility-preserving Tukulpan boundary, define
the canonical active API names, specify the meaningful milestone/decision write
events and compaction recap payload, and explicitly defer automatic search,
schema renames, panel sub-agents, and a generic memory event bus.

## Graph nodes consulted:

- `memory.py`, `Memory service layer (app/services/memory.py)`, `Memory`,
  `models.py`, `db.py`, `009_memory.sql`.
- `assemble_context`, `agent_chat.py`, `app/chat/assistant/nodes.py`,
  `app/chat/assistant/graph.py`, `AssistantState`, `compact_session`.
- `registry.py`, `execute_tool`, `memory.read`, `app/chat/graph.py`,
  `app/chat/state.py`, `test_memory_pipeline.py`,
  `test_memory_observations.py`, `test_assistant_harness_context.py`.

Graph paths/edges consulted:

- `memory.py --imports_from--> models.py <--imports_from-- agent_chat.py
  --contains--> assemble_context()` (undirected shortest path).
- `app/chat/assistant/graph.py <--imports_from-- agent_chat.py`.
- BFS query over Tukulpan panel context, memory service API, consumers, and
  lifecycle reached the panel assistant, memory, models, tools, and test
  communities.

Graph report status: graph present; report read. It was built from commit
`a7abba4b`, while the worktree is at `c6f3c636`; queries were used as required,
but the report may be stale relative to this branch.

## skill_resolution

`paths-injected` — loaded the exact `cortex-persona` and `graphify` skills plus
the shared SDD phase and OpenSpec conventions. `cortex-session` was loaded as
the relevant planning-mode project skill. `component-adapter` and
`design-agent-lead` were checked and not loaded because this is a backend
memory/runtime exploration with no UI or catalog work.

# Exploration: H2 Multi-Agent LangGraph Router

## Current State

LumatAgent's conversation handling is a single linear LangGraph `StateGraph` over
`ConversationState`, built by `build_graph()` in `app/chat/graph.py` and invoked
per inbound message by `run_conversation()` **without a checkpointer** (design D2 —
state is rebuilt from Postgres each run via `ConversationState.from_db()`).

**Graph anatomy today (app/chat/graph.py):**
```
START -> emergency_gate (deterministic, EM-1/EM-5)
   strong -> emergency (EM-3 safety protocol, no LLM)
   weak   -> handoff
   miss   -> cost_gate (SS-3, deterministic SQL spend state)
              blocked  -> handoff (no LLM, canned reply)
              else     -> handoff_gate (HH-3 deterministic triggers)
                           trigger -> handoff
                           clear   -> receive -> classify_intent -> route
route (deterministic on intent, no LLM):
   capture intents (calefont/caldera/calefaccion/solicitar_visita) -> capture -> summary
   retrieval intents (valores/postventa) -> respond (KB-grounded)
   persona/emergencia/injection -> handoff
   unknown -> respond (clarification) or escalate
respond -> handoff on KB miss
```

**Agent declarative layer (agent/):** `personas/`, `prompts/`, `skills/`,
`registry.yaml` exist behind the single loader `app/services/prompts.py`
(`load()` with lru_cache + literal `FALLBACKS`, strict `render()`). Chat nodes
`respond`, `classify_intent`, `summary` are already wired to `prompts.load/render`.
`registry.yaml` declares exactly one agent (`orchestrator`) with `skills:
[sdb, emergency, handoff, capture]`, an **empty** `tools_whitelist`, `kb_scope:
null`, `memoria_scope: null`, `model: deepseek-chat`. AC-4 explicitly states the
registry MUST NOT enforce tools/KB/memory scope at runtime **until H2**. There is
NO registry reader today (documented in registry.yaml and agent/README.md as
"D-A7 / Fase-2").

**Cost gate (SS-3):** `cost_gate` computes per-conversation and UTC-day spend via
`costs.conversation_cost_state()` / `daily_cost_state()` from `messages.cost_llm`
columns (SQL SUM, design D6 — no separate ledger table). `record_llm_cost()` writes
token-based cost per LLM call onto the message row.

## Affected Areas

- `app/chat/graph.py` — the linear state graph is the unit a supervisor/router
  would replace or wrap.
- `app/chat/state.py` — `ConversationState` dataclass is BOTH the LangGraph state
  schema and the per-message rebuilt state; a router would extend it (active
  sub-agent, per-node context).
- `app/chat/nodes/*` — `route.py` (deterministic intent routing), `respond.py`
  (KB retrieval + answer), `handoff.py` (deriva bundle + human), `emergency.py`,
  `capture.py`, `summary.py`, `classify_intent.py`, `cost_gate.py` — the reusable
  worker surfaces.
- `app/services/prompts.py` — loader is the contract a registry reader /
  sub-agent prompt builder would consume.
- `agent/registry.yaml` — the schema to extend (sub-agents, roles, tools,
  KB/memory scopes, per-model config).
- `app/services/kb.py` — `retrieve()` currently filters pgvector by
  `kb_documents.active` + active version only; per-sub-agent KB scoping would add
  a scope filter with NO schema change. Chunks carry
  document_id/version/chunk_index/content/source_meta/embedding — there is NO
  category/source field today (`source_meta` is only populated with
  `chunk_index` at ingest). H2 introduces the `source_meta.category` JSONB
  convention (documents ingested with a category store
  `source_meta: {"category": "..."}`) so the scope filter has data.
- `app/services/memory.py` — `load_customer_context()` is customer-scoped today;
  memory is keyed by `(proyecto, scope, entity_id, topic_key)`.
- `app/services/costs.py` — cost aggregation unchanged (per-message `cost_llm`
  already aggregates sub-agent LLM calls into the same columns).
- `app/chat/nodes/respond.py` — today the ONLY KB consumer (single intent-driven
  retrieval inside the node). A research/triage sub-agent would move retrieval
  into a tool called by a sub-graph.

## Approaches

1. **Evolve the current graph into a supervisor-with-subgraphs**
   Keep `build_graph()` as the orchestrator; the deterministic gates
   (`emergency_gate`, `cost_gate`, `handoff_gate`) stay as a fixed pre-filter
   (safety + budget before any LLM). Replace the single `route -> respond`
   classification with an orchestrator node that reads `registry.yaml`, builds a
   tools whitelist + KB/memory scope per sub-agent, and routes to one of ~5
   sub-graphs (research/triage, KB retrieval, customer records, handoff,
   escalation/emergency). Each sub-graph reuses the existing node modules.
   - Pros: minimal restructuring; the mandatory gates stay intact as the outer
     envelope (safety-first ordering preserved); sub-agents reuse vetted nodes.
     - Cons: the "orchestrator = swap classifier for LLM node" risks mixing
       where gates live relative to sub-agents; needs a clear boundary.
   - Effort: High.

2. **Separate routing layer + reusable worker nodes**
   Two independent layers: a deterministic pre-router (gates) + an
   LLM-orchestrator that dispatches to independent worker nodes, each exposed as
   a tool the orchestrator can call. Workers are thin and stateless wrappers over
   existing services (`kb.retrieve`, `memory.load_customer_context`,
   `cases.create_handoff_case`, etc.).
   - Pros: cleanest tool-whitelist model (the registry whitelist literally
     enumerates the callable tools); worker reuse is trivial; natural for
     LangGraph Supervisor patterns.
   - Cons: more moving parts than needed today; the existing nodes already do
     most of this work, so a "separate layer" is mostly new orchestration glue.
   - Effort: High (highest).

3. **Keep current graph; add sub-agents only for specific intents**
   The linear graph stays for the common capture/retrieval/handoff paths. A
   sub-agent dispatch is added ONLY where the current single-agent flow is
   demonstrably insufficient (e.g. complex multi-hop research that needs KB +
   customer records + context in one answer).
   - Pros: smallest diff; ponytail-minimal — no speculative multi-agent structure
     for flows the single graph already handles well (capture, simple KB,
     handoff, emergency).
   - Cons: the registry's declared sub-agent model (AC-4/H2 intent) isn't
     realized end-to-end; the router is a new node sitting alongside the existing
     linear graph rather than restructuring it.
   - Effort: Low.

## Recommendation

**Approach 1 — evolve the current graph into a supervisor-with-subgraphs** is the
single best fit for THIS codebase, with a ponytail-minimal slice boundary.

The decisive facts: (a) the deterministic gates (emergency/cost/handoff) are
already a correct, tested **outer safety envelope** — they must run before ANY
LLM, so they should stay as a fixed prefix to the orchestrator, not be
re-implemented inside sub-agents; (b) the registry exists and AC-4 explicitly
deferred runtime enforcement until H2, so this change is *completing* the
declared architecture, not inventing one; (c) worker nodes already exist and are
vetted — sub-agents should **wrap, not replace** them.

The recommended slice boundaries for a future tasks phase (directional, not an
implementation plan):

1. **Registry schema + reader**: extend `registry.yaml` to a multi-agent schema
   (orchestrator + ~5 sub-agents with name, persona path, tools_whitelist,
   kb_scope, memoria_scope, model, temperature). Add a small, read-only registry
   loader (`app/agent_registry.py` or extend `prompts.py`) that parses it once at
   startup. **No runtime enforcement yet.**
2. **Orchestrator node**: add an `orchestrate` node that, per message, selects the
   sub-agent (reusing `classify_intent` output + deterministic triggers) and
   dispatches to its sub-graph. Gates stay as the outer prefix.
3. **Sub-graphs wrapping existing nodes**: each sub-agent is a tiny StateGraph or
   direct node call reusing `respond`, `handoff`, `capture`, etc. The first
   sub-agent to build is the **KB research/triage** one (combines classify +
   retrieve + respond), since it delivers the clearest value over today's single
   linear `respond`.
4. **Tools whitelist plumbing**: introduce registry-driven allow/deny so each
   sub-agent can only call its declared services (`kb.retrieve`, memory read,
   `send_text`). Enforcement is a thin assert/tool-boundary check, not a new
   service layer.
5. **KB/memory scoping**: `kb.retrieve` gains an optional scope filter keyed on
   the new `source_meta.category` convention (no schema change — `source_meta`
   already exists on `kb_chunks`); `load_customer_context` is already
   customer-scoped. No new tables.
6. **Observability**: no schema change; sub-agent LLM calls already land on
   `messages.cost_llm` (D6) and are covered by the existing cost gate.
7. **Tests**: routing determinism via a fix-the-router table (given intent/gate
   state, expect sub-agent); keep the `test_chat_intent` / `test_handoff` /
   `test_cost_guardrails` suites green (they exercise the outer envelope).

**Out of scope for H2 backend** (locked): checkpointer (D2 is correct — no
multi-turn graph state yet), DB migrations (D3/D8/HH already covered; no schema
change needed for scoping), panel production endpoints (panel-h2-advance is
Storybook-only, archived; the web frontend lives in a separate worktree
`lumat-agent-frontend-iter` and is NOT touched).

## Risks

- **Checkpointer ambiguity (CRITICAL)**: H2 does not need one — state is rebuilt
  per message (D2) and sub-agent runs are per-message too. Introducing one now
  would be over-engineering. Decision must be recorded so it is not re-litigated.
- **Multi-agent routing determinism (WARNING)**: routing must stay reproducible
  for tests. Mitigation: keep a deterministic gate prefix (no LLM before gates),
  and route to sub-agents via a pure function of `(intent, gate flags)` so tests
  can enumerate the routing table without invoking LLM dispatch.
- **Cost multi-LLM per message (WARNING)**: a multi-agent turn has up to 1
  classify + 1 orchestrator + N sub-agent calls. The SQL SUM cost gate already
  covers all of it (per-message `cost_llm`), but per-message spend can climb.
  Mitigation: the existing `cost_mode=conservative` short-reply directive and the
  `blocked` escape hatch already bound the worst case; re-verify thresholds.
- **Registry schema churn (WARNING)**: AC-4 pinned a one-agent schema. Extending
  it to multi-agent must stay data-only and backward-compatible with the existing
  AC-4 test (exactly one orchestrator).
- **SH-5 audit append-only (INFO)**: sub-agent dispatches are operational, not
  business transitions — do not force them into `audit_log`. `conversation_events`
  already carries event rows; add a `sub_agent_dispatch` event there if tracking is
  needed.
- **Web/frontend boundary (INFO)**: panel-h2-advance is archived and separate
  worktree; H2 backend must NOT add production panel endpoints in this change.

## Ready for Proposal

**Yes.** The architecture is clear, the existing code reuses cleanly, and the
gates/cost/security constraints are already encoded. The design phase should
answer 2 human/product questions before proposal is finalized: (1) confirm the
~5 sub-agent roster (research/triage, KB retrieval, customer records, human
handoff, escalation/emergency) is the agreed set; (2) confirm H2 does NOT need to
wire production panel inbox/chat endpoints this change (contract says panel is a
separate frontend milestone).

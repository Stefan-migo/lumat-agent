# Agent Orchestration Specification

## Purpose

Supervise sub-agent dispatch for Lumat's WhatsApp assistant. Deterministic gates remain the outer safety/budget envelope; an orchestrator dispatches to per-capability sub-graphs wrapping vetted nodes. Slice-first: KB research/triage ships; full roster data-only.

## Requirements

### Requirement: AO-1 — Registry Declares Multi-Agent Roster

The system MUST declare five sub-agents in `agent/registry.yaml` (research/triage, KB retrieval, customer records, handoff, escalation/emergency), each with `name`, `persona`, `tools_whitelist`, `kb_scope`, `memoria_scope`, `model`, `temperature`. The `orchestrator` entry shape MUST NOT change (AC-4 invariant preserved).

#### Scenario: Full roster declared
- GIVEN `registry.yaml` parses at boot
- THEN five sub-agents exist with all seven fields
- AND the `orchestrator` entry resolves exactly as before

#### Scenario: Slice-1 identifiable
- GIVEN the roster
- WHEN only KB research/triage is implemented
- THEN the other four are data-only with no runtime behavior

### Requirement: AO-2 — Read-Only Startup Registry Reader

The system MUST load the registry once at startup via a read-only reader (`app/agent_registry.py`) that validates and exposes data; it MUST NOT enforce scope beyond the dispatch boundary, and MUST NOT be wired into `app/services/prompts.py` or `app/chat/nodes/respond.py`.

#### Scenario: Reader validates at boot
- GIVEN a valid `registry.yaml`
- WHEN the reader runs
- THEN it returns orchestrator and sub-agents without error

#### Scenario: Invalid registry rejected
- GIVEN a sub-agent missing `temperature`
- WHEN the reader runs
- THEN startup fails; no graph builds

### Requirement: AO-3 — Deterministic Orchestrator Dispatch

The system MUST select a sub-agent via a pure function of `(intent, gate flags)`, no LLM. Each `(intent, flags)` row maps to exactly one sub-graph, table-tested for all combos. The complete dispatch table lives in design.md and preserves today's route semantics: escalate flags → handoff; persona/emergencia/injection → handoff; CAPTURE_INTENTS (calefont/caldera/calefaccion/solicitar_visita) → capture; RETRIEVAL_INTENTS (valores/postventa) → research_triage; unknown (first occurrence, no escalate) → respond (clarification); anything else → respond (linear). The mid-capture shortcut is preserved: when `_pending` is in `state.captured`, the flow goes `receive → capture` directly, skipping re-classification.

#### Scenario: KB intent routes to research/triage
- GIVEN emergency/cost/handoff gates all clear and intent `valores`
- WHEN the orchestrator runs
- THEN it dispatches to the KB research/triage sub-graph

#### Scenario: Capture intent still routes to capture (regression)
- GIVEN gates all clear and intent `calefont`
- WHEN the orchestrator runs
- THEN it dispatches to the capture sub-flow, unchanged from today

#### Scenario: Escalate flag routes to handoff
- GIVEN `escalate=True` (2x unknown, injection, SS-1 always_escalate)
- WHEN the orchestrator runs
- THEN it dispatches to handoff with the escalation reason

#### Scenario: Unknown first occurrence routes to respond
- GIVEN intent `unknown` and no escalate flag
- WHEN the orchestrator runs
- THEN it dispatches to respond (clarification)

#### Scenario: Gate short-circuits the router
- GIVEN `cost_mode = blocked`
- WHEN the gates run
- THEN the flow ends at `handoff`, the orchestrator never runs

### Requirement: AO-4 — Gates Stay the Outer Envelope

The system MUST keep `emergency_gate → cost_gate → handoff_gate` as a fixed prefix running before any LLM and before the orchestrator. Gate semantics MUST be unchanged.

#### Scenario: Safety first
- GIVEN a strong emergency hit during a budget block
- WHEN the gate prefix runs
- THEN the emergency protocol fires, orchestrator skipped

### Requirement: AO-5 — Sub-Graphs Wrap Vetted Nodes

Each dispatched sub-agent MUST be a sub-graph reusing existing node modules (`respond`, `handoff`, `capture`, `classify_intent`), not a re-implementation.

#### Scenario: Research reuses respond
- GIVEN the KB research/triage sub-graph runs
- THEN it invokes the existing `classify_intent`/`respond` nodes unchanged

### Requirement: AO-6 — Tools Whitelist Thin Boundary

The system MUST gate each sub-agent's service calls against its `tools_whitelist` via a thin assert/boundary check, not a service layer.

#### Scenario: Whitelisted call passes
- GIVEN a research sub-agent calling a whitelisted `kb.retrieve`
- THEN the call proceeds

#### Scenario: Denied call blocked
- GIVEN a sub-agent calls a non-whitelisted service
- THEN it is rejected with a log

### Requirement: AO-7 — KB/Memory Scoping via Filter

Chunks carry `source_meta.category` (JSONB convention, no schema change): documents ingested with a category store `source_meta: {"category": "..."}`. `kb.retrieve(..., scope=...)` SHOULD filter chunks to those whose `source_meta.category` is in the scope list; `scope=None` returns the unfiltered active-version set (backward compatible). A sub-agent with `kb_scope: [valores, postventa]` (e.g. research_triage) may only retrieve chunks whose category is in that list. Memory stays customer-scoped (unchanged).

#### Scenario: Scoped retrieve
- GIVEN a sub-agent with `kb_scope`
- WHEN it calls `kb.retrieve(scope=kb_scope)`
- THEN results contain only chunks whose `source_meta.category` is in the scope list

#### Scenario: Unscoped retrieve unchanged
- GIVEN `kb.retrieve` called with `scope=None`
- THEN results equal today's active-version retrieval (no filtering)

### Requirement: AO-8 — Handoff Bounded Retry

A sub-agent MUST hand off to a human when it cannot resolve; it MUST NOT loop. Retries MUST be bounded (≤1) with escalation to `handoff` and terminate.

#### Scenario: Resolution failure hands off
- GIVEN a research sub-agent can't answer after one retry
- THEN it transitions to human handoff and the graph reaches END

### Requirement: AO-9 — Invisible Orchestration

Sub-agent orchestration MUST NOT change end-customer tone/format on common paths.

#### Scenario: Customer sees same tone
- GIVEN a KB-intent message answered via research sub-agent
- WHEN the reply is assembled
- THEN copy/tone/format equal the pre-H2 single-agent reply

### Requirement: AO-10 — Cost Gate Covers Multi-LLM

The system MUST keep the SQL SUM cost gate covering every LLM call (classify + orchestrator + sub-agents) per conversation and UTC day; thresholds re-verified in design.

#### Scenario: Sub-agent spend counted
- GIVEN a multi-sub-agent turn
- WHEN the cost gate computes spend
- THEN all LLM calls are summed via `messages.cost_llm`

## Boundary

No checkpointer, no production panel endpoints, no new DB tables, no `audit_log` entries for sub-agent dispatch. Other sub-agents (retrieval, customer records, handoff, escalation) are data-only this slice.

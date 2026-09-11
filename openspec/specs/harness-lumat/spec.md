# Harness Lumat Specification

## Purpose

Provide a durable, session-aware panel harness without duplicating the database, tool registry, approval boundary, or WhatsApp runtime.

## Requirements

### Requirement: HL-1 — Session-Aware Turn Harness

The harness MUST assemble each authorized panel turn from DB-authoritative thread history, attachments, and the Tukulpan projection limited to `scope='panel'` and `entity_id='thread:{id}'`. The projection MUST place pinned entries first, use the fixed deterministic injection budget, and expose source IDs plus truncation metadata. It MUST NOT auto-invoke `hybrid_search()`.

#### Scenario: Deterministic context assembly

- GIVEN an authorized thread with prior messages, attachments, and panel/pinned context
- WHEN `assemble_context()` runs
- THEN pinned Tukulpan entries precede other panel entries and the planner receives only budgeted context with source IDs

#### Scenario: Context over budget

- GIVEN assembled context exceeds the configured injection budget
- WHEN the turn is prepared
- THEN deterministic truncation occurs and `AssistantState.context_meta` records truncation evidence

### Requirement: HL-2 — Structured Planning and Guardrails

The harness MUST replace keyword planning with validated structured LLM output representing a typed tool action, response, or complex request. Deterministic guardrails MUST enforce the assistant whitelist, exact-argument approval for writes, configured cost bounds, and audit/evidence ordering. Invalid plans MUST NOT execute unchecked.

#### Scenario: Valid read plan

- GIVEN a planner response naming a whitelisted read tool with valid arguments
- WHEN guardrails evaluate it
- THEN the tool may execute and ordered audit/evidence is emitted

#### Scenario: Invalid plan

- GIVEN malformed output or an unwhitelisted tool
- WHEN guardrails evaluate it
- THEN no tool executes and a bounded error or response evidence is persisted

### Requirement: HL-3 — Rolling Session and Recovery Evidence

The harness MUST keep DB thread history authoritative and, before `compact_session()` rotates a session, persist a bounded meaningful recap or milestone with idempotency and source/truncation evidence. A failed write MUST be surfaced as failed/degraded compaction evidence and MUST NOT be reported as successful completion. The harness MUST NOT implement panel sub-agents, SDB, or Cortex-session mode.

#### Scenario: Preflight compaction

- GIVEN the configured compaction threshold is reached
- WHEN a new turn enters preflight
- THEN the bounded recap is attempted before rotation and its result is persisted in session evidence

#### Scenario: Recovery after interruption

- GIVEN a persisted active run or compaction state
- WHEN the administrator reloads the thread
- THEN recovery uses DB state and does not duplicate a completed execution

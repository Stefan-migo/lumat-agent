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

The harness MUST replace keyword planning with validated structured LLM output representing a typed tool action, response, Cortex turn classification, or SDB request. Deterministic guardrails MUST enforce the assistant whitelist, exact-argument approval for writes, configured cost bounds, trigger validity, and audit/evidence ordering. Invalid plans or triggers MUST NOT execute unchecked.
(Previously: structured planning represented only tool, response, or complex requests and had no Cortex route.)

#### Scenario: Valid read plan

- GIVEN a planner response naming a whitelisted read tool with valid arguments
- WHEN guardrails evaluate it
- THEN the tool may execute and ordered audit/evidence is emitted

#### Scenario: Valid SDB plan

- GIVEN a valid structured SDB classification
- WHEN guardrails evaluate it
- THEN the request routes to the SDB phases without ordinary tool execution

#### Scenario: Valid Cortex plan

- GIVEN a valid Cortex classification on a thread with an active valid flag
- WHEN guardrails evaluate it
- THEN the turn uses the Cortex loop and its permitted route

#### Scenario: Invalid plan

- GIVEN malformed output, an unwhitelisted tool, invalid Cortex state, or conflicting SDB signals
- WHEN guardrails evaluate it
- THEN no unsafe action executes and bounded rejection evidence is persisted

### Requirement: HL-3 — Rolling Session and Recovery Evidence

The harness MUST keep DB thread history authoritative and, before `compact_session()` rotates a session, persist a bounded meaningful recap or milestone with idempotency and source/truncation evidence. It MUST preserve valid Cortex session state and MUST NOT report failed writes as successful completion.

#### Scenario: Preflight compaction

- GIVEN the configured compaction threshold is reached
- WHEN a new turn enters preflight
- THEN the bounded recap is attempted before rotation and its result is persisted in session evidence

#### Scenario: Recovery after interruption

- GIVEN a persisted active run or compaction state
- WHEN the administrator reloads the thread
- THEN recovery uses DB state and does not duplicate a completed execution

### Requirement: HL-4 — Native SDB Routing Boundary

The harness MUST route only a normalized, valid SDB trigger to the native SDB branch and MUST preserve ordinary tool/response routing for non-SDB turns. Terminal evidence MUST identify the selected route and any fail-closed trigger reason.

#### Scenario: Ordinary turn remains unchanged

- GIVEN a valid non-SDB planner result
- WHEN routing completes
- THEN the existing guardrails, execution, and evidence path is used

#### Scenario: Invalid SDB signal

- GIVEN an incomplete or conflicting SDB classification
- WHEN routing evaluates the turn
- THEN ordinary safe response handling occurs and evidence records the rejection

## ADDED Requirements

### Requirement: HL-5 — Cortex routing boundary

The harness MUST route Cortex only when the per-turn gate finds a valid active thread flag; otherwise it MUST retain ordinary safe routing or fail closed.

#### Scenario: Inactive thread

- GIVEN a normal thread
- WHEN a planning-sounding message is submitted
- THEN ordinary routing remains unchanged

#### Scenario: Missing flag

- GIVEN a Cortex request with missing or invalid thread state
- WHEN routing evaluates it
- THEN no Cortex turn runs and the rejection is recorded

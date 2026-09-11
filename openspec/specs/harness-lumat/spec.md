# Harness Lumat Specification

## Purpose

Provide a durable, session-aware panel harness without duplicating the database, tool registry, approval boundary, or WhatsApp runtime.

## Requirements

### Requirement: HL-1 — Session-Aware Turn Harness

The harness MUST assemble each authorized panel turn from DB-authoritative thread history, attachments, and Tukulpan context limited to `panel` scope and pinned entries. It MUST enforce the configured injection budget.

#### Scenario: Context assembly

- GIVEN an authorized thread with prior messages, attachments, and panel/pinned context
- WHEN a turn starts
- THEN the planner receives bounded, ordered context from those sources

#### Scenario: Context over budget

- GIVEN assembled context exceeds the configured injection budget
- WHEN the turn is prepared
- THEN the harness applies deterministic bounded handling and records the resulting context evidence

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

The harness MUST persist the turn result and evidence, keep the DB thread authoritative, and enforce configured rolling-session and preflight-compaction bounds. Before compaction it MUST flush the required memory evidence and persist compaction/rotation evidence. It MUST expose extension hooks without implementing panel sub-agents, Tukulpan internals, the SDB subgraph, or Cortex-session.

#### Scenario: Preflight compaction

- GIVEN the configured compaction threshold is reached
- WHEN a new turn enters preflight
- THEN required memory flush completes before compaction and the resulting session evidence is persisted

#### Scenario: Recovery after interruption

- GIVEN a persisted active run or compaction state
- WHEN the administrator reloads the thread
- THEN recovery uses DB state and does not duplicate a completed execution

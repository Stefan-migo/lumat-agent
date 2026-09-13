# Delta for harness-lumat

## MODIFIED Requirements

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
- THEN the request routes to SDB phases without ordinary tool execution

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
(Previously: the harness explicitly excluded Cortex-session mode.)

#### Scenario: Preflight compaction
- GIVEN the compaction threshold is reached
- WHEN a new turn enters preflight
- THEN the bounded recap is attempted before rotation and its result is persisted

#### Scenario: Recovery after interruption
- GIVEN persisted active Cortex or compaction state
- WHEN the administrator reloads the thread
- THEN DB state recovers the session without duplicating completed work

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

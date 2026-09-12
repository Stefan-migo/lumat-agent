# Delta for Harness Lumat

## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: HL-2 — Structured Planning and Guardrails

The harness MUST replace keyword planning with validated structured LLM output representing a typed tool action, response, or SDB request. Deterministic guardrails MUST enforce the assistant whitelist, exact-argument approval for writes, configured cost bounds, trigger validity, and audit/evidence ordering. Invalid plans or triggers MUST NOT execute unchecked.
(Previously: structured planning represented only tool, response, or complex requests and had no native SDB route.)

#### Scenario: Valid read plan

- GIVEN a planner response naming a whitelisted read tool with valid arguments
- WHEN guardrails evaluate it
- THEN the tool may execute and ordered audit/evidence is emitted

#### Scenario: Valid SDB plan

- GIVEN a valid structured SDB classification
- WHEN guardrails evaluate it
- THEN the request routes to the SDB phases without ordinary tool execution

#### Scenario: Invalid plan

- GIVEN malformed output, an unwhitelisted tool, or conflicting SDB signals
- WHEN guardrails evaluate it
- THEN no unsafe action executes and bounded rejection evidence is persisted

# Automation Rules Specification

## Purpose

Evaluate safe, deterministic automation rules against durable domain events.

## Requirements

### Requirement: AR-1 — Deterministic Rule Evaluation

Rules MUST evaluate declared event types and conditions deterministically before any LLM decision, and MUST enqueue only policy-valid notification operations.

#### Scenario: Matching rule

- GIVEN an enabled rule whose event type and conditions match
- WHEN the event is processed
- THEN one policy-valid notification operation is enqueued

#### Scenario: Non-matching rule

- GIVEN an event that fails a rule condition
- WHEN the rule is evaluated
- THEN no notification operation is enqueued

### Requirement: AR-2 — Cooldown and Deduplication

Rules MUST support a bounded cooldown and stable execution key, and MUST NOT create duplicate customer-visible operations during the cooldown or on event retry.

#### Scenario: Cooldown suppresses repeat

- GIVEN a rule execution succeeded within its cooldown
- WHEN an equivalent event is processed
- THEN no second customer-visible operation is created

#### Scenario: Retry remains safe

- GIVEN a rule execution is retried after a worker lease expires
- WHEN it is processed again
- THEN its prior operation is reused rather than duplicated

### Requirement: AR-3 — Audit and Disablement

The system MUST audit rule evaluation, outcome, and reason, and disabled rules MUST NOT execute.

#### Scenario: Disabled rule

- GIVEN a disabled automation rule
- WHEN a matching event arrives
- THEN it is recorded as skipped and creates no operation

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

### Requirement: AR-4 — Authenticated Rule Management

The panel API MUST expose authenticated list, detail, create, and update operations for existing `AutomationRule` fields. It MUST preserve `created_by`, MUST NOT hard-delete rules, and MUST provide explicit enable/disable mutations.

#### Scenario: Read and update a rule
- GIVEN an authenticated user and an existing rule
- WHEN they request its detail and an admin submits a valid update
- THEN the API returns the serialized rule and persists the changed fields while preserving `created_by`

#### Scenario: Disable instead of delete
- GIVEN an existing rule
- WHEN an admin requests disable
- THEN the rule remains persisted with `enabled` false and its executions remain available

### Requirement: AR-5 — Bounded Authoring Validation

The management API MUST reject before persistence any event or channel outside the automation service allowlists, cooldown outside 0–2,592,000 seconds, or conditions that are not a flat JSON object of exact payload key/value matches supported by `evaluate_event`. It MUST NOT create LLM rules or template-version links.

#### Scenario: Invalid policy rejected
- GIVEN a create or update request with an unsupported event, channel, condition operator, or cooldown
- WHEN the request is submitted
- THEN the API returns a validation error and creates no database change

#### Scenario: Valid bounded rule accepted
- GIVEN allowed event/channel values, a bounded cooldown, and evaluator-supported conditions
- WHEN an admin creates the rule
- THEN the rule is persisted and can be evaluated by the existing H4 semantics

### Requirement: AR-6 — CRUD Audit Trail

The system MUST audit create, update, enable, and disable mutations with stable automation CRUD actions, authenticated actor identity, and before/after snapshots where applicable. Evaluation and delivery behavior MUST remain unchanged.

#### Scenario: Mutation is auditable
- GIVEN an admin successfully creates, updates, enables, or disables a rule
- WHEN the transaction completes
- THEN an audit record identifies the actor, rule, action, and relevant before/after state

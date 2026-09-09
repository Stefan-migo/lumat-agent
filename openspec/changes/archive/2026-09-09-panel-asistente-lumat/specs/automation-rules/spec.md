# Delta for automation-rules

## ADDED Requirements

### Requirement: AR-7 — Confirmed Assistant Rule Authoring

The existing automation service MUST accept assistant-created rules only from an approved exact-argument tool call. Created rules MUST use the existing section, history, and worker behavior; the assistant MUST be represented as the actor in the audit trail.

#### Scenario: Assistant rule appears in automation management
- GIVEN an administrator approves a valid assistant rule plan
- WHEN the existing service creates the rule
- THEN the rule is visible through existing automation management and is evaluated by the existing worker

#### Scenario: Assistant write without approval
- GIVEN an assistant proposes a rule without durable approval
- WHEN execution is attempted
- THEN the service creates no rule and records no successful creation

## MODIFIED Requirements

### Requirement: AR-6 — CRUD Audit Trail

The system MUST audit create, update, enable, and disable mutations with stable automation CRUD actions, authenticated actor identity, and before/after snapshots where applicable. Assistant-created mutations MUST identify the assistant actor and preserve existing evaluation and delivery behavior.
(Previously: CRUD audit identified only the authenticated actor for panel mutations.)

#### Scenario: Assistant mutation is auditable
- GIVEN an approved assistant creates an automation
- WHEN the transaction completes
- THEN an audit record identifies the assistant actor, rule, action, and relevant state

#### Scenario: Existing mutation remains unchanged
- GIVEN an admin updates or disables a rule through the existing panel management API
- WHEN the transaction completes
- THEN the existing audit and rule evaluation behavior remains intact

#### Scenario: Panel mutation is auditable
- GIVEN an admin successfully creates, updates, enables, or disables a rule
- WHEN the transaction completes
- THEN an audit record identifies the authenticated actor, rule, action, and relevant before/after state

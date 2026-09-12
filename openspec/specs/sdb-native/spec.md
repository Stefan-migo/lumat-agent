# SDB Native Specification

## Purpose

Define the bounded native SDB execution mode inside the panel assistant.

## Requirements

### Requirement: SDB-1 — Seven-Phase Execution and Fail-Closed Triggers

The system MUST execute SDB work in `CLARIFY → SPEC → PLAN → APPROVE → EXECUTE → VERIFY → DELIVER`. Entry MUST require either a valid structured planner classification or an authenticated admin request. Malformed or conflicting trigger signals MUST fail closed without entering SDB.

#### Scenario: Classified SDB request

- GIVEN the planner emits a valid SDB classification
- WHEN the trigger gate evaluates the turn
- THEN the run enters CLARIFY and records the normalized trigger

#### Scenario: Explicit admin request

- GIVEN an authenticated admin requests SDB and the planner returns a valid non-SDB result
- WHEN the trigger gate evaluates the turn
- THEN the explicit request selects SDB and the non-SDB result is not executed

#### Scenario: Conflicting trigger signals

- GIVEN trigger fields are malformed or contain contradictory SDB classifications
- WHEN the trigger gate evaluates the turn
- THEN SDB does not start and a bounded clarification or normal response is recorded

### Requirement: SDB-2 — Frozen Scope and Verifiable Tasks

The system MUST persist a bounded SPEC before PLAN, freeze its scope for the run, and require every planned task to declare one verifiable output. A lookup outside frozen scope MUST return `scope-not-found`; an absent requested entity inside scope MUST return `not-exist`.

#### Scenario: Scope freeze

- GIVEN CLARIFY produces an accepted bounded scope
- WHEN SPEC is persisted
- THEN later phases use that scope and reject unapproved expansion

#### Scenario: Distinct absence errors

- GIVEN a task asks for an item outside scope or for a missing item inside scope
- WHEN the task resolves the request
- THEN the result is respectively `scope-not-found` or `not-exist`

### Requirement: SDB-3 — Checkpoints and Bounded Artifacts

The system MUST persist bounded SPEC, STATE, and RESULT artifacts using typed memory semantics and MUST write a checkpoint after every task. Artifact payloads, task outputs, evidence, and event history MUST remain bounded and MUST NOT create new tables or a separate runtime.

#### Scenario: Task checkpoint

- GIVEN a task completes with its declared output
- WHEN the task result is recorded
- THEN one bounded RESULT/evidence record and a resumable checkpoint are persisted

#### Scenario: Oversized output

- GIVEN a task or event exceeds its configured bound
- WHEN the artifact is persisted
- THEN it is truncated or rejected with bounded degradation evidence

### Requirement: SDB-4 — Approval, Verification, and Durable Recovery

The system MUST reuse the existing exact-plan approval and atomic execution claim. APPROVE MUST cover the canonical phase/task plan, and VERIFY MUST compare persisted outputs with the persisted SPEC before DELIVER. Resume MUST continue from the last successful checkpoint without repeating completed tasks.

#### Scenario: Changed SPEC after approval

- GIVEN the SPEC or canonical task plan changes after approval
- WHEN execution or verification is requested
- THEN approval is rejected and delivery does not occur

#### Scenario: Resume after interruption

- GIVEN a run stops after a persisted task checkpoint
- WHEN the thread is resumed
- THEN only incomplete work continues and completed tasks are not repeated

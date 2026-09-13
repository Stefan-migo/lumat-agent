# SDB Native Specification

## Purpose

Define the bounded native SDB execution mode inside the panel assistant.

## Requirements

### Requirement: SDB-1 — Seven-Phase Execution and Fail-Closed Triggers

The system MUST execute SDB work in `CLARIFY → SPEC → PLAN → APPROVE → EXECUTE → VERIFY → DELIVER`. Entry MUST require either a valid structured planner classification, an authenticated admin request, or an approved closed Cortex session supplied as SPEC. Malformed or conflicting trigger signals MUST fail closed without entering SDB.

#### Scenario: Classified SDB request

- GIVEN the planner emits a valid SDB classification
- WHEN the trigger gate evaluates the turn
- THEN the run enters CLARIFY and records the normalized trigger

#### Scenario: Explicit admin request

- GIVEN an authenticated admin requests SDB and the planner returns a valid non-SDB result
- WHEN the trigger gate evaluates the turn
- THEN the explicit request selects SDB and the non-SDB result is not executed

#### Scenario: Closed Cortex SPEC

- GIVEN a closed Cortex report and administrator approval
- WHEN the handoff enters SDB
- THEN the report is consumed as the SPEC and the run proceeds through APPROVE

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

The system MUST reuse the existing exact-plan approval and atomic execution claim. APPROVE MUST cover the canonical phase/task plan derived from either a native SPEC or an approved Cortex report, and VERIFY MUST compare persisted outputs with that SPEC before DELIVER. Resume MUST continue from the last successful checkpoint without repeating completed tasks. A Cortex handoff MUST deliver only an approved plan where execution is unavailable.

#### Scenario: Changed SPEC after approval

- GIVEN the SPEC or canonical task plan changes after approval
- WHEN execution or verification is requested
- THEN approval is rejected and delivery does not occur

#### Scenario: Resume after interruption

- GIVEN a run stops after a persisted task checkpoint
- WHEN the thread is resumed
- THEN only incomplete work continues and completed tasks are not repeated

#### Scenario: Stub execution remains truthful

- GIVEN an approved Cortex-derived plan
- WHEN the run reaches its available delivery boundary
- THEN the result is labeled an approved plan and does not claim execution

### Requirement: SDB-5 — Project propagation through the existing seam

The SDB runtime MUST propagate the selected authorized project through the existing parameterized seam without changing the seven phases or recovery semantics. Writes MUST retain `scope="panel"`, thread or cross-thread entity identity, and run keys `sdb:{run_id}:{kind}`. `sdb:spec|state|result` MUST remain semantic categories, not literal key replacements; project-level artifacts MAY use `sdb:project:{kind}`.

#### Scenario: Run artifact isolation
- GIVEN an SDB run selects an authorized project
- WHEN SPEC, STATE, or RESULT is persisted
- THEN the project reaches the memory seam with panel scope and the run-specific key

#### Scenario: Cross-thread or project-level artifact
- GIVEN a run records a cross-thread entity or project-level evidence
- WHEN the artifact is persisted
- THEN entity identity is preserved and a project-level artifact uses `sdb:project:{kind}` only when needed

#### Scenario: Phase and recovery compatibility
- GIVEN a project-aware run is interrupted
- WHEN it resumes
- THEN the existing seven-phase flow and checkpoint recovery behavior are unchanged

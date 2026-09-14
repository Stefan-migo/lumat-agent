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

The system MUST reuse exact-plan approval and atomic execution claim. APPROVE MUST cover the canonical phase/task plan, VERIFY MUST compare all results with SPEC, and recovery MUST reuse the frozen plan without repeating completed tasks. Unknown commit outcomes MUST fail closed and require recovery; exactly-once is not claimed beyond the database boundary. (Seams: `app/services/agent_chat.py:567-639`, `app/chat/assistant/recovery.py:26-54`; integration tests inject persistence and unknown outcomes.)

#### Scenario: Persistence failure

- GIVEN a mutation is flushed and checkpoint or artifact persistence fails
- WHEN the caller transaction is rolled back
- THEN no committed mutation remains without its checkpoint

#### Scenario: Unknown commit outcome

- GIVEN commit completion cannot be determined
- WHEN execution reports the outcome
- THEN it fails closed and requires recovery rather than blindly retrying

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

### Requirement: SDB-6 — Typed Bounded Write Tasks

SDB MUST allow write tasks only after whitelist membership, Pydantic validation, and write classification. One approval MUST freeze every ordered `{task_id, tool, validated arguments}` binding in the canonical SDB digest, covering identity, tool, arguments, and order. Gate order MUST be whitelist → validation → classification → cost gate → project capability. (Seams: `app/services/agent_chat.py:90-106`, `app/chat/assistant/state.py:90-110`; unit tests cover schemas/gates.)

#### Scenario: Valid frozen write plan
- GIVEN a plan uses an allow-listed `automation.create_rule` or project lifecycle tool with valid typed arguments
- WHEN approval is prepared
- THEN every binding is frozen in order and approval covers the canonical digest

#### Scenario: Tampered or reordered plan
- GIVEN a consumed approval and a changed task ID, tool, arguments, or order
- WHEN execution validates the plan
- THEN execution is rejected before any handler runs

#### Scenario: Gate denial

- GIVEN a write is not allow-listed, malformed, classified read-only, cost-blocked, or missing project capability
- WHEN EXECUTE evaluates it
- THEN no write handler runs and rejection evidence is recorded

### Requirement: SDB-7 — Write Execution and Recovery

SDB EXECUTE MUST pass each write through `execute_tool` with consumed exact approval, audit every attempt, persist checkpoint/result/event state, and stop on first failure. A blocked cost gate MUST block all writes. Recovery MUST reuse the frozen plan and execute only incomplete tasks. (Seams: `app/services/agent_chat.py:79-136`, `app/chat/assistant/tools/registry.py:272-308`, `app/chat/assistant/recovery.py:47-54`; unit/integration tests cover ordering and rollback.)

#### Scenario: Ordered mutations
- GIVEN an approved frozen plan and permitted cost/capability gates
- WHEN EXECUTE runs
- THEN writes execute in order through `execute_tool`, with audit, checkpoint, result, and event for each task

#### Scenario: First failure
- GIVEN one task fails or raises
- WHEN its attempt is persisted
- THEN it is failed and no subsequent task executes

#### Scenario: Recovery
- GIVEN completed checkpoints and an interrupted run
- WHEN recovery resumes
- THEN only incomplete tasks execute and prior results remain in verification input

### Requirement: SDB-9 — Canonical Execution Route

The durable `_run_sdb_tasks` route MUST be the only SDB runner. Graph routing MAY project compatibility state, but approval MUST remain `consumed` and dispatch through that route. Delivery MUST report verified mutation outcomes or truthful failure, never `not-implemented`. (Seams: `app/services/agent_chat.py:79-80,567-639`, `app/chat/assistant/graph.py:69-115`; integration tests prove one runner and truthful outcomes.)

#### Scenario: Consumed approval routing
- GIVEN approval is atomically consumed
- WHEN execution starts through API or graph
- THEN `_run_sdb_tasks` is used and approval remains `consumed`

### Requirement: SDB-10 — Project Write Boundary

SDB MUST fail closed when a non-default project lacks capability, and MUST preserve that capability for mutation and artifact persistence. (Seams: `app/services/agent_chat.py:74-76,177-241`, `app/services/tukulpan.py:268-303`; integration tests cover authorized and missing capability.)

#### Scenario: Authorized project mutation
- GIVEN an active capability for the selected project
- WHEN a project write executes and persists its result
- THEN the service and SDB artifacts use that authorized project

#### Scenario: Missing capability
- GIVEN a non-default project without an active capability
- WHEN EXECUTE is requested
- THEN no mutation or artifact write commits

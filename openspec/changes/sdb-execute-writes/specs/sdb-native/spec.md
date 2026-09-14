# Delta for sdb-native

## MODIFIED Requirements

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

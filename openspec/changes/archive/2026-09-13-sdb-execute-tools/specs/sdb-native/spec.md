# Delta for sdb-native

## ADDED Requirements

### Requirement: SDB-6 — Typed Read Tasks

Each frozen SDB task MUST declare one concrete registry `tool` string and validated `arguments` dictionary. The plan MUST use `conversations.search` with the frozen request as `query` and `limit` 10 for the first read task. Unknown tools, malformed arguments, and tools not classified read-only MUST be rejected before approval.

#### Scenario: Valid typed plan
- GIVEN a bounded frozen request
- WHEN PLAN is created
- THEN its task contains the concrete read tool and validated arguments

#### Scenario: Invalid task rejected
- GIVEN a task names an unknown tool or invalid arguments
- WHEN approval is requested
- THEN the plan is rejected before approval and no tool executes

### Requirement: SDB-7 — Real Read Execution and Recovery

SDB EXECUTE MUST invoke the existing assistant tool boundary with its whitelist and cost decision, persist a bounded task result and checkpoint, and aggregate persisted results with newly executed results after resume.

#### Scenario: Successful read
- GIVEN an approved typed read task and permitted cost decision
- WHEN EXECUTE runs
- THEN `execute_tool` returns bounded evidence and the task result is `completed`

#### Scenario: Failed or blocked read
- GIVEN a read times out, raises, or is denied by a gate
- WHEN EXECUTE records the task
- THEN it records bounded error evidence and audit as `failed`, never `completed`

#### Scenario: Resume aggregation
- GIVEN completed checkpoints exist before a resume
- WHEN remaining tasks execute and VERIFY starts
- THEN VERIFY receives every frozen task result, including persisted and new results

### Requirement: SDB-9 — Canonical Durable Execution Route

The durable `_run_sdb_tasks` route MUST be authoritative for SDB execution. Graph nodes MAY remain compatibility logic, but graph approval routing MUST reconcile to canonical `consumed` approval state and MUST NOT create a second execution runner.

#### Scenario: Consumed approval routing
- GIVEN an approval is atomically consumed
- WHEN SDB execution is requested through the graph or durable API
- THEN the canonical route is used and the persisted status remains `consumed`

### Requirement: SDB-10 — Authorized Project Read Boundary

The SDB runtime MUST preserve the selected project through the existing panel-scoped, run-specific artifact seam. A non-default project MUST have its active capability before a read executes; otherwise no tool or mutation may run.

#### Scenario: Project-aware read
- GIVEN an SDB run selects an authorized project
- WHEN a result or evidence artifact is persisted
- THEN panel scope, entity identity, project, and run-specific key are preserved

#### Scenario: Missing project capability
- GIVEN execution targets a non-default project without active authorization
- WHEN EXECUTE is requested
- THEN no tool or mutation runs and bounded rejection evidence is recorded

## MODIFIED Requirements

### Requirement: SDB-4 — Approval, Verification, and Durable Recovery

The system MUST reuse exact-plan approval and the atomic execution claim. APPROVE MUST cover the canonical phase/task plan, and VERIFY MUST compare all persisted and newly produced outputs with that SPEC before DELIVER. Resume MUST continue from the last successful checkpoint without repeating completed tasks. An executable SDB plan MUST produce real read evidence or truthful failure.
(Previously: recovery and verification described a stub-compatible delivery boundary and did not require the complete result set after resume.)

#### Scenario: Changed SPEC after approval
- GIVEN the SPEC or canonical task plan changes after approval
- WHEN execution or verification is requested
- THEN approval is rejected and delivery does not occur

#### Scenario: Resume after interruption
- GIVEN a run stops after a persisted task checkpoint
- WHEN the thread is resumed
- THEN only incomplete work continues, completed tasks are not repeated, and VERIFY receives the complete result set

#### Scenario: Executable SDB delivery
- GIVEN an approved native SDB plan
- WHEN the run reaches DELIVER
- THEN it reports verified bounded read evidence or truthful bounded failure, never `not-implemented`

# Delta for assistant-operations

## ADDED Requirements

### Requirement: AO-4 — Durable SDB Result Truth

The durable SDB API MUST persist bounded task results, checkpoints, evidence, audit, and ordered phase events for both successful and failed reads. A failed, timed-out, exceptioning, or cost-blocked task MUST remain failed and MUST prevent successful verification or delivery.

#### Scenario: Successful execution evidence
- GIVEN an approved SDB read executes successfully
- WHEN the durable runner completes the task
- THEN a task-bound result, checkpoint, evidence, audit, and ordered event are persisted

#### Scenario: Failed execution evidence
- GIVEN the read fails or the cost gate denies execution
- WHEN the durable runner records the outcome
- THEN bounded error evidence and audit are persisted, with no completed result

#### Scenario: Recovery result set
- GIVEN a run resumes after one or more completed checkpoints
- WHEN the API performs verification
- THEN its verification input includes all persisted completed results and newly executed results

## MODIFIED Requirements

### Requirement: AO-2 — Exact-Argument Approval

Every write, including SDB execution, MUST require server-validated approval bound to the exact canonical tool or phase/task plan and serialized arguments. The server MUST reject replayed, altered, expired, or client-only approvals. A read-only SDB task MUST still be bound to the frozen validated tool and arguments before approval is consumed.
(Previously: approval required exact binding for writes and SDB plans but the SDB task payload could contain `tool=None` and empty arguments.)

#### Scenario: Approved SDB execution
- GIVEN a pending SDB plan with an exact canonical phase/task payload
- WHEN an administrator approves that plan
- THEN only that payload executes once and approval is durably consumed

#### Scenario: Tampering is rejected
- GIVEN an approval whose plan, SPEC digest, or arguments differ from persisted state
- WHEN execution is requested
- THEN the server rejects it and performs no write

#### Scenario: Typed read binding
- GIVEN a persisted SDB task with a concrete tool and validated arguments
- WHEN its approval is consumed
- THEN execution uses exactly that tool and argument payload

## MODIFIED Requirements

### Requirement: AO-3 — Admin SSE and Audit

The system MUST expose admin-only ordered events for SDB phases, checkpoints, approval, task execution, verification, evidence, delivery, and errors. Every execution attempt MUST record `record_audit`; streams MUST NOT hold an unbounded transaction. Events MUST identify the run and task and MUST distinguish completed from failed outcomes.
(Previously: events identified SDB execution and evidence but did not require truthful task outcome distinction.)

#### Scenario: SDB evidence streams
- GIVEN an authorized SDB run
- WHEN a task produces output
- THEN ordered events identify the run/task and evidence, while execution audit is persisted

#### Scenario: Unauthorized stream
- GIVEN an authenticated operador requests an SDB stream
- WHEN authorization is checked
- THEN access is rejected and no SDB data is sent

#### Scenario: Failed task stream
- GIVEN an SDB read fails
- WHEN events are streamed
- THEN the task event is failed/error and is never presented as completed

## REMOVED Requirements

### Requirement: `not-implemented` SDB delivery
(Reason: the read-only execution slice now has a real result or truthful failure.)
(Migration: Update intentional RED API assertions to assert real evidence or failed delivery.)

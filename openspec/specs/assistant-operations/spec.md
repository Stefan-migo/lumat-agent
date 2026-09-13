# assistant-operations Specification

## Purpose

Provide an admin-only, durable operations assistant with visible planning, exact approvals, typed execution, evidence, audit, and recoverable streaming.

## Requirements

### Requirement: AO-1 — Durable Assistant Graph

The system MUST run the separate durable panel `AssistantState` graph for normal requests and native SDB requests. It MUST persist bounded context, normalized trigger, phase, SPEC reference, checkpoints, plan, and evidence in the existing thread boundary, recover from DB state without duplicate execution, and MUST NOT couple to WhatsApp state.
(Previously: the graph persisted normal planner, approval, execution, and evidence state but had no SDB phase state.)

#### Scenario: Contextual plan is persisted

- GIVEN an authorized administrator submits an assistant request
- WHEN planning completes
- THEN bounded context, structured plan, and thread state are persisted and exposed

#### Scenario: SDB phase state is persisted

- GIVEN a valid SDB trigger enters the native branch
- WHEN a phase or task completes
- THEN the current phase, bounded SPEC reference, checkpoint, and evidence are durable

#### Scenario: Recovery after interruption

- GIVEN a persisted plan or SDB checkpoint is interrupted
- WHEN the administrator reloads the thread
- THEN the assistant resumes from durable state without duplicating completed work

### Requirement: AO-2 — Exact-Argument Approval

Every write, including SDB execution, MUST require server-validated approval bound to the exact canonical tool or phase/task plan and serialized arguments. The server MUST reject replayed, altered, expired, or client-only approvals. A read-only SDB task MUST still be bound to the frozen validated tool and arguments before approval is consumed.
(Previously: approval was bound only to a tool name and serialized arguments.)

#### Scenario: Approved SDB execution

- GIVEN a pending SDB plan with an exact canonical phase/task payload
- WHEN an administrator approves that plan
- THEN only that payload executes once and approval is durably consumed

#### Scenario: Tampering is rejected

- GIVEN an approval whose plan, SPEC digest, or arguments differ from persisted state
- WHEN execution is requested
- THEN the server rejects it and performs no write

### Requirement: AO-3 — Admin SSE and Audit

The system MUST expose admin-only ordered events for SDB phases, checkpoints, approval, task execution, verification, evidence, delivery, and errors. Every execution attempt MUST record `record_audit`; streams MUST NOT hold an unbounded transaction. Events MUST identify the run and task and MUST distinguish completed from failed outcomes.
(Previously: events covered plan, approval, tool, evidence, status, and error but not SDB phases or checkpoints.)

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

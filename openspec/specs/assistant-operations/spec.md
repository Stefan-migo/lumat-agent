# assistant-operations Specification

## Purpose

Provide a role-authorized, durable operations assistant with visible planning, exact approvals, typed execution, evidence, audit, and recoverable streaming.

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

Every SDB mutation MUST require server-validated approval bound to the complete canonical phase/task plan and every ordered `{task_id, tool, validated arguments}` binding. The server MUST reject replayed, altered, expired, or client-only approvals. One approval MUST be consumed once for the frozen plan. (Seams: `app/chat/assistant/approval.py:16-30,85-157`, `app/services/agent_chat.py:567-609`; unit tests MUST cover task substitution, reorder, digest tampering, expiry, and replay.)

#### Scenario: Whole-plan approval

- GIVEN a pending multi-task SDB plan
- WHEN an administrator approves it
- THEN one approval covers the unchanged ordered plan and becomes `consumed`

#### Scenario: Tampering

- GIVEN any task identity, tool, argument, order, or SPEC digest differs
- WHEN execution is requested
- THEN approval fails and no mutation runs

### Requirement: AO-3 — Admin SSE and Audit

Admin-only ordered events MUST identify run, task, and completed or failed mutation outcomes. Every attempt MUST call `record_audit`; events MUST be persisted with the same caller transaction as mutation and checkpoint state, and streams MUST NOT hold an unbounded transaction. (Seams: `app/services/agent_chat.py:117-132,625-637`, `app/services/realtime.py:59-70`; integration tests MUST verify ordering, authorization, and rollback.)

#### Scenario: Mutation evidence stream

- GIVEN an authorized SDB mutation run
- WHEN a task completes
- THEN ordered task, evidence, checkpoint, and audit data identify the run and task

#### Scenario: Failed mutation stream
- GIVEN a task fails
- WHEN events are streamed
- THEN the task event is failed/error and is never presented as completed

### Requirement: AO-4 — Durable SDB Result Truth

The durable API MUST persist mutation, audit, checkpoint/result, thread state, and artifact in the same caller transaction. A persistence failure MUST roll back the mutation so no committed mutation lacks its checkpoint. Unknown commit outcome MUST fail closed and require recovery. The contract MUST NOT claim exactly-once execution beyond the DB boundary. (Seams: `app/services/agent_chat.py:177-241,622-637`, `app/services/tukulpan.py:268-303`; integration tests MUST force persistence failure and recovery.)

#### Scenario: Atomic mutation record
- GIVEN a write service flushes a mutation
- WHEN audit, checkpoint, result, thread, and artifact persistence succeeds
- THEN all are committed together

#### Scenario: Persistence rollback
- GIVEN any required persistence step fails
- WHEN the caller transaction rolls back
- THEN no mutation is committed without its durable execution evidence

#### Scenario: Recovery after uncertain commit
- GIVEN commit outcome is unknown
- WHEN the run is resumed
- THEN recovery consults committed checkpoints and executes only incomplete frozen tasks

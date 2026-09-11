# assistant-operations Specification

## Purpose

Provide an admin-only, durable operations assistant with visible planning, exact approvals, typed execution, evidence, audit, and recoverable streaming.

## Requirements

### Requirement: AO-1 — Durable Assistant Graph

The system MUST run a separate LangGraph `AssistantState` for panel requests, with context assembly, structured planning, approval, execution, and evidence stages. It MUST persist assembled-turn state and plan metadata using `InternalChatThread`, recover from DB state without duplicate execution, and MUST NOT couple to WhatsApp state.
(Previously: the graph had planner, approval, execution, and evidence stages but no durable history-aware context assembly.)

#### Scenario: Contextual plan is persisted
- GIVEN an authorized administrator submits an assistant request
- WHEN planning completes
- THEN bounded context, structured plan, and thread state are persisted and exposed

#### Scenario: Recovery after interruption
- GIVEN a persisted plan or execution is interrupted
- WHEN the administrator reloads the thread
- THEN the assistant resumes or reports the durable recoverable state without duplicating execution

### Requirement: AO-2 — Exact-Argument Approval

Every write MUST require server-validated approval bound to the exact tool name and serialized arguments. The server MUST reject replayed, altered, expired, or client-only approvals.

#### Scenario: Approved write executes once
- GIVEN a pending write plan with exact arguments
- WHEN an administrator approves that plan
- THEN only those arguments execute once and the approval is durably consumed

#### Scenario: Tampering is rejected
- GIVEN an approval whose tool or arguments differ from the persisted plan
- WHEN execution is requested
- THEN the server rejects it and performs no write

### Requirement: AO-3 — Admin SSE and Audit

The system MUST expose admin-only SSE for ordered plan, approval, tool, evidence, status, and error events. Every tool execution MUST record `record_audit`; streams MUST NOT hold an unbounded transaction.

#### Scenario: Evidence streams
- GIVEN an authorized assistant run
- WHEN tool execution produces a result
- THEN ordered SSE events identify the run and return evidence, while the execution audit is persisted

#### Scenario: Unauthorized stream
- GIVEN an authenticated operador requests the assistant stream
- WHEN authorization is checked
- THEN access is rejected and no thread, plan, tool, or evidence data is sent

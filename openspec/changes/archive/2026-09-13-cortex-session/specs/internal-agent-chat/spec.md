# Delta for internal-agent-chat

## MODIFIED Requirements

### Requirement: IAC-2 — Context Boundary

The agent MUST use the separate `AssistantState` graph for panel requests, with only declared typed tools and admin authorization. It MUST assemble history-aware turns from the durable thread and persist normal, Cortex, or SDB state, approvals, execution, evidence, cost diagnostics, phase, and checkpoints in the existing thread boundary. Cortex state MUST be explicitly merged under `assistant_state["cortex_session"]` without clobbering other keys, and MUST NOT couple to WhatsApp state. The deterministic cost gate MUST retain its current behavior before planning.
(Previously: the boundary persisted normal and SDB state but did not include Cortex session state.)

#### Scenario: History-aware assistant response
- GIVEN an authorized administrator submits a panel request
- WHEN the assistant processes it
- THEN bounded context and assistant metadata, usage, and cost are persisted

#### Scenario: Durable SDB context
- GIVEN an authorized administrator starts a valid SDB run
- WHEN a phase transition occurs
- THEN phase, frozen scope, task, and checkpoint sequence persist

#### Scenario: Durable Cortex context
- GIVEN an authorized administrator turns an active Cortex thread
- WHEN session state changes
- THEN the nested Cortex state persists while unrelated assistant-state keys remain

#### Scenario: Blocked mode
- GIVEN a thread or UTC-day spend reaches its blocking limit
- WHEN an administrator submits a request
- THEN a deterministic reply is persisted and no LLM node is called

### Requirement: IAC-3 — Panel States

The panel MUST render normal, Cortex active/closed, SDB approval-pending, phase, checkpoint, verification, delivery, blocked, success, and error states without losing persisted messages or recoverable assistant metadata. A blocked result MUST remain a completed internal reply.
(Previously: panel states covered ordinary and SDB lifecycle states only.)

#### Scenario: Cortex recovery
- GIVEN a persisted active or closed Cortex session
- WHEN the administrator reloads the thread
- THEN the indicator, status, report, and next recoverable action remain visible

#### Scenario: Stream failure
- GIVEN an SSE stream fails during a Cortex turn
- WHEN the panel reconnects or reloads
- THEN persisted state is authoritative and no partial turn is treated as complete

## ADDED Requirements

### Requirement: IAC-7 — Literal planning controls

The chat surface MUST send planning lifecycle changes only from its planning button or exact `/planning` commands; ordinary message text MUST NOT change thread mode.

#### Scenario: Close control
- GIVEN an active Cortex thread
- WHEN the administrator clicks Close session
- THEN the same literal lifecycle operation runs as `/planning close`

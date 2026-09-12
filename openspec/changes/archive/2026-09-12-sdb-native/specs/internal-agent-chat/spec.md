# Delta for Internal Agent Chat

## MODIFIED Requirements

### Requirement: IAC-2 — Context Boundary

The agent MUST use the separate `AssistantState` graph for panel requests, with only declared typed tools and admin authorization. It MUST assemble history-aware turns from the durable thread, persist normal or SDB plan state, approval, execution, evidence, cost diagnostics, phase, and checkpoints in the existing thread boundary, and MUST NOT couple to WhatsApp state. The deterministic cost gate MUST retain its current behavior before planning.
(Previously: the boundary persisted normal assistant state but did not include SDB phase and checkpoint state.)

#### Scenario: History-aware assistant response

- GIVEN an authorized administrator submits a panel request
- WHEN the assistant processes it
- THEN bounded thread context and assistant metadata, usage, and cost are persisted

#### Scenario: Durable SDB context

- GIVEN an authorized administrator starts a valid SDB run
- WHEN a phase transition occurs
- THEN phase, frozen scope reference, current task, and checkpoint sequence persist in the thread

#### Scenario: Blocked mode

- GIVEN a thread or UTC-day spend reaches its blocking limit
- WHEN an administrator submits a request
- THEN a deterministic reply is persisted, no LLM node is called, and panel access remains available

### Requirement: IAC-3 — Panel States

The panel MUST render normal and SDB loading, planning, approval-pending, phase, checkpoint, verification, delivery, blocked, success, and error states without losing persisted messages or recoverable assistant metadata. A blocked result MUST remain a completed internal reply.
(Previously: panel states covered ordinary assistant lifecycle states only.)

#### Scenario: SDB recovery

- GIVEN a persisted SDB run is paused at approval or a checkpoint
- WHEN the administrator reloads the thread
- THEN the phase, approval state, and next recoverable action remain visible

#### Scenario: Stream failure

- GIVEN an SSE stream fails after an SDB phase starts
- WHEN the panel reconnects or reloads
- THEN persisted state is authoritative and no partial phase is treated as complete

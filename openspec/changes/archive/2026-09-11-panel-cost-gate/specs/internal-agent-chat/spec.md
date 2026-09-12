# Delta for Internal Agent Chat

## MODIFIED Requirements

### Requirement: IAC-2 — Context Boundary

The agent MUST use the separate `AssistantState` graph for panel requests, with only declared typed tools and admin authorization. It MUST assemble history-aware turns from the durable thread, persist plan, approval, execution, evidence, and cost diagnostics in the existing thread boundary, and MUST NOT couple to WhatsApp state. A deterministic cost gate MUST run after `assemble_context` and before `plan_llm`, using the configured internal-thread and global UTC-day limits. It MUST allow `normal`, apply a concise directive while allowing LLM use in `conservative`, and return a deterministic persisted internal reply in `blocked` without any LLM call or operator lockout.
(Previously: the panel graph assembled durable context but had no panel cost measurement or pre-planner cost gate.)

#### Scenario: History-aware assistant response

- GIVEN an authorized administrator submits a panel request below both limits
- WHEN the assistant processes it
- THEN the response uses bounded thread context and assistant metadata, usage, and measured cost are persisted on the request message

#### Scenario: Conservative mode

- GIVEN a thread or UTC-day spend reaches its configured conservative threshold
- WHEN an authorized administrator submits a request
- THEN the assistant uses a concise directive, may call the LLM, and persists the selected mode and resulting usage diagnostics

#### Scenario: Blocked mode

- GIVEN a thread or UTC-day spend reaches its configured blocking limit
- WHEN an authorized administrator submits a request
- THEN a deterministic canned reply is persisted as an internal response, no LLM node is called, and panel access remains available

#### Scenario: Unknown pricing or usage

- GIVEN a completed planner or streamed response call has unknown model pricing or absent usage
- WHEN its usage is recorded
- THEN `cost_llm` records zero for that call and a diagnostic identifies the missing pricing or usage without fabricating tokens or cost

#### Scenario: Operator denied

- GIVEN an authenticated operador requests assistant data or a tool
- WHEN authorization is evaluated
- THEN no thread, tool, evidence, cost, or gate data is exposed

### Requirement: IAC-3 — Panel States

The panel MUST render loading, empty, planning, approval-pending, streaming, success, blocked, and error states without losing persisted messages or recoverable assistant metadata. A blocked result MUST be represented as a completed internal assistant reply and MUST NOT be represented as operator lockout or customer-facing escalation.
(Previously: the panel rendered processing and error states but had no persisted deterministic blocked result.)

#### Scenario: Approval recovery

- GIVEN a persisted plan awaits approval
- WHEN the administrator reloads the thread
- THEN the approval state and exact proposed action remain visible

#### Scenario: Processing recovery

- GIVEN a message request is processing
- WHEN the response fails
- THEN the error is actionable and the submitted message remains recoverable

#### Scenario: Blocked recovery

- GIVEN a cost gate returns blocked
- WHEN the administrator reloads the thread
- THEN the canned assistant reply and completed/degraded state remain persisted and visible

#### Scenario: Stream failure

- GIVEN an SSE stream fails after a run starts
- WHEN the panel reconnects or reloads
- THEN persisted state is authoritative and no partial response is treated as complete

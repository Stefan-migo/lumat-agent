# Internal Agent Chat Specification

## Purpose

Provide persistent owner/admin conversations with the agent inside the authenticated panel.

## Requirements

### Requirement: IAC-1 — Role-Bound Threads

The system MUST restrict internal agent chat to the owner/admin authorization boundary, MUST persist threads and messages, and MUST audit creation and message actions.

#### Scenario: Authorized thread

- GIVEN an authenticated owner or admin
- WHEN they open or send a message in an internal thread
- THEN the thread and message are persisted and the action is audited

#### Scenario: Operator denied

- GIVEN an authenticated operador
- WHEN they request an internal agent thread
- THEN the server returns an authorization error and exposes no thread data

### Requirement: IAC-2 — Context Boundary

The agent MUST use the separate `AssistantState` graph for panel requests, with only declared typed tools and admin authorization. It MUST assemble history-aware turns from the durable thread, persist plan, approval, execution, evidence, and cost diagnostics in the existing thread boundary, and MUST NOT couple to WhatsApp state. A deterministic cost gate MUST run after `assemble_context` and before `plan_llm`, using the configured internal-thread and global UTC-day limits. It MUST allow `normal`, apply a concise directive while allowing LLM use in `conservative`, and return a deterministic persisted internal reply in `blocked` without any LLM call or operator lockout.
(Previously: the panel graph assembled durable context but had no panel cost measurement or pre-planner cost gate.)

#### Scenario: History-aware assistant response

- GIVEN an authorized administrator submits a panel request
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
- THEN no thread, tool, or evidence data is exposed

### Requirement: IAC-3 — Panel States

The panel MUST render loading, empty, planning, approval-pending, streaming, success, blocked, and error states without losing persisted messages or recoverable assistant metadata. A blocked result MUST be represented as a completed internal assistant reply and MUST NOT be represented as operator lockout or customer-facing escalation.

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

### Requirement: IAC-4 — Conversation Surface Presentation

`AgentChat` MUST present the existing persisted internal thread as an agent conversation surface: messages MUST expose author direction, avatar/identity, processing status, empty state, failure state, retry affordance, and a labeled composer. This presentation MUST NOT add WebSocket, SSE, polling truth, or alter `createChatThread`, `getChatThread`, or `sendChatMessage` persistence behavior.

#### Scenario: Persisted messages render by role
- GIVEN an authorized `AgentChat` response contains agent and administrator messages
- WHEN the thread renders
- THEN each message has a testable author label, directional bubble semantics, and reused avatar/identity treatment

#### Scenario: Empty and processing states
- GIVEN the persisted thread has no messages or `sendChatMessage` is processing
- WHEN `AgentChat` renders
- THEN a labeled empty state or processing `status` is visible and the composer is disabled while processing

#### Scenario: Failed message is recoverable
- GIVEN `sendChatMessage` fails or returns a failed message
- WHEN the error state renders
- THEN an `alert` and `Reintentar` affordance appear, the submitted content remains recoverable, and persisted messages are not discarded

### Requirement: IAC-5 — Authorization and Context Non-Regression

The `AgentChat` presentation MUST remain inside the existing owner/admin authorization and conversation graph/model context boundaries defined by IAC-1 and IAC-2. Visual roles, avatars, bubbles, and retry controls MUST NOT expose thread data or privileged tools to an operador.

#### Scenario: Operator remains denied
- GIVEN an authenticated operador opens `AgentChat`
- WHEN the existing authorization response is forbidden
- THEN no internal thread or message content renders and the visible state is an actionable permission error

#### Scenario: Authorized failure does not escalate context
- GIVEN an authorized user requests an unavailable privileged action through the internal chat
- WHEN the response is rendered
- THEN the existing refusal/escalation behavior remains unchanged and only the existing thread context is shown

### Requirement: IAC-6 — Compatible Token Streaming

The assistant MUST stream ordered plan, approval, tool, evidence, response, and error events over its dedicated admin-only SSE endpoint. Existing thread endpoints and serialized fields MUST remain compatible, while DB-authoritative history-aware turns replace the prior stateless backend.
(Previously: the assistant graph replaced the old chat backend but processed only the current request context.)

#### Scenario: SSE and thread persistence coexist
- GIVEN an authorized administrator submits a message
- WHEN the assistant generates a response
- THEN SSE events identify the thread and the existing endpoint returns the persisted compatible thread shape

#### Scenario: Streaming failure
- GIVEN SSE delivery fails after the request starts
- WHEN the assistant run completes
- THEN no partial stream is persisted as a complete response and the persisted error remains recoverable

#### Scenario: Existing endpoint remains safe
- GIVEN an existing client uses thread creation, retrieval, or message endpoints
- WHEN it calls them after the assistant rollout
- THEN authorization and persistence contracts remain compatible

#### Scenario: Operator remains denied
- GIVEN an authenticated operador requests assistant chat or its SSE stream
- WHEN authorization is checked
- THEN access is rejected and no token, plan, or thread data is exposed

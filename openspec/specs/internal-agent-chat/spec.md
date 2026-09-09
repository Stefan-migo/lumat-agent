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

The agent MUST use the separate `AssistantState` graph for panel requests, with only declared typed tools and admin authorization. It MUST persist plan, approval, execution, and evidence metadata in the existing thread boundary and MUST NOT couple to WhatsApp state.
(Previously: internal chat used only the existing conversation graph/model and had no tools or privileged data access.)

#### Scenario: Assistant response

- GIVEN an authorized administrator submits a panel request
- WHEN the assistant processes it
- THEN the response and assistant metadata are persisted in the same thread with evidence

#### Scenario: Operator denied

- GIVEN an authenticated operador requests assistant data or a tool
- WHEN authorization is evaluated
- THEN no thread, tool, or evidence data is exposed

### Requirement: IAC-3 — Panel States

The panel MUST render loading, empty, planning, approval-pending, streaming, success, and error states without losing persisted messages or recoverable assistant metadata.

#### Scenario: Approval recovery
- GIVEN a persisted plan awaits approval
- WHEN the administrator reloads the thread
- THEN the approval state and exact proposed action remain visible

#### Scenario: Processing recovery

- GIVEN a message request is processing
- WHEN the response fails
- THEN the error is actionable and the submitted message remains recoverable

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

The assistant MUST stream ordered plan, approval, tool, evidence, response, and error events over its dedicated SSE endpoint. Existing thread endpoints MUST remain compatible, while the assistant graph replaces `run_internal_conversation` as the chat backend.
(Previously: token events were published on `/panel/ws` while synchronous POST remained authoritative and tool-free.)

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

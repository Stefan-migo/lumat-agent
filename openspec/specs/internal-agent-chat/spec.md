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

The agent MUST use only the existing conversation graph/model boundary and MUST NOT gain tools, data access, or permissions beyond that model through internal chat.

#### Scenario: Normal response

- GIVEN an authorized internal message
- WHEN the agent responds
- THEN the response is persisted in the same thread with its processing status

#### Scenario: Tool escalation denied

- GIVEN an internal prompt requesting an unavailable privileged action
- WHEN the agent processes it
- THEN the action is refused or escalated without unauthorized side effects

### Requirement: IAC-3 — Panel States

The panel MUST render loading, empty, processing, success, and error states without losing persisted messages.

#### Scenario: Processing recovery

- GIVEN a message request is processing
- WHEN the response fails
- THEN the error is actionable and the submitted message remains recoverable

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

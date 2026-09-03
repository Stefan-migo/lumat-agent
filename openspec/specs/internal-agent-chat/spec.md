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

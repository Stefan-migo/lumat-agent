# Delta for Internal Agent Chat

## ADDED Requirements

### Requirement: IAC-9 — Bounded Thread List and Read

The internal chat API MUST expose owner/admin-authorized, bounded thread-list and thread-read data for the navigator, including stable identity, title or preview, updated time, selected state support, and run/approval or unread status where available. It MUST NOT fabricate planning sessions as conversation threads or expand write permissions.

#### Scenario: Authorized bounded list

- GIVEN an authenticated owner or admin requests internal threads
- WHEN the list is read
- THEN only a bounded, stable result is returned with fields sufficient for navigation

#### Scenario: Unauthorized or unbounded request

- GIVEN an operador requests the list or a client requests an unsupported unbounded page
- WHEN authorization or bounds are checked
- THEN the server rejects the request without exposing thread data

## MODIFIED Requirements

### Requirement: IAC-4 — Conversation Surface Presentation

`AgentChat` MUST present the existing persisted internal thread as the center assistant conversation surface: messages MUST expose author direction, avatar/identity, processing status, empty state, failure state, retry affordance, and a labeled composer. Streaming output MAY be shown transiently during the active run, but persisted messages remain authoritative and this presentation MUST NOT alter `createChatThread`, `getChatThread`, or `sendChatMessage` persistence behavior.
(Previously: `AgentChat` presented the persisted thread without an explicit transient-stream versus persisted-history contract.)

#### Scenario: Persisted messages render by role

- GIVEN an authorized response contains agent and administrator messages
- WHEN the thread renders
- THEN each message has a testable author label, directional semantics, and reused avatar/identity treatment

#### Scenario: Empty and processing states

- GIVEN the persisted thread is empty or `sendChatMessage` is processing
- WHEN `AgentChat` renders
- THEN a labeled empty or processing status is visible and the composer is disabled while processing

#### Scenario: Failed message is recoverable

- GIVEN sending fails or returns a failed message
- WHEN the error renders
- THEN an alert and `Reintentar` affordance appear, submitted content remains recoverable, and persisted messages are not discarded

### Requirement: IAC-6 — Compatible Token Streaming

The assistant MUST stream ordered plan, approval, tool, evidence, response, and error events over its dedicated admin-only SSE endpoint while retaining compatible thread endpoints and serialized fields. Stream tokens are transient presentation; persisted history and durable approval state are authoritative after completion, reconnect, or reload.
(Previously: compatibility required ordered SSE and persistence but did not define transient token authority after reconnect.)

#### Scenario: SSE and thread persistence coexist

- GIVEN an authorized administrator submits a message
- WHEN the assistant generates a response
- THEN SSE identifies the thread and the endpoint returns the persisted compatible thread shape

#### Scenario: Streaming failure

- GIVEN SSE delivery fails after a run starts
- WHEN the panel reconnects or reloads
- THEN no partial stream is treated as a complete response and persisted error or recovery state remains authoritative

#### Scenario: Existing endpoint remains safe

- GIVEN an existing client uses thread creation, retrieval, or message endpoints
- WHEN it calls them after the rollout
- THEN authorization, approval, and persistence contracts remain compatible

## Graph Check Consulted

Nodes: `AgentChat.tsx`, `chat.py`, `api.ts`, `InternalChatThread`, `InternalChatMessage`, `agent_chat.py`. Edges: `AgentChat.tsx` references `domain/PanelShell.tsx`; `api.ts` reaches `chat.py` through the recorded graph path.

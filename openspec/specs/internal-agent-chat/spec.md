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

The agent MUST use the separate `AssistantState` graph for panel requests and persist SDB phase, approval, execution, evidence, cost diagnostics, checkpoints, thread state, and artifacts in the existing boundary. SDB writes MUST use `_run_sdb_tasks` as the only durable runner, with approval canonically `consumed`; the graph MUST NOT create a second runner or bypass `execute_tool`. (Seams: `app/chat/assistant/graph.py:69-115`, `app/services/agent_chat.py:79-80,608-610`; unit and integration tests MUST prove canonical routing and no bypass.)

#### Scenario: Canonical approved execution

- GIVEN an approved SDB write plan
- WHEN execution starts
- THEN the consumed approval reaches the canonical runner and every write reaches `execute_tool`

#### Scenario: Recovery state

- GIVEN a run has persisted checkpoints and thread state
- WHEN the thread resumes
- THEN the same frozen plan determines only incomplete work

### Requirement: IAC-3 — Panel States

The panel MUST render normal, Cortex active/closed, SDB approval-pending, phase, checkpoint, verification, delivery, blocked, success, and error states without losing persisted messages or recoverable assistant metadata. A blocked result MUST remain a completed internal reply.
(Previously: panel states covered ordinary assistant lifecycle states only.)

#### Scenario: SDB recovery

- GIVEN a persisted SDB run is paused at approval or a checkpoint
- WHEN the administrator reloads the thread
- THEN the phase, approval state, and next recoverable action remain visible

#### Scenario: Cortex recovery

- GIVEN a persisted active or closed Cortex session
- WHEN the administrator reloads the thread
- THEN the indicator, status, report, and next recoverable action remain visible

#### Scenario: Stream failure

- GIVEN an SSE stream fails during a Cortex turn
- WHEN the panel reconnects or reloads
- THEN persisted state is authoritative and no partial phase is treated as complete

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

### Requirement: IAC-7 — Literal planning controls

The chat surface MUST send planning lifecycle changes only from its planning button or exact `/planning` commands; ordinary message text MUST NOT change thread mode.

#### Scenario: Close control

- GIVEN an active Cortex thread
- WHEN the administrator clicks Close session
- THEN the same literal lifecycle operation runs as `/planning close`

#### Scenario: Operator remains denied
- GIVEN an authenticated operador requests assistant chat or its SSE stream
- WHEN authorization is checked
- THEN access is rejected and no token, plan, or thread data is exposed

### Requirement: IAC-8 — Honest SDB Conversation Delivery

Internal agent chat MUST present verified bounded outcomes for writes: success only when every frozen task completed and its durable evidence committed; otherwise it MUST present bounded failure or recovery evidence. It MUST NOT present `not-implemented`. (Seams: `app/services/agent_chat.py:139-148,622-639`, `app/chat/assistant/nodes.py:291-309`; integration tests MUST cover successful mutation, first failure, rollback, and recovery.)

#### Scenario: Successful write conversation
- GIVEN every frozen write task completed and persistence committed
- WHEN the conversation receives delivery
- THEN it presents the bounded verified evidence and no `not-implemented` status

#### Scenario: Failed or uncertain write
- GIVEN a task fails, persistence rolls back, or commit outcome is unknown
- WHEN delivery is requested
- THEN the conversation presents an honest bounded failure/error outcome and remains recoverable

#### Scenario: No second runner
- GIVEN an SDB write request enters graph or durable API routing
- WHEN execution is dispatched
- THEN only `_run_sdb_tasks` performs execution

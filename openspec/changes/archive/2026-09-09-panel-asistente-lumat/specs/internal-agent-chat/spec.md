# Delta for internal-agent-chat

## MODIFIED Requirements

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
(Previously: the panel rendered loading, empty, processing, success, and error states for synchronous messages.)

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

### Requirement: IAC-6 — Compatible Assistant Streaming

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

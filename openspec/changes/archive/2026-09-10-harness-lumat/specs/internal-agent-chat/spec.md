# Delta for internal-agent-chat

## MODIFIED Requirements

### Requirement: IAC-2 — Context Boundary

The agent MUST use the separate `AssistantState` graph for panel requests, with only declared typed tools and admin authorization. It MUST assemble history-aware turns from the durable thread while persisting plan, approval, execution, and evidence metadata in the existing thread boundary, and MUST NOT couple to WhatsApp state.
(Previously: the graph used declared typed tools but did not consume durable thread history for planning or response context.)

#### Scenario: History-aware assistant response

- GIVEN an authorized administrator submits a panel request in a thread with prior messages
- WHEN the assistant processes it
- THEN the response uses the bounded thread context and all assistant metadata is persisted in that thread with evidence

#### Scenario: Operator denied

- GIVEN an authenticated operador requests assistant data or a tool
- WHEN authorization is evaluated
- THEN no thread, tool, or evidence data is exposed

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
- THEN no partial stream is persisted as complete and the persisted error remains recoverable

#### Scenario: Operator remains denied

- GIVEN an authenticated operador requests assistant chat or its SSE stream
- WHEN authorization is checked
- THEN access is rejected and no token, plan, or thread data is exposed

#### Scenario: Existing endpoint remains safe

- GIVEN an existing client uses thread creation, retrieval, or message endpoints
- WHEN it calls them after the harness rollout
- THEN authorization and persistence contracts remain compatible

# Delta for internal-agent-chat

## ADDED Requirements

### Requirement: IAC-6 — Compatible Token Streaming

For an authorized owner/admin internal chat request, the system MUST publish ordered `token` events on `/panel/ws` as response text becomes available, while the existing synchronous POST MUST continue to persist the complete response and return its current response shape. Internal chat MUST NOT gain tools, global commands, or new authorization scope.

#### Scenario: Stream and POST coexist
- GIVEN an authorized owner/admin submits an internal message
- WHEN the agent generates a response
- THEN token events identify the thread and the POST eventually returns the persisted complete response

#### Scenario: Streaming failure
- GIVEN token delivery fails after the request starts
- WHEN the POST completes
- THEN the existing synchronous success or error contract remains authoritative and no partial token is persisted as a complete message

#### Scenario: Operator remains denied
- GIVEN an authenticated operador requests internal chat
- WHEN the request or WebSocket subscription is authorized
- THEN access is rejected and no token or thread data is exposed

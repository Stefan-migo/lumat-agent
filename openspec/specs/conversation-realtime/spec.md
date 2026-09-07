# Conversation Realtime Specification

## Purpose

Provide authenticated, best-effort realtime updates for the panel without replacing REST commands or introducing replay infrastructure.

## Requirements

### Requirement: CRT-1 — Authenticated WebSocket Contract

The system MUST expose `/panel/ws`, authenticate the existing session cookie during the handshake, and reject unauthenticated or unauthorized clients. Each frame MUST use `{type, conversation_id?, data}` and MUST use only the event types `token`, `message`, `conversation`, `activity`, or `snapshot`. The server MUST preserve causal order per conversation and send the initial snapshot before live events.

#### Scenario: Authorized connection
- GIVEN a valid authorized panel session
- WHEN the client connects to `/panel/ws`
- THEN the handshake succeeds and a snapshot frame precedes live frames

#### Scenario: Rejected connection
- GIVEN no valid session or an unauthorized role
- WHEN the client connects to `/panel/ws`
- THEN the handshake is rejected and no panel data is sent

### Requirement: CRT-2 — Best-Effort Recovery

Delivery MAY lose events and MUST NOT require a replay bus, durable subscription, or multi-worker fan-out. On connect the server SHALL provide current snapshot data; after reconnect the SPA MUST refetch authoritative REST resources before presenting the connection as recovered.

#### Scenario: Dropped event
- GIVEN a live event is not delivered
- WHEN the client reconnects
- THEN REST refetch restores current conversation and active-summary truth without replay

### Requirement: CRT-3 — Typed Live Events

The server MUST publish persisted message, conversation-state, activity, and internal-agent token changes through the shared envelope. Snapshot data MUST include the current panel conversation view and reconnect-safe activity history. Token events MUST identify their internal-chat thread and preserve token order.

#### Scenario: Conversation update
- GIVEN a message or state change is committed
- WHEN a connected panel client is subscribed
- THEN the matching `message` or `conversation` event is delivered in causal order

#### Scenario: Internal token stream
- GIVEN an authorized internal chat request is processing
- WHEN response tokens become available
- THEN ordered `token` events are published while the synchronous POST contract remains valid

### Requirement: CRT-4 — Active Conversation Summary

The system MUST expose `GET /panel/api/conversations/active`, joining customer names and ordering by `last_message_at` descending. A conversation is active only when `state IN (bot, human)`, `last_message_at` is non-null, and it is within the configured 24-hour window; closed, stale, and null-recency rows MUST be excluded.

#### Scenario: Active result
- GIVEN bot and human conversations with valid recent recency
- WHEN the endpoint is requested by an authorized panel user
- THEN it returns customer names ordered newest first

#### Scenario: Excluded result
- GIVEN a closed, stale, or null-recency conversation
- WHEN the active endpoint is requested
- THEN that conversation is absent

### Requirement: CRT-5 — Deployment WebSocket Routing

Production nginx MUST route `/panel/ws` with HTTP/1.1 WebSocket upgrade headers and an appropriate read timeout. Vite development configuration MUST proxy `/panel/ws` with WebSocket support. The v1 deployment MUST assume a single API process.

#### Scenario: Development proxy
- GIVEN the SPA runs through Vite
- WHEN it opens `/panel/ws`
- THEN the proxy forwards the WebSocket upgrade to the API

#### Scenario: Production upgrade
- GIVEN nginx fronts the API
- WHEN a panel WebSocket handshake arrives
- THEN nginx preserves the upgrade and routes it to the API

# Delta for panel-app

## ADDED Requirements

### Requirement: PNL-APP-13 — Realtime Conversation Surfaces

The SPA MUST use one authenticated `/panel/ws` client for live conversation list, thread, ficha, activity, and internal-chat token updates. It MUST retain REST POST commands and MUST refetch conversations and the active summary after reconnect before clearing its disconnected state.

#### Scenario: Live conversation update
- GIVEN the conversation list and thread are open with a connected socket
- WHEN a message or state event arrives
- THEN the matching list, thread, and ficha data update without a manual refresh

#### Scenario: Reconnect recovery
- GIVEN the socket disconnects
- WHEN it reconnects
- THEN the SPA refetches authoritative resources and renders recovered data without replaying events

### Requirement: PNL-APP-14 — Active Summary Rail

`PanelShell` MUST feed its `Conversaciones activas` rail from `GET /panel/api/conversations/active`, including customer name and recency, with loading, empty, error, and disconnected states. It MUST NOT compose active truth from the general conversation list.

#### Scenario: Active rail data
- GIVEN the active-summary endpoint returns rows
- WHEN the expanded rail renders
- THEN rows show customer names ordered by server-provided recency

#### Scenario: Active rail failure
- GIVEN the active-summary request fails or the socket is disconnected
- WHEN the rail renders
- THEN an accessible status/error state appears without fabricated rows

### Requirement: PNL-APP-15 — Agent Activity Semantics

Conversation activity and token-streaming states MUST render with existing panel primitives and accessible `role="status"` semantics; errors MUST use `role="alert"`. The UI MUST distinguish persisted activity history from transient connection status.

#### Scenario: Activity announcement
- GIVEN a `classified`, `kb_retrieved`, or `escalation` event arrives
- WHEN the thread renders it
- THEN a visible labeled activity uses `role="status"`

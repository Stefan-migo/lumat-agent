# Delta for conversation-realtime

## MODIFIED Requirements

### Requirement: CRT-3 — Typed Live Events and Queue Snapshot

The server MUST publish persisted message, conversation-state, activity, and internal-agent token changes through the shared envelope. The initial `snapshot` MUST include the unified conversation queue view, including the same embedded selected-case context and count data used by REST list/detail payloads, plus reconnect-safe activity history. Token events MUST identify their internal-chat thread and preserve token order. (Previously: snapshots exposed the panel conversation view and activity history but did not require case context or queue counts.)

#### Scenario: Snapshot carries queue context (pytest)
- GIVEN an authorized client connects with conversations linked to cases
- WHEN the initial snapshot is sent
- THEN each conversation uses the REST-equivalent case selection and includes queue count data

#### Scenario: Conversation update
- GIVEN a message, state, case acknowledgement, or assignment change is committed
- WHEN a connected panel client is subscribed
- THEN the matching event is delivered and the queue refreshes from authoritative data without replay assumptions

## ADDED Requirements

### Requirement: CRT-6 — Bounded Queue Refresh

The SPA MUST refresh the queue from snapshot events rather than refetching for every individual conversation or message event. Repeated snapshot-driven refreshes MUST be bounded by a debounce or equivalent coalescing window, while an open thread MAY retain its existing more immediate refresh behavior.

#### Scenario: Burst coalescing (vitest)
- GIVEN multiple snapshot events arrive within the refresh window
- WHEN the queue observes them
- THEN it performs one coalesced authoritative list refresh rather than one request per event

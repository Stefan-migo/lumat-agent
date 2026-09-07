# Delta for panel-design-system

## ADDED Requirements

### Requirement: DS-RT-1 — Realtime State Grammar

Realtime conversation, active-rail, token-streaming, disconnected, loading, and error states MUST reuse existing tokenized primitives and MUST expose visible labels with `role="status"` or `role="alert"` as appropriate. Styling MUST add no hard-coded colors, new dependency, or duplicate primitive.

#### Scenario: Live activity is accessible
- GIVEN a conversation receives a persisted activity or token update
- WHEN the activity surface renders
- THEN its label is visible, status is announced, and existing tokenized styles are used

#### Scenario: Connection error is actionable
- GIVEN the WebSocket is disconnected or reconnecting
- WHEN the panel renders the state
- THEN a visible status explains the condition without hiding existing conversation content

### Requirement: DS-RT-2 — Realtime Responsive Surfaces

The active-conversation rail and live thread MUST preserve existing keyboard focus, compact/expanded rail behavior, reduced-motion behavior, and approved responsive layout. Realtime updates MUST NOT reserve empty inspector space on unrelated pages.

#### Scenario: Compact rail remains usable
- GIVEN the rail is compact and the connection changes state
- WHEN keyboard navigation is used
- THEN labels/tooltips and focus-visible behavior remain available

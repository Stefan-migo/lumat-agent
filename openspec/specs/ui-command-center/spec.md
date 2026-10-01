# UI Command Center Specification

## Purpose

Define the production-owned assistant workspace for the `chat` route: a centered conversation surface with progressive-disclosure navigation and context, durable conversation state, and narrow browser-verifiable interaction behavior.

## Requirements

### Requirement: CC-1 — Responsive Three-Zone Workspace

The command center MUST replace the three-zone desktop layout and zone tablist with one centered conversation column inside the existing shell. History SHALL be available through a popover and context through a closed-by-default drawer. At narrow widths, the column MUST reflow without clipping send, approval, retry, attachment, or planning actions.

#### Scenario: Desktop composition

- GIVEN an authorized user opens the `chat` route at 1024px or wider
- WHEN the Command Center renders
- THEN the three zones appear in left-to-right order and remain independently scannable

#### Scenario: Mobile zone selection

- GIVEN the route is rendered below 1024px
- WHEN the viewport is in either responsive tier
- THEN one zone is active, the user can switch zones, and send, approval, retry, and emergency actions remain reachable

### Requirement: CC-3 — Durable Conversation and Read-Only Context

The center MUST treat persisted messages, inline evidence, approval, and recovery as authoritative. Streaming MAY be transient but MUST NOT imply completion. The context drawer MUST remain read-only and show operational context only; it MUST be closed by default.

#### Scenario: Recoverable stream

- GIVEN an SSE or WebSocket stream disconnects before persistence completes
- WHEN the user reloads the thread
- THEN persisted history remains visible and the incomplete run is shown as recoverable, not successful

#### Scenario: Context does not execute tools

- GIVEN the context zone displays capabilities, plan, evidence, or run status
- WHEN a capability includes a writable tool
- THEN no context control executes it and approval remains the explicit action boundary

### Requirement: CC-5 — Thread-Scoped Ownership

Every thread-scoped route and action MUST verify that the authenticated user owns the thread or has authorized admin access before reading, renaming, deleting, sending, approving, or opening it.

#### Scenario: Foreign thread
- GIVEN an authenticated user addresses another user's thread identifier
- WHEN any thread-scoped route is requested
- THEN the server rejects the request without exposing thread data or performing the action

#### Scenario: Owned deep link
- GIVEN an authorized user opens `?thread_id=` for an owned thread
- WHEN the route loads
- THEN that thread is selected without creating another thread

### Requirement: CC-4 — Narrow Browser Verification

The change MUST provide narrow Playwright checks for zone order/presence, responsive visibility, keyboard access, and critical-action reachability. Screenshot baselines, PWA behavior, and CI integration are not part of this requirement.

#### Scenario: Geometry and breakpoint checks

- GIVEN a browser test runs at widths below 640px, 640–1023px, and at least 1024px
- WHEN the Command Center renders
- THEN the expected zone visibility and ordering invariants pass

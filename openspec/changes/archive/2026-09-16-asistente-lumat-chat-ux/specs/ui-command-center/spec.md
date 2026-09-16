# Delta for UI Command Center

## MODIFIED Requirements

### Requirement: CC-1 — Centered Conversation with Progressive Disclosure

The command center MUST replace the three-zone desktop layout and zone tablist with one centered conversation column inside the existing shell. History SHALL be available through a popover and context through a closed-by-default drawer. At narrow widths, the column MUST reflow without clipping send, approval, retry, attachment, or planning actions.
(Previously: the desktop surface rendered three persistent zones and narrow tiers selected one active zone.)

#### Scenario: Desktop composition
- GIVEN an authorized user opens `chat` at 1024px or wider
- WHEN the page renders
- THEN one readable centered conversation column is dominant, with `Historial` popover and closed `Contexto` drawer controls and no zone tablist

#### Scenario: Narrow reflow
- GIVEN the viewport is below 1024px
- WHEN the assistant renders
- THEN content remains usable in one column and all critical actions remain reachable without horizontal clipping

### Requirement: CC-3 — Durable Conversation and Read-Only Context

The center MUST treat persisted messages, inline evidence, approval, and recovery as authoritative. Streaming MAY be transient but MUST NOT imply completion. The context drawer MUST remain read-only and show operational context only; it MUST be closed by default.
(Previously: the right context zone was persistent and capabilities could be displayed there.)

#### Scenario: Recoverable stream
- GIVEN a stream disconnects before persistence completes
- WHEN the user reloads the thread
- THEN persisted history and recoverable state remain visible and no partial stream is treated as complete

#### Scenario: Context boundary
- GIVEN the user opens `Contexto`
- WHEN run or connection details render
- THEN no displayed context control executes a tool and approval remains the explicit action boundary

## ADDED Requirements

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

## Graph Check Consulted

Nodes: `AgentChat.tsx`, `domain/PanelShell.tsx`, `panelRoutes.ts`, `api.ts`, `chat.py`, `api/deps.py`. Edges: `AgentChat.tsx` → `panelRoutes.ts`/`api.ts`; `chat.py` → `api/deps.py`.

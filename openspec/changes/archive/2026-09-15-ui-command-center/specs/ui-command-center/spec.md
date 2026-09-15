# UI Command Center Specification

## Purpose

Define the production-owned assistant workspace for the `chat` route: a responsive three-zone surface with bounded navigation, durable conversation state, read-only execution context, focus mode, and narrow browser-verifiable interaction behavior.

## Requirements

### Requirement: CC-1 — Responsive Three-Zone Workspace

The Command Center MUST render production-owned left thread navigation, center assistant conversation, and right execution context at `>=1024px`. At `640–1023px` and `<640px`, it MUST select one active zone at a time without horizontal squeezing or clipping critical actions.

#### Scenario: Desktop composition

- GIVEN an authorized user opens the `chat` route at 1024px or wider
- WHEN the Command Center renders
- THEN the three zones appear in left-to-right order and remain independently scannable

#### Scenario: Mobile zone selection

- GIVEN the route is rendered below 1024px
- WHEN the viewport is in either responsive tier
- THEN one zone is active, the user can switch zones, and send, approval, retry, and emergency actions remain reachable

### Requirement: CC-2 — Focus Mode Contract

Focus mode MUST hide or minimize secondary shell regions while preserving the current route, an accessible name, keyboard operation, an escape path, and restoration of the prior shell visibility state.

#### Scenario: Keyboard entry and escape

- GIVEN a user activates focus mode with keyboard input
- WHEN focus mode opens and the user presses Escape
- THEN focus mode is announced, Escape exits it, and focus returns to the initiating control

#### Scenario: Resize restoration

- GIVEN focus mode is active and the viewport crosses a responsive tier
- WHEN focus mode closes
- THEN the prior navigation and zone visibility state is restored without losing the selected thread

### Requirement: CC-3 — Durable Conversation and Read-Only Context

The center MUST treat persisted messages and evidence as authoritative history. Streaming tokens MAY appear transiently during an active run but MUST NOT imply completion or replace persisted history. The right context zone MUST remain read-only; approval remains an explicit center action.

#### Scenario: Recoverable stream

- GIVEN an SSE or WebSocket stream disconnects before persistence completes
- WHEN the user reloads the thread
- THEN persisted history remains visible and the incomplete run is shown as recoverable, not successful

#### Scenario: Context does not execute tools

- GIVEN the context zone displays capabilities, plan, evidence, or run status
- WHEN a capability includes a writable tool
- THEN no context control executes it and approval remains the explicit action boundary

### Requirement: CC-4 — Narrow Browser Verification

The change MUST provide narrow Playwright checks for zone order/presence, responsive visibility, focus entry/escape/restoration, keyboard access, and critical-action reachability. Screenshot baselines, PWA behavior, and CI integration are not part of this requirement.

#### Scenario: Geometry and breakpoint checks

- GIVEN a browser test runs at widths below 640px, 640–1023px, and at least 1024px
- WHEN the Command Center renders
- THEN the expected zone visibility and ordering invariants pass

#### Scenario: Interaction checks

- GIVEN a browser test uses keyboard navigation and Escape
- WHEN it enters and exits focus mode
- THEN the focus and restoration contract passes without relying on hover

## Graph Check Consulted

Nodes: `AgentChat.tsx`, `domain/PanelShell.tsx`, `api.ts`, `chat.py`. Edges: `AgentChat.tsx` references `domain/PanelShell.tsx`; `api.ts` reaches `chat.py` through the recorded five-hop path.

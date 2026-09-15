# Delta for Panel Design System

## ADDED Requirements

### Requirement: DS-CC-1 — Command Center Responsive Zones

The production panel design system MUST define Command Center zones for thread navigation, assistant conversation, and execution context. At `>=1024px` they MUST render in that order; at `640–1023px` and `<640px`, the design MUST select one active zone and preserve usable overflow and critical actions.

#### Scenario: Desktop zone geometry

- GIVEN the Command Center is rendered at 1024px or wider
- WHEN layout is inspected in a real browser
- THEN all three named zones are present in left-to-right order without horizontal overflow

#### Scenario: Narrow tier behavior

- GIVEN the viewport is below 1024px
- WHEN a user switches the active zone
- THEN only the selected zone is primary and send, approval, retry, and emergency actions remain reachable

### Requirement: DS-CC-2 — Focus Visibility and Restoration

`PanelShell` MUST provide a reusable focus-mode and region-visibility contract with an accessible name, visible keyboard focus, Escape exit, and restoration of the prior route, selected thread, focus target, and shell visibility state.

#### Scenario: Focus mode keyboard contract

- GIVEN a user activates focus mode from a keyboard-operable control
- WHEN focus mode opens and Escape is pressed
- THEN secondary regions are minimized, an escape path remains available, and focus returns to the initiating control

#### Scenario: Responsive restoration

- GIVEN focus mode is active during a resize across a responsive tier
- WHEN it closes
- THEN the previous shell and zone visibility state is restored without losing selection

### Requirement: DS-CC-3 — Accessible, Production-Owned States

Command Center surfaces MUST use existing tokenized primitives and visible semantic labels for loading, streaming, disconnected, approval, error, and recovery states. The execution context MUST be read-only by default, and no quarantined prototype or phantom catalog entry MAY own production behavior.

#### Scenario: State semantics

- GIVEN a stream, disconnect, approval, or error state
- WHEN the surface renders
- THEN its status is visible, keyboard reachable, and exposed through the appropriate `status` or `alert` semantics

#### Scenario: Ownership boundary

- GIVEN a production story or route renders a Command Center surface
- WHEN its imports are inspected
- THEN it uses production components and API data rather than `InboxThread`, `ChatWithAgent`, or fabricated catalog entries

### Requirement: DS-CC-4 — Narrow Browser Contract

The design system MUST support narrow Playwright verification of zone presence/order, breakpoint visibility, focus behavior, keyboard access, and resolved token/layout invariants. Screenshot baselines, visual regression, CI integration, PWA behavior, and catalog completion are explicitly out of scope.

#### Scenario: Browser invariants

- GIVEN a Playwright run at `<640px`, `640–1023px`, and `>=1024px`
- WHEN the Command Center is inspected
- THEN the declared visibility, geometry, focus, and keyboard invariants are testable and pass

## Graph Check Consulted

Nodes: `domain/PanelShell.tsx`, `AgentChat.tsx`, `AppShell.tsx`, `types.ts`, `api.ts`. Edges: `AppShell.tsx` imports `domain/PanelShell.tsx`; `AgentChat.tsx` references `domain/PanelShell.tsx`.

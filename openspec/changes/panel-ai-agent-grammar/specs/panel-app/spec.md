# Delta for panel-app

## ADDED Requirements

### Requirement: PNL-APP-10 — Agent-App Shell Grammar

`PanelShell` and `AppShell` MUST present the panel as an agent application: a forest rail, brand, role-safe `NAVIGATION`, active-thread region, and compact/expanded rail states. Existing native History routing, `aria-current="page"`, drawer focus behavior, and operator filtering MUST remain unchanged.

#### Scenario: Role-safe compact rail
- GIVEN an operador renders `AppShell`
- WHEN `PanelShell` is compact
- THEN navigation remains keyboard reachable with labels/tooltips and admin-only `NAVIGATION` entries are absent

#### Scenario: History contract survives shell change
- GIVEN a user navigates through `AppShell` using `panelRoutes.ts`
- WHEN browser back, forward, deep-link, or an unknown path is exercised
- THEN the existing route and accessibility outcomes of PNL-APP-1 remain unchanged

### Requirement: PNL-APP-11 — Truthful Active-Thread Chrome

`PanelShell` MAY accept an optional `activeThreads` contract with explicit loading, empty, error, and placeholder states, but MUST NOT fetch conversations, call `listConversations()`, or fabricate customer/thread data. The structural region MUST be labeled `Conversaciones activas` when expanded and MAY be hidden in compact mode.

#### Scenario: No supplied data
- GIVEN `PanelShell` receives no active-thread data
- WHEN the expanded shell renders
- THEN a labeled truthful empty/placeholder state appears and no conversation request is made

#### Scenario: Supplied state matrix
- GIVEN the optional contract is loading, empty, or failed
- WHEN the rail renders
- THEN the matching visible state and `status`/`alert` semantics appear without shell-owned retry/fetch behavior

### Requirement: PNL-APP-12 — Conditional Conversation and Dense-Page Surfaces

Conversation routes MUST render `ConversationThread` and `ConversationsList` with directional bubbles/avatars, approved owner-status labels, handoff and reply-window presentation, retry/error affordances, and an optional inspector slot only when context exists. Dashboard, `ClientesList`, `ClientFicha` history, `CasesList`, `AgendaPage`, `AutomationRulesPage`, `Settings`, and `KbList` MUST retain their `DataTable`, KPI, `Badge`, filter, and `StateMessage` control-room primitives.

#### Scenario: Conversation detail states
- GIVEN `/panel/app/conversations/:id` renders a loaded thread
- WHEN messages, handoff, delivery failure, or a closed reply window are present
- THEN the DOM exposes direction, owner/status, handoff, retry, and disabled-reason semantics around the existing mutation behavior

#### Scenario: Inspector is conditional
- GIVEN a non-conversation dense page or a conversation without inspector context
- WHEN the page renders
- THEN no empty inspector column is reserved and dense control-room primitives remain present

#### Scenario: List chrome alignment
- GIVEN `ConversationsList` renders loading, empty, error, or rows
- WHEN its page chrome is inspected
- THEN its table/state behavior remains intact while header, filters, and selected-row treatment use the agent-app grammar

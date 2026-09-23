# Delta for Panel Design System

## MODIFIED Requirements

### Requirement: DS-GRAMMAR-1 — Agent-App Appearance, Control-Room Physiology

The production panel MUST apply the agent-app appearance to every production
surface, not only to conversation surfaces: shell chrome, page regions, visual
hierarchy, disclosure, status presentation, and interaction affordances MUST
follow one grammar across the panel. `PanelShell`, `ConversationThread`,
`ConversationsList`, and `AgentChat` expose that grammar through named DOM regions
for rail, active threads, bubbles, status/handoff, composer, and optional
inspector; their conversation-specific components — bubbles, composer shell,
thread rail, inspector — MUST NOT be imposed on non-conversation pages. Dense
content physiology is preserved: `Dashboard`, `ClientesList`, `ClientFicha`,
`CasesList`, `AgendaPage`, `AutomationRulesPage`, `Settings`, and `KbList` MUST
retain control-room `DataTable`, KPI, `Badge`, filter, and state primitives as
their data-presentation layer.
(Previously: only `PanelShell`, `ConversationThread`, `ConversationsList`, and
`AgentChat` exposed the agent-app grammar and dense pages were limited to
retaining control-room primitives; the app-wide appearance axis decided on
2026-09-04 was not restated, which narrowed the requirement to conversation
surfaces.)

#### Scenario: Grammar is structurally testable

- GIVEN a production surface renders on a conversation route and on a dense route
- WHEN production DOM is compared by semantic labels/classes and roles
- THEN both routes expose the same shared appearance regions for chrome,
  hierarchy, disclosure, and status, the conversation surfaces expose the agent
  regions (rail, bubbles, composer, inspector), and the dense routes retain
  control-room `DataTable`, KPI, `Badge`, filter, and state primitives as their
  data layer

#### Scenario: Dense pages do not adopt conversation components

- GIVEN `Dashboard`, `ClientesList`, `ClientFicha`, `CasesList`, `AgendaPage`,
  `AutomationRulesPage`, `Settings`, or `KbList` renders
- WHEN its component tree is inspected
- THEN no bubble, composer shell, thread rail, or inspector is rendered, and its
  data presentation remains tabular

#### Scenario: Appearance parity is verifiable across surfaces

- GIVEN a dense page and a conversation page render in the same session
- WHEN their chrome, region hierarchy, and status presentation are compared
- THEN they resolve through the same tokens and the same shared appearance
  contracts, with no surface left on browser-default control styling

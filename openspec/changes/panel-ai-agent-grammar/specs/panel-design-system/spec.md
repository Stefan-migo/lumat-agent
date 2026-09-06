# Delta for panel-design-system

## ADDED Requirements

### Requirement: DS-GRAMMAR-1 — Agent-App Appearance, Control-Room Physiology

The production panel MUST make `PanelShell`, `ConversationThread`, `ConversationsList`, and `AgentChat` expose the agent-app grammar through named DOM regions for rail, active threads, bubbles, status/handoff, composer, and optional inspector. `Dashboard`, `ClientesList`, `ClientFicha`, `CasesList`, `AgendaPage`, `AutomationRulesPage`, `Settings`, and `KbList` MUST retain control-room `DataTable`, KPI, `Badge`, filter, and state primitives.

#### Scenario: Grammar is structurally testable
- GIVEN the approved `AiAgentGrammar.stories.tsx` states are rendered
- WHEN production DOM is compared by semantic labels/classes and roles
- THEN conversation surfaces expose the agent regions while dense pages retain control-room primitives

### Requirement: DS-GRAMMAR-2 — Tokenized Shared Style Boundary

Grammar styles MUST be implemented in `web/src/components/primitives/primitives.css` or another existing tokenized stylesheet boundary, MUST reuse existing `tokens.css`/`--corp-*` roles before adding any token, MUST add no dependency, and MUST contain no hard-coded color values. `PanelShell` MUST NOT inject shell-owned `<style>` content.

#### Scenario: Source and DOM contract
- GIVEN the grammar is rendered by `PanelShell` or a production page
- WHEN source and computed stylesheet ownership are inspected
- THEN styles come from the shared stylesheet, colors resolve through `var(--*)`, and no injected shell style or new dependency exists

#### Scenario: Existing token validation
- GIVEN rail, bubble, inspector, activity, and composer states
- WHEN token drift/no-hex tests and Storybook states run
- THEN existing token values remain valid and any new semantic token is justified by a repeated consumer

### Requirement: DS-GRAMMAR-3 — Primitive Reuse and Accessibility

Grammar surfaces MUST reuse existing `Avatar`, `Badge`/`StatusBadge`, `Button`, `Textarea`, `DataTable`, `StateMessage`, and `EmptyState` primitives where their contracts apply; they MUST preserve visible labels, semantic `status`/`alert` roles, focus-visible behavior, reduced-motion behavior, and keyboard operation.

#### Scenario: Shared primitives are present
- GIVEN a conversation header, message, composer, or dense page state
- WHEN its component tree is inspected
- THEN the applicable existing primitive is rendered rather than a duplicate equivalent

#### Scenario: Accessibility and motion
- GIVEN expanded/compact, loading/error, and reduced-motion states at approved Storybook viewports
- WHEN keyboard and DOM assertions run
- THEN labels, roles, focus indicators, and no-essential-motion behavior remain verifiable without clipped critical actions

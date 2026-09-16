# Delta for Panel Design System

## MODIFIED Requirements

### Requirement: DS-CC-1 — Centered Assistant Surface

The assistant surface MUST use the existing light Lumat grammar: one centered readable conversation column, progressive-disclosure history popover, and context drawer closed by default. The zone tablist and persistent three-zone contract SHALL be removed without changing token values.
(Previously: the design system defined three desktop zones and narrow active-zone switching.)

#### Scenario: Disclosure and hierarchy
- GIVEN the assistant is rendered on desktop
- WHEN the user inspects the page
- THEN conversation is visually dominant, `Historial` opens history, `Contexto` opens operational detail, and no zone tablist is present

#### Scenario: Narrow assistant layout
- GIVEN the assistant is rendered below 1024px
- WHEN the user switches between history and context disclosures
- THEN the conversation remains primary and send, approval, retry, and attachment actions remain reachable without horizontal overflow

### Requirement: DS-CC-3 — Reusable Complete States and Localization

Assistant states MUST use existing primitives and semantic tokens for loading, empty, error, streaming, disabled, permission, approval, connection, and recovery. Product copy MUST be neutral Chilean Spanish and MUST NOT expose English labels or raw backend state values.
(Previously: states covered loading, streaming, disconnected, approval, error, and recovery but not the complete assistant state model or localization boundary.)

#### Scenario: State and language semantics
- GIVEN the assistant is loading, empty, streaming, disabled, denied, or failed
- WHEN the surface renders
- THEN a visible Spanish label and appropriate status/alert semantics explain the state and next action

#### Scenario: Production ownership
- GIVEN a production assistant story or route renders a state
- WHEN its imports and data are inspected
- THEN it uses production primitives and serializer-shaped data rather than quarantined prototypes or fabricated entries

## ADDED Requirements

### Requirement: DS-CC-5 — Accessibility and Primitive Reuse

The surface MUST reuse existing primitives and semantic tokens, add no dependency, and preserve token values. It SHALL support keyboard operation, visible focus, 200% zoom reflow, reduced motion, and non-color-only state communication. Every contrast pair the surface introduces or modifies SHALL meet the applicable WCAG 2.2 AA threshold.

Contrast of an inherited token pair is outside this change's authority: the change MAY NOT alter token values, so a pair whose ratio predates it cannot be remediated here. Such a pair SHALL be recorded with its computed ratio rather than silently dropped or silently tolerated.

#### Scenario: Keyboard and responsive accessibility
- GIVEN a user operates the assistant by keyboard, at 200% zoom, or with reduced motion enabled
- WHEN history, context, planning, composer, approval, or retry is used
- THEN focus remains visible and ordered, actions reflow without loss, and motion is reduced without removing meaning

#### Scenario: Contrast and semantics
- GIVEN a state or action the surface introduces or modifies is shown
- WHEN it is inspected or announced
- THEN its text and boundary contrasts meet the applicable WCAG 2.2 AA threshold, and accessible names plus status/alert semantics identify the action and result

#### Scenario: Inherited contrast debt is recorded, not hidden
- GIVEN the surface reuses a token pair whose contrast ratio predates this change and whose token value this change may not alter
- WHEN contrast is verified
- THEN the pair is listed with its computed ratio and threshold in `contrast-verification.md`, and it is attributed to a design-system change rather than to this one

## Graph Check Consulted

Nodes: `tokens.css`, `Button.tsx`, `Dialog.tsx`, `Popover.tsx`, `Textarea.tsx`, `StatusBadge.tsx`, `AgentChat.tsx`. Edges: `AgentChat.tsx` → primitive components/tokens; `DESIGN_SYSTEM.md` → accessibility/localization contracts.

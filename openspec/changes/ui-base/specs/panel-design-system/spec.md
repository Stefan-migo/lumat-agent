# Delta for Panel Design System

## ADDED Requirements

### Requirement: DS-SHELL-7 — Real Storybook Shell Harness
Storybook MUST apply shared `withPanelShell` context and `primitives.css` to every story.
#### Scenario: Production
- GIVEN a story
- WHEN rendered
- THEN both apply
#### Scenario: Shared
- GIVEN stories
- WHEN preview is inspected
- THEN no local shell or duplicate import

### Requirement: DS-DOC-1 — Platform-First Interaction Policy
`DESIGN_SYSTEM.md` MUST record platform-first popover/CSS anchors/native dialog; Radix only for menu/combobox ARIA composites; package names; and line-480 justification.
#### Scenario: Documented
- GIVEN the document
- WHEN read
- THEN defaults, scope, packages, justification appear
#### Scenario: Platform
- GIVEN a platform-covered interaction
- WHEN reviewed
- THEN platform precedes Radix

## MODIFIED Requirements

### Requirement: DS-STORY-7 — Viewports Aligned to Breakpoints
Presets MUST align to `--bp-*`: 640px, 1024px, and 1280px. A test MUST detect drift without excluding other widths.
(Previously: no drift test existed.)
#### Scenario: Presets
- GIVEN the toolbar
- WHEN selected
- THEN preset matches `--bp-*`
#### Scenario: Drift rejected
- GIVEN a preset or token changes
- WHEN tested
- THEN drift fails; 390px and 768px remain permitted

### Requirement: R-PRD-PG-1 — Page Stories
CSF page stories MUST exist at `web/src/stories/pages/*.stories.tsx` for Dashboard, Clientes list/ficha, Conversations list/thread, Cases, KB, Settings, and Login, composed from shared patterns. The page-story restriction applies only to `web/src/stories/pages/**`; harness, primitive, and closure work MAY modify components. Triage MUST delete `concept/AiAgentGrammar`, quarantine `pages/ChatWithAgent`, and document `pages/InboxThread`.
(Previously: immutability covered the whole change.)
#### Scenario: Glob
- GIVEN `main.ts`
- WHEN reviewed
- THEN the glob is unchanged
#### Scenario: Scope
- GIVEN page-story-only diff
- WHEN reviewed
- THEN no component changes
#### Scenario: Triage
- GIVEN targeted stories
- WHEN inspected
- THEN grammar absent, ChatWithAgent quarantined, InboxThread disposed

### Requirement: R-PRD-PG-2 — Production Helper Boundary (Slice 2)
The helper closure MUST include EmptyState, DataTable, PageHeader, StatCard, PageFrame, StateMessage, and toneMaps under components. Production pages MUST import components, not stories. The boundary test MUST permit only two compatibility tests to import wrappers.
(Previously: compatibility-test scope was undefined.)
#### Scenario: Component imports
- GIVEN production imports a helper
- WHEN scanned
- THEN it resolves from components
#### Scenario: Compatibility
- GIVEN a story imports a wrapper
- WHEN the suite runs
- THEN its contract remains
#### Scenario: Boundary
- GIVEN either compatibility test imports a wrapper
- WHEN tested
- THEN it passes; production imports fail
#### Scenario: Closure
- GIVEN production uses a closure helper
- WHEN inspected
- THEN it is in the closure

### Requirement: DS-VER-1 — Web Verification Gates
The change MUST keep `npm test` green, including token-drift/no-hex checks, and `npm run build-storybook` green. It MUST NOT modify `app/`, `db/`, or `infra/`; it MAY modify only the listed web files and directories: preview, components, stories, `DESIGN_SYSTEM.md`, and `package.json`.
(Previously: component code was prohibited.)
#### Scenario: Tests
- GIVEN the change
- WHEN `npm test` runs
- THEN all tests pass, including drift
#### Scenario: Build
- GIVEN the change
- WHEN built
- THEN Storybook succeeds
#### Scenario: Boundaries
- GIVEN the diff
- WHEN reviewed
- THEN approved web files changed; backend unchanged

# Delta: Panel Shell AI-Agent Infrastructure

## MODIFIED Requirements

### Requirement: PNL-APP-1 — D7 URL Routing Without a Router (Slice 1)

The SPA MUST use a small typed native History API route table in AppShell, MUST NOT add a router dependency, and MUST synchronize the nine top-level views plus `/panel/app/clients/:id` and `/panel/app/conversations/:id`. Navigation MUST use clean links or equivalent controls with `aria-current="page"`; hash navigation MUST NOT be used.
(Previously: AppShell used state-only routing, drill-down callbacks, and treated URL shareability as a non-goal.)

#### Scenario: View navigation updates URL
- GIVEN an authenticated user at `/panel/app/`
- WHEN they activate Clients
- THEN the Clients view renders and the URL is `/panel/app/clients`
- AND its navigation item has `aria-current="page"`

#### Scenario: Deep link and refresh
- GIVEN a valid client or conversation drill-down URL
- WHEN the SPA loads or refreshes at that URL
- THEN the authenticated shell renders the matching detail view

#### Scenario: Back, forward, and unknown paths
- GIVEN navigation has produced multiple valid history entries
- WHEN the user uses browser back/forward or opens an unknown `/panel/app/*` path
- THEN the matching prior view renders, or the unknown path safely falls back to `/panel/app/`

#### Scenario: Role-safe admin deep link
- GIVEN an operador opens a KB or Settings deep link
- WHEN the view loads and the API returns 403
- THEN the permission-denied state renders and the shell does not crash or bypass authorization

### Requirement: R-PRD-PG-2 — Production Helper Boundary (Slice 2)

The production helper closure MUST be available under `web/src/components/`, including EmptyState, DataTable, PageHeader, StatCard, PageFrame, StateMessage, and toneMaps. Production pages MUST import that closure from components; story wrappers MAY preserve existing story exports, but production code MUST NOT depend on story infrastructure.
(Previously: helpers were defined in `stories/pages/_shared/`, and component imports from that directory were permitted.)

#### Scenario: Production imports use components
- GIVEN a production page imports a shared helper
- WHEN imports are scanned
- THEN the helper resolves from `web/src/components/`, not `stories/pages/_shared/`

#### Scenario: Story compatibility remains
- GIVEN an existing story imports a shared helper or wrapper export
- WHEN the story suite runs
- THEN the export remains available and renders the same contract

#### Scenario: Closure is complete
- GIVEN production pages use PageFrame, StateMessage, or toneMaps
- WHEN the boundary test inspects dependencies
- THEN those dependencies are promoted alongside the four named helpers

### Requirement: DS-SHELL-3 — Tokenized Shell Styles Without Injection (Slice 2)

Shell layout, navigation, drawer, focus, motion, and responsive styles MUST consume `--corp-*` or existing design tokens, MUST contain no hard-coded hex values, and MUST be loaded through the tokenized stylesheet boundary. PanelShell MUST NOT inject the former `PANEL_SHELL_STYLES` `<style>` block. Existing visual, responsive, focus, collapse, drawer, and reduced-motion behavior MUST remain unchanged.
(Previously: the injected `PANEL_SHELL_STYLES` block was the shell style boundary and was only required to be hex-free.)

#### Scenario: Stylesheet boundary is tokenized
- GIVEN PanelShell is rendered
- WHEN its DOM and source are inspected
- THEN no shell-owned injected `<style>` exists and all shell values resolve through tokens

#### Scenario: Accessibility behavior is preserved
- GIVEN desktop, mobile, expanded, collapsed, and reduced-motion states
- WHEN navigation and drawer interactions are tested
- THEN focus, roles, keyboard behavior, responsive collapse, and motion preferences remain valid

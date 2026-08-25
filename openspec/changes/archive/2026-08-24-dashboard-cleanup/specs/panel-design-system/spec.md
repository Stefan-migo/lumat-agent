# Delta for panel-design-system

## ADDED Requirements

### Requirement: DS-DASH-1 — Dashboard Data Roles Resolve Through var(--corp-value)

Dashboard story data roles (KPI values, activity times, comparable numbers) MUST resolve `font-variant-numeric` through `var(--corp-value)` and MUST NOT use literal `tabular-nums` (extends DS-TKN-11/CST-ALIAS-5 to the dashboard story).

#### Scenario: KPI values use the contract token

- GIVEN the dashboard story KPI cards
- WHEN the `.kpi__value` renders
- THEN tabular-nums comes from `var(--corp-value)` (primitives rule), with no literal inline override

#### Scenario: Activity times use the contract token

- GIVEN `.dashboard-activity__time`
- WHEN rendered
- THEN `font-variant-numeric` is `var(--corp-value)`, not the literal

### Requirement: DS-DASH-2 — Dashboard Story and Tests Derive from Mock Data

The dashboard story MUST render KPI cards from the `kpis` mock export, and the story tests MUST derive assertions from the same `kpis`/`activity` sources (no hardcoded literals).

#### Scenario: Story renders from mock

- GIVEN the dashboard story
- WHEN KPI cards render
- THEN label/value/delta come from the `kpis` mock export

#### Scenario: Tests derive from mock

- GIVEN the dashboard story test
- WHEN KPI assertions run
- THEN they read from `kpis` (and activity rows from `activity`), so a mock change updates both story and test together

## MODIFIED Requirements

### Requirement: DS-STORY-2 — Description and Usage Guidance

(Previously: the AppShell/entry docs described the shell with inaccurate color claims. The port re-targeted copy to --corp-*; this delta extends the scenario set.)

#### Scenario: Entry docs match the shell

- GIVEN the PanelEntry story docs after slice-3
- WHEN the shell description is read
- THEN it states the sidebar brand is dark green (`--corp-primary`) and the panel header is white (`--corp-surface`), same height — no "same color" claim

## Non-Goals

- KbList.stories.tsx literal tabular-nums (follow-up).
- Remaining Corporate components; optional count-up/fade-content; icon library; dark mode; Jinja migration.
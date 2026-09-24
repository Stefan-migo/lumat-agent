# Agenda Calendar UI Specification

## Purpose

Provide operators a calendar-navigated, chronological, responsive view of local visits and calendar-sync state.

## Requirements

### Requirement: AG-UI-1 — Agenda Route, Calendar Navigation, and Register Sections

The SPA MUST expose operator-visible `Agenda` at `/panel/app/agenda` through native History API routing. It MUST render a calendar with a month view and a week view over the request timezone, and MUST NOT present days outside the visible month or week as agenda days.

The register MUST render chronological `Hoy` and `Próximas` sections in the request timezone when the visible calendar window contains today. When the visible window does not contain today and no day is selected, the register MUST present the window's visits in a single `Visitas del período` section. When the operator selects a day, the register MUST filter to that day and present it as a single dated section; clearing the selection MUST restore the window's section behavior.

The agenda MUST NOT render availability blocks or create/edit/rebook controls.

#### Scenario: Operator opens agenda
- GIVEN an authenticated operador
- WHEN they activate Agenda
- THEN the route renders with `aria-current="page"`
- AND the calendar opens on the current month in the request timezone

#### Scenario: Navigate the calendar window
- GIVEN an authenticated operador viewing the agenda
- WHEN they move the calendar to another month or week
- THEN the register reflects that window's visits in the request timezone

#### Scenario: Select a day
- GIVEN the calendar is showing a month or a week
- WHEN the operator selects a day
- THEN the register shows only that day's visits as a single dated section

#### Scenario: Clear the day selection
- GIVEN a day is selected
- WHEN the operator clears the selection
- THEN the register returns to the window's `Hoy`/`Próximas` or `Visitas del período` behavior

#### Scenario: No days outside the visible window
- GIVEN the calendar is showing a month that does not fill whole weeks
- WHEN the grid renders
- THEN days outside that month appear as empty cells and are not selectable agenda days

### Requirement: AG-UI-2 — Complete Table State Contract

The agenda MUST represent loading, empty, error, permission, and stale states with visible labeled feedback and recovery. The calendar and the register MUST share that state contract: a period with no visits is an explicit empty state, not a bare grid. The agenda MUST use semantic table/list markup, keyboard-operable focused actions, and an unclipped mobile layout.

#### Scenario: State matrix
- GIVEN loading, empty, failed, forbidden, or stale data
- WHEN the page renders
- THEN the matching labeled state and applicable retry/refresh appear

### Requirement: AG-UI-3 — Authorized Cancellation

The agenda MAY show cancellation only for `booked` appointments. It MUST require confirmation and a reason, use the existing action, show success/actionable failure, and refresh after completion. It MUST NOT offer creation, editing, or rebooking.

#### Scenario: Cancel booked visit
- GIVEN an authorized user selects a booked appointment
- WHEN they confirm with an optional reason
- THEN cancellation is audited and the refreshed row shows `cancelled`

#### Scenario: Non-booked visit
- GIVEN status is `completed`, `no_show`, or `cancelled`
- WHEN the row renders
- THEN cancellation is unavailable and no request is issued

### Requirement: AG-UI-4 — Sync Retry and Storybook Coverage

The agenda MUST show separate lifecycle/sync badges, offer `Retry calendar` only for `pending`/`failed`, refresh after retry, and provide Storybook coverage for data, loading, empty, error, permission, stale, cancel-confirmation, sync-failure/retry, keyboard, mobile, month and week calendar views, a selected day, and an empty period.

#### Scenario: Retry calendar sync
- GIVEN sync is `pending` or `failed`
- WHEN the user activates `Retry calendar`
- THEN the existing action runs and the agenda refreshes with its state

#### Scenario: Independent failure labels
- GIVEN a booked appointment with failed provider sync
- WHEN its row renders
- THEN booked, failed, and retry remain separately visible

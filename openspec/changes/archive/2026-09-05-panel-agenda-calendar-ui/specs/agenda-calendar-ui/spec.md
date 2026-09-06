# Agenda Calendar UI Specification

## Purpose

Provide operators a chronological, responsive view of local visits and calendar-sync state.

## Requirements

### Requirement: AG-UI-1 — Agenda Route and Sections

The SPA MUST expose operator-visible `Agenda` at `/panel/app/agenda` through native History API routing. It MUST render chronological `Hoy` and `Próximas` sections in the request timezone, and MUST NOT render month grids, availability blocks, or create/edit/rebook controls.

#### Scenario: Operator opens agenda
- GIVEN an authenticated operador
- WHEN they activate Agenda
- THEN the route renders with `aria-current="page"`

### Requirement: AG-UI-2 — Complete Table State Contract

The agenda MUST represent loading, empty, error, permission, and stale states with visible labeled feedback and recovery. It MUST use semantic table/list markup, keyboard-operable focused actions, and an unclipped mobile layout.

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

The agenda MUST show separate lifecycle/sync badges, offer `Retry calendar` only for `pending`/`failed`, refresh after retry, and provide Storybook coverage for data, loading, empty, error, permission, stale, cancel-confirmation, sync-failure/retry, keyboard, and mobile states.

#### Scenario: Retry calendar sync
- GIVEN sync is `pending` or `failed`
- WHEN the user activates `Retry calendar`
- THEN the existing action runs and the agenda refreshes with its state

#### Scenario: Independent failure labels
- GIVEN a booked appointment with failed provider sync
- WHEN its row renders
- THEN booked, failed, and retry remain separately visible

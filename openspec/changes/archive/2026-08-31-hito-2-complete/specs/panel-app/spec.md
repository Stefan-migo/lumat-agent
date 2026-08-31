# Delta for panel-app

## MODIFIED Requirements

### Requirement: PNL-APP-7 — Production conversations

`ConversationsListView` MUST consume the filtered production list, show state/assignee/window and refresh after commands; each row MUST open a thread that loads current messages and outbound delivery states. (Previously: unfiltered read-only list and thread.)

#### Scenario: List and thread
- GIVEN an authenticated operator
- WHEN the list and a row are loaded
- THEN production fields and chronological current messages render

#### Scenario: Refresh after command
- GIVEN a successful take/reply/close command
- WHEN the command completes
- THEN list and thread refresh, while loading/error states remain actionable

## ADDED Requirements

### Requirement: PNL-APP-9 — Composer and permissions

The SPA MUST expose take/return/close and a text composer with typed API contracts; it MUST show loading, disabled, policy, failed-delivery/retry, 401, 403, and conflict states without optimistic state corruption. Archived Storybook UI remains a dependency, not reimplementation.

#### Scenario: Window and permission states
- GIVEN stale-window, anonymous, or forbidden responses
- WHEN the thread renders or submits
- THEN the composer is disabled or a specific permission/policy state is shown

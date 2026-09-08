# Delta for notification-center

## ADDED Requirements

### Requirement: NC-4 — Header Notification Affordance

The authenticated shell MUST expose a header bell linked to the existing notification center and MUST derive its unread badge from the existing notification API. It MUST fetch on mount and mark items read through the existing API; it MUST NOT invent realtime polling, push events, or fabricated counts. Loading, zero, and API-error states MUST be truthful and accessible.

#### Scenario: Mount and mark read
- GIVEN an authenticated user opens the shell with unread notifications
- WHEN the header mounts and the user opens/reads the center
- THEN the badge reflects the API result and the existing mark-read call is made.

#### Scenario: Empty or failed source
- GIVEN the unread request returns zero or an error
- WHEN the bell renders
- THEN zero/unknown state is shown accessibly, with no fabricated number and no realtime request.

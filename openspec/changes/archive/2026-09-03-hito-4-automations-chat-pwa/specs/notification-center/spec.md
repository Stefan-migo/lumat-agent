# Notification Center Specification

## Purpose

Give authorized panel users a durable, filterable view of user-facing notifications and browser push availability.

## Requirements

### Requirement: NC-1 — Notification Read Model

The system MUST expose authenticated notifications with recipient, title/content, source, channel/status, timestamps, and read state; users MUST be able to mark an item read without changing delivery history.

#### Scenario: List and read

- GIVEN an authenticated authorized panel user with notifications
- WHEN they list and mark one notification read
- THEN the item is returned with read state and its delivery attempts remain unchanged

#### Scenario: Unauthorized access

- GIVEN an unauthenticated or unauthorized user
- WHEN they request another user's notification center
- THEN the server returns an authorization error and changes nothing

### Requirement: NC-2 — Filters and Ordering

The notification center MUST support bounded filtering by read state, status, and source, and MUST order results by newest notification first.

#### Scenario: Filter unread failures

- GIVEN notifications with different read states and statuses
- WHEN the user filters unread failed items
- THEN only matching items are returned in descending creation order

### Requirement: NC-3 — Push With Fallback

The system MAY deliver supported notifications by browser push, but MUST retain WhatsApp/SMTP policy-aware fallback and MUST record push success or failure in the same audit trail. Unsupported or denied browsers MUST receive a clear fallback state.

#### Scenario: Push unavailable

- GIVEN a browser or permission state that does not support push
- WHEN a notification is delivered
- THEN the center remains available and the configured fallback path is used

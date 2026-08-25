# Delta for admin-panel

## ADDED Requirements

### Requirement: AP-9 — Conversations List Endpoint

The system MUST expose `GET /panel/api/conversations` returning `{"conversations": [...]}` where each item is `to_conversation_dict(conversation)` — read-only (no assignee/responsible field, no reply/state mutation, no migration of existing conversations), following the JSON API router conventions in `app/panel/api/routes/conversations.py` (`require_user_json`, JSON 401/403, same-origin cookie, no redirects, no CORS). Rows MUST be ordered by most recent activity first (`last_message_at` DESC NULLS LAST, then `id` DESC). No pagination in this change (ponytail: add a cap only if the inbox grows).

#### Scenario: List returns serialized conversations

- GIVEN an authenticated user
- WHEN they request `GET /panel/api/conversations`
- THEN the response is 200 with `{"conversations": [...]}` and every item matches the `to_conversation_dict` shape (snake_case, ISO dates, nullable timestamps)

#### Scenario: Read-only, no assignee

- GIVEN the response payload
- WHEN it is inspected
- THEN no assignee/responsible field appears and no mutation endpoint is added

#### Scenario: Most recent first

- GIVEN conversations with different `last_message_at` values
- WHEN the list is requested
- THEN conversations with the most recent activity sort first (nulls last, `id` tiebreak)

#### Scenario: Anonymous rejected

- GIVEN no session cookie
- WHEN the endpoint is requested
- THEN it returns JSON 401 `{"detail": ...}` with no redirect

#### Scenario: Backend tests cover the endpoint

- GIVEN the applied change
- WHEN `pytest` runs against the functional suite
- THEN tests cover the response shape, ordering, and the 401 case

## Non-Goals

- Assignee/responsible column on conversations; reply/state mutation endpoints (HH-5); pagination; migration of existing conversation rows.
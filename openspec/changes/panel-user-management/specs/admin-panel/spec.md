# Delta for admin-panel

## ADDED Requirements

### Requirement: USR-API-1 — Safe User Listing

The panel MUST expose `GET /panel/api/users` to authenticated admins only. It MUST return users ordered by username and then id, with only `id`, `username`, `role`, and `active`. It MUST NOT serialize `password_hash`, `failed_logins`, or `locked_until`.

#### Scenario: Admin receives safe list (pytest)
- GIVEN an authenticated admin and users with all three roles
- WHEN `GET /panel/api/users` is requested
- THEN the response is 200, ordered by username then id, and each row has only the allow-listed fields

#### Scenario: Operational credential fields are absent (pytest)
- GIVEN a user with a password hash, failed logins, and a lock timestamp
- WHEN an admin lists users
- THEN none of those fields appears in the response body

### Requirement: USR-API-2 — User Creation

The panel MUST expose `POST /panel/api/users` for admins to create a user from `username`, `password`, and `role`. Username MUST be non-empty and unique, password MUST be at least 8 characters, and role MUST be `admin`, `operador`, or `tecnico`. Successful creation MUST return the safe user shape, hash the password, and record an audit event with the acting admin as actor.

#### Scenario: Valid user creation (pytest)
- GIVEN an authenticated admin and a unique username, password of at least 8 characters, and valid role
- WHEN the create endpoint is submitted
- THEN the user is created with a password hash, the safe shape is returned, and a create audit is recorded

#### Scenario: Invalid or duplicate input (pytest)
- GIVEN an authenticated admin
- WHEN username is blank, password is shorter than 8 characters, role is invalid, or username already exists
- THEN the API returns a validation/conflict error and creates no user

### Requirement: USR-API-3 — Active Status Toggle

The panel MUST expose `POST /panel/api/users/{id}/toggle-active` for admins to flip a target user’s `active` status. An admin MUST NOT toggle their own account. Every successful toggle MUST record an audit event identifying the acting admin, target user, and resulting status.

#### Scenario: Admin toggles another user (pytest)
- GIVEN an authenticated admin targeting another existing user
- WHEN the toggle endpoint is submitted
- THEN `active` is flipped, the safe user shape is returned, and a toggle audit is recorded

#### Scenario: Admin cannot deactivate self (pytest)
- GIVEN an authenticated admin targeting their own user id
- WHEN the toggle endpoint is submitted
- THEN the API returns JSON 403 and the account remains unchanged

### Requirement: USR-API-4 — Password Reset

The panel MUST expose `POST /panel/api/users/{id}/reset-password` for admins to set another user’s password. The replacement password MUST be at least 8 characters, MUST be stored as a hash, and MUST never be returned. An admin MUST NOT reset their own password. Successful resets MUST record an audit event with the acting admin as actor.

#### Scenario: Admin resets another password (pytest)
- GIVEN an authenticated admin targeting another existing user and a password of at least 8 characters
- WHEN the reset endpoint is submitted
- THEN the password hash changes, the plaintext is absent from the response, and a reset audit is recorded

#### Scenario: Self-reset and short password are rejected (pytest)
- GIVEN an authenticated admin
- WHEN they reset their own password or submit fewer than 8 characters
- THEN the API returns 403 or a validation error and does not change the password

### Requirement: USR-API-5 — Admin JSON Authorization

All user-management routes MUST use the existing admin JSON authorization contract. Anonymous requests MUST receive JSON 401; authenticated `operador` and `tecnico` requests MUST receive JSON 403; denied requests MUST not change state or reveal user data.

#### Scenario: Authorization matrix (pytest)
- GIVEN no session, an operador session, or a tecnico session
- WHEN any user-management route is requested
- THEN it returns JSON 401, JSON 403, or JSON 403 respectively, without performing the operation

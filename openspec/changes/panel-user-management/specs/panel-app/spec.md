# Delta for panel-app

## ADDED Requirements

### Requirement: USR-UI-1 — Admin User View and Navigation

The SPA MUST provide an admin-only `Usuarios` view wired through the existing `PanelShell` navigation, `AppShell` view switch, and `panelRoutes` path mapping. Non-admin users MUST NOT see or reach the view.

#### Scenario: Admin navigation (vitest)
- GIVEN an authenticated admin
- WHEN the panel shell renders and `Usuarios` is selected
- THEN the navigation item is visible and the user-management page renders at its mapped panel route

#### Scenario: Non-admin navigation is filtered (vitest)
- GIVEN an authenticated operador or tecnico
- WHEN the panel shell renders or the user route is opened
- THEN `Usuarios` is absent and the view is denied without user data

### Requirement: USR-UI-2 — User List Presentation

The user-management page MUST load and render username, role, and active status for each user, including all supported roles. Role labels MUST be `Administrador`, `Operador`, and `Técnico`; the `tecnico` value MUST never display as an untranslated technical identifier.

#### Scenario: Render roles and status (vitest)
- GIVEN a successful list response containing admin, operador, and tecnico users
- WHEN the page renders
- THEN each username, translated role label, and active/inactive status is visible

#### Scenario: Safe list shape is respected (vitest)
- GIVEN list data without credential or lockout fields
- WHEN the rows render
- THEN the page renders normally and does not require or display sensitive fields

### Requirement: USR-UI-3 — Create User Flow

The page MUST provide username, password, and role controls. It MUST prevent submission of blank usernames or passwords shorter than 8 characters, submit valid data, refresh or update the list on success, and present API validation/conflict errors without losing entered non-password context.

#### Scenario: Successful creation (vitest)
- GIVEN valid username, password of at least 8 characters, and selected role
- WHEN the create form is submitted
- THEN a create request is made and the new safe user row becomes visible

#### Scenario: Client and API validation errors (vitest)
- GIVEN invalid form data or a duplicate username response
- WHEN submission is attempted
- THEN an accessible error is shown and no successful-user state is presented

### Requirement: USR-UI-4 — Active Toggle and Password Reset

The page MUST offer active-status toggling and password reset for other users. Controls for the current admin’s row MUST be disabled. Toggle and reset actions MUST expose pending, success, and error outcomes; reset MUST confirm before submission and MUST NOT display a password.

#### Scenario: Manage another user (vitest)
- GIVEN an admin viewing another user
- WHEN the admin confirms a toggle or password reset
- THEN the corresponding request is sent, pending state is visible, and success updates the row or reports completion

#### Scenario: Self-protection in the UI (vitest)
- GIVEN the current admin appears in the list
- WHEN their row renders
- THEN toggle and reset controls are disabled and cannot initiate a request

### Requirement: USR-UI-5 — User View State Matrix

The view MUST represent loading, empty, API error, and denied states with accessible existing panel state primitives, without fabricated rows. It MUST preserve actionable error messaging when mutations fail.

#### Scenario: List state matrix (vitest)
- GIVEN the list is loading, empty, failed, or forbidden
- WHEN the page renders
- THEN the matching loading, empty, error, or denied state is visible and no user rows are fabricated

# Delta for panel-app

## MODIFIED Requirements

### Requirement: PNL-APP-1 — D7 URL Routing Without a Router (Slice 1)

The SPA MUST use the typed native History API route table, MUST NOT add a router dependency, and MUST expose exactly eight navigation destinations: Panel unificado, Asistente Lumat, Conversaciones, Clientes, Agenda, Base de Conocimientos, Automatizaciones, and Configuración. Notifications, push, and advanced-dashboard MUST NOT be visible navigation items. `/panel/app/cases` and `/panel/app/advanced-dashboard` MUST still resolve as compatibility routes.
(Previously: nine top-level views, including notifications, push, and advanced-dashboard, were synchronized by the navigation contract.)

#### Scenario: Approved IA and active URL
- GIVEN an authenticated user at `/panel/app/`
- WHEN they activate Conversaciones
- THEN the view renders at `/panel/app/conversations` with `aria-current="page"`
- AND only the eight approved destinations appear in navigation.

#### Scenario: Compatibility deep links
- GIVEN a user opens `/panel/app/cases` or `/panel/app/advanced-dashboard`
- WHEN the SPA parses the path or refreshes
- THEN the existing compatible view resolves without a router or data-model migration.

#### Scenario: History and authorization remain safe
- GIVEN valid history entries or an operador opening an admin-only deep link
- WHEN back/forward or the API authorization check runs
- THEN the prior view or permission-denied state renders without a crash or bypass.

### Requirement: PNL-APP-10 — Agent-App Shell Grammar

`PanelShell` and `AppShell` MUST retain the forest rail, brand, role-safe navigation, active-thread region, compact/expanded states, native History routing, `aria-current`, and drawer focus behavior. The header MUST expose notification-bell and avatar affordances; identity/logout MUST remain available from the avatar affordance.
(Previously: the shell grammar had a text-only header and user block in the sidebar.)

#### Scenario: Header actions are usable
- GIVEN an authenticated user renders the shell
- WHEN the header is inspected and keyboard operated
- THEN bell and avatar controls have accessible names, visible focus, and usable destinations/actions.

#### Scenario: Compact rail remains role-safe
- GIVEN an operador renders a compact shell
- WHEN navigation is keyboard traversed
- THEN labels/tooltips remain available and admin-only entries remain absent.

## ADDED Requirements

### Requirement: PNL-APP-21 — Conversations and Cases Segment

The Conversations destination MUST provide a `Conversaciones|Casos` segment. Cases MUST retain its existing page semantics and API ownership; `/panel/app/cases` MUST remain an alias.

#### Scenario: Segment switches surface
- GIVEN an authenticated user on Conversations
- WHEN they select Casos
- THEN CasesList renders in the shared destination and the selected segment is exposed accessibly.

### Requirement: PNL-APP-22 — Settings Push Composition

Configuración MUST include the existing PushSettings surface as a section without deleting its permission, unsupported, or fallback states; push MUST NOT be a top-level navigation destination.

#### Scenario: Push settings remain functional
- GIVEN an authorized user opens Configuración
- WHEN the push section is rendered
- THEN existing browser permission actions and states remain available.

#### Scenario: PWA boundary preserved
- GIVEN shell routes change
- WHEN PWA registration and cache rules are exercised
- THEN scope remains `/panel/app/` and API/HTML exclusions remain unchanged.

### Requirement: PNL-APP-23 — Skeleton Verification Gates

The skeleton MUST preserve existing page-body, API, data-model, and PWA contracts; acceptance MUST include green backend and web suites.

#### Scenario: Required suites pass
- GIVEN the completed skeleton change
- WHEN `uv run pytest tests/` and `cd web && npx vitest run` execute
- THEN both suites pass without changing page-body or backend contracts.

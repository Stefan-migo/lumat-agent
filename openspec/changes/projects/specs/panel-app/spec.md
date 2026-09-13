# Delta for panel-app

## MODIFIED Requirements

### Requirement: PNL-APP-1 — D7 URL Routing Without a Router (Slice 1)

The SPA MUST use the typed native History API route table, MUST NOT add a router dependency, and MUST expose exactly nine navigation destinations: Panel unificado, Asistente Lumat, Conversaciones, Clientes, Agenda, Base de Conocimientos, Automatizaciones, Configuración, and Proyectos. Notifications, push, and advanced-dashboard MUST NOT be visible navigation items. `/panel/app/cases` and `/panel/app/advanced-dashboard` MUST still resolve as compatibility routes.
(Previously: the navigation contract exposed exactly eight approved destinations and had no Proyectos destination.)

#### Scenario: Projects navigation
- GIVEN an authenticated user at `/panel/app/`
- WHEN they activate Proyectos
- THEN the view renders at `/panel/app/projects` with `aria-current="page"`

#### Scenario: Compatibility deep links
- GIVEN a user opens `/panel/app/cases` or `/panel/app/advanced-dashboard`
- WHEN the SPA parses the path or refreshes
- THEN the existing compatible view resolves without a router or data-model migration

#### Scenario: History and authorization remain safe
- GIVEN valid history entries or an operador opening an admin-only deep link
- WHEN back/forward or the API authorization check runs
- THEN the prior view or permission-denied state renders without a crash or bypass

## ADDED Requirements

### Requirement: PNL-APP-27 — Read-only project SDB browse

The panel MUST provide authenticated read-only list and detail endpoints and UI at `/panel/app/projects`, navigating list → detail. Detail MUST show only typed `sdb:*` artifacts, including cross-thread grouping where applicable, and MUST exclude WhatsApp conversations. The panel MUST NOT expose project CRUD or mutation endpoints.

#### Scenario: Project detail contents
- GIVEN an authorized user selects a project
- WHEN the detail view loads
- THEN only its typed SDB artifacts are shown, grouped by entity, with no WhatsApp conversation rows

#### Scenario: Read-only boundary
- GIVEN a user attempts project create, rename, archive, or merge through panel routes
- WHEN the request is made
- THEN no CRUD endpoint exists and no registry mutation occurs

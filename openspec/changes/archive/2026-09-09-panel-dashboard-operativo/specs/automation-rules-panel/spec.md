# Delta for automation-rules-panel

## MODIFIED Requirements

### Requirement: ARP-1 — Rule List and Detail Surface

The SPA MUST keep the automation-rules route and detail surface available to admins, but MUST mark the navigation entry `adminOnly: true` and omit it for operadores. An operador reaching a deep link MUST receive the existing forbidden state rather than rule data.
(Previously: authenticated operadores could open the automation-rules page.)

#### Scenario: Admin navigation (vitest)
- GIVEN an authenticated admin
- WHEN the shell renders
- THEN automation rules appears in navigation and the route remains usable

#### Scenario: Operator navigation (vitest)
- GIVEN an authenticated operador
- WHEN the shell renders
- THEN automation rules is absent from navigation

#### Scenario: Operator deep link (pytest/vitest)
- GIVEN an authenticated operador opens the automation route directly
- WHEN the page requests rules
- THEN the backend returns JSON 403 and the UI renders a permission-denied state

## ADDED Requirements

### Requirement: ARP-4 — Admin-Only Backend Read Guard

The automation list and detail GET endpoints MUST require admin authorization, in addition to existing admin-only mutations. Anonymous requests MUST receive JSON 401; operador requests MUST receive JSON 403 without rule data.

#### Scenario: Backend guard (pytest)
- GIVEN an operador requests automation list or detail
- WHEN the API evaluates authorization
- THEN it returns JSON 403

#### Scenario: Existing guard preserved (pytest)
- GIVEN an authenticated admin
- WHEN the admin requests automation rules
- THEN the authorized rule response remains available

# Automation Rules Panel Specification

## Purpose

Provide an authenticated React panel surface for inspecting and safely managing deterministic automation rules.

## Requirements

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

### Requirement: ARP-2 — Actionable Page States

The page MUST visibly represent loading, error, empty, and forbidden states. Error states MUST offer recovery where applicable, and the UI MUST remain keyboard-operable and accessible.

#### Scenario: State matrix renders
- GIVEN the API is loading, returns no rules, fails, or returns 403
- WHEN the page renders
- THEN the matching labeled state is visible and error recovery is available when applicable

### Requirement: ARP-3 — Admin Mutations and Confirmation

Admins MUST be able to create and edit valid rules and explicitly enable or disable them. Enable/disable MUST require confirmation; operadores MUST have no mutation controls, and the UI MUST refresh from the API after every successful mutation.

#### Scenario: Confirm and refresh status change
- GIVEN an admin views a rule
- WHEN they confirm enable or disable
- THEN the mutation succeeds and the refreshed detail/list reflects the persisted enabled state

#### Scenario: Operator sees read-only controls
- GIVEN an authenticated operador views a rule
- WHEN the detail view renders
- THEN create, edit, enable, and disable controls are unavailable
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

# Automation Rules Panel Specification

## Purpose

Provide an authenticated React panel surface for inspecting and safely managing deterministic automation rules.

## Requirements

### Requirement: ARP-1 — Rule List and Detail Surface

The SPA MUST provide a top-level automation-rules route with a list and a separate detail/edit view. It MUST display existing rule fields, including enabled state and notification event/content semantics, without presenting `template_event` as a template-version selector or offering execution-history management.

#### Scenario: Operator opens the page
- GIVEN an authenticated operador
- WHEN they navigate to automation rules
- THEN the list loads and a rule can be opened in the detail view

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

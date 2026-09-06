# Delta for admin-panel

## ADDED Requirements

### Requirement: AP-12 — Automation Rule Role Access

The panel MUST expose automation-rule reads to authenticated admins and operadores. Only admins MAY create, update, enable, or disable rules; unauthenticated requests MUST receive JSON 401 and operator mutation attempts MUST receive JSON 403 without changing state.

#### Scenario: Operator reads rules
- GIVEN an authenticated operador
- WHEN they request the automation list or detail
- THEN the API returns the authorized rule data

#### Scenario: Operator mutation is forbidden
- GIVEN an authenticated operador
- WHEN they submit an automation mutation
- THEN the API returns JSON 403 and the rule is unchanged

#### Scenario: Anonymous request is rejected
- GIVEN no valid session
- WHEN the automation API is requested
- THEN it returns JSON 401 without an HTML redirect

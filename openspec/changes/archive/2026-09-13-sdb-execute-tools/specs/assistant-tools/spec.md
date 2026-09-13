# Delta for assistant-tools

## ADDED Requirements

### Requirement: AT-6 — SDB Read Dispatch

SDB MUST dispatch only a validated, allow-listed, read-only registry tool through `execute_tool`, passing the existing assistant whitelist and cost decision. The SDB contract MUST be read-only; write tools remain unavailable from SDB in this change.

#### Scenario: SDB read dispatch
- GIVEN a frozen `conversations.search` task with valid arguments
- WHEN SDB executes it
- THEN the existing typed domain boundary returns bounded read evidence and performs no mutation

#### Scenario: Gate denial
- GIVEN a task is not allow-listed, has invalid arguments, or lacks cost permission
- WHEN SDB attempts dispatch
- THEN execution is rejected before the domain handler and rejection evidence is auditable

#### Scenario: Deferred writes
- GIVEN an SDB plan names `automation.create_rule` or a project lifecycle write
- WHEN the plan is validated
- THEN SDB rejects it as unavailable and creates no side effect

### Requirement: AT-7 — Read Failure Truthfulness

The SDB boundary MUST preserve bounded failure results from timeout or handler exception and MUST NOT reinterpret them as successful tool evidence.

#### Scenario: Tool exception
- GIVEN a typed read handler raises during SDB execution
- WHEN the result is persisted
- THEN it is a bounded failure with error evidence and no successful completion status

## MODIFIED Requirements

### Requirement: AT-1 — Typed Domain Tool Registry

The assistant MUST expose the existing typed, exact-argument tools over domain services, with each tool declaring read/write classification. Dispatch MUST enforce the validated `assistant.tools_whitelist` immediately before service execution and MUST NOT duplicate domain tools or call panel HTTP routes. SDB plans MUST validate the concrete tool and arguments before approval.
(Previously: registry validation and whitelist enforcement applied to assistant dispatch but did not require typed SDB task payloads before approval.)

#### Scenario: Whitelisted read
- GIVEN an authorized plan for a typed read tool present in the assistant whitelist
- WHEN dispatch validates it
- THEN the domain service result is returned as evidence without a write

#### Scenario: Declared but disallowed tool
- GIVEN a valid registry tool absent from `assistant.tools_whitelist`
- WHEN execution is requested
- THEN dispatch rejects it before any service call

#### Scenario: SDB payload validation
- GIVEN a planned SDB task with an unknown tool or invalid arguments
- WHEN approval is prepared
- THEN validation rejects the task before approval or execution

## REMOVED Requirements

### Requirement: SDB write dispatch in this change
(Reason: side-effecting SDB execution is explicitly deferred.)
(Migration: Handle writes in a separate approved SDD change.)

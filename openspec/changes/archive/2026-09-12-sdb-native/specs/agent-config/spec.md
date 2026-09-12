# Delta for Agent Config

## ADDED Requirements

### Requirement: AC-11 — Structured SDB Classification Declaration

The assistant configuration MUST declare the structured planner fields and allowed values required to distinguish an SDB request from ordinary `tool`, `respond`, or non-SDB complex work. The declaration MUST be read-only, schema-validated at startup, and MUST NOT infer SDB from arbitrary tool text.

#### Scenario: Valid classification declaration

- GIVEN the registry and planner contract declare the SDB classification shape
- WHEN configuration loads
- THEN the harness can validate and normalize an SDB trigger

#### Scenario: Malformed declaration

- GIVEN the SDB classification declaration is malformed or incomplete
- WHEN startup validation runs
- THEN configuration fails deterministically and no ambiguous SDB route is enabled

#### Scenario: Ordinary complex request

- GIVEN a planner returns a valid non-SDB complex result
- WHEN the harness evaluates it
- THEN it remains on ordinary safe routing

## MODIFIED Requirements

### Requirement: AC-9 — Assistant Runtime Configuration

The system MUST provide existence-validated assistant registry, personas, prompts, declared tool capabilities, and structured SDB classification under `agent/` for read-only runtime consumption. Startup MUST fail clearly for missing or invalid references; reference-only skills remain non-executable.
(Previously: runtime configuration validated prompts, personas, and tools but did not declare structured SDB classification.)

#### Scenario: Complete configuration loads

- GIVEN registry entries reference existing runtime files and a valid SDB declaration
- WHEN configuration loads for a panel turn
- THEN the validated read-only assistant configuration is available to the harness

#### Scenario: Missing or invalid runtime reference

- GIVEN a required prompt, persona, tool declaration, or SDB classification is invalid
- WHEN configuration loads
- THEN validation reports the defect and prevents an invalid assistant from starting

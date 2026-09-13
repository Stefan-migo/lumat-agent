# Delta for agent-config

## MODIFIED Requirements

### Requirement: AC-9 — Assistant Runtime Configuration

The system MUST provide existence-validated assistant registry, personas, prompts, declared tool capabilities, structured Gates deterministas / Guardrails classification, and a Cortex-session runtime declaration under `agent/` for read-only consumption. The Cortex declaration MUST define the allowed turn classes and lifecycle command forms. Startup MUST fail clearly for missing or invalid references; reference-only skills remain non-executable.
(Previously: runtime configuration validated prompts, personas, tools, and guardrails but did not declare Cortex-session runtime behavior.)

#### Scenario: Complete configuration loads
- GIVEN registry entries reference existing runtime files and valid guardrails and Cortex declarations
- WHEN configuration loads for a panel turn
- THEN validated read-only assistant configuration is available to the harness

#### Scenario: Missing or invalid runtime reference
- GIVEN a required prompt, persona, tool, guardrails, or Cortex declaration is invalid
- WHEN configuration loads
- THEN validation reports the defect and prevents an invalid assistant from starting

## ADDED Requirements

### Requirement: AC-12 — Cortex classification declaration

The assistant configuration MUST declare `question`, `research`, `decision`, `continue`, and `close` as the permitted Cortex classifications and MUST NOT infer lifecycle from arbitrary text.

#### Scenario: Valid classification
- GIVEN a planner returns one declared Cortex class
- WHEN the harness validates it
- THEN the class is accepted for routing

#### Scenario: Unknown classification
- GIVEN a planner returns an undeclared class or free-text lifecycle intent
- WHEN validation runs
- THEN the Cortex route is rejected fail-closed

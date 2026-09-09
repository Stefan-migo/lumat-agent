# Delta for agent-config

## ADDED Requirements

### Requirement: AC-9 — Assistant Runtime Configuration

The system MUST provide existence-validated assistant registry, personas, prompts, and declared tool capabilities under `agent/`. Startup MUST fail clearly for missing referenced runtime files, while reference-only skills remain non-executable.

#### Scenario: Complete configuration loads
- GIVEN registry entries reference existing personas, prompts, and declared tools
- WHEN configuration loads
- THEN the assistant capability set is available to runtime consumers

#### Scenario: Missing runtime reference
- GIVEN a registry entry references a missing required file or tool
- WHEN configuration loads
- THEN validation reports the missing reference and prevents an invalid assistant from starting

### Requirement: AC-10 — Read-Only Capability View

The panel API MUST expose an authenticated, read-only view of active assistant tools, data scopes, personas, and knowledge/memory capabilities. v1 MUST NOT expose configuration editing.

#### Scenario: Admin views capabilities
- GIVEN an authorized administrator requests the capability view
- WHEN the API responds
- THEN it returns the validated active capabilities without mutable configuration controls

#### Scenario: Operator cannot inspect capabilities
- GIVEN an authenticated operador requests the capability view
- WHEN authorization is checked
- THEN the API returns an authorization error and no configuration data

## MODIFIED Requirements

### Requirement: AC-4 — Data-Only Registry

The system MUST declare the assistant registry as data with a defined schema and MUST validate referenced runtime files and declared capabilities at startup. It MUST NOT provide panel editing or enforce unrelated scope outside the assistant dispatch boundary.
(Previously: the registry was data-only and declared a multi-agent roster without runtime existence validation.)

#### Scenario: Valid registry
- GIVEN `registry.yaml` parses and all runtime references exist
- WHEN startup validation runs
- THEN exactly one orchestrator and its declared roster resolve successfully

#### Scenario: Invalid registry
- GIVEN the registry is malformed or references an absent runtime file
- WHEN startup validation runs
- THEN startup reports a deterministic validation failure

#### Scenario: Reader remains outside prompt rendering
- GIVEN startup registry validation is wired
- WHEN a prompt is rendered
- THEN prompt loading does not read or enforce registry data outside the assistant dispatch boundary

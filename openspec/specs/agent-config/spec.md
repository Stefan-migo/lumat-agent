# Agent Config Specification

## Purpose

Move every prompt the LLM reads into declarative files under `agent/` behind a single loader (`app/services/prompts.py`): one loader, one strict renderer, one data-only registry — editable without deploy, consumable by H2 router.

## Requirements

### Requirement: AC-1 — Declarative `agent/` Layout

The system MUST host all LLM-facing prompts under `agent/`, with subdirs `personas/`, `prompts/`, `skills/`, plus `registry.yaml` at root.

#### Scenario: Full tree hosts all prompts
- GIVEN a full `agent/` tree
- WHEN the loader resolves any node prompt
- THEN it originates from a file under `agent/`

### Requirement: AC-2 — Single Loader with Constant Fallback

The system MUST load prompt files through one loader (`prompts.load`) reading at boot with bounded caching, falling back to current node constants (logging a `warning`) when a file is missing, so partial trees and raw-node tests remain green.

#### Scenario: File present
- GIVEN a prompt file exists under `agent/`
- WHEN the loader resolves its key
- THEN it returns the file content verbatim, no fallback

#### Scenario: File missing
- GIVEN a prompt key has no `agent/` file
- WHEN the loader resolves it
- THEN it returns the node constant and logs a `warning`

### Requirement: AC-3 — Behavior-Preserving Extraction

Extraction MUST NOT change what the LLM sees: for the same inputs the assembled prompt MUST equal the pre-change constant/template output. Canned strings (`CANNOT_ANSWER_REPLY`, `CLARIFICATION_REPLY`, `HANDOFF_REPLY`) and deterministic gate lists must stay in code.

#### Scenario: Static slot unchanged
- GIVEN a node used a hardcoded system prompt
- WHEN the loader supplies its persona file
- THEN the text equals the pre-change constant

#### Scenario: Typed template identical
- GIVEN a user-slot template now in `agent/prompts/`
- WHEN rendered with the same slot values as before
- THEN the output equals the pre-change f-string

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
- GIVEN the startup registry reader is wired
- THEN prompt loading does not read or enforce registry data outside the assistant dispatch boundary

### Requirement: AC-5 — Strict Typed Template Rendering

The system MUST render `{{name}}` placeholders via a strict renderer that raises on an unknown/unprovided variable, so prompt typos fail. Persona files MUST be static, no `{{}}`.

#### Scenario: All variables provided
- GIVEN a template with `{{kb}}`/`{{user_input}}`
- WHEN both are supplied
- THEN both substitute, output complete

#### Scenario: Missing variable
- GIVEN a template rendered with a missing `{{var}}`
- WHEN the renderer runs
- THEN it raises, no partial output

### Requirement: AC-6 — Skills as Reference Files

The system MUST ship `agent/skills/*.md` as declarative, non-executable references and MUST NOT load skill content into an LLM prompt. Runtime assistant behavior MUST use validated persona, prompt, and registry configuration read-only. The configuration terminology MUST call Lumat’s former “SDB (Deterministic Behavior Database)” surface “Gates deterministas / Guardrails”; the implementation MUST inventory all repository consumers before changing references.
(Previously: skills were reference-only and deterministic gates were described as the authoritative SDB.)

#### Scenario: Skill never loaded
- GIVEN a conversation runs end-to-end
- WHEN runtime prompts are assembled
- THEN no `agent/skills/` content appears in any LLM prompt

### Requirement: AC-7 — DB-Migration Triggers Documented

The system MUST document the D6 migration triggers: (1) runtime editing by non-developers, (2) multi-tenancy, (3) frequent production content changes. No DB migration in this iteration.

#### Scenario: Trigger documented
- GIVEN the agent-config guidance
- WHEN a developer consults it
- THEN the three D6 triggers and hybrid pattern are stated, no DB change now

### Requirement: AC-8 — Test-Import Compatibility

Extraction MUST keep `CANNOT_ANSWER_REPLY` importable from `app.chat.nodes.respond` and `HANDOFF_REPLY` from `app.chat.nodes.handoff`, so importing suites pass unchanged.

#### Scenario: Re-exports resolve
- GIVEN `from app.chat.nodes.respond import CANNOT_ANSWER_REPLY` and `from app.chat.nodes.handoff import HANDOFF_REPLY`
- WHEN extraction is applied
- THEN both imports resolve with unchanged values

## Boundary

Deterministic gates and canned replies stay in code; the registry remains data-only (enforcement at the orchestrator dispatch boundary per AO-2/AO-6/AO-7, defined in the `agent-orchestration` capability). Web/ out of scope.

### Requirement: AC-9 — Assistant Runtime Configuration

The system MUST provide existence-validated assistant registry, personas, prompts, and declared tool capabilities under `agent/` for read-only runtime consumption. Startup MUST fail clearly for missing references, while reference-only skills remain non-executable.
(Previously: configuration was validated and exposed to consumers, but the panel harness did not consume its assistant persona and prompt set.)

#### Scenario: Complete configuration loads
- GIVEN registry entries reference existing personas, prompts, and declared tools
- WHEN configuration loads for a panel turn
- THEN the validated read-only assistant configuration is available to the harness

#### Scenario: Missing runtime reference
- GIVEN a required persona or prompt reference is missing
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

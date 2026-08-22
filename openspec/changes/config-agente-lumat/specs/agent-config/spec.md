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

The system MUST declare agents in `registry.yaml` as data with a defined schema, registering exactly one agent (`orchestrator`). The registry MUST NOT enforce tools, KB scope, or memory scope at runtime.

#### Scenario: Declarative, one agent
- GIVEN `registry.yaml` parses at boot
- THEN it contains exactly one agent `orchestrator` per schema
- AND no tools, KB-scope, or memory-scope rule instantiates from it

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

The system MUST ship `agent/skills/*.md` as declarative references only and MUST NOT load any skill file into an LLM prompt. The deterministic gates remain the authoritative SDB.

#### Scenario: Skill never loaded
- GIVEN a conversation runs end-to-end
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

Deterministic gates and canned replies stay in code; Fase-2 consumers (router, tools whitelist, KB/memory scoping, sub-agents) are not implemented here. Web/ out of scope.

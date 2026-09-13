# assistant-tools Specification

## Purpose

Expose bounded typed native tools over existing domain services, with safe automation writes and evidence.

## Requirements

### Requirement: AT-1 — Typed Domain Tool Registry

The assistant MUST expose the existing typed, exact-argument tools over domain services, with each tool declaring read/write classification. Dispatch MUST enforce the validated `assistant.tools_whitelist` immediately before service execution and MUST NOT duplicate domain tools or call panel HTTP routes.
(Previously: registry validation rejected undeclared tools, but panel assistant dispatch did not enforce the assistant-specific whitelist.)

#### Scenario: Whitelisted read
- GIVEN an authorized plan for a typed read tool present in the assistant whitelist
- WHEN dispatch validates it
- THEN the domain service result is returned as evidence without a write

#### Scenario: Declared but disallowed tool
- GIVEN a valid registry tool absent from `assistant.tools_whitelist`
- WHEN execution is requested
- THEN dispatch rejects it before any service call

### Requirement: AT-2 — Confirmed Automation Write

The automation creation tool MUST be classified as a write, MUST execute only after exact approval, and MUST use the existing automation service in the same transaction. It MUST return the created rule and preserve existing history and worker semantics.

#### Scenario: Rule creation
- GIVEN an approved valid automation rule plan
- WHEN the tool executes
- THEN the existing service persists and audits the rule in the request transaction and returns it as evidence

#### Scenario: Unapproved write
- GIVEN a plan to create an automation without valid approval
- WHEN the assistant reaches execution
- THEN no rule or domain event is created

### Requirement: AT-3 — Bounded Web Evidence

Web search MUST use one bounded adapter interface over `httpx` and return source evidence. Tavily and other external integrations MUST NOT be required by this capability.

#### Scenario: Search result
- GIVEN an authorized read plan containing a web query
- WHEN web search completes
- THEN bounded results and source references are returned as evidence

#### Scenario: Search failure
- GIVEN a timeout, malformed response, or unsafe result
- WHEN the adapter runs
- THEN the tool returns a testable error evidence state and performs no domain mutation

### Requirement: AT-4 — Typed project tools

The assistant registry MUST expose typed agent-owned project tools for `list`, `find`, `create`, `rename`, `archive`, and `merge`, each with explicit read/write classification and bounded arguments. Dispatch MUST enforce the assistant whitelist immediately before service execution.

#### Scenario: Exact project read
- GIVEN an allow-listed `project.find` request with an exact slug
- WHEN dispatch executes it
- THEN the matching project is returned without approval or mutation

#### Scenario: Lifecycle tool classification
- GIVEN an allow-listed rename, archive, or merge request
- WHEN its schema is inspected
- THEN it is classified as a write and cannot execute as a read

### Requirement: AT-5 — Project approval boundary

Semantic project ambiguity MUST produce bounded candidates and an approval request containing the candidate payload's SHA-256 digest and 15-minute TTL. Namespace selection MUST occur only after SDB `APPROVE`; lifecycle mutations MUST require the same exact-payload approval. The assistant MUST NOT silently reuse or create a project.

#### Scenario: Semantic ambiguity
- GIVEN `project.find` has no exact slug and multiple plausible purposes
- WHEN the tool is called
- THEN it returns an approval-required result and selects no namespace

#### Scenario: Approved mutation
- GIVEN an exact approved rename or merge payload
- WHEN SDB `APPROVE` is consumed
- THEN the typed service executes once; absent, expired, or changed approval performs no mutation

# assistant-tools Specification

## Purpose

Expose bounded typed native tools over existing domain services, with safe automation writes and evidence.

## Requirements

### Requirement: AT-1 — Typed Domain Tool Registry

The assistant MUST expose the existing typed, exact-argument tools over domain services, with each tool declaring read/write classification. Dispatch MUST enforce the validated `assistant.tools_whitelist` immediately before service execution and MUST NOT duplicate domain tools or call panel HTTP routes. SDB plans MUST validate the concrete tool and arguments before approval.
(Previously: registry validation rejected undeclared tools, but panel assistant dispatch did not enforce the assistant-specific whitelist.)

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

### Requirement: AT-8 — Scoped Memory Contract

The `memory.read` tool MUST accept only `scope="panel"` or `scope="customer"`. A panel conversation read MUST use `entity_id="thread:<thread id>"`, and a customer read MUST use `entity_id="customer:<customer id>"` or a legacy numeric customer id.

#### Scenario: Valid scoped memory read
- GIVEN a memory read with a closed-domain scope and its matching entity identifier
- WHEN the assistant validates the arguments
- THEN validation accepts the read for execution

#### Scenario: Unknown memory scope
- GIVEN a memory read with a scope outside `panel` or `customer`
- WHEN the assistant validates the arguments
- THEN validation rejects the arguments before service execution

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

### Requirement: AT-6 — SDB Approved Write Dispatch

SDB MUST dispatch validated allow-listed read or write registry tools through `execute_tool`. Every write MUST receive the exact consumed approval for the frozen task binding; dispatch MUST never bypass `execute_tool` or domain services. Existing AT-1–AT-5 and AT-7 whitelist, typed validation, project decision, and failure boundaries remain unchanged. (Seams: `app/chat/assistant/tools/registry.py:272-308`, `app/services/agent_chat.py:93-109`; unit tests MUST cover approval forwarding and bypass prevention.)

#### Scenario: Approved write dispatch
- GIVEN a validated frozen write task and its consumed exact approval
- WHEN SDB dispatches it
- THEN `execute_tool` validates the whitelist, arguments, approval, cost, and project decision before the domain handler runs

#### Scenario: Missing or altered approval
- GIVEN a write task with absent, expired, replayed, or changed approval
- WHEN dispatch is requested
- THEN no domain mutation occurs

#### Scenario: Gate ordering
- GIVEN a malformed, disallowed, or cost-blocked write
- WHEN dispatch evaluates it
- THEN rejection occurs before the handler and remains auditable

### Requirement: AT-7 — Write Failure Truthfulness

The assistant boundary MUST preserve bounded failure results from write validation, service errors, or transaction failures and MUST NOT reinterpret them as successful evidence. (Seam: `app/chat/assistant/tools/registry.py:316-327`; unit and integration tests MUST assert failed status and no false completion.)

#### Scenario: Mutation handler failure
- GIVEN a typed write handler raises
- WHEN SDB records the outcome
- THEN it returns bounded failure evidence and no successful completion

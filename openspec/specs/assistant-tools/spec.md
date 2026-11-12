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

The `memory.read` and `memory.search` tools MUST accept only the public `scope="own"` or `scope="customer"` contracts. An own read MUST omit `entity_id`; the server MUST derive the trusted current thread axis and project-qualified agent axis, reject any model-supplied entity, preserve their interleave order, and return a digest whose `contenido` is bounded to 500 characters. A customer read MUST use `entity_id="customer:<customer id>"` or a legacy numeric customer id and MUST retain its full projection. `memory.search` MUST bound each returned `contenido` field before it becomes tool evidence.

#### Scenario: Valid scoped memory read
- GIVEN an own memory read without `entity_id`, or a customer read with a matching customer entity identifier
- WHEN the assistant validates the arguments
- THEN validation accepts the read for execution

#### Scenario: Own read server-side binding
- GIVEN an own `memory.read` or `memory.search` with a positive trusted thread id
- WHEN the assistant executes it
- THEN the server derives the trusted `thread:<trusted thread id>` axis and project-qualified `agent:<project>` axis, and rejects any model-supplied `entity_id`

#### Scenario: Unknown public memory scope
- GIVEN a memory read with a scope outside `own` or `customer`
- WHEN the assistant validates the arguments
- THEN validation rejects the arguments before service execution

#### Scenario: Bounded scoped memory search
- GIVEN a valid memory search with a matching scope and entity identifier
- WHEN the assistant executes it
- THEN ranked results are returned only for that entity and each `contenido` field is truncated to the fixed tool bound

#### Scenario: Bounded own memory digest
- GIVEN an own memory read with a positive trusted thread id and a requested limit
- WHEN the assistant executes it
- THEN the trusted thread and project axes are interleaved before the limit is applied, each item includes its identifying metadata, and `contenido` is truncated to at most 500 characters

#### Scenario: Full entity-scoped memory projection
- GIVEN a valid customer memory read with an entity identifier
- WHEN the assistant executes it
- THEN the result retains the existing full memory projection without the own-read digest bound

#### Scenario: Own search entity rejection
- GIVEN an own memory search whose model-supplied entity identifier is present
- WHEN the assistant validates the arguments
- THEN validation rejects the search before service execution

#### Scenario: Server-derived project axis
- GIVEN an own memory read or search
- WHEN the assistant validates the arguments
- THEN the public contract exposes no agent scope or entity argument, and the server derives the canonical project-qualified `agent:<project>` axis

### Requirement: AT-9 — Autonomous Thread Memory Write

The `memory.write` tool MUST accept a declared `visibility` of `thread` or `global`, defaulting to `global`. It MUST accept no model-supplied scope or entity identifier: the server derives `thread` as `scope="panel"`, `entity_id="thread:<trusted thread id>"`, and `global` as `scope="agent"`, `entity_id="agent:<project>"`, with the project bound server-side. The server MUST stamp `producer="agent"` and the trusted origin thread. It MUST require an `agent:` topic namespace, use nested-savepoint upsert semantics, and return a degraded result rather than raising on persistence failure. Only `memory.write` may skip approval, and only with a positive trusted thread id; every other write MUST retain exact approval.

#### Scenario: Bounded autonomous write
- GIVEN an allow-listed `memory.write` call with a positive trusted thread id
- WHEN the assistant executes it without approval
- THEN the memory is upserted on the axis its declared visibility selects, stamped with the trusted origin thread, and the result reports the written row

#### Scenario: Declared global visibility
- GIVEN an allow-listed `memory.write` call with `visibility="global"`
- WHEN the assistant executes it with a positive trusted thread id
- THEN the memory is stored on the canonical agent axis with agent provenance and the trusted origin thread

#### Scenario: Autonomous target cannot be supplied by the model
- GIVEN a `memory.write` payload containing `scope` or `entity_id`
- WHEN the assistant validates the arguments
- THEN validation rejects the payload before execution

#### Scenario: Autonomous topic namespace
- GIVEN a `memory.write` payload whose topic key does not start with `agent:`
- WHEN the assistant validates the arguments
- THEN validation rejects the payload before execution

#### Scenario: Missing trusted thread fails closed
- GIVEN a `memory.write` call without a positive trusted thread id, including an SDB dispatch
- WHEN execution is requested
- THEN the tool rejects the call and performs no write

#### Scenario: Other writes remain approval-gated
- GIVEN any write tool other than `memory.write`
- WHEN execution is requested without consumed exact approval
- THEN the tool rejects the call before mutation

### Requirement: AT-11 — Autonomous Agent Memory Correction

The assistant MUST expose `memory.update` and `memory.delete` as autonomous writes alongside `memory.write`, requiring a positive trusted thread id and permitting only agent-authored `agent:` memories on the current thread or project axis; every other write MUST retain exact approval, and rejected targets MUST NOT be mutated.

#### Scenario: Owned row updates without approval
- GIVEN an agent-authored `agent:` memory on the trusted panel thread or canonical project axis
- WHEN the assistant executes `memory.update` with a non-empty patch and no approval
- THEN the owned row is updated in place without an approval step

#### Scenario: Non-owned row is rejected without mutation
- GIVEN a customer memory, system recap, another thread's row, or a row in a foreign `proyecto`
- WHEN the assistant executes `memory.update` or `memory.delete`
- THEN dispatch raises a validation error and the row remains unchanged

#### Scenario: Empty update patch is rejected
- GIVEN a `memory.update` payload containing only a positive memory id
- WHEN the assistant validates the arguments
- THEN validation rejects the payload before service execution

#### Scenario: Owned row deletion
- GIVEN an agent-authored `agent:` memory on an allowed axis
- WHEN the assistant executes `memory.delete` without approval
- THEN the owned row is removed

#### Scenario: Other writes remain approval-gated
- GIVEN any write tool other than `memory.write`, `memory.update`, or `memory.delete`
- WHEN execution is requested without exact approval
- THEN the tool rejects the call before mutation

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

Web search MUST use one bounded adapter interface over `httpx` and return source evidence. The provider MUST
be configurable, return bounded textual content with each source reference, and fail loudly for provider
failures rather than representing them as empty results. The adapter seam MUST remain provider-neutral so
another provider can replace the configured integration without changing the tool contract.

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

### Requirement: AT-10 — Read Failure Truthfulness

The assistant boundary MUST degrade the turn when a read-only tool fails, preserve bounded failure evidence for the responder, and MUST NOT expose the raw exception as the answer. (Seams: `app/chat/assistant/nodes.py:614-622`, `app/chat/assistant/graph.py:83-84`; unit and integration tests MUST assert responder continuation and bounded evidence.)

#### Scenario: Memory read failure
- GIVEN `memory.read` fails with an internal exception
- WHEN the assistant executes the tool
- THEN the turn is marked degraded, continues to the responder, and the raw exception never becomes the answer

#### Scenario: Memory search failure
- GIVEN `memory.search` fails with an internal exception
- WHEN the assistant executes the tool
- THEN the turn is marked degraded, continues to the responder, and the raw exception never becomes the answer

### Requirement: AT-12 — Declared Assistant Capability Inventory

The assistant MUST expose `assistant.capabilities` as a read-only tool with no arguments. It MUST report every tool in the assistant's validated whitelist exactly once using the registry description and read/write classification. Its result MUST preserve the exact whitelist count and include one capability line for every whitelisted tool, without relying on the generic item limit. Registry tools absent from the whitelist MUST NOT appear. Capability answers MUST use only this tool result, and business questions MUST remain subject to the bounded knowledge-base grounding rule.

#### Scenario: Complete inventory is not item-truncated
- GIVEN the assistant whitelist contains more entries than the generic item bound
- WHEN `assistant.capabilities` executes
- THEN the result reports the exact whitelist length and one capability line for every whitelisted tool

#### Scenario: Non-whitelisted registry entry is excluded
- GIVEN a tool exists in `TOOL_REGISTRY` but is absent from the assistant whitelist
- WHEN `assistant.capabilities` executes
- THEN that tool is absent from the capability text

#### Scenario: Capability inventory is read-only
- GIVEN a valid plan for `assistant.capabilities`
- WHEN guardrails evaluate the plan
- THEN execution proceeds without approval and performs no write

#### Scenario: Business grounding remains unchanged
- GIVEN a business question without sufficient bounded `<kb>` evidence
- WHEN the assistant evaluates the question
- THEN the answer carries no business fact without evidence behind it rather than using the capability inventory
- AND the assistant explains what it checked, what it lacks and the operator's next step instead of returning a fixed clarification

### Requirement: AT-13 — Bounded Single-URL Reader

The assistant MUST expose `web.fetch` as a read-only tool that reads one public URL and returns bounded citable evidence: the final URL after redirects, the page title when present, and extracted visible text sized to fit the existing tool-evidence budget. Every request MUST pass an explicit policy — an `http`/`https` scheme allowlist, no URL credentials, default ports only, and every resolved address validated as public across IPv4 and IPv6 before any request — and redirects MUST be followed manually with a cap, each hop revalidated. The body MUST be byte-capped while reading, timeouts MUST be explicit, and only text content types MAY be read. Script, style, noscript and template bodies MUST NOT become page text, and block-level elements MUST separate text. Any refusal or failure MUST surface as an explicit error state and never as an empty result. `web.search` and the evidence budget MUST remain unchanged.

#### Scenario: Reader returns citable bounded evidence
- GIVEN an allow-listed `web.fetch` plan for a public page
- WHEN the reader completes
- THEN the evidence carries the final URL, the page title when present, and visible text

#### Scenario: Every redirect hop is revalidated
- GIVEN a public URL that redirects to a non-public address or to a non-`http(s)` scheme
- WHEN the reader evaluates the redirect
- THEN the hop is refused and no request is made to that target

#### Scenario: Policy refusal is explicit and makes no request
- GIVEN a URL with credentials, a non-default port, a disallowed scheme, or a non-public address
- WHEN the reader evaluates it
- THEN the tool returns a testable error evidence state and performs no request

#### Scenario: Extracted text excludes script and style bodies
- GIVEN an HTML page whose script and style bodies contain text
- WHEN the reader extracts the page text
- THEN those bodies are absent and adjacent block text stays separated

#### Scenario: Oversized page stays inside the evidence budget
- GIVEN a page whose title and body exceed the evidence budget by an order of magnitude
- WHEN the reader serializes its evidence
- THEN the result fits the existing tool-evidence limit with margin

### Requirement: AT-14 — Bounded Read-Only Sub-Agent Delegation

The panel assistant MUST accept a validated `delegate` plan for the declared `customer_records` sub-agent and execute its bounded read-only span using only that sub-agent's resolved whitelist. The span MUST refuse writes and out-of-scope tools, honour the sub-agent's customer memory scope, count as exactly one parent tool step, and return structured results with sub-agent/tool provenance to the existing responder as evidence. The responder MUST answer from and cite that evidence; delegated planning usage MUST use the existing assistant LLM cost accounting path. Delegation MUST NOT add tools to the assistant planner catalog or change non-delegating turn behavior.

#### Scenario: Delegated evidence reaches the responder
- GIVEN a valid `delegate` plan for `customer_records` and successful read-only tool results
- WHEN the assistant completes the graph turn
- THEN the responder receives those results with `customer_records` and tool provenance, and its answer cites the gathered evidence

#### Scenario: Worker scope rejects an unlisted tool
- GIVEN a delegated plan whose tool is absent from the resolved `customer_records` whitelist
- WHEN the delegation span evaluates that plan
- THEN it records an explicit refusal and does not invoke that tool

#### Scenario: Worker scope rejects writes
- GIVEN a delegated plan for a registered write tool
- WHEN the delegation span evaluates that plan
- THEN it records a write-refusal decision and performs no mutation

#### Scenario: Delegation uses one parent step
- GIVEN a valid delegation whose internal span reaches its configured step cap
- WHEN the span returns to the parent graph
- THEN the parent `tool_steps` has increased by exactly one and the span has stopped

#### Scenario: Customer memory reads keep customer scope
- GIVEN a customer-records span planning `memory.read` or `memory.search` with `scope="own"`
- WHEN the span validates the read
- THEN it refuses the read before tool execution

#### Scenario: Delegated planner usage is accounted
- GIVEN a delegated planner completion with provider usage metadata
- WHEN the span records that LLM call
- THEN the existing assistant cost ledger contains one usage record for that delegated call

#### Scenario: Assistant catalog and normal turns remain unchanged
- GIVEN the existing assistant whitelist and a non-delegating plan
- WHEN delegation capability is wired
- THEN the serialized assistant planner catalog remains byte-identical to its pre-delegation value and the normal plan follows its existing state and cost path

### Requirement: AT-15 — Bounded Per-Customer Operational Drill-Down

The assistant MUST provide a read-only per-customer operational drill-down containing that customer's cases, including closed cases, and appointments, including past appointments. Each list MUST respect its requested limit, and the serialized evidence MUST fit the existing evidence budget; the projection MUST exclude customer contact/consent fields, message content and `media_url`, and all `customer_notes` data. An out-of-scope read or execution failure MUST be represented as an explicit error state, never as silence or an empty successful result.

#### Scenario: Closed cases and past appointments are included
- GIVEN a customer with open and closed cases and future and past appointments
- WHEN the operational drill-down is read for that customer
- THEN both cases and both appointments are returned, including the closed case and past appointment

#### Scenario: Per-list limits and evidence budget are enforced
- GIVEN more cases or appointments than the requested per-list limit, with a combined result that could exceed the evidence budget
- WHEN the operational drill-down is serialized as tool evidence
- THEN neither list exceeds its requested limit and the evidence does not exceed the existing budget

#### Scenario: Private customer and message data is excluded
- GIVEN a customer with contact fields, consent data, messages with text and media URLs, and internal customer notes
- WHEN the operational drill-down is returned
- THEN it contains no phone, email, address, comuna, consent, message content, `media_url`, or `customer_notes` data

#### Scenario: Out-of-scope reads and failures are explicit
- GIVEN a request for a customer outside the resolved read scope or a failure while reading operational history
- WHEN the drill-down is attempted
- THEN the result reports an explicit error state rather than silence or an empty successful result

### Requirement: AT-15 — Live Thread Artifact Inventory and Deduplicated Save
The assistant MUST include the current artifacts of its thread in assembled context, bounded to the configured inventory limit, with each artifact's id, filename, version and size and guidance to edit it with `artifact.update`. `artifact.save` MUST reuse the current artifact root when the sanitized filename already exists in the thread: identical content MUST return the current revision unchanged without a new row, blob or audit, and different content MUST append a revision under the same root.

#### Scenario: Current artifacts are available deterministically
- GIVEN a thread with current artifacts
- WHEN assistant context is assembled
- THEN the bounded inventory lists each artifact id, filename, version and size and directs edits through `artifact.update`

#### Scenario: Same named deliverable is deduplicated or revised
- GIVEN a thread with a current artifact of the requested filename
- WHEN `artifact.save` receives identical or different content
- THEN identical content returns the current row without a new revision, while different content creates the next version under the same root

### Requirement: AT-16 — Automatic Project Outputs Publication
When a thread artifact is created or revised and its thread resolves to an owned project, the assistant MUST publish its bytes as a project file inside the root `outputs` folder. Publication MUST be best effort and MUST NOT fail the artifact operation when project resolution, owner lookup, allowed-file validation or publication fails. A revision MUST update the existing project file identified by project and artifact root, preserving its row identity and updating its bytes, size and digest. Publication MUST be audited as `assistant_artifact.published` or `assistant_artifact.republished`. The published file MUST survive deletion of the thread artifact.

#### Scenario: Creation and revisions publish idempotently
- GIVEN an artifact in a thread associated with an owned project
- WHEN it is created and later revised
- THEN one file in the project's `outputs` folder is created and then updated in place with the current bytes and an audit record

#### Scenario: Unavailable or unsupported publication is non-fatal
- GIVEN a default/unresolved project, missing owner, or artifact file type rejected by project file policy
- WHEN the artifact is saved or revised
- THEN the artifact operation succeeds without publishing a project file

#### Scenario: Other project threads can read published output
- GIVEN a published artifact file in a project's `outputs` folder
- WHEN another thread of that project lists and reads project files
- THEN it sees and reads the published file without access to the source thread

#### Scenario: Published file survives artifact deletion
- GIVEN a project file published from a thread artifact
- WHEN the thread artifact is deleted
- THEN the project file and its bytes remain available

### Requirement: AT-17 — Structured PDF Report Artifacts
The assistant MUST expose `artifact.pdf` as a write tool that accepts only a structured report specification, never model-supplied HTML, CSS, or resource paths. The filename MUST end in `.pdf`; the title MUST contain 1–200 characters, the optional subtitle MUST contain at most 300 characters, and the specification MUST contain 1–40 sections. Each section MUST have a 1–200 character heading, an optional body of at most 4,000 characters, and an optional table with 1–8 columns, at most 200 rows, and string cells of at most 200 characters. All argument models MUST forbid extra fields. Rendering MUST use Jinja2 with autoescape enabled AND a URL fetcher that refuses every URL, including HTTP, HTTPS, file, data, and relative URLs; these MUST remain independent injection controls. The resulting PDF MUST be stored as a normal `application/pdf` thread artifact and, when the thread resolves to an owned project, published into its root `outputs` folder using the existing filename identity and revision rules. Saving identical PDF bytes MUST return `changed: false` without a new artifact revision or a `republished` audit.

#### Scenario: Structured bounds and independent rendering defenses
- GIVEN a structured PDF report specification within the declared filename, title, subtitle, section, heading, body, column, row, and cell bounds, with text containing HTML-like markup
- WHEN `artifact.pdf` renders the report
- THEN the HTML body text is escaped by Jinja2 autoescape, the refusing URL fetcher rejects all resource URL schemes independently, and the output is a valid PDF without accepting HTML/CSS/path fields

#### Scenario: PDF artifact publication and unchanged save
- GIVEN a thread associated with an owned project and a valid structured report specification
- WHEN `artifact.pdf` saves the resulting PDF and the same specification is saved again with identical rendered bytes
- THEN the PDF artifact has content type `application/pdf`, one project file is published inside the root `outputs` folder, and the unchanged save returns `changed: false` without a new revision or `assistant_artifact.republished` audit

### Requirement: AT-18 — Approval-Gated Project Text File Save
The assistant MUST expose `project_file.save` as a default-tier write requiring the owner's class-A approval. It MUST resolve the authenticated thread and its project by normalized thread slug and matching thread owner, and fail closed when either the project or owner is unavailable with guidance to use `artifact.save` for a thread deliverable. It MUST accept only `.md`, `.txt`, or `.csv` files accepted by the project-file policy, with a filename of 1–255 characters, content of 1–200,000 characters, and an optional folder name of at most 120 characters. A requested folder MUST already exist at the project root. The tool MUST store the bytes through the project-file service and audit `project_file.assistant_saved`; it MUST NOT create folders or expose delete, rename, or move operations.

#### Scenario: Save text at root or in an existing folder with approval and audit
- GIVEN an owned project thread, valid text content, and optionally an existing root folder
- WHEN the owner approves `project_file.save`
- THEN the file is created at the project root or in that folder and an assistant audit records project, filename, size, and folder id

#### Scenario: Reject non-text filenames
- GIVEN a requested filename outside `.md`, `.txt`, and `.csv`
- WHEN `project_file.save` is validated or executed
- THEN the tool fails closed without creating a file

#### Scenario: Missing project directs to thread deliverables
- GIVEN a thread without an owned project or a resolvable owner
- WHEN `project_file.save` is executed
- THEN it fails with an explicit message that the thread has no project and directs the assistant to `artifact.save`

#### Scenario: Missing folder is not created
- GIVEN a folder name that does not identify an existing root folder in the project
- WHEN `project_file.save` is executed
- THEN it fails closed and creates neither a folder nor a file

### Requirement: AT-19 — Approval-Gated Project Text File Update
The assistant MUST expose `project_file.update` as a default-tier write requiring the owner's class-A approval. It MUST resolve the thread project using the same ownership rules as AT-18 and retrieve the requested file only within that project. It MUST reject missing files, files with `source_artifact_root_id` (whose source of truth is `artifact.update`), non-text suffixes, and content rejected by project-file size policy. Before a changed update overwrites the existing blob, it MUST read and save the previous bytes as an artifact in the same thread, named with the file's stem plus `.bak` plus its suffix (for example, `notes.md` becomes `notes.bak.md`), using the safe artifact filename policy, and publish that artifact into the project's root `outputs` folder. If the backup cannot be stored, the update MUST fail with `ToolValidationError` and leave the target file unchanged. After successful backup and publication, the changed update MUST overwrite the existing blob, update its size and SHA-256, preserve the row identity, and audit `project_file.assistant_updated` with previous and new SHA-256 values plus `backup_artifact_id`; the returned result MUST also include `backup_artifact_id`. Identical content MUST write nothing, add no audit or backup, and return `changed: false`. The assistant MUST NOT gain delete, rename, or move tools.

#### Scenario: Update preserves identity and audits changed content
- GIVEN an approved update for a text file in the thread's project
- WHEN the content differs from the stored bytes
- THEN the existing row keeps its id, the blob, size, and SHA-256 are updated, and an assistant audit records both digests

#### Scenario: Artifact-published file cannot be updated directly
- GIVEN a project file carrying `source_artifact_root_id`
- WHEN `project_file.update` is executed
- THEN it fails closed and directs the assistant to `artifact.update`

#### Scenario: Changed content is recoverable from a published backup
- GIVEN an approved update for a text file in the thread's project
- WHEN the content differs from the stored bytes
- THEN the previous bytes are stored in a same-thread artifact named with the `.bak` suffix before the target is changed, the artifact is published in the project's root `outputs` folder, the live file contains the new content, and the result and audit identify the backup artifact

#### Scenario: Refuse an update when its backup cannot be stored
- GIVEN an approved update for a text file and a failure to store the backup artifact
- WHEN `project_file.update` is executed
- THEN it raises `ToolValidationError` and leaves the target file bytes, size, and SHA-256 unchanged

#### Scenario: Identical content is a no-op
- GIVEN an approved update whose content has the same SHA-256 as the stored file
- WHEN `project_file.update` is executed
- THEN it returns `changed: false` without writing bytes, changing the row, or adding an audit

#### Scenario: Approval is required for both project file writes
- GIVEN either project file write tool
- WHEN it is registered and invoked
- THEN it belongs to `APPROVED_WRITE_ALLOWLIST`, is absent from `AUTONOMOUS_WRITE_ALLOWLIST`, and cannot execute without exact owner approval

# Delta for Memory

## MODIFIED Requirements

### Requirement: MEM-2 — Tukulpan Boundary and Memory Service CRUD

The canonical Tukulpan façade MUST expose upsert, get, list, delete, and mark, reuse `kb.embed_texts()` for embeddings, and preserve persisted table, enum, and identifier contracts. `app.services.memory` MUST remain a forwarding-only alias; writes MUST target `proyecto='default'` only.
(Previously: `app.services.memory` was the sole named service boundary.)

#### Scenario: Canonical and legacy imports
- GIVEN either service import
- WHEN CRUD is invoked
- THEN behavior matches and persisted identifiers remain unchanged

#### Scenario: Upsert writes memory
- GIVEN a scoped entity and new topic key
- WHEN upsert stores content
- THEN one row with its embedding persists

#### Scenario: Non-default project rejected
- GIVEN `proyecto != 'default'`
- WHEN upsert is invoked
- THEN it rejects the write and persists nothing

### Requirement: MEM-3 — Explicit, Scoped Hybrid Search

The system MUST retain `hybrid_search()` as an explicit, project- and scope/entity-filtered operation. `assemble_context()` and `load_panel_context()` MUST NOT invoke it; panel reads MUST use `scope='panel'`, `entity_id='thread:{id}'`, and WhatsApp reads MUST retain customer scope.
(Previously: hybrid search was available as a scoped service operation, but the panel boundary was not a canonical Tukulpan contract.)

#### Scenario: Explicit search only
- GIVEN a panel turn enters `assemble_context()`
- WHEN context is assembled without a `memory.read` tool call
- THEN no hybrid search runs and only the deterministic panel projection is used

#### Scenario: Threshold recall
- GIVEN one scoped memory exceeds the similarity threshold
- WHEN hybrid search runs
- THEN only above-threshold results return, ranked by fused score

#### Scenario: Panel and WhatsApp isolation
- GIVEN memories for `thread:{id}` and `customer:{id}`
- WHEN panel and WhatsApp context paths load memory
- THEN each path returns only its own scope/entity rows

#### Scenario: Role isolation
- GIVEN a caller without cross-project rights
- WHEN search runs
- THEN only its visible scope/entity rows return

#### Scenario: Empty result
- GIVEN no memory exceeds the threshold
- WHEN hybrid search runs
- THEN an empty set returns without fallback

## ADDED Requirements

### Requirement: MEM-7 — Milestone, Decision, and Recap Lifecycle

The system MUST search before responding and save only meaningful milestones, explicit Cortex-session decisions, or a bounded pre-rotation recap; it MUST NOT write every message. Recaps MUST be idempotent, retain source/truncation evidence, and surface failures as degraded evidence.

#### Scenario: Milestone and recap writes
- GIVEN a panel turn reaches a milestone or `compact_session()` reaches rotation
- WHEN the write seam runs
- THEN one durable milestone/decision or bounded recap is stored, without a metadata-only synthetic row

#### Scenario: Idempotent retry and failure
- GIVEN the same recap is retried, or its persistence fails
- WHEN the write is attempted
- THEN retrying does not duplicate it, and failure is surfaced to the turn/rotation evidence

#### Scenario: Deferred boundaries
- GIVEN panel memory is exercised
- WHEN the runtime is inspected
- THEN no SDB subgraph, Cortex-session mode, archived-artifact rename, second event bus, or implicit search is introduced

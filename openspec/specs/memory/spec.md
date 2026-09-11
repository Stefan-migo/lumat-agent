# Memory Specification

## Purpose

Give the agent a persistent, domain-aware memory layer over PostgreSQL + pgvector: typed memories per `(proyecto, scope, entity_id)` keyed by `topic_key`, hybrid semantic+FTS recall, typed observations, close-time customer memo, and panel management. Single-agent (`proyecto default`); cross-project and ToolNode out of scope.

## Requirements

### Requirement: MEM-1 — Schema and Migration

Migration `009_memory.sql` MUST create `memories`, `memory_relations`, and `memory_observations`, and MUST index `memories.embedding` with HNSW `vector_cosine_ops` on vector(384, local). `memories` MUST enforce `UNIQUE(proyecto, scope, entity_id, topic_key)`. `EXPECTED_TABLES` MUST list the new tables.

#### Scenario: Migration applies
- GIVEN a reachable pgvector and the current migration runner
- WHEN `db/migrate.sh` runs migration 009
- THEN the three tables and the HNSW embedding index exist
- AND `EXPECTED_TABLES` includes them

#### Scenario: Topic-key uniqueness
- GIVEN two stores with identical `(proyecto, scope, entity_id)` but distinct `topic_key`
- WHEN both upserts run
- THEN two rows exist (no collision, first untouched)

### Requirement: MEM-2 — Tukulpan Boundary and Memory Service CRUD

The canonical Tukulpan façade MUST expose upsert, get, list, delete, and mark, reuse `kb.embed_texts()` for embeddings, and preserve persisted table, enum, and identifier contracts. `app.services.memory` MUST remain a forwarding-only alias; writes MUST target `proyecto='default'` only.

#### Scenario: Canonical and legacy imports
- GIVEN either service import
- WHEN CRUD is invoked
- THEN behavior matches and persisted identifiers remain unchanged

#### Scenario: Upsert writes memory
- GIVEN a scoped entity and a new `topic_key`
- WHEN upsert stores content
- THEN the row persists with its 384-dim embedding and no duplicates

#### Scenario: Non-default project rejected
- GIVEN a write targeting `proyecto != 'default'`
- WHEN upsert is invoked
- THEN the system rejects it and persists nothing

### Requirement: MEM-3 — Explicit, Scoped Hybrid Search

The system MUST retain `hybrid_search()` as an explicit, project- and scope/entity-filtered operation. `assemble_context()` and `load_panel_context()` MUST NOT invoke it; panel reads MUST use `scope='panel'`, `entity_id='thread:{id}'`, and WhatsApp reads MUST retain customer scope.

#### Scenario: Explicit search only
- GIVEN a panel turn enters `assemble_context()`
- WHEN context is assembled without a `memory.read` tool call
- THEN no hybrid search runs and only the deterministic panel projection is used

#### Scenario: Threshold recall
- GIVEN memories where one is semantically close to the query
- WHEN a scoped hybrid search runs
- THEN only results above the threshold return, ranked by fused score

#### Scenario: Role isolation
- GIVEN a search by a role without cross-project rights
- WHEN the search runs
- THEN only that scope's visible memories return, never another's

#### Scenario: Empty result
- GIVEN no memory above the threshold
- WHEN hybrid search runs
- THEN an empty set returns with no out-of-scope fallback

### Requirement: MEM-4 — Close-Time Customer Memo

On `set_conversation_state(CLOSED)`, the system MUST upsert the customer_memo as a memory with `scope=customer`, reusing the `summary.py` acta content (CM-5 unchanged), and MUST also persist typed observations.

#### Scenario: Close writes memo
- GIVEN a conversation transitions to CLOSED
- WHEN the close trigger fires
- THEN a customer_memo is upserted under the customer `entity_id`
- AND the acta content is reused verbatim

### Requirement: MEM-5 — Observations

The system MUST persist observations typed `recurrencia`, `sin_respuesta`, `riesgo`, or `oportunidad`, each linked to a memory with a detail payload, and MUST update observation state on close.

#### Scenario: Observation persisted
- GIVEN a conversation reveals a repeated incident or an unanswered contact
- WHEN the pattern fires at close
- THEN a `memory_observations` row is stored with type and detail

#### Scenario: Recurrence threshold
- GIVEN the same issue recurs across conversations within the configured window
- WHEN the count reaches the trigger
- THEN a `recurrencia` observation is created (not before)

### Requirement: MEM-6 — Panel Management

Authorized users MUST manage memories at `GET/POST /panel/api/clients/{id}/memories`, rendered in `web/src/components/domain` via the `ClientFicha` pattern. Users MUST view, edit, delete, and mark memories; listing MUST be scoped to the selected client.

#### Scenario: List and edit
- GIVEN an authorized user opens a client ficha
- WHEN they request that client's memories
- THEN they see only that client's memories with stable identity for edit, delete, or mark

#### Scenario: Unauthorized access
- GIVEN a user without the required role
- WHEN they call the memories API
- THEN the request is rejected

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

## Boundary

Batch compression, automatic conflict judgment, and decay are deferred (schema only). Cross-project recall and ToolNode tools are out of scope.

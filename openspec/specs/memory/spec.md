# Memory Specification

## Purpose

Give the agent a persistent, domain-aware memory layer over PostgreSQL + pgvector: typed memories per `(proyecto, scope, entity_id)` keyed by `topic_key`, hybrid semantic+FTS recall, typed observations, close-time customer memo, and panel management. Single-agent (`proyecto default`); cross-project and ToolNode out of scope.

## Requirements

### Requirement: MEM-1 — Schema and Migration

Migration `009_memory.sql` MUST create `memories`, `memory_relations`, and `memory_observations`, and MUST index `memories.embedding` with HNSW `vector_cosine_ops` on vector(384, local). `memories` MUST enforce `UNIQUE(proyecto, scope, entity_id, topic_key)` and deduplicate normalized content within `(proyecto, scope, entity_id)` using `normalized_hash`, incrementing `duplicate_count` for repeated content under a different `topic_key`. `EXPECTED_TABLES` MUST list the new tables.

#### Scenario: Migration applies
- GIVEN a reachable pgvector and the current migration runner
- WHEN `db/migrate.sh` runs migration 009
- THEN the three tables and the HNSW embedding index exist
- AND `EXPECTED_TABLES` includes them

#### Scenario: Topic-key uniqueness
- GIVEN two stores with identical `(proyecto, scope, entity_id)` but distinct `topic_key`
- WHEN both upserts run with different normalized content
- THEN two rows exist (no collision, first untouched)

#### Scenario: Repeated content under a new topic key deduplicates
- GIVEN an existing memory holding some content for a `(proyecto, scope, entity_id)`
- WHEN a second upsert stores content equal to it after normalization under a different `topic_key`
- THEN no second row is created and the existing row's `duplicate_count` is incremented

#### Scenario: A keyed rewrite colliding with existing content folds the duplicate
- GIVEN an existing memory holding some content under one `topic_key` for a `(proyecto, scope, entity_id)`
- WHEN a keyed upsert rewrites a different `topic_key` of the same identity to content equal to it after normalization
- THEN the written key survives holding that content, and the earlier holder is folded into it with its references re-pointed

### Requirement: MEM-2 — Tukulpan Boundary and Memory Service CRUD

The canonical Tukulpan façade MUST expose upsert, get, list, delete, mark, and SDB artifact/checkpoint writes with an explicit `proyecto` parameter defaulting to `'default'`. It MUST preserve persisted table, enum, and identifier contracts. Writes to `'default'` MUST remain compatible, while writes to non-default namespaces MUST be accepted only when authorized by the agent/service project boundary. `app.services.memory` MUST remain a forwarding-only alias.
(Previously: writes targeting every non-default project were rejected before persistence.)

#### Scenario: Authorized project propagation
- GIVEN an agent writes a memory or SDB artifact for an authorized project
- WHEN the canonical façade is called with `proyecto`
- THEN the value reaches persistence and the artifact is stored in that namespace

#### Scenario: Default compatibility and unauthorized namespace
- GIVEN a caller omits `proyecto`, or targets a namespace without authorization
- WHEN a write is invoked
- THEN default uses `'default'`, while the unauthorized write is rejected before persistence

### Requirement: MEM-3 — Explicit, Scoped Hybrid Search

The system MUST retain `hybrid_search()` as an explicit, project- and scope/entity-filtered operation. Panel context assembly MUST NOT invoke it or automatically load memory rows; memory reads MUST occur through explicit `memory.read` tool calls, and WhatsApp reads MUST retain customer scope.

#### Scenario: Explicit search only
- GIVEN a panel turn enters `assemble_context()`
- WHEN context is assembled without a `memory.read` tool call
- THEN no hybrid search runs and no memory row is added to the panel context

#### Scenario: Threshold recall
- GIVEN memories where one is semantically close to the query
- WHEN a scoped hybrid search runs
- THEN only results above the threshold return, ranked by fused score

#### Scenario: Role isolation
- GIVEN a search by a role without cross-project rights
- WHEN the search runs
- THEN panel reads derive `thread:<trusted thread id>` server-side and return only that thread's memories, project-visible agent memories return from any thread in the same project, and customer memories remain client-gated

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

### Requirement: MEM-8 — Typed Native SDB Artifacts

The memory layer MUST support bounded native SDB artifacts in panel scope using `PATTERN` for SPEC, `SESSION` for STATE/checkpoints, and `DISCOVERY` for RESULT/evidence. Every seam MUST accept an explicit `proyecto` parameter defaulting to `'default'`; SDB MUST pass authorized project namespaces through without changing artifact storage or typed semantics.
(Previously: SDB accepted the project parameter but non-default project behavior was prohibited.)

#### Scenario: Typed artifact persistence
- GIVEN an authorized SDB run persists SPEC, STATE, or RESULT
- WHEN the artifact is written for `thread:{id}` with a project
- THEN its type and bounded payload are stored in `memories` under that namespace

#### Scenario: Default project compatibility
- GIVEN an SDB caller omits `proyecto`
- WHEN an artifact or checkpoint is written
- THEN `proyecto='default'` is used and existing write safety remains enforced

#### Scenario: Broad recall is not implicit
- GIVEN an SDB task needs memory recall
- WHEN no explicit scoped search is requested
- THEN no hybrid search or out-of-scope fallback runs

### Requirement: MEM-9 — Memory Provenance and Axis Coherence

The `memories` table MUST record `producer` as `user`, `system`, `agent`, or
`pipeline`, the nullable `origin_thread_id`, and the declared `visibility` as
`thread` or `project`. Existing rows MUST use `system` and `thread` as
conservative backfill values because their true producer is unrecoverable. The
database MUST enforce `visibility='project'` if and only if `scope='agent'`.
The agent-axis entity MUST be project-qualified as `entity_id='agent:<project>'`
so a project-visible memory can never be reached by a read bound to another
project. The server MUST derive this target from the declared visibility rather
than accepting it from the model.

#### Scenario: Provenance and coherent axis
- GIVEN an agent writes project-visible memory from a trusted thread
- WHEN the row is persisted
- THEN it records `producer='agent'`, the origin thread, `visibility='project'`, `scope='agent'`, and the project-qualified entity `entity_id='agent:<project>'`

#### Scenario: Coherence constraint
- GIVEN a memory row declares `visibility='project'` with `scope='panel'`
- WHEN the row is inserted
- THEN the database rejects it

#### Scenario: Project visibility across threads
- GIVEN a project-visible agent memory written from one thread
- WHEN another thread in the same project reads the agent axis
- THEN the memory is readable

#### Scenario: Thread default remains episodic
- GIVEN a memory write omits `visibility`
- WHEN the row is persisted
- THEN it uses `visibility='thread'`, `scope='panel'`, and the writing thread entity

## MODIFIED Requirements

## Boundary

Batch compression, automatic conflict judgment, and decay are deferred (schema only). Cross-project recall and ToolNode tools are out of scope.

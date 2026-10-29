# Memory Specification

## Purpose

Give the agent a persistent, domain-aware memory layer over PostgreSQL + pgvector: typed memories per `(proyecto, scope, entity_id)` keyed by `topic_key`, hybrid semantic+FTS recall, typed observations, close-time customer memo, and panel management. One agent across project namespaces: an assistant turn is bound to its thread's project, so a memory declared `global` stays inside that project. Cross-project and ToolNode out of scope.
(Previously: this read "Single-agent (`proyecto default`)", which described the era before a thread carried a project binding. MEM-9, MEM-3 and AT-9 already required the project-qualified agent axis; only the binding on the thread was missing.)

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

The system MUST retain `hybrid_search()` as an explicit, project- and scope/entity-filtered operation. An `own` read MUST union the trusted current thread axis with the project-qualified agent axis, while never including other threads' panel rows. The own read MUST preserve that axis interleave before applying its limit and MUST return a bounded digest with `contenido` limited to 500 characters plus identifying metadata. Within each axis the own read MUST order rows by pin first, then handoff, then most-recently-updated, before the axes are interleaved. Entity-scoped reads MUST retain their existing full projection. Panel context assembly MUST NOT invoke it or automatically load memory rows; memory reads MUST occur through explicit `memory.read` tool calls, and WhatsApp reads MUST retain customer scope. A `memory.read` initiated by the runtime at the start of a turn, delivered as a tool result and never injected into the assembled context, satisfies the explicit-read requirement. Admission MUST be per channel: a row qualifies when its dense cosine similarity clears the configured gate OR when a Spanish full-text match of the query's terms holds within its content, and the qualifying rows MUST be ranked by the fused score. The lexical channel MUST tolerate accent variants of the query's terms.

#### Scenario: Explicit search only
- GIVEN a panel turn enters `assemble_context()`
- WHEN context is assembled without a `memory.read` tool call
- THEN no hybrid search runs and no memory row is added to the panel context

#### Scenario: Code-initiated startup read
- GIVEN a panel turn starts while the thread or its project holds memory
- WHEN the runtime emits a `memory.read` for the own scope before planning and it returns rows
- THEN the bounded digest is delivered as a tool result and no memory row is loaded into the assembled panel context

#### Scenario: No memory, no startup read
- GIVEN a panel turn starts while the thread and its project hold no memory
- WHEN the runtime performs the startup own read
- THEN the read returns no rows and no tool result is added

#### Scenario: Own read order and bounded digest
- GIVEN an own-scope read where a pinned row, a handoff row, and a more recently updated row exist on both the thread axis and the agent axis
- WHEN the own read returns
- THEN each axis is ordered pin first, then handoff, then most-recently-updated, the axes are interleaved before the limit, and every `contenido` is limited to 500 characters

#### Scenario: Threshold recall
- GIVEN memories where one is semantically close to the query
- WHEN a scoped hybrid search runs
- THEN only results that clear the dense gate or match the query's terms lexically return, ranked by fused score

#### Scenario: Literal phrase recall
- GIVEN a memory whose content carries a literal keyword among unrelated text
- WHEN a scoped hybrid search runs with that keyword
- THEN the memory returns even when its dense cosine does not clear the dense gate

#### Scenario: Accent-insensitive lexical match
- GIVEN a memory whose content carries a keyword with an accent
- WHEN a scoped hybrid search runs with the unaccented form of that keyword
- THEN the memory returns

#### Scenario: Role isolation
- GIVEN a search by a role without cross-project rights
- WHEN the search runs
- THEN an `own` read derives `thread:<trusted thread id>` server-side and returns that thread's memories unioned with global-visible agent memories from the same project, other threads' panel rows remain invisible, and customer memories remain client-gated

#### Scenario: Bounded query-less recall
- GIVEN an own read with memories on both trusted axes
- WHEN the read is executed
- THEN rows are interleaved across both axes before the limit, and every returned `contenido` is at most 500 characters while scope, entity, topic, and available timing metadata remain present

#### Scenario: Empty result
- GIVEN no memory clears the dense gate and none matches the query's terms
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
`thread` or `global`; agent writes MUST default to `global` visibility. Existing rows MUST use `system` and `thread` as
conservative backfill values because their true producer is unrecoverable. The
database MUST enforce `visibility='global'` if and only if `scope='agent'`.
The agent-axis entity MUST be project-qualified as `entity_id='agent:<project>'`
so a memory declared `global` inside one project can never be reached by a read
bound to another project. The server MUST derive this target from the declared visibility rather
than accepting it from the model.

(Previously: the `agent`-scope label was named `project`, which collided with the
`proyecto` namespace axis that qualifies `entity_id='agent:<project>'`. Renamed to
`global` by `db/migrations/030_memory_visibility_global.sql`, an in-place catalog
update with no row rewrite.)

#### Scenario: Provenance and coherent axis
- GIVEN an agent writes global-visible memory from a trusted thread
- WHEN the row is persisted
- THEN it records `producer='agent'`, the origin thread, `visibility='global'`, `scope='agent'`, and the project-qualified entity `entity_id='agent:<project>'`

#### Scenario: Coherence constraint
- GIVEN a memory row declares `visibility='global'` with `scope='panel'`
- WHEN the row is inserted
- THEN the database rejects it

#### Scenario: Global visibility across threads
- GIVEN a global-visible agent memory written from one thread
- WHEN another thread in the same project reads the agent axis
- THEN the memory is readable

#### Scenario: Global visibility is the write default
- GIVEN a memory write omits `visibility`
- WHEN the row is persisted
- THEN it uses `visibility='global'`, `scope='agent'`, and the project-qualified entity `agent:<project>`

### Requirement: MEM-10 — Lifecycle Decay

The system MUST assign a 30-day `review_after` instant when it writes a `SUMMARY`, `SESSION`, or `DISCOVERY` memory, and MUST reset that instant on every write of a decaying row. `DECISION`, `PATTERN`, and `PREFERENCE` memory types MUST retain `review_after = NULL`. The system MUST evaluate staleness lazily on read, MUST NOT delete or silently filter stale memories, and MUST NOT assign `NEEDS_REVIEW`. `hybrid_search()` MUST include `stale: true` or `stale: false` without changing its filtering or ordering. Customer context injection MUST annotate stale lines as `stale since YYYY-MM-DD`.

#### Scenario: Decaying writes receive a review date
- GIVEN a `SUMMARY`, `SESSION`, or `DISCOVERY` memory is written
- WHEN the write succeeds
- THEN `review_after` MUST be set to approximately 30 days after the write instant
- AND a subsequent write of that row MUST reset `review_after`

#### Scenario: Non-decaying writes remain without a review date
- GIVEN a `DECISION`, `PATTERN`, or `PREFERENCE` memory is written
- WHEN the write succeeds, including a duplicate-content fold
- THEN `review_after` MUST remain `NULL`

#### Scenario: Discovery writes receive a review date
- GIVEN a `DISCOVERY` memory is written
- WHEN the write succeeds
- THEN `review_after` MUST be set to approximately 30 days after the write instant

#### Scenario: Stale search results remain visible and ordered
- GIVEN a memory has a `review_after` instant in the past
- WHEN `hybrid_search()` reads it
- THEN the result MUST include `stale: true`
- AND the memory MUST remain in the result without changing result ordering

#### Scenario: Stale injected context is annotated
- GIVEN a customer `SUMMARY` or `SESSION` memory has passed its review date
- WHEN customer context is rendered
- THEN its line MUST include `stale since YYYY-MM-DD`
- AND fresh and non-decaying lines MUST remain unannotated

### Requirement: MEM-11 — Judged Memory Relations

The system MUST judge a newly written assertional memory against at most `top_k`
nearby memories in the same `(proyecto, scope, entity_id)` axis, using the
declared cosine gate. The judge MUST return one fixed-vocabulary relation,
confidence, and reason per candidate in strict JSON. Confidence at or above
0.7 MUST record a judged relation; lower confidence MUST record the relation as
pending for the human queue. A failed, timed-out, or malformed judge response
MUST write no relation and MUST NOT fail the memory write. `SESSION` and
`SUMMARY` memories MUST NOT be judged.

#### Scenario: A confident contradiction is recorded
- GIVEN a newly written assertion has a candidate above the cosine gate
- WHEN the judge returns `conflicts` with confidence at least 0.7
- THEN the system MUST record the relation, confidence, and reason with judge provenance

#### Scenario: An uncertain verdict enters the human queue
- GIVEN a newly written assertion has a candidate above the cosine gate
- WHEN the judge returns a valid verdict below confidence 0.7
- THEN the system MUST record the relation as pending and leave it available to the human queue

#### Scenario: Relation signals annotate reads without hiding memories
- GIVEN a memory is contradicted or superseded by a recorded relation
- WHEN hybrid search or customer context reads it
- THEN the result MUST expose or render that relation signal
- AND the memory MUST remain visible unless its status is `ARCHIVED`

#### Scenario: Archived memories are excluded from reads
- GIVEN a memory has status `ARCHIVED`
- WHEN hybrid search or customer context reads the entity
- THEN that memory MUST NOT be returned or injected

#### Scenario: Pending relations are human-resolvable
- GIVEN a valid judge verdict is below confidence 0.7
- WHEN the customer-scoped human queue reads pending relations for the selected customer
- THEN the pair MUST be available for human resolution and no longer pending after resolution
- AND the queue MUST expose both memory contents, titles, the proposed relation, confidence, and reason
- AND a human verdict MUST use `supersedes`, `conflicts`, `related`, `compatible`, `scoped`, or `not_conflict`
- AND pending relations whose memories are outside the selected customer's scope MUST NOT be listed there

### Requirement: MEM-12 — Handoff Marker

The assistant MAY mark an agent-authored memory as a **handoff** — a continuation point across threads (an open line of work or the ordering of pending tasks) — by passing `handoff: true` to `memory.write`. The marker MUST persist on the stored row, MUST default to `false` for rows written without it, and MUST remain `false` for pre-existing rows. A repeat upsert of the same `(proyecto, scope, entity_id, topic_key)` that OMITS `handoff` MUST leave the stored marker unchanged; only an explicit `handoff: false` MAY clear it.

#### Scenario: A handoff write persists the marker
- GIVEN an agent writes a memory through `memory.write` with `handoff: true`
- WHEN the row is persisted
- THEN the stored memory has `handoff` set to true

#### Scenario: Default is false
- GIVEN a memory is written without passing `handoff`
- WHEN it is persisted
- THEN the stored memory has `handoff` set to false

#### Scenario: An omitted handoff preserves the marker
- GIVEN an existing memory holds `handoff` true
- WHEN the same `(proyecto, scope, entity_id, topic_key)` is upserted again without passing `handoff`
- THEN the stored `handoff` remains true

#### Scenario: An explicit false clears the marker
- GIVEN an existing memory holds `handoff` true
- WHEN it is upserted with `handoff: false`
- THEN the stored `handoff` becomes false

### Requirement: MEM-13 — Deterministic Autonomous Capture

The runtime, not the user and not the model, MUST decide when autonomous memory capture runs. Capture MUST be gated by the configured turn interval, a durable write outcome, or a rotation; it MUST NOT run on every turn. A blocked cost budget, an untrusted thread, or an exhausted per-thread daily budget MUST produce no capture and no paid call. The model MUST only produce candidates under a strict schema of at most three items, and any candidate that does not validate MUST be dropped rather than written. Each accepted capture MUST be persisted through the canonical Tukulpan write seam with `producer=agent` and `origin_thread_id` (MEM-9), so content-hash deduplication (MEM-1) and relation judging (MEM-11) apply unchanged. A failed capture MUST degrade as evidence and MUST never fail or block the turn. Capture MUST never inject or mutate the assembled panel context (MEM-3 stays intact). An idle-thread sweep MUST capture a thread that stopped without a rotation, idempotently by its last message.

#### Scenario: Runtime gates decide capture
- GIVEN a trusted thread with available cost budget and remaining per-thread daily budget
- WHEN the configured turn interval, a durable write outcome, or a rotation is reached
- THEN the runtime decides whether capture runs without requiring a user request or model decision
- AND a blocked cost budget, an untrusted thread, or an exhausted per-thread daily budget produces no capture and no paid call

#### Scenario: Candidate schema is strict and bounded
- GIVEN the runtime has deterministically decided to capture
- WHEN the model produces candidates
- THEN it produces no more than three items under the strict candidate schema
- AND each candidate that does not validate is dropped rather than written

#### Scenario: Capture uses the canonical write seam
- GIVEN a candidate validates for a trusted thread
- WHEN the runtime persists the capture
- THEN it uses the canonical Tukulpan write seam with `producer=agent` and `origin_thread_id`
- AND content-hash deduplication and relation judging apply unchanged

#### Scenario: Capture failure and panel context remain isolated
- GIVEN capture fails or a panel turn assembles its context
- WHEN the turn continues or context is assembled
- THEN failure is surfaced as degraded evidence and never fails or blocks the turn
- AND capture never injects or mutates the assembled panel context

#### Scenario: Idle-thread sweep captures without rotation idempotently
- GIVEN a thread has stopped after its last message without a rotation
- WHEN the idle-thread sweep processes it more than once
- THEN it captures the thread idempotently by its last message

### Requirement: MEM-14 — User Axis

A memory MAY be written to a `user` axis whose entity MUST be derived server-side from the authenticated user as `user:<owner_id>`. The user axis MUST be stored with `proyecto='default'` and MUST use no project filter on read, so a fact about the person is readable from the default project and from every named project that user owns. The user axis MUST be filtered by the authenticated user and MUST never be reachable through a project's owner or through another user's read. An `own` read MUST union the user axis with the thread and project axes under a dedicated budget so no axis hides another. Writing to the user axis without an authenticated user MUST fail before persistence. The database coherence constraint between `visibility` and `scope` MUST accept `scope='user'` with `visibility='global'` — the persisted `visibility` enum has no `user` value, and the axis is named by `scope` — while still rejecting incoherent rows. MEM-3's explicit-read and no-context-injection semantics and MEM-9's server-derived-target semantics MUST remain intact. The default project's agent axis MUST stay team-visible and unchanged.

#### Scenario: User facts are readable across the owner's projects
- GIVEN a memory is written to the `user` axis for an authenticated user
- WHEN that user reads from the default project and from every named project they own
- THEN the same user memory is readable without a project filter
- AND the entity is derived server-side as `user:<owner_id>` and stored with `proyecto='default'`

#### Scenario: User-axis reads are isolated by authenticated user
- GIVEN a user-axis memory belongs to one authenticated user
- WHEN another user reads it, or a project's owner is used as the read identity
- THEN the memory is never reachable through that project's owner or through another user's read
- AND the read is filtered by the authenticated user

#### Scenario: Own reads include each axis under a dedicated budget
- GIVEN memories exist on the user, thread, and project axes
- WHEN an `own` read runs
- THEN it unions the user axis with the thread and project axes under a dedicated budget
- AND no axis hides another

#### Scenario: User-axis writes require authentication
- GIVEN a write targets the user axis without an authenticated user
- WHEN persistence is attempted
- THEN the write fails before persistence

#### Scenario: User visibility and global scope are coherent
- GIVEN a row declares `visibility='user'` and `scope='global'`, or declares an incoherent visibility and scope
- WHEN the row is inserted
- THEN the user/global row is accepted and the incoherent row is rejected

#### Scenario: Existing memory boundaries remain unchanged
- GIVEN memory is read or written on the user axis
- WHEN the operation runs
- THEN memory remains explicit through the tool and is never injected into context (MEM-3)
- AND the server derives the target rather than accepting it from the model (MEM-9)
- AND the default project's agent axis stays team-visible and unchanged

## MODIFIED Requirements

## Boundary

Batch compression remains deferred. Automatic conflict judgment is now
implemented as thresholded judging with a human queue for uncertain verdicts.
Cross-project recall and ToolNode tools are out of scope.
The human relation queue is customer-scoped: a pending relation between memories outside a customer's
scope is not listed in that customer's panel queue.

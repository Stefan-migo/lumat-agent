# Delta for Harness Lumat

## MODIFIED Requirements

### Requirement: HL-1 — Session-Aware Turn Harness

The harness MUST assemble each authorized panel turn from DB-authoritative thread history, attachments, and the Tukulpan projection limited to `scope='panel'` and `entity_id='thread:{id}'`. The projection MUST place pinned entries first, use the fixed deterministic injection budget, and expose source IDs plus truncation metadata. It MUST NOT auto-invoke `hybrid_search()`.
(Previously: the harness assembled bounded panel/pinned context without requiring Tukulpan evidence metadata or an explicit-search boundary.)

#### Scenario: Deterministic context assembly
- GIVEN an authorized thread with history, attachments, and pinned/non-pinned panel memories
- WHEN `assemble_context()` runs
- THEN pinned Tukulpan entries precede other panel entries and the planner receives only budgeted context with source IDs

#### Scenario: Context over budget
- GIVEN the projection exceeds the fixed injection budget
- WHEN `assemble_context()` prepares the turn
- THEN deterministic truncation occurs and `AssistantState.context_meta` records truncation evidence

### Requirement: HL-3 — Rolling Session and Recovery Evidence

The harness MUST keep DB thread history authoritative and, before `compact_session()` rotates a session, persist a bounded meaningful recap or milestone with idempotency and source/truncation evidence. A failed write MUST be surfaced as failed/degraded compaction evidence and MUST NOT be reported as successful completion. The harness MUST NOT implement panel sub-agents, SDB, or Cortex-session mode.
(Previously: pre-compaction flush persisted a required session record, including a synthetic compaction row.)

#### Scenario: Preflight compaction
- GIVEN the configured compaction threshold is reached
- WHEN `compact_session()` enters preflight
- THEN the bounded recap is attempted before rotation and its result is persisted in session evidence

#### Scenario: Recovery after interruption
- GIVEN a completed recap or an interrupted compaction is reloaded
- WHEN the administrator reloads the thread
- THEN DB state remains authoritative and replay does not duplicate the completed recap

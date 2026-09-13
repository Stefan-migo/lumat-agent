# Delta for memory

## MODIFIED Requirements

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

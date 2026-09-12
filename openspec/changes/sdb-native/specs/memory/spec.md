# Delta for Memory

## ADDED Requirements

### Requirement: MEM-8 — Typed Native SDB Artifacts

The memory layer MUST support bounded native SDB artifacts in panel scope using `PATTERN` for SPEC, `SESSION` for STATE/checkpoints, and `DISCOVERY` for RESULT/evidence. Every seam MUST accept an explicit `proyecto` parameter defaulting to `'default'`; SDB MUST pass it through without introducing project registry or non-default project behavior.

#### Scenario: Typed artifact persistence

- GIVEN an SDB run persists SPEC, STATE, or RESULT
- WHEN the artifact is written for `thread:{id}`
- THEN its type and bounded payload are stored under the supplied project parameter

#### Scenario: Default project compatibility

- GIVEN an SDB caller omits `proyecto`
- WHEN an artifact or checkpoint is written
- THEN `proyecto='default'` is used and existing write safety remains enforced

#### Scenario: Broad recall is not implicit

- GIVEN an SDB task needs memory recall
- WHEN no explicit scoped search is requested
- THEN no hybrid search or out-of-scope fallback runs

## MODIFIED Requirements

### Requirement: MEM-2 — Tukulpan Boundary and Memory Service CRUD

The canonical Tukulpan façade MUST expose upsert, get, list, delete, mark, and SDB artifact/checkpoint writes with an explicit `proyecto` parameter defaulting to `'default'`. It MUST preserve persisted table, enum, and identifier contracts; writes targeting unsupported projects MUST remain rejected before persistence. `app.services.memory` MUST remain a forwarding-only alias.
(Previously: only the core CRUD façade exposed project behavior and milestone/decision seams were implicitly defaulted.)

#### Scenario: Explicit project propagation

- GIVEN a caller writes a milestone, decision, recap, or SDB artifact
- WHEN it supplies `proyecto`
- THEN the same value reaches the canonical upsert boundary

#### Scenario: Non-default project rejected

- GIVEN a write targets `proyecto != 'default'`
- WHEN it is invoked
- THEN the system rejects it and persists nothing

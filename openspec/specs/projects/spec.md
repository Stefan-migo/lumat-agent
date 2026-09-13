# projects Specification

## Purpose

Define the agent-owned `proyecto` registry and safe lifecycle operations for
project namespace selection and read-only browsing.

## Requirements

### Requirement: Project registry identity and purpose

The registry MUST persist a unique slug, display name, one-line purpose, lifecycle status, and purpose embedding. `list` MUST return active and archived entries; `find` MUST enforce exact-slug matching before bounded purpose-semantic candidates.

#### Scenario: Exact project lookup
- GIVEN an existing slug
- WHEN the agent calls `find`
- THEN that project is returned as a normal read without approval

#### Scenario: Bounded purpose candidates
- GIVEN no exact slug and multiple purpose matches
- WHEN `find` evaluates the purpose
- THEN only a bounded candidate set is returned and no namespace is selected

### Requirement: Agent-owned lifecycle operations

The agent/service MUST expose typed `list`, `find`, `create`, `rename`, `archive`, and `merge` operations. User input MUST NOT directly create, rename, archive, or merge registry entries.

#### Scenario: Create a distinct project
- GIVEN an authorized agent request with a unique slug and purpose
- WHEN `create` executes
- THEN one active registry entry is created

#### Scenario: Purpose deduplication is uncertain
- GIVEN purpose candidates do not establish reuse or creation
- WHEN `create` or semantic `find` is requested
- THEN approval is required and neither action silently proceeds

### Requirement: Stable rename and atomic artifact migration

`rename` MUST preserve the stable slug, record the new name as an alias, and atomically migrate all namespace references without orphaned or duplicated artifacts. Rename MUST pass through the mandatory rename valve.

#### Scenario: Approved rename
- GIVEN a project with SDB artifacts and an approved rename
- WHEN `rename` commits
- THEN the slug remains stable, the alias is auditable, and every artifact has exactly one valid namespace reference

#### Scenario: Rename cannot complete safely
- GIVEN migration validation fails
- WHEN `rename` is attempted
- THEN no registry or artifact change is committed

### Requirement: Merge preserves target and rejects active runs

`merge` MUST preserve the target project, record the source as an auditable alias, and atomically consolidate source artifacts without duplication. It MUST reject source/target merges when either has an active SDB run and MUST pass the mandatory merge valve.

#### Scenario: Merge with no active runs
- GIVEN approved source and target projects with no active SDB runs
- WHEN `merge` commits
- THEN target identity is preserved and source history is auditable

#### Scenario: Merge during active SDB
- GIVEN either project has an active SDB run
- WHEN `merge` is requested
- THEN it is rejected and artifacts remain unchanged

### Requirement: Namespace selection is approval-safe

Semantic reuse or creation MUST require explicit approval containing a SHA-256 digest and a 15-minute TTL, followed by SDB `APPROVE`; ambiguity MUST never silently select a namespace.

#### Scenario: Approved semantic selection
- GIVEN bounded candidates and a non-expired matching approval
- WHEN SDB `APPROVE` is received
- THEN the approved namespace is selected

#### Scenario: Expired or absent approval
- GIVEN semantic selection has no valid approval
- WHEN namespace selection is attempted
- THEN selection is blocked and the user is asked to resolve ambiguity

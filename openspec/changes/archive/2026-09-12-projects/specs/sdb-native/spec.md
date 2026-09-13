# Delta for sdb-native

## ADDED Requirements

### Requirement: SDB-5 — Project propagation through the existing seam

The SDB runtime MUST propagate the selected authorized project through the existing parameterized seam without changing the seven phases or recovery semantics. Writes MUST retain `scope="panel"`, thread or cross-thread entity identity, and run keys `sdb:{run_id}:{kind}`. `sdb:spec|state|result` MUST remain semantic categories, not literal key replacements; project-level artifacts MAY use `sdb:project:{kind}`.

#### Scenario: Run artifact isolation
- GIVEN an SDB run selects an authorized project
- WHEN SPEC, STATE, or RESULT is persisted
- THEN the project reaches the memory seam with panel scope and the run-specific key

#### Scenario: Cross-thread or project-level artifact
- GIVEN a run records a cross-thread entity or project-level evidence
- WHEN the artifact is persisted
- THEN entity identity is preserved and a project-level artifact uses `sdb:project:{kind}` only when needed

#### Scenario: Phase and recovery compatibility
- GIVEN a project-aware run is interrupted
- WHEN it resumes
- THEN the existing seven-phase flow and checkpoint recovery behavior are unchanged

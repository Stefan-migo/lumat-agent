# Delta for sdb-native

## MODIFIED Requirements

### Requirement: SDB-1 — Seven-Phase Execution and Fail-Closed Triggers

The system MUST execute SDB work in `CLARIFY → SPEC → PLAN → APPROVE → EXECUTE → VERIFY → DELIVER`. Entry MUST require either a valid structured planner classification, an authenticated admin request, or an approved closed Cortex session supplied as SPEC. Malformed or conflicting trigger signals MUST fail closed without entering SDB.
(Previously: only planner classification or an authenticated admin request could enter SDB.)

#### Scenario: Classified SDB request
- GIVEN the planner emits a valid SDB classification
- WHEN the trigger gate evaluates the turn
- THEN the run enters CLARIFY and records the normalized trigger

#### Scenario: Explicit admin request
- GIVEN an authenticated admin requests SDB
- WHEN the trigger gate evaluates the turn
- THEN the request selects SDB and the non-SDB result is not executed

#### Scenario: Closed Cortex SPEC
- GIVEN a closed Cortex report and administrator approval
- WHEN the handoff enters SDB
- THEN the report is consumed as the SPEC and the run proceeds through APPROVE

#### Scenario: Conflicting trigger signals
- GIVEN trigger fields are malformed or contradictory
- WHEN the trigger gate evaluates the turn
- THEN SDB does not start and bounded clarification or normal response is recorded

### Requirement: SDB-4 — Approval, Verification, and Durable Recovery

The system MUST reuse the existing exact-plan approval and atomic execution claim. APPROVE MUST cover the canonical phase/task plan derived from either a native SPEC or an approved Cortex report, and VERIFY MUST compare persisted outputs with that SPEC before DELIVER. Resume MUST continue from the last successful checkpoint without repeating completed tasks. A Cortex handoff MUST deliver only an approved plan where execution is unavailable.
(Previously: SDB accepted only native SPEC input and did not define Cortex handoff delivery.)

#### Scenario: Changed SPEC after approval
- GIVEN the SPEC or canonical task plan changes after approval
- WHEN execution or verification is requested
- THEN approval is rejected and delivery does not occur

#### Scenario: Resume after interruption
- GIVEN a run stops after a persisted task checkpoint
- WHEN the thread is resumed
- THEN only incomplete work continues

#### Scenario: Stub execution remains truthful
- GIVEN an approved Cortex-derived plan
- WHEN the run reaches its available delivery boundary
- THEN the result is labeled an approved plan and does not claim execution

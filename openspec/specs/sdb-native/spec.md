# SDB Native Specification

## Purpose

Define SDB as the normal panel assistant loop with a deterministic, isolated verification step when required.

## Requirements

### Requirement: SDB-11 — Normal Assistant Loop with Conditional Verification

SDB MUST use the normal assistant planning and execution loop (`plan → execute`), including its existing tool-loop behavior. It MUST NOT route a turn through a separate seven-phase SDB subgraph. After the execution loop, the system MUST evaluate the verification gate and, when it fires, run verification before final response and evidence collection.

#### Scenario: Effectful normal-loop request

- GIVEN a request is planned and executed by the normal assistant loop
- WHEN the execution loop finishes
- THEN the system evaluates whether verification is required before producing the final response and evidence

#### Scenario: Verification is not required

- GIVEN the verification gate does not fire
- WHEN the normal execution loop finishes
- THEN the turn proceeds to its final response and evidence without an SDB phase sequence

### Requirement: SDB-12 — Deterministic Verification Gate

The system MUST run verification if and only if at least one of these conditions holds: the turn dispatched an effect tool named `memory.update`, `memory.delete`, `automation.create_rule`, `project.create`, `project.rename`, `project.archive`, or `project.merge`; the request explicitly asks for verification; or the request carries the authenticated admin handoff flag `sdb_requested`. `memory.write` alone MUST NOT trigger verification. The gate MUST be determined from executed tool steps and trusted request fields, never inferred from free text.

#### Scenario: Effect tool dispatched

- GIVEN at least one executed step dispatched a listed effect tool
- WHEN the verification gate is evaluated
- THEN verification runs, regardless of whether `memory.write` was also dispatched

#### Scenario: Memory write alone

- GIVEN the only dispatched effect is `memory.write`
- AND the request does not explicitly ask for verification or carry the admin handoff flag
- WHEN the verification gate is evaluated
- THEN verification does not run

#### Scenario: Explicit verification request

- GIVEN the request explicitly asks for verification
- WHEN the verification gate is evaluated
- THEN verification runs even if no listed effect tool was dispatched

#### Scenario: Admin handoff

- GIVEN the authenticated request carries `sdb_requested`
- WHEN the verification gate is evaluated
- THEN verification runs without relying on planner classification or request prose

#### Scenario: Free-text mention is not a trusted trigger

- GIVEN request text mentions SDB or verification but no explicit verification signal or admin handoff flag is present
- WHEN the verification gate is evaluated
- THEN free text alone does not trigger verification

### Requirement: SDB-13 — Observable Success Criterion

A plan containing an effect step MUST include an observable `success_criterion` that can be evaluated against execution evidence or independent read-only observations. If the criterion is missing or not observable, verification MUST return `unverifiable`, and the turn MUST be qualified rather than reported as a silent success.

#### Scenario: Observable criterion supplied

- GIVEN a plan contains an effect step and an observable `success_criterion`
- WHEN verification begins
- THEN the verifier evaluates that criterion against the available execution evidence

#### Scenario: Criterion missing or not observable

- GIVEN a plan contains an effect step without an observable `success_criterion`
- WHEN verification begins
- THEN verification returns `unverifiable` and the response qualifies the outcome

### Requirement: SDB-14 — Isolated Read-Only Verifier

Verification MUST run in a separate verifier with fresh context. Its complete input MUST be limited to the success criterion, executed steps (tool names and arguments), and their results or evidence. It MUST NOT receive conversation history, thread state, memory, or parent context. The verifier MAY call at most two bounded read-only tools to independently confirm the effect, under the same read-only scope rules as delegation. It MUST NOT write or dispatch an effect tool.

#### Scenario: Verifier receives bounded evidence only

- GIVEN a verification run has a criterion and execution evidence
- WHEN the verifier is invoked
- THEN it receives only the criterion, executed tool-and-argument steps, and their results or evidence

#### Scenario: Independent bounded confirmation

- GIVEN execution evidence alone is insufficient to evaluate the criterion
- WHEN the verifier performs independent confirmation
- THEN it may use no more than two bounded read-only tool steps under delegation read-only scope rules

#### Scenario: Verifier attempts a write or exceeds its read bound

- GIVEN the verifier attempts a write or requests more than two read-only tool steps
- WHEN the verifier scope is enforced
- THEN the operation is refused and no write is dispatched

### Requirement: SDB-15 — Truthful Qualified Verification Outcomes

Verification MUST report an explicit outcome. If verification flags a discrepancy, the turn MUST complete with a qualified response that reports the effect ran and identifies `verification: failed` with a reason. The system MUST NOT automatically retry the effect and MUST NOT present a failed or unverifiable verification as silent success.

#### Scenario: Verification finds a discrepancy

- GIVEN an effect ran and verification flags a discrepancy
- WHEN the turn completes
- THEN the response reports that the effect ran and includes `verification: failed` with the reason
- AND the effect is not automatically retried

#### Scenario: Verification cannot establish the criterion

- GIVEN verification is `unverifiable`
- WHEN the turn completes
- THEN the response is qualified and does not claim verified success

#### Scenario: Verification confirms the criterion

- GIVEN verification independently confirms the observable criterion
- WHEN the turn completes
- THEN the response may report the effect as verified and include its evidence

### Requirement: SDB-16 — Explicit Admin Handoff Signal

The admin handoff is optional and MUST be triggered only by the explicit authenticated admin request flag `sdb_requested`. The system MUST NOT infer handoff from free text or planner classification. The obsolete `sdb_classification` trigger remnant MUST NOT be part of the handoff contract. Existing tool security and whitelist enforcement, approval, audit, and project-boundary guarantees remain governed by the normal assistant and tool specifications and MUST continue to apply.

#### Scenario: Explicit admin handoff requested

- GIVEN an authenticated admin request carries `sdb_requested`
- WHEN the assistant evaluates the handoff
- THEN it applies the handoff contract and retains the normal assistant execution and tool safeguards

#### Scenario: Handoff inferred from prose or planner output

- GIVEN prose or planner output suggests SDB but the explicit admin flag is absent
- WHEN the assistant evaluates the handoff
- THEN no admin handoff is triggered

#### Scenario: Existing execution safeguards

- GIVEN a handoff turn dispatches a tool
- WHEN the normal assistant and tool specifications govern execution
- THEN their whitelist, approval, audit, and project-boundary guarantees remain in force

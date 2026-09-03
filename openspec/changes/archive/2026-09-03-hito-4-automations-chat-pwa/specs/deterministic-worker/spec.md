# Deterministic Worker Specification

## Purpose

Process durable inbound work in bounded, lease-safe, repeatable units.

## Requirements

### Requirement: DW-1 — Bounded Work Claiming

The worker MUST claim at most the configured batch limit, MUST use an expiring ownership lease, and MUST make expired work claimable again.

#### Scenario: Batch limit

- GIVEN more pending events than the configured limit
- WHEN one worker cycle runs
- THEN it claims no more than that limit

#### Scenario: Expired lease recovery

- GIVEN a claimed event whose lease has expired
- WHEN another cycle runs
- THEN the event can be claimed again without concurrent ownership

### Requirement: DW-2 — Repeat-Safe Processing

The worker MUST mark successful processing once, MUST retain failure state for retry, and MUST NOT apply a successful side effect twice when a claim is retried.

#### Scenario: Successful event

- GIVEN a claimed event with a valid handler
- WHEN processing succeeds
- THEN it is completed and a repeated cycle does not reapply its side effect

#### Scenario: Handler failure

- GIVEN a claimed event whose handler fails
- WHEN processing ends
- THEN the failure is recorded and the event remains eligible under retry policy

### Requirement: DW-3 — Explicit Entrypoint

The system MUST provide a runnable worker entrypoint that performs bounded cycles and MUST expose health-visible counts for pending, failed, and leased work.

#### Scenario: Worker invocation

- GIVEN the worker entrypoint is invoked
- WHEN it processes a cycle
- THEN it exits or waits according to its configured mode without unbounded work

#### Scenario: Health visibility

- GIVEN pending and failed work exists
- WHEN worker health is requested
- THEN the counts are returned without processing additional work

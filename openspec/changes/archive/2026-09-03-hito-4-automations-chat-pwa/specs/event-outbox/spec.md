# Event Outbox Specification

## Purpose

Persist domain events for bounded, repeat-safe downstream processing without requiring an external broker.

## Requirements

### Requirement: EO-1 — Durable Event Publication

The system MUST persist an event with type, entity reference, payload, occurrence time, and processing status before exposing it for consumption.

#### Scenario: Event is available after commit

- GIVEN a successful message, case, or appointment transition
- WHEN the transaction completes
- THEN one corresponding durable event is available for processing

#### Scenario: Failed transaction emits nothing

- GIVEN a transition transaction rolls back
- WHEN an event consumer checks the outbox
- THEN no event for that uncommitted transition is available

### Requirement: EO-2 — Idempotent Event Identity

The system MUST assign a stable event identity and MUST NOT create duplicate logical events for the same source transition.

#### Scenario: Duplicate publication

- GIVEN the same source transition is published twice
- WHEN the outbox persists both requests
- THEN one logical event remains and its identity is stable

#### Scenario: Operation linkage

- GIVEN an event causes a notification operation
- WHEN the operation is created
- THEN the operation records the originating event identity for audit and deduplication

# Notifications Specification

## Purpose

Provide durable, attributable WhatsApp and SMTP notification operations.

## Requirements

### Requirement: NT-1 — Durable Delivery Operation

The system MUST record recipient, channel, rendered content, source entity, idempotency key, status, attempts, and timestamps before delivery. Duplicate keys MUST NOT cause duplicate sends.

#### Scenario: Idempotent send
- GIVEN a pending operation with an idempotency key
- WHEN the same operation is submitted twice
- THEN one logical delivery is recorded and repeated submission is safe

#### Scenario: Channel failure
- GIVEN a delivery adapter returns an error
- WHEN the operation is processed
- THEN the failure is recorded and the operation remains retryable

### Requirement: NT-2 — Bounded Reminders and Retries

The system MUST process due reminders and retryable operations through a bounded, ownership-controlled sweep, with a maximum retry policy and auditable exhaustion.

#### Scenario: Due reminder
- GIVEN an eligible appointment and due reminder
- WHEN the sweep runs
- THEN one notification operation is created or advanced idempotently

#### Scenario: Retry exhaustion
- GIVEN repeated delivery failures reach the configured limit
- WHEN the next sweep runs
- THEN the operation is marked permanently failed and is not retried again

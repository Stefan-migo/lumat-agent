# Notifications Specification

## Purpose

Provide durable, attributable WhatsApp and SMTP notification operations.

## Requirements

### Requirement: NT-1 — Durable Delivery Operation

The system MUST record recipient, channel, rendered content, source entity, originating event when applicable, idempotency key, status, attempts, and timestamps before delivery. Duplicate keys MUST NOT cause duplicate sends, including event fan-out or push delivery.
(Previously: durable WhatsApp/SMTP operations did not include event linkage, fan-out, or push.)

#### Scenario: Idempotent send

- GIVEN a pending operation with an idempotency key
- WHEN the same operation is submitted twice
- THEN one logical delivery is recorded and repeated submission is safe

#### Scenario: Channel failure

- GIVEN a delivery adapter returns an error
- WHEN the operation is processed
- THEN the failure is recorded and the operation remains retryable

#### Scenario: Event fan-out

- GIVEN one eligible domain event matches multiple policy-valid notification channels
- WHEN fan-out runs
- THEN each permitted channel has one linked operation and no duplicate logical send

### Requirement: NT-2 — Bounded Reminders and Retries

The system MUST process due reminders and retryable operations through a bounded, ownership-controlled sweep, with a maximum retry policy and auditable exhaustion. Push operations MUST follow the same retry and audit guarantees without replacing emergency fallback.
(Previously: bounded retries covered the existing reminder and WhatsApp/SMTP operation paths.)

#### Scenario: Due reminder

- GIVEN an eligible appointment and due reminder
- WHEN the sweep runs
- THEN one notification operation is created or advanced idempotently

#### Scenario: Retry exhaustion

- GIVEN repeated delivery failures reach the configured limit
- WHEN the next sweep runs
- THEN the operation is marked permanently failed and is not retried again

#### Scenario: Emergency fallback preserved

- GIVEN an emergency notification's preferred delivery fails
- WHEN retry or fallback processing runs
- THEN the existing emergency delivery and acknowledgement guarantees remain auditable

### Requirement: NT-3 — Read State and Push

The system MUST expose authenticated notification read state independently from delivery status. It MAY deliver browser push for supported permission/browser combinations, MUST record its result, and MUST use policy-aware WhatsApp/SMTP fallback when push is unavailable or fails.
(Previously: no notification-center read state or browser push channel existed.)

#### Scenario: Read state does not alter delivery

- GIVEN a delivered notification
- WHEN an authorized user marks it read
- THEN read state changes while delivery status and attempt history remain unchanged

#### Scenario: Unsupported push

- GIVEN push is unsupported, denied, or unavailable
- WHEN a push-eligible notification is processed
- THEN fallback delivery is attempted according to policy and the outcome is audited

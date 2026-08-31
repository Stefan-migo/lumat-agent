# Operator Messaging Specification

## Purpose

Define safe, attributable operator text replies through Meta WhatsApp.

## Requirements

### Requirement: OM-1 — Authorized outbound reply

An authenticated `admin` or `operador` MUST send non-empty text only for a `human` conversation; the system MUST persist the outbound message with actor, request key, and status before/around delivery.

#### Scenario: Reply is delivered
- GIVEN an authorized operator, human conversation, and open customer window
- WHEN valid text is submitted
- THEN one attributable outbound row is persisted and Meta delivery is attempted

#### Scenario: Invalid or unauthorized reply
- GIVEN an anonymous user, forbidden role, non-human conversation, or blank text
- WHEN a reply is submitted
- THEN it is rejected, no Meta call occurs, and the attempt is audited

### Requirement: OM-2 — Latest inbound 24-hour policy

The backend MUST calculate eligibility from the latest customer inbound message, not operator activity or `last_message_at`; outside the window it MUST reject free text without persistence or Meta delivery.

#### Scenario: Stale window
- GIVEN the latest customer inbound is older than 24 hours
- WHEN free text is submitted
- THEN the API returns a policy error and records the rejection

### Requirement: OM-3 — Delivery, retry, and idempotency

Each request key MUST identify one conversation/text operation; concurrent or repeated submissions MUST return the same durable result and MUST NOT duplicate Meta sends. States MUST distinguish pending, sent, and failed; retry MUST be explicit and allowed only for failed delivery.

#### Scenario: Meta failure and retry
- GIVEN a claimed outbound operation and a transient Meta failure
- WHEN the operator retries it
- THEN the failed row is reused, one new delivery attempt is made, and the final state/wamid/error is persisted

### Requirement: OM-4 — Migration and audit

Required assignment/outbound fields and constraints MUST be added by an idempotent migration; all commands, denials, delivery outcomes, and retries MUST be append-only audited with actor, conversation, cause, and request key.

#### Scenario: Existing database upgrade
- GIVEN an H1 database with existing conversations/messages
- WHEN migrations run once or repeatedly
- THEN existing rows remain readable and new constraints/columns are available without duplicate schema objects

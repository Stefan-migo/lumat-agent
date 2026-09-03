# Calendar Integration Specification

## Purpose

Provide a narrow, non-authoritative calendar boundary for local bookings.

## Requirements

### Requirement: CI-1 — Stable Calendar Identity

The system MUST export or synchronize a local appointment through a provider boundary with a stable UID, idempotency key, timezone, and cancellation state. Local scheduling MUST remain authoritative.

#### Scenario: Repeat synchronization
- GIVEN an unchanged appointment is synchronized twice
- WHEN both requests are processed
- THEN one external calendar identity is retained and no duplicate event is created

#### Scenario: Cancellation export
- GIVEN a locally cancelled appointment
- WHEN its calendar representation is synchronized
- THEN the external event is cancelled or marked cancelled

### Requirement: CI-2 — Visible Partial Failure

The system MUST retain the local appointment when an external calendar operation fails, record a visible pending/failed status, and permit retry or reconciliation.

#### Scenario: Provider unavailable
- GIVEN a valid local appointment and an unavailable provider
- WHEN synchronization runs
- THEN booking remains intact and failure is auditable and retryable

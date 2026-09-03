# Proposal: Hito 3 Scheduling and Notifications

## Intent

Provide scheduling and notifications. Today `agendado` is only a state; appointments, availability, calendar integration, templates, and durable operations are absent. Preserve emergency safety/audit guarantees.

## Scope

### In Scope
- Local services, technician availability, fixed-duration appointments, timezone/DST rules, transactional conflicts, cancellation/rebooking, and case/customer linkage.
- Narrow ICS/provider boundary with stable UIDs, idempotency, visible sync status, and partial-failure handling.
- Versioned templates and durable, auditable WhatsApp/SMTP operations with bounded cron/sweep reminders and retries.
- Authenticated panel/API scheduling, notification, template, calendar actions.

### Out of Scope
- Payments, broad catalog expansion, PWA, internal owner/admin chat, and H4 event-bus/automation infrastructure.
- Google Calendar as source of truth, unconstrained recurring availability, or reimplementation of H1/H2 foundations.

## Capabilities

### New Capabilities
- `service-scheduling`: Local appointments, availability, conflicts, lifecycle, timezone, history.
- `calendar-integration`: ICS/provider boundary, identity, sync, and failures.
- `notifications`: Durable channel operations, retries, idempotency, reminders, and audit.
- `notification-templates`: Versioned templates and policy rendering.

### Modified Capabilities
- `customer-records`: Link scheduled visits to customer/case history.
- `admin-panel`: Expose authorized scheduling, notification, template, and calendar operations.
- `emergency-detection`: Share delivery primitives without weakening its guarantees.

## Approach

Persist local state and enforce conflicts transactionally. Isolate ICS/provider behavior behind an adapter. Render versioned templates into durable attempts; process reminders/retries through an owned, locked cron/sweep with visible failures. Strict TDD remains active (`pytest tests/`; applicable web tests and `npx tsc -b`); RDD remains enabled. Delivery: `auto-chain`, 400-line budget.

Graphify: queries covered `Case`, `Message`, `models.py`, `services/cases.py`, `send_emergency_notification()`, `services/send.py`, and panel APIs/routes. Seams support proposal; no unsupported milestone-to-notification edge was inferred.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/models.py`, `db/migrations/` | New | Domain records. |
| `app/services/`, `app/main.py`, `app/ops/` | Modified | Services and sweeps. |
| `app/panel/`, `web/src/` | Modified | Authenticated workflows. |
| `tests/`, `web/src/**/*.test.*` | New | TDD and regressions. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| External writes/delivery are non-transactional | High | Idempotency, reconciliation, retries, audit. |
| DST, conflicts, or duplicate workers fail | Med | Canonical timezone, constraints/locking, ownership. |
| Generic delivery weakens emergencies | Med | Preserve contract and regression tests. |

## Rollback Plan

Ship reversible chained slices. Disable new triggers/adapters, retain emergency delivery, and revert additive code without rewriting existing rows.

## Dependencies

- Existing PostgreSQL/FastAPI panel, WhatsApp/SMTP adapters, cron ownership, and justified ICS/provider client.

## Success Criteria

- [ ] Appointments prevent conflicts and preserve timezone, lifecycle, idempotency, and audit.
- [ ] Calendar failures are visible/retryable without losing local bookings.
- [ ] Notifications/templates are durable, attributable, compliant, and safely swept.
- [ ] Emergency guarantees remain green under backend/web tests and typecheck.

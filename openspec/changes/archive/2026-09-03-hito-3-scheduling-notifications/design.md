# Design: Hito 3 Scheduling and Notifications

## Technical Approach

Additive PostgreSQL tables and thin FastAPI/SQLAlchemy services extend the existing panel. Local appointments are authoritative; ICS/provider synchronization is a narrow, idempotent side effect. UTC instants retain the submitted IANA local representation. Immutable template versions render into durable operations before delivery; a bounded, advisory-locked sweep handles reminders, retries, and reconciliation. No H4 event bus/automation, Google source of truth, internal owner/admin chat, PWA, payments, or catalog expansion is introduced.

## Architecture Decisions

| Option | Tradeoff | Decision |
|---|---|---|
| Local schedule vs Google source | Sync state is required, but OAuth would make Google authoritative | Local source of truth; provider adapter only |
| Generic worker vs bounded sweep | Worker/event bus expands into H4 | Small `app/ops` sweep with lock and batch limits |
| Mutable vs immutable templates | Mutation breaks reproducible audit | Append versions and record the selected version |
| Generic emergency flow vs dedicated fast path | Shared delivery risks delaying safety | Reuse compatible audit/delivery primitives, but EM-4 stays immediate and non-blocking |

## Data Flow

```text
Panel/API -> scheduling -> appointment + audit -> ICS/provider -> sync status
                         \-> template policy/render -> durable operation
Sweep -> locked due operations -> WhatsApp/SMTP -> attempts/audit
Emergency graph -> immediate safety reply + owner/technician attempt (no wait)
```

Migration `011_h3_scheduling.sql` adds bounded availability, appointments, calendar status, template versions, and notification operations. Foreign keys require customer and case; `tstzrange` exclusion constraints reject overlapping active technician/customer bookings atomically. Booking rejects nonexistent/ambiguous DST times; cancellation/rebooking append history.

EM-4 sends the configured owner/technician the customer number, known location, and emergency context, explicitly requiring acknowledgement, and flags the case escalated. It attempts immediately without scheduling, calendar sync, retry, or sweep; the safety reply always completes. Every attempt is audited, failures remain visible/retryable, and acknowledgement state is preserved.

Template rendering rejects missing required variables before creating any sendable operation. Channel-policy rejection (WhatsApp approval or SMTP policy) likewise creates no sendable operation; WhatsApp-policy failures are audited. Valid operations persist recipient, channel, rendered content, source, template version, idempotency key, status, attempts, and timestamps before adapters run.

## File Changes

| File | Action | Description |
|---|---|---|
| `db/migrations/011_h3_scheduling.sql` | Create | Tables, constraints, indexes, grants. |
| `app/models.py` | Modify | Scheduling, sync, template, operation models. |
| `app/services/{scheduling,calendar,notifications,templates}.py` | Create | Domain rules, adapter, durable delivery, policy rendering. |
| `app/services/notify.py`, `app/chat/nodes/emergency.py` | Modify | Preserve EM-4 payload, escalation, ack, audit, retry, and non-blocking reply. |
| `app/ops/sweep.py`, `app/main.py` | Create/modify | Owned bounded sweep entry. |
| `app/panel/api/`, `web/src/` | Modify | Authorized H3 actions and operational error/status views. |
| `tests/`, `web/src/**/*.test.*` | Create/modify | Strict RED-GREEN traceability coverage. |

## Interfaces / Contracts

```python
class CalendarProvider(Protocol):
    def sync(self, appointment: Appointment, *, uid: str, idempotency_key: str) -> ProviderResult: ...
```

## Testing Strategy

| Layer | Traceability |
|---|---|
| Backend | RED tests map SS-1/2 (DST, lifecycle, conflicts), CI-1/2 (UID, cancellation, provider failure), NT-1/2 (idempotency, retry exhaustion), NTP-1/2 (approved render, missing-variable no-operation, SMTP/WhatsApp policy rejection and audited WhatsApp failure), and EM-4 (number/location/context, acknowledgement requirement, escalation, immediate non-blocking reply, retry/audit failure). |
| API/UI | Functional tests map CR-8 visit/lifecycle chronology and unlinked rejection; AP-10 auth/audit and AP-11 conflict, calendar, notification, and template-policy operational errors with actionable status. Run `pytest tests/`, applicable web tests, and `npx tsc -b`. |

## Threat Matrix

| Boundary | Applicability | Safe/failure behavior | Planned RED tests |
|---|---|---|---|
| Documentation-like paths | N/A — no executable classification | None added | None |
| Git repository selection | N/A — no Git automation | No repository selection | None |
| Commit state | N/A — no commit automation | No index mutation | None |
| Push state | N/A — no push automation | No ref mutation | None |
| PR commands | N/A — no PR automation | No command composition | None |

The sweep is application-level scheduling, not a shell/subprocess/VCS process-integration boundary.

## Migration / Rollout

Additive and reversible; retain existing emergency rows and disable only new provider/sweep triggers on rollback. Deliver auto-chained slices under the 400-line budget.

## Open Questions

- [ ] Confirm initial service/technician seed data and canonical timezone.
- [ ] Confirm first external provider beyond ICS export.

## Graph Notes

Consulted `GRAPH_REPORT.md` (3,052 nodes, 6,389 edges, 233 communities; built at `f09fba0b`). Nodes: `Case`, `Customer`, `Message`, `models.py`, `send_emergency_notification()`, `_audit_notification()`, `services/cases.py`, `app/panel/*`, `main.py`, `AuditLog`, `sweep_received()`. Edges: `send_emergency_notification() -> _audit_notification()`; `services/cases.py -> send_emergency_notification()`; `main.py -> sweep_received()`; `Customer -> customer_history()`; `app/panel/* -> panel/deps.py`. No unsupported H3 milestone edge was inferred.

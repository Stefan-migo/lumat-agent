## Exploration: H3 Scheduling and Notifications

### Current State
LumatAgent currently has a FastAPI/SQLAlchemy/PostgreSQL backend and a state-based panel. The existing model supports customers, conversations, cases, messages, audit rows, and a customer state named `agendado`, but it has no appointment, availability, technician, calendar-event, ICS, or reservation-conflict model. `Case.service` is a free-text classification field rather than a service catalog.

Outbound delivery is split between the generic text primitive in `app/services/send.py` and the narrowly scoped emergency implementation in `app/services/notify.py`. The latter sends one approved WhatsApp utility template (`emergency_alert`), falls back to SMTP email, audits attempts, and performs emergency acknowledgements/reminder sweeps. There is no reusable notification/template registry, scheduling worker, or calendar integration. The application lifespan currently performs only webhook recovery; no scheduler is registered. Dependencies contain no Google Calendar or ICS library.

The canonical H3 boundary is calendar/ICS integration, service scheduling, notifications, and notification templates. The broader roadmap's payments, catalog expansion, and unrelated H4 automation/event-bus capabilities are not part of this change. Existing H1/H2 customer, case, message, audit, authentication, and Meta delivery behavior should be treated as foundations, not reimplemented.

Graph Check completed before code inspection. Consulted graph report: 3,052 nodes, 6,389 edges, 233 communities; graph built from commit `f09fba0b` and therefore structural context only. Relevant queried nodes included `Milestone 3 - Servicios, agendamiento e integraciones`, `Case`, `Message`, `services/cases.py`, `notify.py`, `send_emergency_notification()`, `services/send.py`, `models.py`, `app/panel/* — admin panel routes/templates`, and `Quality Metrics`. Consulted edges included `Case <--imports-- notify.py --contains--> send_emergency_notification()`, `Case <--imports-- services/cases.py <--rationale_for-- Cases service`, and the five-hop `Message` → `run_conversation()` → `test_chat_capture.py` → `db.py` → `send.py` path. Directed paths from the milestone to notification nodes were unavailable; no edge was inferred.

### Affected Areas
- `app/models.py`, `db/migrations/` — add the smallest durable representation for services, appointments, technicians/availability, notification attempts/templates, and integration metadata while preserving existing rows and audit constraints.
- `app/services/cases.py`, `app/services/customers.py` — connect a scheduled visit to the existing case/customer history without conflating a case's free-text `service` with a future catalog or appointment record.
- `app/services/send.py`, `app/services/notify.py`, `app/services/settings.py` — reuse Meta/SMTP primitives and emergency behavior while introducing generic, attributable template/channel delivery and retry semantics.
- `app/main.py`, `app/ops/` and deployment/cron documentation — provide a bounded trigger for reminders and delivery retries; avoid silently turning H3 into the H4 worker/event-bus system.
- `app/panel/api/`, `app/panel/routes/`, `web/src/` — expose authenticated scheduling, conflict/error states, notification/template administration, and calendar/ICS actions through the existing state-based panel rather than a new router.
- `tests/` and `web/src/**/*.test.*` — prove conflict prevention, timezone/ICS correctness, notification idempotency, authorization, external failure behavior, and regression of emergency notifications.
- `pyproject.toml` — evaluate whether an ICS/Google client dependency is justified; the current dependency set has neither.

### Approaches
1. **Local scheduling source of truth with ICS/provider boundary** — persist services, technicians, availability, appointments, and notification operations locally; enforce conflicts transactionally; generate/import ICS through a narrow adapter and add Google Calendar synchronization only behind that boundary.
   - Pros: local customer history and audit remain authoritative; deterministic conflict checks; ICS works without locking the domain to Google; external failures can be retried without losing a booking.
   - Cons: synchronization state and provider reconciliation must be specified; timezone and recurring-availability rules need explicit limits.
   - Effort: High

2. **Google Calendar as scheduling source of truth** — create and update Google events first, then mirror event identifiers and status into Lumat; use Google availability for conflict checks.
   - Pros: less calendar UI/storage to build; technicians can use an existing calendar immediately.
   - Cons: OAuth, permissions, quota, webhook/poll reconciliation, and partial-failure handling become core dependencies; local audit and customer history can lag or disagree; ICS remains secondary.
   - Effort: Very High

### Recommendation
Use a local scheduling source of truth with a narrow ICS/export and calendar-provider boundary. Start with fixed-duration appointments, explicit timezone handling, technician availability/blocks, database-backed conflict prevention, and an integration status that makes external synchronization failures visible. Represent notifications as durable, auditable operations rendered from versioned templates; keep WhatsApp approved-template rules and SMTP as channel-specific adapters. Use a simple scheduled sweep/cron trigger for reminders and retries, not a new event bus or generalized worker. This keeps H3 coherent, preserves rollback, and avoids importing H4 infrastructure prematurely.

### Risks
- External calendar writes and message delivery are non-transactional; idempotency keys, reconciliation, and visible pending/failed states must be designed before implementation.
- Calendar correctness depends on one canonical timezone, DST behavior, appointment duration, technician availability, cancellation/rebooking semantics, and ICS UID stability.
- WhatsApp business-initiated notifications require approved templates and may be outside the customer-service window; template/channel policy must be enforced server-side.
- A scheduler embedded in application startup can duplicate work across processes; trigger ownership and locking must be explicit.
- Existing emergency notification behavior is safety-sensitive; generic notification refactoring must not weaken its never-block-the-safety-reply or audit guarantees.
- The working tree already contains unrelated dirty changes in `web/`, `web/public/`, and `graphify-out/`; H3 artifacts and later implementation must not attribute or overwrite them.

### Ready for Proposal
Yes. The proposal should first lock the local-vs-external source-of-truth decision, H3 exclusions (payments, broad catalog work, H4 automation/event bus), timezone/ICS compatibility contract, notification delivery/idempotency policy, and the bounded reminder trigger. Then it can split implementation into reviewable slices under the 400-line budget.

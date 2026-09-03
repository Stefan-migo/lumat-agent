# Tasks: Hito 3 Scheduling and Notifications

## Review Workload Forecast

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|---|---|---|---|---|---|
| 1 | Scheduling, DST, conflicts, history | PR 1 | `pytest tests/ -k scheduling` | API booking flow | migration/models/service/tests |
| 2 | ICS identity and template policy | PR 2 | `pytest tests/ -k 'calendar or template'` | provider stub | calendar/templates/tables |
| 3 | Delivery, retries, sweep, EM-4 | PR 3 | `pytest tests/ -k 'notification or emergency'` | channel fakes | notify/ops/emergency |
| 4 | Panel/API, history, UI | PR 4 | `pytest tests/ && cd web && npm test && npx tsc -b` | authenticated flow | H3 routes/components/stories |

## Phase 1: Foundation and Scheduling (PR 1)

- [x] 1.1 **RED:** test SS-1/2 and CR-8: required links, lifecycle history, availability, atomic technician/customer conflicts, cancellation freeing slots, nonexistent/ambiguous DST rejection, and unlinked no-partial-history rejection.
- [x] 1.2 **GREEN:** create `db/migrations/011_h3_scheduling.sql`, models in `app/models.py`, and `app/services/scheduling.py` for IANA/UTC-local time, ranges, actor history, cancel/rebook, and availability.
- [x] 1.3 **RED → GREEN:** test then wire AP-10 booking authorization/audit and AP-11 conflict status in authenticated `app/panel/api/` endpoints; unauthorized requests make no changes.

## Phase 2: Calendar and Templates (PR 2)

- [x] 2.1 **RED:** test CI-1/2 stable UID/idempotency, timezone/cancellation export, provider failure retaining booking, visible retry; test NTP-1/2 approved rendering, missing-variable no-operation, WhatsApp rejection/audit, immutable versions.
- [x] 2.2 **GREEN:** implement `app/services/calendar.py` (`CalendarProvider`) identity/status/reconciliation and `app/services/templates.py` immutable version/policy rendering.
- [x] 2.3 **GREEN:** expose calendar/template actions and actionable errors in `app/panel/api/`; audit mutations.

## Phase 3: Durable Notifications and Emergency (PR 3)

- [x] 3.1 **RED:** test NT-1/2 durable pre-delivery fields, duplicate-key single send, adapter retry, due-reminder idempotency, advisory-lock bounds, and permanent exhaustion/audit.
- [x] 3.2 **GREEN:** implement `app/services/notifications.py`, attempts/idempotency, `app/ops/sweep.py`, and bounded owned entry in `app/main.py`.
- [x] 3.3 **RED:** extend `tests/integration/test_emergency_notify.py` for EM-4 number/location/context, acknowledgement, escalation, immediate non-blocking safety reply, failure visibility/retry/audit, and preserved ack.
- [x] 3.4 **GREEN:** update `app/services/notify.py` and `app/chat/nodes/emergency.py` to reuse compatible primitives while bypassing scheduling/calendar/retry waits; implement acknowledgement persistence.

## Phase 4: History, Panel, and Verification (PR 4)

- [x] 4.1 **RED → GREEN:** test and expose CR-8 chronological visit/lifecycle history in `app/panel/api/routes/clients.py` and serializers, preserving conversation/case records.
- [x] 4.2 **RED → GREEN:** test and wire AP-10/11 authenticated actions, unauthorized no-op, and actionable conflict/calendar/notification/template-policy statuses in `app/panel/api/` and `web/src/` views/tests/stories.
- [x] 4.3 Run `pytest tests/`, `cd web && npm test`, `cd web && npx tsc -b`, and applicable Storybook build; verify all 21 scenarios/RDD receipts, then refactor green code.

Graph Check nodes: `Customer`, `Case`, `Message`, `models.py`, `main.py`, `app/panel/*`, emergency/sweep tests. Edges: emergency→audit, main→sweep, customer→history, panel→deps.

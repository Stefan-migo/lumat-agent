# ODD — notificaciones-panel

## Objective

Make the panel bell functional end-to-end: produce `panel_notifications` rows for a curated
set of events (fan-out to every admin), deliver them live over the existing panel WebSocket,
and keep the existing campana / Notification Center UI as the render surface.

## Problem

The campana and Notification Center read real data from `GET /panel/api/notifications`, but
nothing ever produces rows:

- `app/services/notifications.py:129-143` — `create_operation()` only adds a `PanelNotification`
  when `operation.user_id is not None`, and no production caller passes `user_id`.
- `app/services/notifications.py:146-154` — `create_panel_notification()` has no production
  caller (only tests use it).
- `web/src/components/domain/AppShell.tsx:50-61` — `listNotifications()` runs once on mount;
  no polling or WebSocket, so a new row never appears without a reload.
- `panel_notifications.operation_id` is `NOT NULL` FK to `notification_operations`
  (`app/models.py:843`, `db/migrations/016_h4_notification_center.sql:11`).

Result: the bell is always empty, in dev and prod.

## Why

The owner has never seen a notification while testing. The feature was declared done, but the
producer was never wired. This unit closes that gap for the events that are actionable and
low-frequency, without making the panel noisy.

## Scope (authorized by the owner)

**In:**

- `app/services/notifications.py`: a `notify_admins(...)` helper that creates one carrier
  `NotificationOperation` (`channel="panel"`) and fans out one `PanelNotification` per admin,
  idempotently.
- `app/services/scheduling.py`: call the helper on `appointment.booked`, `cancelled`,
  `rescheduled`, and `no_show`.
- `app/chat/nodes/emergency.py`: call the helper when an emergency is detected.
- `app/services/realtime.py`: add `"notification"` to the `RealtimeEnvelope.type` literal.
- `web/src/realtime.ts` and `web/src/components/domain/AppShell.tsx`: subscribe and update the
  unread badge live.
- Tests for fan-out, idempotency, and the realtime envelope.
- `odd/tasks/notificaciones-panel.md`: this unit record.

**Out:** database migrations, push/PWA notifications, `message.received` / `case.created` /
`case.updated` notifications, `appointment.completed` and automation notifications (deferred
panel-only), the roadmap M1 categories Técnicos / Sistema / Reportes, and any recipient logic
beyond "all admins".

## Decisions

- **D1 — Event set v1:** `emergencia` + `appointment.booked` / `cancelled` / `rescheduled` / `no_show`.
  Everything else is out (noise or no signal).
- **D2 — Recipients:** every user with `UserRole.ADMIN` (fan-out: one row per admin).
- **D3 — Producer:** synchronous and transactional — the row is created in the same commit as
  the event, not in the worker tick.
- **D4 — `operation_id NOT NULL`:** no migration. One carrier `NotificationOperation`
  (`channel="panel"`, a status the sweep ignores) anchors the fan-out via
  `UNIQUE(user_id, operation_id)`; idempotency key `panel:{dedupe}`. This reactivates the
  currently dead `create_panel_notification()`.
- **D5 — Refresh:** reuse the existing panel WebSocket with a new `"notification"` envelope type.

Source: `.rapsodia-code/sessions/ready-for-odd/2026-10-09-notificaciones-panel/report.md`.

## Constraints

- No DB migration; server may be single-process (the panel WebSocket is process-local).
- Fan-out must be idempotent: a replayed event must not double-notify.
- Operator-facing UI copy stays Spanish. Code, comments, task documentation, and commit
  messages are English.
- Do not push, open a PR, or merge; those are the owner's decisions.
- Commit as reviewable work units; keep tests with the code they cover.

## Graph check

Consulted `graphify-out/GRAPH_REPORT.md` and ran
`graphify query "notifications panel bell campana"`. Nodes consulted: `notifications`,
`PanelShell.tsx`, `AppShell.tsx`, `PanelNotification` (`web/src/types.ts:167`),
`NotificationsPopover.stories.tsx`, `api.ts`, `useAsyncData`. Backend modules inspected directly:
`app/services/notifications.py`, `app/services/realtime.py`, `app/services/scheduling.py`,
`app/chat/nodes/emergency.py`, `app/panel/api/routes/realtime.py`. Graph refresh runs once at
session close.

## Tasks

| ID | Task | Route |
|----|------|-------|
| T1 | `notify_admins(...)` helper in `app/services/notifications.py`: carrier op + admin fan-out, idempotent. Reuse `create_panel_notification`. | delegated writer |
| T2 | Call the helper on the 4 appointment events in `app/services/scheduling.py`. | delegated writer |
| T3 | Call the helper in `app/chat/nodes/emergency.py` when an emergency is detected. | delegated writer |
| T4 | Add `"notification"` to `RealtimeEnvelope.type` and publish it from the helper. | delegated writer |
| T5 | Frontend: handle `notification` in `web/src/realtime.ts`; `AppShell.tsx` subscribes and updates the unread badge. | delegated writer |
| T6 | Tests: fan-out to N admins, idempotency/dedupe, realtime envelope; commit units. | delegated writer |

## Delivery

Single PR against `main`. Forecast ~250–320 authored changed lines (well under ~400). No chained
slices. `chained-pr` not required unless the running count crosses the budget.

## Checks

- Backend focused: `uv run pytest tests/integration/test_h4_notifications.py -q` and any new tests.
- Backend suite: `uv run pytest -q` (integration tests need their DB).
- Frontend tests: `npm --prefix web run test`.
- Frontend typecheck + build: `npm --prefix web run build` (`tsc -b` lives only inside `build`).
- TDD mode: not configured for this project — run ordinary functional checks.

## Progress / Evidence

- [x] T1 helper `notify_admins` — commit `e082efad` (`feat(notifications): fan out transactional panel alerts`)
- [x] T2 appointment events wired — commit `d120c026` (`feat(scheduling): notify admins of appointment outcomes`)
- [x] T3 emergency wired — commit `02f0d8d8` (`feat(emergency): surface incidents in the admin panel`)
- [x] T4 realtime envelope type — commit `e082efad` (`feat(notifications): fan out transactional panel alerts`)
- [x] T5 frontend subscription + badge — commit `da02cf6a` (`feat(web): refresh notification badge from realtime`)
- [x] T6 fan-out, replay, envelope, and appointment outcome tests — commits `e082efad`, `d120c026`, `2146c335`, and `da02cf6a`

Verification evidence (orchestrator re-run; PostgreSQL on `localhost:5761` up, web dependencies installed):

- `uv run pytest tests/integration/test_h4_notifications.py tests/integration/test_h4_automations.py -q`: 14 passed.
- `uv run pytest -q`: 1844 passed in 398.54s.
- `npm --prefix web run build`: green (`tsc -b` + `vite build`).
- `npm --prefix web run test`: this branch adds no failures — the same 8-file set fails the same 3
  pre-existing `ClientFicha` tests on `origin/main` and on the branch. The full-suite 46-report was
  parallel-load flakiness; running the affected files in isolation reproduces only the base 3.

Post-writer corrections (commits `d9f20f48`, `245b9f4e`, `947ed57a`):

- carrier operation now uses `source_entity="panel"` / `source_id="panel:<id>"` so it cannot collide
  with appointment operations read by source; the shared `source_entity="appointment"` had broken 4
  reminder tests.
- `AppShell` subscription cleanup returns `void` (it returned a `boolean`-returning unsubscribe, which
  failed `tsc -b`).
- the automations fan-out test now asserts 6 rows (booked x3, rescheduled, cancelled, no_show) instead
  of 4.

Graph check for implementation: queried notification production/delivery, scheduling publishers,
emergency handling, and the AppShell realtime subscription. Consulted nodes: `create_operation`,
`create_panel_notification`, `stage_event`, `NotificationOperation`, `book`, `cancel`, `close`,
`reschedule`, `publish_event`, `emergency`, `send_emergency_notification`, `RealtimeClient`,
`RealtimeEnvelope`, `listNotifications`, and `AppShell`. Confirmed `book -> publish_event` and
`stage_event -> dispatch_staged_events` is the commit dispatch path; ambiguous/no-directed-path
queries between separate helper/client nodes returned no graph path and were not used as proof.

## Next step

Delivered as **PR #552** (`https://github.com/Stefan-migo/lumat-agent/pull/552`) against `main`.
Merge is the owner's decision.

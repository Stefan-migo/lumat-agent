# Design: Panel Agenda / Calendar UI

## Technical Approach

Add a bounded, authenticated range read to the existing appointments API and render it in a native History API `AgendaPage`. Local scheduling remains authoritative; the SPA groups server-ordered rows into `Hoy` and `Próximas` and uses existing table, feedback, and dialog primitives. No grid, availability UI, booking/editing, rebooking, ICS download, permissions, or new dependency is introduced.

Graph nodes consulted: `appointments.py`, `scheduling.py`, `serializers.py`, `Appointment`, `AppointmentCalendarSync`, `panel/deps.py`, `PanelShell.tsx`, `AppShell.tsx`, `panelRoutes.ts`, `ClientFicha.tsx`, `NotificationCenter.tsx`, `calendar_templates.py`, `notifications.py`, `DataTable`, `PageFrame`, `StateMessage`, and `toneMaps.ts`. Relevant communities were appointments, scheduling, serializers, panel shell, ClientFicha, notifications, and calendar templates; no directed route-to-page path exists because `AgendaPage` is new.

## Architecture Decisions

| Option | Tradeoff | Decision |
|---|---|---|
| Bounded `GET /panel/api/appointments?from=&to=&timezone=` | Explicit date semantics and one read model | Choose; place before `/{appointment_id}`. |
| Service-owned range query | Keeps ORM and DST rules out of the thin route | Choose `list_for_range(session, from_date, to_date, timezone_name)`. |
| Joined read with left sync join | Avoids N+1 and preserves local rows without sync | Choose customer/case/technician joins plus nullable sync projection. |
| Browser-only timezone conversion | DST boundaries can disagree | Reject; server validates IANA zone and owns UTC bounds. |

## Data Flow and Contracts

`AgendaPage → listAppointments() → authenticated route → scheduling.list_for_range() → agenda serializer → Hoy/Próximas rows`. Local midnight at `from` is inclusive and midnight after `to` exclusive; ranges over 31 calendar days, reversed dates, and unknown zones return `invalid_range` or `invalid_timezone` without writes. Order is `local_start, id`; cancelled rows remain visible. Each row includes display joins, local/UTC times, lifecycle status, and independent `sync {status,error,retry}`. Missing sync is pending/retryable. Existing cancel and `/calendar/sync` actions preserve audit, UID/idempotency, and lifecycle.

AP-11 resolution: H3 already exposes booking conflicts as the actionable `409 appointment_conflict` contract (`test_operator_can_book_and_conflict_is_actionable`); Agenda has no create/rebook control, so it adds no conflict endpoint or duplicate conflict workflow. Agenda renders each persisted lifecycle status (including cancelled/non-booked states) and renders cancellation/sync mutation errors inline, keeping lifecycle and sync badges separate. ClientFicha already renders calendar errors and retry. Failed notification status/retry is owned by the existing notification-operations API and NotificationCenter/notification surfaces; template-policy errors are owned by the existing template render API (`template_policy_rejected`) and template surface. Agenda does not duplicate those signals. Shared visibility contract: status/error/action codes remain stable snake_case API values, and shared tone maps provide consistent lifecycle, sync, notification, and policy labels across surfaces.

## Mandatory Slices (auto-chain stacked-to-main; each targets ≤400 authored lines)

| Slice | Mandatory boundary | Requirements | Files and tests |
|---|---|---|---|
| 1 | Backend read contract | CI-3 | `app/services/scheduling.py`, `app/panel/api/routes/appointments.py`, `app/panel/api/serializers.py`, `tests/functional/test_api_scheduling.py`; RED then auth, bounds/DST, joins/order, cancelled, missing/failed sync tests. |
| 2 | Page, route, navigation, API types | AG-UI-1, AG-UI-2 | `web/src/types.ts`, `web/src/api.ts`, `web/src/components/domain/{panelRoutes,PanelShell,AppShell}.tsx`, new `AgendaPage.tsx`, route/AppShell tests, page state tests; mandatory loading/empty/error/forbidden/stale, table, grouping, and mobile structure. |
| 3 | Mutations and status language | AG-UI-3, AG-UI-4, AP-11 agenda scope | `AgendaPage.tsx`, `toneMaps.ts`, `AgendaPage.test.tsx`; RED then booked-only confirmed cancel/reason/refresh and pending/failed sync retry/refresh, keyboard actions, separate lifecycle/sync and actionable failures. |
| 4 | Storybook and final frontend gate | AG-UI-2, AG-UI-4 | `web/src/stories/pages/AgendaPage.stories.tsx` and story tests; mandatory data, loading, empty, error, permission, stale, cancel-confirmation, sync-failure/retry, keyboard, and mobile fixtures, then `npx tsc -b`, `npm run build`, and focused Vitest verification. |

## Testing Strategy

Backend uses pytest functional fixtures and session assertions. Web uses Vitest/Testing Library with same-origin fetch mocks. Stories use controlled fixtures at narrow, medium, and desktop widths. RED tests must precede implementation in every slice.

## Threat Matrix

| Boundary | Applicability | Safe/failure behavior | Planned RED tests |
|---|---|---|---|
| Documentation-like paths | N/A — no file execution | None | None |
| Git repository selection | N/A — no VCS automation | None | None |
| Commit state | N/A — no commit automation | None | None |
| Push state | N/A — no push automation | None | None |
| PR commands | N/A — no PR command execution | None | None |

Routing is applicable: malformed/unknown SPA paths retain dashboard fallback; canonical `/panel/app/agenda` is operator-visible. RED tests cover parser fallback, deep link, `aria-current`, and role-gated rendering.

## Migration / Rollout

No migration or flag. Each slice is independently revertible; rollback removes Agenda route/nav/page while retaining H3 APIs.

## Open Questions

None.

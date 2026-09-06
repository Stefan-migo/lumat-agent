# Proposal: Panel Agenda / Calendar UI

## Intent

Give authenticated Lumat operators one operational view of scheduled visits. H3 has detail, cancellation, and sync actions but no global read path.

## Scope

### In Scope
- Add one bounded, authenticated appointment-range endpoint with explicit IANA timezone, stable ordering, customer/case/technician display joins, local/UTC times, lifecycle status, and sync status/error/retryability.
- Add an Agenda route and navigation entry using a chronological responsive table/list with **Hoy** and **Próximas** sections.
- Support cancellation with explicit confirmation/reason and calendar-sync retry for pending/failed records; refresh after mutations and show actionable failures.
- Cover loading, empty, error, permission, keyboard, mobile, and Storybook states.

### Out of Scope
- Month-grid calendar, availability-block/slot UI, creation/editing/rebooking forms, selectors, ICS download, and external links.
- New permissions; local scheduling remains authoritative.

## Capabilities

### New Capabilities
- `agenda-calendar-ui`: Agenda presentation, range semantics, lifecycle/sync visibility, and supported actions.

### Modified Capabilities
- `admin-panel`: Agenda surface plus authorized cancellation and sync-retry visibility.
- `calendar-integration`: Existing sync state exposed in the agenda read model; provider failure remains visible and retryable.

## Requirements Sketch

- Range reads are authenticated, bounded, timezone-explicit, ordered, and display-ready.
- Lifecycle and calendar-sync states are separate; provider failure never hides a valid local appointment.
- Cancellation is limited to booked appointments, confirmed, audited, and followed by refresh.

## Approach and Assumptions

Extend the appointments panel API with the minimal range query and serializer, joining names server-side because no global source exists. Build the SPA with existing page/table/feedback/dialog primitives and native History API routing. “Today” uses the request IANA timezone. Admin and operador retain current H3 access. Cancelled rows remain visible as status; “Retry calendar” invokes existing server-side sync. Delivery is auto-chain, stacked to main, in 2–3 slices: read contract; page/routing; actions and verification.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/panel/api/routes/appointments.py`, serializers | Modified | Range contract. |
| `web/src/components/`, `web/src/api.ts`, `web/src/types.ts` | New/Modified | Route, page, API types/actions. |
| `tests/functional/`, `web/src/**/*.test.*`, stories | New/Modified | Contract and state coverage. |

## Risks

| Risk | Mitigation |
|------|------------|
| Timezone/DST misdisplay | Server-owned IANA range semantics and labels. |
| Sync failure confused with booking failure | Separate badges; retain row and retry. |
| Cancellation surprise | Confirmation, reason, audit, and refresh. |

## Rollback Plan

Revert the additive route/page and hide Agenda navigation; retain existing H3 endpoints and data unchanged.

## Dependencies

- Existing H3 models/services, authenticated panel API, primitives, and PostgreSQL.

## Success Criteria

- [ ] Operators understand today/upcoming visits, timezone, identities, lifecycle, and sync state.
- [ ] Cancel/retry are authorized, audited, and recoverable.
- [ ] Tests, typecheck/build, responsive, and accessibility states pass.

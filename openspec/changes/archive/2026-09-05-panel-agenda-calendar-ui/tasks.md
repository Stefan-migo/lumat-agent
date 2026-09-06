# Tasks: Panel Agenda / Calendar UI

## Review Workload Forecast

| Slice | Estimated authored lines | Risk | PR boundary |
|---|---:|---|---|
| 1 | 220 | Low | PR 1: backend range contract |
| 2 | 300 | Low | PR 2: route, navigation, page, API types |
| 3 | 220 | Low | PR 3: mutations and tones |
| 4 | 180 | Low | PR 4: stories and frontend gate |
| Total | 920 | High overall | Four stacked PRs |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|---|---|---|---|---|---|
| 1 | CI-3 range read | PR 1 | `uv run pytest tests/functional/test_api_scheduling.py` | pytest PostgreSQL | Revert backend files |
| 2 | AG-UI-1/2 page shell | PR 2 | `cd web && npm test -- panelRoutes AppShell AgendaPage` | Vitest jsdom | Revert route/nav/page/API files |
| 3 | AG-UI-3/4 actions | PR 3 | `cd web && npm test -- AgendaPage toneMaps` | Vitest + userEvent | Revert mutation/tone files |
| 4 | Story matrix/gate | PR 4 | `cd web && npx tsc -b && npm run build` | Storybook fixtures | Revert stories/tests |

## Phase 1: Slice 1 — Backend Range Read Contract (CI-3)

- [x] 1.1 RED: extend `tests/functional/test_api_scheduling.py` for auth, joins/order, local+UTC/DST, cancelled/missing/failed sync, invalid ranges, and no mutation.
- [x] 1.2 Add `list_for_range()` in `app/services/scheduling.py` with IANA, bound, ordering, and nullable-sync rules.
- [x] 1.3 Add the range GET before `/{appointment_id}` in `app/panel/api/routes/appointments.py`; serialize it in `app/panel/api/serializers.py` and pass tests.

## Phase 2: Slice 2 — Agenda Page, Routing, Navigation, API Types

- [x] 2.1 RED: add route/AppShell tests for deep link, malformed-path fallback, operator visibility, `aria-current`, and role gating.
- [x] 2.2 RED: add `AgendaPage` tests for loading, empty, error/forbidden, stale recovery, Hoy/Próximas, semantic table, and mobile structure.
- [x] 2.3 Extend `PanelView`, `PANEL_ROUTES`, `NAVIGATION`, and `AppShell` dispatch in `panelRoutes.ts`, `PanelShell.tsx`, and `AppShell.tsx`.
- [x] 2.4 Add range types in `web/src/types.ts`, `listAppointments()` in `web/src/api.ts`, and create `AgendaPage.tsx` with existing primitives.

## Phase 3: Slice 3 — Cancellation, Retry, Status Tones

- [x] 3.1 RED: in `AgendaPage.test.tsx`, prove booked-only cancel/reason/refresh, no non-booked request, sync retry/refresh, separate labels, keyboard actions, and errors.
- [x] 3.2 Add Dialog cancellation and existing cancel/sync calls in `AgendaPage.tsx`; refresh and show inline failures.
- [x] 3.3 Extend `web/src/components/shared/toneMaps.ts` with appointment lifecycle/sync labels and tones; make Slice 3 tests pass.

## Phase 4: Slice 4 — Storybook Matrix and Frontend Verification

- [x] 4.1 RED: add `AgendaPage.stories.test.tsx` assertions for data, loading, empty, error, permission, stale, cancel, sync failure/retry, keyboard, and mobile.
- [x] 4.2 Create `web/src/stories/pages/AgendaPage.stories.tsx` with controlled widths and the AG-UI-2/4 matrix; pass story tests.
- [x] 4.3 Run `cd web && npx tsc -b && npm run build && npm test -- AgendaPage panelRoutes AppShell`; confirm no out-of-scope controls.

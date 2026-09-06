## Exploration: Panel Agenda / Calendar UI

### Current State

#### Backend H3 surface

The panel JSON router is mounted below `/panel` and the H3 routers are included in `app/panel/api/__init__.py`; therefore the effective paths below are `/panel/api/...`. Every scheduling and calendar endpoint depends on `require_user_json`, so unauthenticated requests receive JSON `401` responses and do not mutate state.

| Method and path | Current contract | UI implication |
|---|---|---|
| `GET /panel/api/availability/{technician_id}?starts_at=<datetime>&ends_at=<datetime>` | Returns `{technician_id, starts_at, ends_at, available}`. It checks whether one interval is covered by an enabled `TechnicianAvailability` block. Invalid/non-positive intervals return `400`. | This is an interval probe, not a range/block listing; the UI cannot render a complete availability calendar from it alone. |
| `POST /panel/api/appointments` | Body: `{service, customer_id, case_id, technician_id, local_date, local_time, timezone, duration_minutes}`. Success: `{ok: true, appointment: <appointment serializer>}`. `400` covers unlinked customer/case and invalid or DST-ambiguous local time; `409` uses `appointment_conflict` or `technician_unavailable`. | Supports create, but the UI needs customer/case/technician selection contracts that do not currently exist in the H3 API. |
| `GET /panel/api/appointments/{appointment_id}` | Returns `{appointment: {id, service, customer_id, case_id, technician_id, local_start, timezone, starts_at, ends_at, duration_minutes, status, history[]}}`. History entries contain `id, actor, action, from_status, to_status, details, created_at`. | There is no appointment list/range endpoint and the appointment serializer does not embed calendar sync state. |
| `POST /panel/api/appointments/{appointment_id}/cancel` | Body `{reason?: string}`. Success returns `{ok: true, appointment: ...}`. Missing appointment is `404`; non-booked lifecycle is `409` with `invalid_lifecycle`. | Supports cancellation, but needs confirmation and a refresh/update strategy. |
| `POST /panel/api/appointments/{appointment_id}/calendar/sync` | Creates or updates the local ICS sync row. Returns `{ok: boolean, calendar: {id, appointment_id, provider, uid, idempotency_key, status, timezone, cancelled, error, attempts, retry, synced_at}}`. Provider failure keeps the appointment and returns a retryable `failed` status. | This is the only calendar action. There is no ICS download endpoint, external-calendar URL, or separate retry endpoint. |

Additional template endpoints (`POST/GET /panel/api/templates`, `POST /panel/api/templates/{id}/render`) exist in `calendar_templates.py`, but they are notification-template administration, not agenda display data. There is no `/appointments` collection endpoint, date-range query, technician directory endpoint, availability-block endpoint, or ICS payload download endpoint.

The authoritative domain model is local. `Appointment` stores service, customer/case/technician foreign keys, naive `local_start`, IANA `timezone`, UTC-aware `starts_at`/`ends_at`, fixed duration, status, and timestamps. `AppointmentHistory` preserves lifecycle actors/actions. `AppointmentCalendarSync` stores stable UID/idempotency key, provider status (`pending`/`synced`/`failed`), cancellation, error, attempt and sync timestamps. `scheduling.book()` validates linked customer/case, DST-safe local time, configured availability, and overlapping booked appointments for either technician or customer. `scheduling.cancel()` only cancels booked appointments and records audit/history/events.

`GET /panel/api/clients/{customer_id}` is currently the only collection-like way for the frontend to obtain appointments. `customers.customer_history()` returns that customer's appointments ordered by `starts_at`, plus `visit_history` sorted by event timestamp. It includes `calendar_status` and `calendar_error`, which is why `ClientFicha` can show the current integration failure. It is not suitable as a global agenda source because it requires one customer ID and returns all customer history.

#### Frontend SPA structure

`web/src/main.tsx` loads token and primitive CSS, mounts `app.tsx` in `StrictMode`, and registers the PWA. `app.tsx` is the authentication gate: it probes `/panel/api/me`, renders `LoginAuth` for `401`, and renders `AppShell` for an authenticated user.

`AppShell.tsx` owns the native History API route state. `PanelRoute` currently supports a `PanelView` plus optional client or conversation drill-down IDs. The top-level views are `dashboard`, `clients`, `conversations`, `cases`, `notifications`, `push`, `chat`, `kb`, and `settings`. `pathForRoute()`/`parsePanelPath()` canonicalize paths under `/panel/app/`; only clients and conversations accept positive nested IDs. `AppShell` maps views to page components and uses `navigateToRoute()` for client ficha and conversation-thread drill-downs. Browser back/forward is handled with `popstate`; no client-side router dependency is used.

`PanelShell.tsx` renders the persistent sidebar, mobile drawer, collapse control, signed-in context, and page header. Navigation is a `Record<PanelView, NavigationItem>` filtered by `user.role`; admin-only items are `chat`, `kb`, and `settings`. The current shipped navigation has no Agenda item. Adding the view requires extending the `PanelView` union, route map/parser, page dispatch, and `NAVIGATION` map, with an icon and Spanish label. Operators currently see all non-admin views, so Agenda would naturally be operator-visible unless a new server/UI permission contract says otherwise.

Appointments are currently shown only inside the client ficha history. `ClientFicha` loads `/panel/api/clients/{id}` and `/memories`, renders visits as a simple list, shows lifecycle history, and POSTs `/appointments/{id}/calendar/sync` for the `Reintentar calendario` action. It does not create or cancel appointments. `types.ts` has `Appointment` and `VisitHistoryEvent` types, but no collection/range response type or availability-block type.

#### Existing design-system assets

The production shared layer is ready for a data-oriented page:

- `PageFrame` and `PageHeader` provide page title, metadata, actions, and region-level state.
- `DataTable` provides semantic tables, empty/loading/stale states, row actions, row keys, and numeric alignment support.
- `StatCard` can summarize today/upcoming/conflict counts only when backed by real data.
- `EmptyState` and `StateMessage` cover empty, loading, permission, warning, danger, and retry-oriented feedback.
- `Card` provides meaningful containment; `Badge` and `StatusBadge` provide labeled state indicators.
- `Button`, `Dialog`, `Tabs`, `Select`, `Input`, `FieldShell`, and `SearchInput` are available for actions/filters/forms without a new dependency.
- `toneMaps.ts` is the existing translation boundary for raw backend states. It has no appointment-status map yet; appointment labels/tone mapping should be added only with the Agenda consumer.

`web/src/components/primitives/primitives.css` and `tokens/tokens.css` are the executable styling foundation. `DESIGN_SYSTEM.md` requires starting from OpenSpec behavior, reusing tokens/primitives, designing the complete permission/recovery state model, keeping code in English and UI copy in neutral Chilean Spanish, and verifying Storybook at narrow/medium/desktop widths with keyboard and failure states. It specifically requires loading, empty, stale, disabled, error, success, and permission coverage; semantic table markup; visible labels; no color-only status; and no new dependency when native/platform behavior is sufficient. A calendar grid is therefore not automatically implied by the design system.

#### Test setup and conventions

The frontend uses Vitest 3 with jsdom and Testing Library (`cd web && npm test`), with `npx tsc -b` as the type check. Existing route tests assert the full route table and invalid-path normalization. Page tests mock `globalThis.fetch`, use `waitFor` for async loading, `userEvent` for actions, and verify exact same-origin API requests including `credentials: include` and JSON headers. Story page tests preserve controlled-data wrappers and exercise loading, empty, lifecycle, failure, and retry behavior. AppShell and PanelLinks tests verify navigation labels, role filtering, and URL/history behavior.

Backend tests use pytest with shared authenticated `client` and `make_user` fixtures for functional API contracts, `SessionLocal` for database assertions, and integration tests against migrated PostgreSQL fixtures. Scheduling tests directly exercise service invariants (linked records, availability, conflicts, cancellation/rebooking); API tests assert status codes, actionable error codes, authorization, and no mutation on unauthorized access. The archived H3 verification reports the full suite and frontend suite as green, but no global-agenda API/UI contract exists yet.

### Affected Areas

- `app/panel/api/routes/appointments.py` — existing create/get/cancel/availability contracts; no list or date-range read endpoint.
- `app/panel/api/routes/calendar_templates.py` — existing calendar sync action and returned operational sync status.
- `app/panel/api/serializers.py` — appointment and calendar payload shapes; appointment detail omits calendar sync.
- `app/services/scheduling.py`, `app/services/calendar.py` — authoritative booking, availability probe, lifecycle, conflict, and ICS/provider behavior.
- `app/services/customers.py`, `app/panel/api/routes/clients.py` — current customer-scoped appointment/history read path and its limited serializer shape.
- `app/models.py` — `TechnicianAvailability`, `Appointment`, `AppointmentHistory`, and `AppointmentCalendarSync` persistence contracts.
- `web/src/components/domain/panelRoutes.ts` — route union, path map, parser, and canonicalization.
- `web/src/components/domain/AppShell.tsx` — top-level page dispatch and navigation handlers.
- `web/src/components/domain/PanelShell.tsx` — `PanelView`, sidebar navigation, role filtering, header label/icon.
- `web/src/components/pages/ClientFicha.tsx`, `web/src/types.ts` — existing ficha-only appointment display and calendar retry contract.
- `web/src/api.ts` — thin same-origin fetch layer where appointment list/detail/action functions would belong.
- `web/src/components/shared/`, `web/src/components/primitives/`, `web/DESIGN_SYSTEM.md` — reusable page/table/feedback/action contracts.
- `web/src/components/**/*.test.tsx`, `web/src/components/domain/panelRoutes.test.ts`, `tests/functional/test_api_scheduling.py`, `tests/integration/test_scheduling.py` — established verification patterns.
- `openspec/changes/archive/2026-09-03-hito-3-scheduling-notifications/specs/{service-scheduling,calendar-integration,customer-records,admin-panel}/spec.md` — H3 business requirements and acceptance scenarios.

### Gap Analysis

A dedicated Agenda view needs a read model/API before it can be implemented cleanly. The requested “today’s + upcoming appointments” cannot be assembled efficiently or safely from the current customer ficha endpoint. The minimum contract should define a date/range query, stable ordering, timezone semantics, customer display fields, case/service, technician display fields, appointment status, start/end/local representation, and calendar sync status/error/retryability. It should explicitly define whether cancelled appointments are included and whether the range is interpreted in a requested IANA timezone.

Availability currently answers only “is this exact interval available for this technician?” It does not expose configured blocks, unavailable blocks, technicians, or a slot grid. An availability section therefore requires either a new range/block endpoint or a deliberately read-only interval-probe UI with a known technician and duration. Rendering availability without that contract would invent data.

The H3 business contract requires:

- local scheduling remains authoritative;
- appointments link to valid customer and case records;
- local time and IANA timezone survive DST rules, with nonexistent/ambiguous times rejected;
- booked overlaps for the same technician or customer are atomically rejected;
- cancellation frees the slot and preserves lifecycle history;
- calendar sync has stable UID/idempotency key, timezone and cancellation state;
- provider failures retain the booking, expose a visible failed/pending state, and allow retry;
- authorized mutations are audited and unauthorized reads/mutations make no changes.

The first UI slice should therefore display agenda data and expose only actions supported by clear contracts: open customer/case context (if route contracts are chosen), cancel with explicit confirmation (if included), and retry calendar sync for failed/pending integrations. “Add to calendar” is not currently a file download; the existing action is a server-side sync that returns ICS/provider status. A direct ICS download or browser calendar link must be specified separately. Creating/editing appointments would require customer/case/technician selectors, canonical timezone and DST validation, duration rules, conflict handling, and likely a technician/availability read model; it is materially larger than a read-only agenda.

The visual choice is also open. A compact chronological list/table is directly supported by `DataTable`, works on mobile, and maps well to the current operational control-room direction. A month-grid calendar would need new layout/accessibility behavior, dense event rendering, date navigation semantics, and a range API. The current backend does not provide enough information for a useful grid without adding contracts.

### Approaches

1. **Read-only agenda list with a minimal range endpoint** — Add a server-owned appointment range/read serializer, then implement a chronological Agenda page with date navigation, today/upcoming sections, status/sync badges, customer/case links where supported, and retry/cancel actions only if explicitly approved.
   - Pros: smallest coherent slice; uses existing `DataTable`, `PageFrame`, `StateMessage`, and API patterns; mobile-friendly; exposes real H3 data without guessing availability or inventing calendar integration.
   - Cons: not a visual month calendar; needs one backend read contract and display-name joins.
   - Effort: Medium

2. **Agenda list plus interval-probe availability and booking form** — Add the range read model, technician/customer/case selection sources, and a form that calls availability before booking while handling server-side conflicts/DST errors.
   - Pros: useful operational creation flow and direct use of existing booking endpoint.
   - Cons: current APIs do not provide selection/availability-block data; preflight availability cannot replace atomic booking; significantly expands scope, test matrix, and permission questions.
   - Effort: High

3. **Month-grid calendar as the primary surface** — Add a range endpoint designed for calendar windows and implement a responsive accessible grid, with event drill-down and sync/cancel actions.
   - Pros: familiar calendar mental model and strong date navigation.
   - Cons: new interaction surface and accessibility burden; backend lacks range, technician, customer display, and block contracts; likely needs a new calendar component rather than existing primitives.
   - Effort: High

### Recommendation

Recommend Approach 1 for this change: a dedicated, authenticated Agenda view built around a chronological list/table and a narrowly defined appointment range read contract. Start with “Hoy” plus “Próximas” (or an explicit selectable date range), show local date/time with timezone context, customer/case/service/technician identifiers, lifecycle status, and calendar sync status. Make failures actionable and persistent; do not hide a locally valid appointment because provider sync failed. Keep creation/editing, full availability-block management, and month-grid behavior out of the first slice unless the proposal explicitly expands the backend contract.

The proposal must first resolve three scope decisions: (1) read-only versus create/cancel/rebook actions, (2) list versus month-grid primary presentation, and (3) whether this change is allowed to add the required range/read endpoint. It should also define the response timezone and display-name strategy, cancellation visibility, role permissions, and whether “calendar action” means server sync/retry or a downloadable ICS artifact.

### Risks

- **Missing collection contract:** There is no global appointment list/range endpoint; using customer fichas would be incomplete and N+1-prone.
- **Availability ambiguity:** The backend exposes only an exact interval boolean and no technician/block listing, so a calendar-style availability display would otherwise be fabricated.
- **Calendar semantics:** Existing sync is a provider/ICS synchronization action, not an ICS download; UI copy must not promise a file or external calendar event unless a new endpoint is approved.
- **Display joins:** Appointment payloads contain IDs only. A useful agenda needs customer and technician names, requiring serializer/query changes or explicit ID-only UI.
- **Lifecycle actions:** Cancel is supported, but rebooking is modeled as cancel plus new booking; edit/update does not exist. Confirmation, reason, refresh, and audit feedback must be specified.
- **Timezone/DST:** Date navigation and “today” must use an explicit IANA timezone, not implicitly mix browser local time with UTC instants.
- **Role and authorization:** Existing H3 routes allow any authenticated panel user; no dedicated Agenda permission exists. UI omission/visibility must match a confirmed server policy.
- **Responsive/accessibility cost:** Month grids add keyboard navigation, announcements, narrow-screen behavior, and event-density complexity not covered by current primitives.
- **Partial integration failure:** Calendar failure must leave the local appointment visible and retryable, consistent with CI-2/AP-11.

### Graph Notes

Graph Check was completed before code inspection. Consulted `graphify-out/GRAPH_REPORT.md` (3,848 nodes, 8,238 edges, 316 communities; built from `f1618eb3`, dated 2026-09-05). Queried nodes/communities included:

- `availability()` → `app/services/scheduling.py`; `appointments.py`; `calendar_templates.py`; `Appointment`; `AppointmentCalendarSync`; `to_appointment_dict()`; `to_calendar_dict()`.
- `panelViews` / `panelRoutes.ts`; `AppShell.tsx`; `PanelShell.tsx`; `PanelView`; `ClientFicha.tsx`; page components and shared helper community.
- `scheduling.py` community; `User` community; `api/routes/clients.py`; `serializers.py`; `models.py`; `panel/deps.py`.
- `Lumat Panel Design System`; `DataTable`; `EmptyState`; `PageHeader`; `StatCard`; `shared/helpers.test.tsx`.
- H3 nodes: `Service Scheduling Spec`, `Calendar Integration Spec`, `Admin Panel Spec (H3)`, `Customer Records Spec (H3)`, `H3 Booking Lifecycle Flow`.

The requested directed `graphify path appointments AppShell` had no directed path because the selected symbols are in separate areas; the undirected relationship is represented by the shared panel/API and scheduling communities. No graph edge was inferred from that failed directed traversal.

### Ready for Proposal

Yes, with clarification recorded in the proposal rather than blocking exploration. The proposal should choose a minimal list-first Agenda, authorize the required appointment-range read contract, and explicitly decide whether cancellation/retry are in scope. It should not claim a full month calendar, availability grid, appointment creation/editing, or ICS download without corresponding backend requirements.

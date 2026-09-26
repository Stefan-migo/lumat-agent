# ODD Task: agenda-appointment-detail

Status: in progress
Worktree: `../lumat-agent-odd-agenda-appointment-detail`
Branch: `odd/agenda-appointment-detail`
Depends on: `agenda-visit-dialog` (PR #370, merged `2a85b675`)

## Objective

Close **AG-UI-5**: give the Agenda a unique page per appointment at
`/panel/app/agenda/:id`, reachable from the agenda, through native History API routing.
The surface shows the linked customer **with a link to the customer record**, the visit
reason/service, the appointment status, and the linked case's **conversation summary when
the case originates from a conversation**. A manually created case has no conversation, so
no summary is shown and the page must not fail.

## Problem

1. **The detail payload carries no display data.** `to_appointment_dict`
   (`app/panel/api/serializers.py:186-206`) returns only scalar fields: `id`, `service`,
   `customer_id`, `case_id`, `technician_id`, `local_start`, `timezone`, `starts_at`,
   `ends_at`, `duration_minutes`, `status`, `history`. No customer name, no case, no
   conversation summary. `GET /panel/api/appointments/{id}` (`app/panel/api/routes/appointments.py:71-76`)
   returns exactly that, wrapped as `{"appointment": ...}` with a 404
   `"appointment not found"`.
2. **Composing in the front is not cheaper.** There is **no `GET /cases/{id}`** route
   (`app/panel/api/routes/cases.py` has only list/create/update/ack), so front composition
   would still need a new backend route. `GET /panel/api/conversations/{id}`
   (`app/panel/api/routes/conversations.py:282-300`) returns the whole thread plus every
   message — over-fetch to read one field. `GET /panel/api/clients/{id}`
   (`app/panel/api/routes/clients.py:108-133`) returns customer + `history` + `notes` +
   `memo` + `states` — over-fetch for a name.
3. **The SPA has no per-appointment route.** `panelRoutes.ts:114` allowlists only
   `['clients', 'conversations', 'automation-rules', 'kb']`; `PanelRoute` (`:3-13`) has no
   `appointmentId`, and `pathForRoute` (`:48-71`) has no branch for it.
4. **The front has no single-appointment fetch.** `web/src/api.ts` exposes
   `listAppointments` (`:129-132`) but no `getAppointment(id)`.

## Why (approved decisions)

- **Payload decision — Option A (owner-approved this session).** Add a **dedicated detail
  serializer** used **only** by `GET /panel/api/appointments/{id}`. Do **not** widen
  `to_appointment_dict`: it is shared by four call sites — create, get-by-id, cancel
  (`app/panel/api/routes/appointments.py:68,76,89`) and the dashboard
  (`app/services/dashboard.py:237`) — and embedding customer/case/conversation there would
  turn every list and the dashboard into an N+1 join.
- **Precedent, not reuse.** `to_technician_appointment_dict`
  (`app/panel/api/serializers.py:209-229`) already embeds customer + `case_summary`, which
  sanctions the shape — but it embeds `{name, address, comuna, phone}` with **no `id`**, so
  it cannot serve the ficha link and must not be reused verbatim.
- **Which summary.** The conversation summary is `Conversation.summary`
  (`app/models.py:272-274`, nullable `Text`) resolved through `Case.conversation_id`
  (`app/models.py:341-344`, nullable; a manual case sets `None` at
  `app/services/cases.py:73-76`). It is **not** `Case.summary`.
- **Two null layers must be tolerated**, not one: (a) a case with no conversation, and
  (b) a conversation whose `summary` is still `None`. Both render no summary, and neither
  may fail the page. This is the requirement's core, and it is stated here because the
  handoff only named layer (a).

## Scope

**In:**

- `app/panel/api/serializers.py`: a new `to_appointment_detail_dict`.
- `app/panel/api/routes/appointments.py`: the detail route returns the enriched payload.
- Backend tests for the three summary states and the embedded customer/case.
- `web/src/components/domain/panelRoutes.ts`, `AppShell.tsx`, `PanelShell.tsx`: route
  parsing and rendering.
- `web/src/types.ts`, `web/src/api.ts`: `AppointmentDetail` type and `getAppointment(id)`.
- A new `AppointmentDetail` page component.
- Reachability from the agenda (a row action that navigates to the detail route).
- Storybook coverage for the named states (AG-UI-4).

**Out:** any change to `to_appointment_dict` or its list/create/cancel/dashboard callers;
edit/reschedule/cancel actions on the detail page; a new `GET /cases/{id}` route; customer
full CRUD; appointment row deletion.

## Constraints

- Work is born in this worktree on `odd/agenda-appointment-detail`; never touch `main`.
- **Strict TDD is ON** (`openspec/config.yaml:38`). RED → GREEN → REFACTOR, no exceptions.
- Runners: backend `eval "$(infra/test-db.sh env)"` then `uv run pytest tests/`; web
  `cd web && npm test` (Vitest); the only type check is `cd web && npm run build`
  (`tsc -b && vite build`). No linter, no formatter.
- `addopts = "-q"` in `pyproject.toml`: a second `-q` yields `-qq` and suppresses the
  summary line. Use `-o addopts='' -q` to see the count.
- The detail payload is **additive**: `{"appointment": {...}}` keeps every current key; the
  new keys are `customer`, `case`, `conversation_summary`.
- Never add an appointment DELETE or any hard delete.
- Operator-facing UI copy stays **Spanish**. Code, comments, docs, and commit messages are
  **English**.

## Contract (`openspec/specs/agenda-calendar-ui/spec.md`)

- **AG-UI-5** — three scenarios: (1) opening an appointment from the agenda renders
  `/panel/app/agenda/:id` with the linked customer, reason/service, and status, and the
  customer provides a link to the customer record; (2) a chatbot case shows its
  conversation summary; (3) a manually created case shows none and the page does not fail.
- **AG-UI-2** — the shared state contract (loading, empty, error, permission, stale) with
  labeled feedback and an unclipped mobile layout; the new page must carry it.
- **AG-UI-4** — Storybook coverage for the named states.
- **AG-UI-1 / AG-UI-3** — the register and its allowed actions are preserved untouched.

## Work units

### WU1 — Backend detail payload

- RED (functional API tests): a case from a conversation with a summary exposes
  `conversation_summary`; a manual case exposes `conversation_summary: null`; a
  conversation-born case whose `summary` is `None` exposes `null`; the payload embeds
  `customer {id, name}` and `case {id, conversation_id}`; an unknown id still 404s with
  `"appointment not found"`.
- Add `to_appointment_detail_dict(appointment, *, customer, case, conversation_summary)`.
- Wire only the `GET /appointments/{appointment_id}` route; leave `to_appointment_dict` and
  its callers byte-identical.
- **Verify**: focused appointment tests, then the full backend suite.

### WU2 — SPA route plumbing

- RED (AppShell / panelRoutes tests): `/panel/app/agenda/7` parses to
  `{ view: 'agenda', appointmentId: 7 }`; `pathForRoute` round-trips it; a non-positive or
  non-integer id falls back; `/panel/app/agenda` still renders the register.
- `PanelRoute.appointmentId`, the `pathForRoute` branch, the parse branch and the
  allowlist, plus the `PanelShell`/`AppShell` render switch.
- **Verify**: focused web tests, then `npm run build`.

### WU3 — AppointmentDetail page

- RED: renders the customer name as a link to `/panel/app/clients/:id`, the service, and
  the status; shows the conversation summary when present; shows **no** summary and does
  **not** fail for a manual case; shows **no** summary when the conversation has none;
  carries loading/error/denied states.
- `AppointmentDetail.tsx` mirroring `KbDocumentDetail.tsx` / `ClientFicha.tsx`
  (`useAsyncData`, controlled-data support), `types.ts`, `api.ts`.
- **Verify**: focused web tests, then `npm run build`.

### WU4 — Reachability from the agenda

- RED: the agenda offers a per-appointment action that navigates to
  `/panel/app/agenda/:id` (keyboard operable, no new destructive control).
- **Verify**: focused web tests.

### WU5 — Story coverage and full verification

- Story for the detail page covering the named states (with a conversation summary, without
  one, and the manual-case path), plus a non-vacuous interaction test.
- **Verify**: full `cd web && npm test`, `cd web && npm run build`, and
  `uv run pytest tests/ -o addopts='' -q`.

## Delivery

Forecast **~500 authored lines** (additions + deletions) across backend, web, and stories —
over the ~400-line review budget, so the native review will run on this slice.
`delivery_strategy: ask-on-risk`; the chain strategy is the owner's call before the first
commit.

## Acceptance criteria

- `/panel/app/agenda/:id` renders the linked customer with a working link to the ficha, the
  reason/service, and the status; it is reachable from the agenda.
- A chatbot case shows its conversation summary.
- A manually created case shows no summary and the page does not fail.
- A conversation-born case with no generated summary shows nothing and does not fail.
- `to_appointment_dict` and its four call sites are unchanged.
- Vitest green, `tsc -b` build green, backend suite green.

## Graph check

- `graphify-out/GRAPH_REPORT.md` — **8001 nodes / 16540 edges / 740 communities**, built
  from `2a85b675`. Community hubs touched: `AppShell.tsx`, `AgendaPage.tsx`,
  `ClientFicha.tsx`, `types.ts`, `models.py`, `scheduling.py`. God nodes `make_user()`,
  `User`.
- `graphify query "panel appointment detail payload serializer"` (785 nodes) and
  `graphify query "panel SPA route agenda appointment detail page"` (562 nodes).
- `graphify path panelRoutes.ts KbDocumentDetail.tsx --undirected` → shortest path
  **2 hops** (`panelRoutes.ts <--references-- AppShell.tsx --imports_from--> KbDocumentDetail.tsx`),
  which confirms AppShell is the single wiring point for route → page.
- Nodes consulted: `Appointment` (`app/models.py:596`), `Case` (`:334`), `Conversation`
  (`:253`), `Message` (`:279`), `Customer` (`:218`), `serializers.py`, `AppShell.tsx`,
  `AgendaPage()`, `KbDocumentDetail.tsx`, `useAsyncData()`, `types.ts`, `api.ts`,
  `SPA-DEL-1 — SPA-only bounded routing`.

## Progress

- [ ] WU1 — Backend detail payload
- [ ] WU2 — SPA route plumbing
- [ ] WU3 — AppointmentDetail page
- [ ] WU4 — Reachability from the agenda
- [ ] WU5 — Story coverage and full verification
- [ ] Owner decision: push and open the PR

## Verification (observed)

| Work unit | Command | Result |
|---|---|---|
| base | `uv run pytest tests/ -o addopts='' -q` | 1479 passed in 216.08s |
| base | `cd web && npm test` | 761 passed (87 files) |

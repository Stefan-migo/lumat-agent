# ODD Task: agenda-appointment-detail

Status: merged — PR #376 (`7fb8cd10`).
Worktree: `../lumat-agent-odd-agenda-appointment-detail`
Branch: `odd/agenda-appointment-detail`
Depends on: `agenda-visit-dialog` (PR #370, merged `2a85b675`)
Inherits from: `client-ficha-case-surface` (parallel, in flight — see "Parallel work")

## Objective

Close **AG-UI-5**: give the Agenda a unique page per appointment at
`/panel/app/agenda/:id`, reachable from the agenda, through native History API routing.
The surface shows the linked customer **with a link to the customer record**, the visit
reason/service, the appointment status, and the linked case's **conversation summary when
the case originates from a conversation**. A manually created case has no conversation, so
no summary is shown and the page must not fail.

It is also the structural home for the **per-appointment audit trail**, which the client
ficha stops owning (owner decision `visit-trail-out-of-ficha`, 2026-09-25).

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
5. **The audit trail has no home until this page exists.** `to_appointment_dict` already
   returns `history` (`serializers.py:199-205`) and `GET /appointments/{id}` already serves
   it, while the ficha's `customer_history` never did (`app/services/customers.py:302-317`).
   The ficha's flattened `<ol aria-label="Ciclo de vida de visitas">` was a workaround for
   the missing page. The owner decided the trail belongs here.

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
- **The audit trail and the ficha card link belong to this unit** (decision
  `visit-trail-out-of-ficha`, 2026-09-25): the ficha drops the flattened `<ol>` and each
  visit card becomes a link to `/panel/app/agenda/:id` once the route exists. The `<ol>` and
  the `visit_history` payload field are removed by the parallel unit
  `odd/client-ficha-case-surface` (`f8e2ea2a`, `4a9f3fb2`), **not here**.

## Scope

**In:**

- `app/panel/api/serializers.py`: a new `to_appointment_detail_dict`.
- `app/panel/api/routes/appointments.py`: the detail route returns the enriched payload.
- Backend tests for the three summary states and the embedded customer/case.
- `web/src/components/domain/panelRoutes.ts`, `AppShell.tsx`, `PanelShell.tsx`: route
  parsing and rendering.
- `web/src/types.ts`, `web/src/api.ts`: `AppointmentDetail` type and `getAppointment(id)`.
- A new `AppointmentDetail` page component, including the per-appointment audit trail
  rendered from `appointment.history`.
- Reachability from the agenda, and `ClientFicha.tsx`: each visit card links to
  `/panel/app/agenda/:id`.
- Storybook coverage for the named states (AG-UI-4).

**Out:** any change to `to_appointment_dict` or its list/create/cancel/dashboard callers;
edit/reschedule/cancel actions on the detail page; a new `GET /cases/{id}` route; customer
full CRUD; appointment row deletion; removing the ficha's `<ol>` trail or the
`visit_history` payload field (owned by `odd/client-ficha-case-surface`); the
`PATCH /appointments/{id}` mentioned in the 2026-09-25 handoff, which AG-UI-5 does not
require.

## Constraints

- Work is born in this worktree on `odd/agenda-appointment-detail`; never touch `main`.
- **Strict TDD is ON** (`openspec/config.yaml:38`). RED → GREEN → REFACTOR, no exceptions.
- Runners: backend `eval "$(infra/test-db.sh env)"` then `uv run pytest tests/`; web
  `cd web && npm test` (Vitest); the only type check is `cd web && npm run build`
  (`tsc -b && vite build`). No linter, no formatter.
- `addopts = "-q"` in `pyproject.toml`: a second `-q` yields `-qq` and suppresses the
  summary line. Use `-o addopts='' -q` to see the count.
- The detail payload is **additive**: `{"appointment": {...}}` keeps every current key; the
  new keys are `customer`, `case`, `conversation_summary`. `appointment` keeps the exact
  `to_appointment_dict` shape, `history` included. `customer` and `case` are **always
  present** (`Appointment.customer_id` and `Appointment.case_id` are `NOT NULL`,
  `app/models.py`); only `case.conversation_id` and `conversation_summary` can be `null`.
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

### WU1 — Backend detail payload — done (`f4e708e6`)

- [x] RED observed: `KeyError: 'conversation_summary'` ×3 —
      `test_appointment_detail_embeds_conversation_summary_and_related_records`,
      `test_appointment_detail_manual_case_has_no_conversation_summary`,
      `test_appointment_detail_conversation_without_summary_is_successful` → 3 failed, 8 passed.
- [x] `to_appointment_detail_dict(appointment, *, customer, case, conversation_summary)` added to
      `app/panel/api/serializers.py`, composing on `to_appointment_dict` so it stays byte-identical.
      The extra keys are siblings of `appointment`.
- [x] Only `get_appointment` changed in `app/panel/api/routes/appointments.py`: loads the customer
      and the case, resolves `Conversation.summary` only when `case.conversation_id` is set, else
      `None`; the 404 `"appointment not found"` is preserved. Create, cancel, list and the dashboard
      are untouched.
- [x] A fourth test pins `to_appointment_dict`'s exact key set, so a future widening of the shared
      serializer fails loudly.
- **Verify**: `uv run pytest tests/functional/test_api_scheduling.py -o addopts='' -q` — **11 passed**;
  `uv run pytest tests/ -o addopts='' -q` — **1483 passed** (baseline 1479 + 4), 2 warnings, 195.45s.
- **Review boundary**: `review assess --base-ref 2a85b675 --committed-only` → `medium`,
  `review_due: false`, `under_budget` (4 paths / 357 lines, the task doc included). Stays pending
  in the slice; the boundary does not advance.

### WU2 — Per-appointment route and detail page — done (`6cdf81f0`, `d48385d8`)

- [x] RED observed: `expected { view: 'dashboard' } to deeply equal { view: 'agenda', appointmentId: 1 }`,
      `expected '/panel/app/agenda' to be '/panel/app/agenda/7'`, and
      `Failed to resolve import "./AppointmentDetail"`. The pre-existing malformed-path test also went
      RED because `/panel/app/agenda/1` used to fall back to the dashboard.
- [x] `panelRoutes.ts` — `PanelRoute.appointmentId`, the `pathForRoute` branch mirroring `kb`, and
      `'agenda'` in the 4-segment allowlist. `/panel/app/agenda` still parses to the register.
- [x] `AppShell.tsx` — `appointmentId !== null ? <AppointmentDetail …/> : <AgendaPage />`. `PanelShell`
      needed **no** change: it already treats Agenda as the shell view.
- [x] `types.ts` (`AppointmentHistoryEntry`, `AppointmentDetail`), `api.ts` (`getAppointment(id)`).
- [x] `AppointmentDetail.tsx` mirrors `KbDocumentDetail`/`ClientFicha`: `useAsyncData` with
      controlled-data support, `StateMessage` loading/denied/error, customer name as a link built
      from `pathForRoute` (never a hardcoded path), status through the existing
      `appointmentStatusLabel`/`appointmentStatusTone`, the summary rendered only when non-null, and
      the audit trail from `appointment.history`.
- [x] No new CSS: the page reuses the existing `detail-region*` layout classes
      (`primitives.css:355-441`, including their responsive rule) already used by `ClientFicha` and
      `KbDocumentDetail`.
- **Verify**: focused `panelRoutes.test.ts` + `AppShell.test.tsx` + `AppointmentDetail.test.tsx` —
  **36 passed** (3 files); `cd web && npm test` — **766 passed** (88 files); `cd web && npm run build`
  — built.
- **Review boundary**: `review assess --base-ref 2a85b675 --committed-only` → `medium`,
  **`review_due: true`** / `slice_budget_reached` (12 paths / 551 lines). The consolidated review ran
  here.
- **Flake note**: one full-suite run timed out the pre-existing `AgendaPage.test.tsx` manual-case
  test; the rerun was green. Same signature the U4 record diagnosed as a timeout; not proven, and not
  caused by this unit's changes.

### WU3 — Reachability from the agenda and the ficha — done (`42c45d94`)

- [x] RED observed: `TestingLibraryElementError: Unable to find an accessible element with the role
      "link" and name "Mantención"` (the ficha assertion failed the same way) → 2 failed, 46 passed.
- [x] `AgendaPage.tsx` — the register's `Servicio` cell is now an anchor to
      `pathForRoute({ view: 'agenda', appointmentId: row.id })`, following the idiom already used by
      `ClientesList`/`KbList`/`CasesList`.
- [x] `ClientFicha.tsx` — the visit card's service, date and status badge are wrapped in one anchor to
      the same route; the calendar-retry `Button` stays **outside** the anchor, so no interactive
      control is nested. The `<ol aria-label="Ciclo de vida de visitas">` block and `visitHistory` were
      left untouched (owned by the parallel unit).
- [x] No new CSS: `table__link` is reused on both surfaces.
- **Verify**: focused `AgendaPage.test.tsx` + `ClientFicha.test.tsx` — **48 passed** (2 files);
  `cd web && npm test` — **768 passed** (88 files); `cd web && npm run build` — built.
- **Review boundary**: `review assess --base-ref d48385d8 --committed-only` → `medium`,
  `review_due: false`, `under_budget` (5 paths / 100 lines). Stays pending in the slice.

### WU4 — Story coverage and full verification — done (`071084ea`)

- [x] RED observed: `Failed to resolve import "./AppointmentDetail.stories" from
      "src/stories/pages/AppointmentDetail.stories.test.tsx"` → 1 failed, no tests.
- [x] `AppointmentDetail.stories.tsx` — six stories: `ConversationSummary` (data, summary shown),
      `ConversationWithoutSummary` (data, `conversation_id` set but summary `null`),
      `ManualCase` (data, `conversation_id: null`), `Loading`, `Error`, `Denied`.
- [x] `AppointmentDetail.stories.test.tsx` — non-vacuous: `it.each` over **both** no-summary variants
      asserts the summary is absent *and* the appointment's facts survive (customer link with the
      right `href`, service, status); the summary is asserted present in variant 1; the audit trail
      renders from `history`; the error story's retry action is wired and observable.
- [x] The story wrapper mirrors the existing per-page `maxWidth` wrapper byte-for-byte
      (`KbDocumentDetail.stories.tsx:9`, `AutomationRuleDetailPage.stories.tsx:26`,
      `AgendaPage.stories.tsx:58`). The `inline-style-boundary` policy targets production code, not
      stories.
- **Verify**: focused story test — **5 passed**; `cd web && npm test` — **773 passed** (89 files);
  `cd web && npm run build` — built; closing backend `uv run pytest tests/ -o addopts='' -q` —
  **1483 passed** in 274.01s; `git diff --check` — clean.
- **Review boundary**: `review assess --base-ref d48385d8 --committed-only` → `medium`,
  `review_due: false`, `under_budget` (7 paths / 240 lines). No second review was due.

## Native review receipt

- Transaction `review-58f45e62d3fee4de` — risk `medium`, **one** selected lens
  (`review-reliability`), correction budget 200, 12 paths / 551 lines, reviewed range
  `a98b6c06` (base) → `0524e2f8` (candidate, = HEAD `d48385d8`).
- Result **`approved`** with **zero findings**: the lens inspected every manifest path and
  recorded no blocker, critical, warning, or suggestion.
- Authority burned via `gentle-ai review acknowledge-approved` → `review-acknowledged/v1`,
  `authority: burned`, `consumed_revision: sha256:ec9b6e8e…`.
- **Scope, stated honestly**: the receipt covers the candidate at WU2 (551 lines). WU3, WU4 and
  the later doc commits are the delta after the acknowledgement; measured from the new boundary
  (`d48385d8`) they are **7 paths / 240 lines**, `under_budget`, `review_due: false` — the native
  authority judged no second review due. The PR therefore ships a body reviewed in bulk (551 lines)
  plus a measured, authority-cleared delta.

## Spec check (read-only, against the live contract)

AG-UI-5 is satisfied scenario by scenario, without launching an SDD phase:

- *Operator opens an appointment from the agenda* → WU2 routes and renders the page; WU3 makes the
  register's `Servicio` cell and the ficha's visit cards link to it; the `AppShell` test asserts the
  deep link renders and that the customer link carries the customer route in its `href`.
- *Appointment linked to a chatbot case* → WU1 resolves `Conversation.summary` through
  `Case.conversation_id`; WU2 renders it; WU4's `ConversationSummary` story and test assert it is
  visible.
- *Appointment linked to a manually created case* → WU1 proves `conversation_summary: null` with a
  passing 200; WU4's `ManualCase` story and test assert no summary **and** that the page still renders
  its facts. The extra state the handoff missed — a conversation whose summary is still `null` — is
  covered by `ConversationWithoutSummary` and its own assertion.
- AG-UI-2 → loading/denied/error states are implemented through `StateMessage` and asserted.
- AG-UI-4 → six stories covering the named states of this surface.
- AG-UI-1/AG-UI-3 → untouched; no appointment action was added beyond navigation.

## Parallel work (do not duplicate)

`odd/client-ficha-case-surface` (worktree `../lumat-agent-odd-client-ficha-case-surface`,
base `cf5f8171`, head `871e54a6`) is in flight on `ClientFicha.tsx` and already removed the
flattened `<ol>` trail (`f8e2ea2a`) and the `visit_history` payload field (`4a9f3fb2`). Its
task doc lists the per-appointment page as explicitly **out** of its scope. This unit must
not touch `visit_history` or the `<ol>`. Both branches edit `ClientFicha.tsx`, so whichever
merges second resolves a small conflict in the visit-cards region.

## Delivery

Forecast **~500 authored lines** (additions + deletions) across backend, web, and stories —
over the ~400-line review budget, so the native review will run on this slice.
`delivery_strategy: single-pr` (**owner decision, this session**): one PR against `main`,
matching U3/U4 exactly; no chained slices and no chain strategy. The ~500-line size is
accepted as ordinary repository policy; no `size:exception` label was requested.

## Acceptance criteria

- `/panel/app/agenda/:id` renders the linked customer with a working link to the ficha, the
  reason/service, the status, and the per-appointment audit trail; it is reachable from the
  agenda and from the ficha's visit cards.
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

- [x] WU0 — worktree, environment, base baselines, and this record (`425cc724`)
- [x] WU1 — Backend detail payload (`f4e708e6`) — focused 11 passed, full backend 1483 passed
- [x] WU2 — Per-appointment route and detail page (`6cdf81f0`, `d48385d8`) — focused 36 passed,
      full web 766 passed, build green; native review `approved`, receipt below
- [x] WU3 — Reachability from the agenda and the ficha (`42c45d94`) — focused 48 passed,
      full web 768 passed, build green
- [x] WU4 — Story coverage and full verification (`071084ea`) — focused 5 passed, full web 773 passed,
      build green, closing backend 1483 passed
- [x] Owner decision: push and open the PR — delivered as **PR #376** (merged). `AppointmentDetail.tsx`,
      its `.test.tsx`, the stories and the per-appointment route are all in `main`. Re-verified against
      `origin/main` (not against this record) during the 2026-09-29 stale-checkbox sweep.

## Verification (observed)

| Work unit | Command | Result |
|---|---|---|
| base | `uv run pytest tests/ -o addopts='' -q` | 1479 passed in 216.08s |
| base | `cd web && npm test` | 761 passed (87 files) |
| WU1 | `uv run pytest tests/functional/test_api_scheduling.py -o addopts='' -q` | 11 passed in 2.41s |
| WU1 | `uv run pytest tests/ -o addopts='' -q` | 1483 passed in 195.45s |
| WU2 | focused (panelRoutes + AppShell + AppointmentDetail) | 36 passed (3 files) |
| WU2 | `cd web && npm test` | 766 passed (88 files) |
| WU2 | `cd web && npm run build` | built |
| WU3 | focused (AgendaPage + ClientFicha) | 48 passed (2 files) |
| WU3 | `cd web && npm test` | 768 passed (88 files) |
| WU3 | `cd web && npm run build` | built |
| WU4 | `cd web && npm test -- src/stories/pages/AppointmentDetail.stories.test.tsx` | 5 passed |
| WU4 | `cd web && npm test` | 773 passed (89 files) |
| WU4 | `cd web && npm run build` | built |
| WU4 | `uv run pytest tests/ -o addopts='' -q` | 1483 passed in 274.01s |
| WU4 | `git diff --check` | clean |

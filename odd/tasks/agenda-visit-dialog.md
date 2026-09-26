# ODD Task: agenda-visit-dialog

Status: in progress
Worktree: `../lumat-agent-odd-agenda-visit-dialog`
Branch: `odd/agenda-visit-dialog`
Depends on: `agenda-manual-case` (PR #367, merged `673d9fba`)

## Objective

Make the Agenda's "Crear visita" dialog usable end to end: group its fields so the form
reads as a form, stop a nullable `Case.service` from wedging creation, let the operator
create a manual case inline (D4), and let the register separate active from non-active
visits without deleting anything (AG-UI-6).

## Problem

1. The dialog's children are emitted as siblings inside `Dialog` (`AgendaPage.tsx:214-225`)
   with no form container. `.field` (`primitives.css:99-103`) spaces a label from its
   control, not field from field. The reported "collapsed dialog" is consistent with this.
2. **A silent `TypeError` blocks creation.** `Case.service` is nullable in the DB and in
   the U3 data, but `web/src/types.ts` declares it `string`. Selecting such a case runs
   `field("service", selected.service)` (`AgendaPage.tsx:216`), putting `null` into the
   form; `create()` then calls `createForm.service.trim()` at `AgendaPage.tsx:129` —
   **outside** the `try` that starts at `:135` — so the handler throws before any request
   and before any feedback. This is the defect the owner reported.
3. "Caso" is a native `Select` of pre-existing cases (`AgendaPage.tsx:216`). There is no
   way to create a case for a walk-in customer, even though `POST /cases` has existed
   since U3.
4. The register renders every status with no way to separate active from non-active visits
   (AG-UI-6).

## Why (approved decisions)

- **D4**: inline case creation through a Combobox, backed by `POST /cases`.
- **AG-UI-6 belongs to U4** (owner decision this session): the register separates active
  from non-active visits without deleting any record.
- **AG-UI-5** already makes a no-conversation case first-class; U4 must not reintroduce a
  conversation requirement.
- **D3**: cancellation is soft; `AppointmentHistory` and `AppointmentCalendarSync` forbid
  row deletion.

## Scope

Frontend only. `POST /cases`, the appointments route, and `scheduling.book()` already
exist and need no change unless verification proves otherwise.

## Constraints

- Work is born in this worktree on `odd/agenda-visit-dialog`; never touch `main`.
- **Strict TDD is ON** (`openspec/config.yaml:38`). RED → GREEN → REFACTOR, no exceptions.
- Runner: `cd web && npm test` (Vitest). The only type check is `cd web && npm run build`
  (`tsc -b && vite build`). No linter, no formatter.
- Backend regression (unchanged by this unit): `eval "$(infra/test-db.sh env)"` then
  `uv run pytest tests/`.
- Never add an appointment DELETE or any hard delete: AG-UI-6 requires records to survive.
- `Appointment.case_id` and `Appointment.service` stay `NOT NULL`.

## Contract (`openspec/specs/agenda-calendar-ui/spec.md`)

- **AG-UI-2** — shared state contract (loading, empty, error, permission, stale) with
  labeled feedback, semantic table/list markup, keyboard-operable focused actions, and an
  unclipped mobile layout. Preserve it while changing the dialog.
- **AG-UI-3** — creation is allowed; edit/reschedule only for `booked`; cancellation
  requires confirmation and a reason; `cancelled` is terminal.
- **AG-UI-4** — Storybook coverage for the named states; keep it while adding create and
  filter states.
- **AG-UI-5** — appointment detail must tolerate a case with no conversation.
- **AG-UI-6** — the register MUST let the operator separate active from non-active visits
  (`cancelled`, `completed`, `no_show`) without deleting any record.

## Work units

### WU1 — Null-safe case service + dialog field rhythm — done (`933686c9`)

- [x] RED: `shows validation instead of throwing when the selected case has no service` —
      observed `TypeError: Cannot read properties of null (reading 'trim')` at
      `AgendaPage.tsx:129`, with no alert rendered and no request issued.
- [x] `web/src/types.ts` — `Case.service: string | null`.
- [x] `AgendaPage.tsx` — the service copy is guarded (`selected?.service &&`) and the
      validation is null-safe (`createForm.service?.trim()`); a service-less case is labelled
      `Caso sin servicio (#id)` instead of `null (#id)`.
- [x] Dialog — the fields sit in `.agenda-create-form` (`display: grid;
      gap: var(--space-3)`) in `primitives.css`, next to `.field`.
- **Verify**: `cd web && npm test -- src/components/pages/AgendaPage.test.tsx` — **24 passed**;
  `cd web && npm run build` — **built**. The widened `Case.service` flagged two
  `CasesList.stories.test.tsx` assertions, both made null-safe.
- **Review boundary**: `review assess --base-ref 673d9fba --committed-only` → `medium`,
  `review_due: false`, `under_budget` (202 lines). Stays pending in the slice.

### WU2 — Inline manual case creation (D4) — done (`bd2d4a5c`, `321d423b`)

- [x] RED: three cases — the Combobox create affordance (`Combobox.test.tsx`), the inline
      creation flow, and the no-customer guard. The pre-existing appointment test also went
      RED because a Combobox is not a native select.
- [x] `types.ts` + `api.ts` — `ManualCaseRequest` and `createCase()` over `POST /panel/api/cases`.
- [x] `Combobox.tsx` — optional `onCreate?: (query: string) => void`; renders
      `Crear «query»` reusing the existing `combobox__option` row, activatable by click or
      Enter. With the prop absent the component behaves exactly as before.
- [x] `AgendaPage.tsx` — "Caso" is a Combobox; the creation path is customer-gated, selects the
      returned case, fills `Servicio` only when that field is empty, and reports failures with
      `role="alert"`.
- **Verify**: `cd web && npm test -- src/components/pages/AgendaPage.test.tsx src/components/primitives/Combobox.test.tsx` — **37 passed**;
  `cd web && npm test` — **755 passed** (87 files); `cd web && npm run build` — **built**.
- **Review boundary**: `review assess --base-ref 673d9fba --committed-only` → `medium`,
  `review_due: false`, `under_budget` (327 lines). Still pending in the slice.

#### Decisions taken in WU2

- **No summary input.** `ManualCaseRequest.summary` stays optional in the client and this flow
  omits it: the dialog has no summary field and adding one is UI scope beyond D4.
- **The customer is associated locally.** `to_case_dict` does not embed a customer, and the web
  `Case.customer` is required (`types.ts:310`), so the created case gets the selected client
  attached from the already-loaded `clients` list. Safe because the id comes from that same list.
- **Switching the customer clears the case.** Otherwise a case belonging to another customer
  could be submitted and rejected by `book()` as `unlinked_appointment`.
- **One flaky failure in four full-suite runs** on the heaviest create-flow test — the caret sat
  on the `it(...)` line, the signature of a timeout, and the test takes 1672 ms in isolation
  against Vitest's 5 s default. Diagnosed as probable, not proven. Hardened with
  `userEvent.setup({ delay: null })` plus an explicit 15 s timeout; the three later full runs
  were green.

### WU3 — AG-UI-6 non-active register filter

- [ ] Separate active from non-active visits by status (`cancelled`, `completed`,
      `no_show`); default view stays active; nothing is deleted.
- **Verify**: `cd web && npm test -- src/components/pages/AgendaPage.test.tsx`; `cd web && npm run build`

### WU4 — Story coverage and full verification

- [ ] Storybook states for the create dialog and the register filter.
- [ ] Full `cd web && npm test` and `cd web && npm run build`.
- [ ] Backend regression `uv run pytest tests/`.
- **Verify**: the three commands above, observed.

## Acceptance criteria

- Selecting a case with a nullable service can no longer throw or wedge the dialog.
- The dialog's fields are visibly grouped with consistent vertical rhythm.
- An operator can create a case inline from the dialog and then create the visit with it.
- The register separates active from non-active visits without deleting records.
- Vitest suite green; `tsc -b` build green; backend suite green.

## Verification (observed)

| Work unit | Command | Result |
|---|---|---|
| WU1 | `cd web && npm test -- src/components/pages/AgendaPage.test.tsx` | 24 passed |
| WU1 | `cd web && npm run build` | ✓ built in 5.77s |
| WU1 | `git diff --check` | clean |
| WU2 | `cd web && npm test -- src/components/pages/AgendaPage.test.tsx src/components/primitives/Combobox.test.tsx` | 37 passed |
| WU2 | `cd web && npm test` | 755 passed (87 files) |
| WU2 | `cd web && npm run build` | ✓ built in 17.43s |

The backend suite and the closing full re-run are WU4.

## Graph nodes consulted

- Nodes: `AgendaPage()` (`web/src/components/pages/AgendaPage.tsx`), `Combobox()`
  (`web/src/components/primitives/Combobox.tsx`), `Dialog()`
  (`web/src/components/primitives/Dialog.tsx`), `Case` and `Appointment`
  (`app/models.py`), `book()` (`app/services/scheduling.py`), `create_manual_case()` and
  `list_open_cases()` (`app/services/cases.py`), `visitLabel()`
  (`web/src/components/shared/AgendaCalendar.tsx`),
  `test_manual_case_creation_returns_and_lists_open_case()`
  (`tests/functional/test_api_cases.py`).
- Edges: `AgendaPage → api.ts → appointments`, `Case → Customer`,
  `Appointment → Case`, `Appointment → Technician`.
- `graphify query "AgendaPage create visit dialog Combobox case selection appointment
  creation"` and narrower queries over the same area; `GRAPH_REPORT.md` (7987 nodes /
  16521 edges, built from `673d9fba`) consulted for the Agenda community.

## Progress

- [x] WU1 done — `933686c9`
- [x] WU2 done — `bd2d4a5c`, `321d423b`
- [ ] WU3 not started
- [ ] WU4 not started

# ODD: agenda-product-register

## Objective

Raise both Agenda surfaces — the operator `AgendaPage` and the technician
`TechnicianAgenda` — to the panel's product register under the already-amended
`DS-GRAMMAR-1`, define the page-architecture section Agenda never had, fix the
real defects a redesign would otherwise leave behind, and extract only the
substrate its slices force into existence with a named second consumer.

This unit carries **no contract amendment**: the two-axis grammar already landed
with `clientes-product-register`, and no live spec forbids this work.

## Problem

Verified against the code at base `9b83e27f`. Every claim is evidence, not
impression.

### Agenda has no page-architecture section

`web/DESIGN_SYSTEM.md:282` states it in writing: `Asistente Lumat`, `Agenda`,
`Automatizaciones` and `Usuarios` "do not yet have page-architecture sections
here; their absence is not permission to improvise." Clientes has one (`:302`).
Without the section defined, the register work has no admission gate.

### The operator surface still carries native controls

- `<button type="button">` retry controls in the stale and error states
  (`AgendaPage.tsx:35-36`); the `Button` primitive exists and is used elsewhere
  on the same page.
- `<label htmlFor="cancel-reason">` plus a raw `<textarea id="cancel-reason">`
  inside the cancellation `Dialog` (`AgendaPage.tsx:113-114`); the `Textarea`
  primitive exists.

### Real defects, verified

- **`1 visitas`.** `AgendaPage.tsx:110` renders `${appointments.length} visitas`
  with no singular form — the same defect class as the `1 clientes` bug closed in
  `clientes-product-register` T3/D4. `TechnicianAgenda.tsx:169` gets it right, so
  the two surfaces disagree about the same list.
- **The two surfaces disagree about the clock, and it is measurable.**
  `AgendaPage.tsx:41` builds `Intl.DateTimeFormat("es-CL", { hour, minute })`
  with no `hourCycle`; `es-CL` resolves to `h12` in this environment (measured
  with `node`: the slot renders `02:30 p. m.`). `TechnicianAgenda.tsx:25-26`
  deliberately pins `hourCycle: "h23"`, and its comment (`:23-24`) explains why:
  an agenda slot must be unambiguous and a range would repeat the meridiem. The
  same appointment therefore reads `02:30 p. m.` to the operator and `14:30` to
  the technician.
- **A group with no rows claims the page is empty.** With `Hoy` empty and
  `Próximas` populated, `AgendaPage.tsx:103-107` renders `<h2>Hoy</h2>` followed
  by a `DataTable` with zero rows, which renders its own `.empty-state`
  "No hay visitas" (`DataTable.tsx:52-58`). The page has visits; one group does
  not.

### The suite cannot see either defect

`AgendaPage.test.tsx` asserts states, the dialog and the failure copy
(lines 45-118) but never asserts the rendered time or the count. The time column
is deterministic per row (it formats with `row.timezone`), so the assertion is
possible and simply absent. Both defects are unobserved today.

### Feedback lands away from the action

`AgendaPage.tsx:110` routes cancellation and sync-retry failures into the
`PageFrame` banner. Clientes T13 moved action feedback to the locus that caused
it (splitting `stateFeedback` / `noteFeedback`); the rule applies here for the
same reason: a failure shown at the top of the page is not attached to the
control the user just used.

### The technician surface carries page-owned grammar

`primitives.css:1505-1572` holds **13** `.technician-agenda__*` selectors —
`.section`, `.error`, `.error .btn`, `.section-title`, `.day`, `.day-label`,
`.item`, `.slot`, `.service`, `.status`, `.safety`, `.call`. They live inside the
shared stylesheet (so `DS-GRAMMAR-2` is satisfied) but they are page-owned names,
not register contracts.

Not all 13 are promotable. Some are a legitimate page-specific composition;
others duplicate a contract that already exists — `.technician-agenda__error` is
a `StateMessage` plus a retry `Button`, a shape the operator surface renders too.
The promotion rule decides each one.

### The technician card states its facts with bare elements

`TechnicianAgenda.tsx:113-121` renders service, customer name, address, comuna,
phone and case summary as unlabelled `<p>`, `<strong>`, `<span>` and one raw
external `<a>`. The address link (`:116`) has no class at all and inherits the
browser default link colour — the open item inherited from
`clientes-product-register`, which fixed the same thing on the Clientes list as
the shared `.table__link` (`primitives.css:292`).

### No shared time formatter exists, and the duplication is wide

Every date in the panel is formatted by a locally constructed
`Intl.DateTimeFormat`. Inside the two Agenda surfaces alone there are two
independent sets of helpers. The same `dateStyle: "short" + timeStyle: "short"`
format is also re-declared in `ClientFicha.tsx:26-30`, `ConversationThread.tsx:42`,
`ConversationsList.tsx:21` and `PlanningSessions.tsx:14`.

Agenda's helpers are agenda-shaped, not universal: a 24h slot in the
appointment's own zone, a long day heading, a comparable `YYYY-MM-DD` day key, and
a reader-clock freshness stamp. `TechnicianAgenda.tsx:25-36` already implements
exactly those four, so promoting them gives the contract its second consumer
immediately.

## Scope

**In**: `web/DESIGN_SYSTEM.md` (the `### Agenda` section),
`web/src/components/pages/AgendaPage.tsx` and its test,
`web/src/components/pages/TechnicianAgenda.tsx` and its test, both page stories
and their tests, agenda mock data under
`web/src/stories/pages/_shared/mockData/`, the promoted time module and other
promoted pieces under `web/src/components/shared/`, and the Agenda sections of
`web/src/components/primitives/primitives.css`.

**Out**: any change to `tokens.css` values; the backend and the panel API; every
other page surface — including `ClientFicha`, `ConversationsList`,
`ConversationThread`, `PlanningSessions`, `AgentChat` and `Dashboard`, whose
duplicated formatters are recorded as an open item rather than migrated here; any
new dependency; and any change to the operator agenda's reading model
(chronological `Hoy`/`Próximas`, tabular, no month grid, no create/edit/rebook —
`AG-UI-1`).

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-agenda-product-register`
- Branch: `odd/agenda-product-register`
- Base: `9b83e27f`
- Files: `odd/tasks/agenda-product-register.md`, `web/DESIGN_SYSTEM.md`,
  `web/src/components/pages/AgendaPage.tsx` (+ `.test.tsx`),
  `web/src/components/pages/TechnicianAgenda.tsx` (+ `.test.tsx`),
  `web/src/stories/pages/AgendaPage.stories.tsx` (+ its test),
  `web/src/stories/pages/TechnicianAgenda.stories.tsx` (+ its test),
  `web/src/stories/pages/_shared/mockData/technicianAgenda.ts`, promoted pieces
  under `web/src/components/shared/`, and the Agenda sections of
  `web/src/components/primitives/primitives.css`.

## Constraints

- **Strict TDD: ON** — source `openspec/config.yaml`. The configured runner is
  pytest; this is a frontend-only change, so the applicable runner is Vitest via
  `cd web && npm run test`. Observe RED before each source change; never invent
  RED evidence.
- **`DS-GRAMMAR-1` as amended** is the target contract. The physiology axis is
  binding: the operator surface keeps `DataTable`, KPI, `Badge`, filters and state
  primitives as its data layer, and no bubble, composer shell, thread rail or
  inspector appears on either Agenda surface.
- **`DS-GRAMMAR-2` / `DS-UI-PRIMS`** — styles live in the tokenized stylesheet
  boundary, resolve through `var(--*)`, add no dependency, and contain no
  hard-coded colour. No component may inject `<style>`.
- **`DS-TKN-2`** — any token addition is additive only; every pre-existing
  declaration keeps its exact value.
- **`DS-GRAMMAR-3`** — reuse `Badge`, `Button`, `Textarea`, `DataTable`,
  `StateMessage`, `EmptyState`, `PageFrame` where their contracts apply.
- UI copy stays neutral Chilean Spanish; no raw backend identifier reaches the
  surface.
- Artifacts in English. Conventional commits, no AI attribution.
- Work-unit commits on this branch are authorized. Push and PR require explicit
  orchestrator authorization.
- Graph Check runs before each task; the nodes consulted are recorded in the
  Progress section.

## Known environmental failures

`cd web && npm run test` on the untouched base at `9b83e27f` reports **80 files /
665 tests — 663 passing, 2 failing** — both failures in
`src/components/domain/AppShell.test.tsx`, plus one teardown error
(`fireEvent` / undici fetch resolving after the environment was torn down). The
same file passes **22/22** when run alone
(`npx vitest run src/components/domain/AppShell.test.tsx`). This is pre-existing
flakiness under full-suite load on the base, not a defect introduced here, and it
is not in this unit's scope.

## Decisions

- **D1 — The register is inherited, not renegotiated.** The two-axis grammar
  landed with `clientes-product-register`. Agenda needs no
  `openspec/changes/` directory and no `DS-GRAMMAR-1` delta: `agenda-calendar-ui`
  (AG-UI-1..4) and `technician-agenda` (TECH-AGENDA-1) constrain behaviour, not
  appearance, and neither forbids the register. A contract change with nothing to
  change is ceremony.
- **D2 — The real defects are fixed in the slice they belong to.** `1 visitas`
  and the h12/h23 divergence are observable wrong behaviour on these surfaces; a
  redesign that leaves them is cosmetic (D4 of `clientes-product-register`).
- **D3 — Substrate promotion requires a named second consumer.** `.data-region`
  is already proven (`clientes-product-register` D12) and its Agenda consumer is
  this unit. The time contract is promoted because both Agenda surfaces need it.
  A summary rail and a filter toolbar are **not** promoted: Agenda does not
  filter and no second consumer exists.
- **D4 — The promoted time contract is agenda-shaped, not a universal date
  helper.** Four named roles, extracted from the technician's existing helpers: a
  24h slot in the appointment's own zone, a long day heading, a comparable
  `YYYY-MM-DD` day key, and a reader-clock freshness stamp. The
  `dateStyle`/`timeStyle` timestamps elsewhere in the panel are a different role
  and are explicitly out of scope.
- **D5 — Both surfaces read an agenda slot the same way: 24 hours.** The
  technician's rationale (`:23-24`) is not surface-specific — an agenda slot must
  be unambiguous, and a meridiem repeated across a range is noise. One contract,
  two consumers.
- **D6 — The operator reading model does not change.** Chronological `Hoy` and
  `Próximas`, tabular, no month grid, no create/edit/rebook (`AG-UI-1`). This
  unit is composition and grammar, not a new paradigm.
- **D7 — No card-on-card.** `.data-region` applies to the operator table wrapper
  only when rows exist: `DataTable` renders its own `.empty-state` when empty
  (`DataTable.tsx:52-58`) and `.data-region`'s own comment (`primitives.css:297`)
  forbids wrapping one (D13 of `clientes-product-register`).
- **D8 — A group with no rows is not the page being empty.** Page-empty and
  section-empty are distinguishable states, and neither renders a nested surface
  claiming there are no visits when the page has some (T7 of
  `clientes-product-register`).
- **D9 — Action feedback appears at the locus.** Cancellation and sync-retry
  outcomes render beside the control that caused them, not in the page banner
  (T13 of `clientes-product-register`).
- **D10 — A promoted selector must name its second consumer; a page-specific
  composition may stay page-specific.** The technician card list is a composition
  and may keep page-owned class names. `.technician-agenda__error` is not: the
  operator surface renders the same `StateMessage` + retry `Button` shape, so
  that contract is promoted or generalised. Each of the 13 is decided on that
  test, with the count before and after recorded.
- **D11 — Delivery is chained, `stacked-to-main`.** PR 1 carries T0 plus the
  operator surface; PR 2 carries the technician surface. ~400 review lines per PR
  is the budget; one honest cutting pass, and if it does not fit, the real number
  is reported and `size:exception` recommended. Code, tests and comments are never
  compressed to fit.
- **D12 — Tests are extended, not created.** Both surfaces already have component
  tests, so D5 of `clientes-product-register` does not apply in its original
  form. This unit adds the assertions missing today — the rendered slot, the
  count, the section-empty case, the feedback locus — and each one fails before
  its fix.

## Tasks

### Slice 1 — operator agenda (ships in PR 1)

- [ ] **T0** — Write the `### Agenda` page-architecture section in
  `web/DESIGN_SYSTEM.md`, in the shape of the neighbouring `### Clientes` section:
  what the operator agenda is for, its required content, its actions, and what it
  must never offer.
- [ ] **T1** — RED/GREEN: `1 visitas`. The count renders singular and plural
  correctly. RED observed before the fix.
- [ ] **T2** — RED/GREEN: the operator slot renders 24 hours through the shared
  contract this unit introduces, matching the technician surface. Asserted on a
  row with a known `timezone` and `starts_at`; RED observed as a meridiem-bearing
  slot before the fix.
- [ ] **T3** — RED/GREEN: a section with no rows renders no nested `.empty-state`
  and no "No hay visitas" copy; page-empty and section-empty are distinct. RED
  observed.
- [ ] **T4** — RED/GREEN: the cancellation `Dialog` uses `Textarea`, states the
  consequence of cancelling, and renders its success/failure at the locus; the
  sync-retry failure renders at the row. RED observed (no `.field__control`,
  feedback only in the page banner).
- [ ] **T5** — RED/GREEN: the retry controls in the stale and error states are
  `Button`. `grep -c "<button" AgendaPage.tsx` → 0.
- [ ] **T6** — RED/GREEN: the operator surface gets the named region and the
  shared `.data-region` surface, applied only when rows exist (D7); the refresh
  control's home is decided and recorded (it is absent from the operator page
  today; the technician keeps it in `PageFrame` actions). RED observed (no region
  role).
- [ ] **T7** — stories: extend the story matrix with the cases the redesign must
  not regress (section-empty with a populated page, denied, cancel-confirmation,
  sync-failure/retry), plus their story assertions.
- [ ] **T8** — Slice 1 verification of record: `npm run test`,
  `npx tsc -b --noEmit`, `npm run build`, `npm run build-storybook`.

### Slice 2 — technician agenda (ships in PR 2)

- [ ] **T9** — RED/GREEN: the technician's four local formatters are replaced by
  the shared contract (same output, second consumer proven). RED observed against
  a deliberate divergence before the extraction.
- [ ] **T10** — RED/GREEN: the address link uses the shared link contract and no
  longer inherits the browser default colour. RED observed (no class on the
  anchor).
- [ ] **T11** — RED/GREEN: the technician card's facts carry label/value structure
  where it fits the phone width (address, comuna, phone, service); no label is
  added that merely repeats its value.
- [ ] **T12** — RED/GREEN: the 13 page-owned selectors are reduced by the D10
  test, with the count before and after recorded and each promotion naming its
  second consumer; the page-specific remainder stays page-owned and keeps its
  tokens.
- [ ] **T13** — stories: extend the technician story matrix for whatever
  T9–T12 changed, with its assertions.
- [ ] **T14** — Slice 2 verification of record: the same four commands.

## Acceptance criteria

1. No raw `<button>`, `<select>` or `<textarea>` remains on either Agenda
   surface; the panel's primitives are used.
2. No bubble, composer shell, thread rail or inspector is rendered on either
   Agenda surface, and the operator data presentation stays tabular.
3. The appearance axis is verifiable on both surfaces: no element is left on
   browser-default control styling, including the technician address link.
4. No inline `style={{}}` visual decision remains in the shared pieces this unit
   touches.
5. No raw backend identifier is rendered in the product UI.
6. The `1 visitas` defect is fixed with a test that fails before the fix.
7. Both surfaces render an agenda slot as 24 hours, asserted by a test that fails
   before the fix.
8. A group with no rows does not render an empty surface claiming the page has no
   visits; page-empty and section-empty are distinguishable.
9. Cancellation and sync-retry feedback appears at the locus of the action, not
   in the page banner.
10. No hard-coded colour is introduced; no new dependency is added; every
    pre-existing token keeps its exact value.
11. Only the authorized files change.
12. `cd web && npm run test`, `cd web && npx tsc -b --noEmit` and
    `cd web && npm run build` pass; rows-per-screen on the operator table does not
    regress against base `9b83e27f`.

## Checks

- `cd web && npm run test`
- `cd web && npx tsc -b --noEmit`
- `cd web && npm run build`
- `cd web && npm run build-storybook`
- density comparison against base `9b83e27f` at 1366×768
- `git status --short` / `git diff --check`

## Progress

- [x] Created this ODD record before the first source change.
- [x] Worktree created (`rapso worktree create agenda-product-register --yes`) and
  confirmed at base `9b83e27f` (`Merge pull request #327 from
  Stefan-migo/odd/clientes-ficha`).
- [x] `npm ci` completed in `web/` (the provision step installs `.opencode`
  dependencies only).
- [x] Baseline established on the untouched worktree, including the known
  environmental failure recorded above.
- [x] Graph Check (Step 1) for the Agenda area. Nodes consulted: `AgendaPage()`
  (`pages/AgendaPage.tsx:48`), `TechnicianAgenda()`
  (`pages/TechnicianAgenda.tsx:146`), `AgendaPageProps`, `DataTable()`
  (`shared/DataTable.tsx:32`), `EmptyState()`, `StateMessage()`, `PageFrame()`,
  `useAsyncData()`, `appointmentStatusLabel()` / `appointmentStatusTone()`
  (`shared/toneMaps.ts`), `listAppointments()` / `cancelAppointment()` /
  `retryCalendarSync()` / `fetchTechnicianAgenda()` (`api.ts`), and
  `AgendaAppointment` (`types.ts:440`). Communities: `AgendaPage.tsx`,
  `TechnicianAgenda.tsx`, `shared/toneMaps.ts`, `scheduling.py`, `types.ts`.
- [ ] T0–T8.

## Size

To be recorded at the end of each slice: changed lines under `web/`
(added/deleted), the dominant terms, and whether the slice fits the ~400
review-line budget.

## Open items

- **The panel has no shared timestamp formatter.** `dateStyle: "short" +
  timeStyle: "short"` is re-declared in `ClientFicha.tsx:26-30`,
  `ConversationThread.tsx:42`, `ConversationsList.tsx:21` and
  `PlanningSessions.tsx:14`, and `AgentChat.tsx` and `Dashboard.tsx` build their
  own. Those are different roles from the agenda slot contract promoted here, and
  those surfaces are outside this unit's authorized scope. A follow-up unit can
  migrate them once the shared role is named.
- **`SearchInput` cannot be cleared programmatically** (inherited). Neither
  Agenda surface uses it, so it is out of scope here; it affects
  `ConversationsList` and `KbList`.
- **The sync status has no database enum or constraint.**
  `db/migrations/012_h3_calendar_templates.sql:9` stores it as a free `VARCHAR`,
  and the frontend union (`pending | synced | failed`) depends on application
  convention (`app/services/calendar.py:70-74`). No value mismatch was found; the
  contract is enforced only by convention.
- **Appointment status is typed as a plain `string`** (`types.ts:454`, `:478`)
  although the domain has exactly four values (`app/models.py:155-159`). An
  unknown value falls back to a raw label and a neutral tone. Tightening it is a
  type change with no behaviour change; whether it belongs here or in the backend
  contract work is undecided.
- **`AutomationRulesPage.tsx:24`** still renders its drill-down link on the
  browser default colour (inherited; out of scope).
- **Density (acceptance 12) is argued structurally, not measured**, and the
  owner's visual confirmation at 1366×768 is the gate between slices.

## Recovery

- Worktree: `/home/stefan/repos/lumat-agent-odd-agenda-product-register`, branch
  `odd/agenda-product-register`, base `9b83e27f`.
- Dev server for this worktree: `cd web && npm run dev -- --host 127.0.0.1 --port
  5177` with `VITE_API_TARGET` pointed at the running API. Ports `5174`–`5176` are
  taken by other worktrees; `odd/assistant-web-search` and
  `odd/kb-product-register` are active and must not be touched.
- No OpenSpec change directory is created and none is archived: this unit carries
  no contract delta (D1).
- On resume: read this file and reconcile the checkbox state against `git log`
  before continuing. Rebase only if `main` has moved.
- Session of record: the 2026-09-23 conversation that opened this unit. The
  reasoning is also in Engram under `odd/agenda-product-register/*`.

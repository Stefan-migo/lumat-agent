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
  and are explicitly out of scope. The promotion rule (D3) applies **per role**: a
  role enters the shared module when two consumers use it today; a role with a
  single consumer stays local until a second one exists, and which roles moved is
  recorded rather than assumed.
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
- **D13 — The clock divergence is fixed in slice 1; the shared contract is
  extracted in slice 2.** A module under `shared/` with a single consumer is
  exactly what D3 refuses, so slice 1 pins the operator's hour cycle with the
  smallest change that fixes the observable defect, and slice 2 extracts the
  agenda-shaped contract at the moment both surfaces consume it. Ordering is a
  correctness rule here, not a packaging preference.
- **D14 — The technician surface's local grammar is deliberate, not debt.**
  `odd/tasks/technician-surface.md` already raised that surface — 748 changed lines
  under `web/`, D1–D7 and T1–T10 — and the 13 `.technician-agenda__*` selectors are
  its documented output, not an accident: the card idiom was chosen after measuring
  that a `--border-strong` stroke lands at 2.84:1 on `--brand-bg`, the slot leads
  the card by decision (D4), the call control hugs its own label (T3), the recovery
  control sits under its alert (T7), and the class was made real (T8). T12 is
  therefore **not** "reduce the 13 selectors": each one is audited against the
  promotion rule, and the page-specific remainder keeps its ownership with its
  rationale recorded.
- **D15 — The card's unlabelled facts are re-examined, not converted.** The ficha's
  six bare `<p>` elements were ambiguous because a desktop identity block carries no
  reading order. The technician card's order was decided instead of inherited
  (`technician-surface` D4/T4: *when*, then *what*, then *who*, then *where*, then
  how to call). A label is added only where a value is genuinely ambiguous without
  one, and no label is added that repeats its value or fights a 390px phone width.

## Tasks

### Slice 1 — operator agenda (ships in PR 1)

- [x] **T0** — Write the `### Agenda` page-architecture section in
  `web/DESIGN_SYSTEM.md`, in the shape of the neighbouring `### Clientes` section:
  what the operator agenda is for, its required content, its actions, and what it
  must never offer.
- [x] **T1** — RED/GREEN: `1 visitas`. The count renders singular and plural
  correctly. RED observed before the fix.
- [x] **T2** — RED/GREEN: the operator slot renders 24 hours, matching the
  technician surface. Minimal targeted change — pin the hour cycle (D13); the
  shared contract is extracted in T9, where a second consumer exists. Asserted on
  a row with a known `timezone` and `starts_at`; RED observed as a meridiem-bearing
  slot before the fix.
- [x] **T3** — RED/GREEN: a section with no rows renders no nested `.empty-state`
  and no "No hay visitas" copy; page-empty and section-empty are distinct. RED
  observed.
- [x] **T4** — REOPENED by independent verification. The `Textarea`, the
  dialog-local cancellation failure and the row-local sync failure landed
  (`bf712125`), but two parts do not hold: the row-locus feedback is a
  `StateMessage` panel inside a table cell, and the confirmation copy states a
  product guarantee the specs do not establish. Closed by C1–C3.
- [x] **T5** — RED/GREEN: the retry controls in the stale and error states are
  `Button`. `grep -c "<button" AgendaPage.tsx` → 0.
- [x] **T6** — RED/GREEN: the operator surface gets the named region and the
  shared `.data-region` surface, applied only when rows exist (D7); the refresh
  control's home is decided and recorded (it is absent from the operator page
  today; the technician keeps it in `PageFrame` actions). RED observed (no region
  role).
- [x] **T7** — stories: extend the story matrix with the cases the redesign must
  not regress (section-empty with a populated page, denied, cancel-confirmation,
  sync-failure/retry), plus their story assertions.
- [x] **T8** — Slice 1 verification of record: `npm run test`,
  `npx tsc -b --noEmit`, `npm run build`, `npm run build-storybook`.

### Slice 1 — correction pass (opened by independent verification)

- [x] **C1** — The row-locus outcome must stay dense. A `StateMessage` is a panel:
  it emits a `<section>` carrying an `<h2>` and its own tinted surface
  (`StateMessage.tsx:22-26`), so inside the actions `<td>` it adds a heading
  landmark per row and inflates row height — against the dense-table contract
  (`DESIGN_SYSTEM.md:409-416`) and acceptance criterion 12. Replace it with a
  compact outcome built only from contracts that already exist; `StateMessage`
  remains correct for the page-level states it already serves. Do **not** add a new
  CSS class or token: if nothing existing fits, stop and report the finding rather
  than inventing substrate with a single consumer (D3).
- [x] **C2** — The destructive confirmation names the affected visit and states a
  truthful consequence. `DESIGN_SYSTEM.md:437` requires a confirmation to name the
  affected customer/entity, and the current copy claims the visit can never be
  rebooked — a guarantee AG-UI-1/AG-UI-3 do not establish: they forbid the panel
  from offering rebooking, not the domain from ever holding that appointment again.
  The `### Agenda` section also gains the consequence clause its `### Clientes`
  sibling already carries (`DESIGN_SYSTEM.md:307`).
- [x] **C3** — The story matrix must represent what it claims. `CancelConfirmation`
  is the plain data story and never opens the dialog
  (`AgendaPage.stories.tsx`), and the copy assertion tests a substring loose enough
  to pass on weakened copy (`AgendaPage.test.tsx`). Either the story represents the
  open confirmation or it stops claiming to, and the assertion pins the copy it
  means to protect.

### Slice 2 — technician agenda (ships in PR 2)

- [ ] **T9** — RED/GREEN: the agenda-shaped time contract is extracted from the
  technician's four local helpers and **both** surfaces consume it (D4, D13) — the
  second consumer is real at the moment of extraction, not promised.
- [ ] **T10** — RED/GREEN: the address link uses the shared link contract and no
  longer inherits the browser default colour. RED observed (no class on the
  anchor).
- [ ] **T11** — RED/GREEN: only the card facts that are genuinely ambiguous without
  a label gain structure (D15). If the audit finds none, close the task with the
  recorded verdict and no code change: the card's reading order is a decision from
  `technician-surface` and inventing labels would churn it.
- [ ] **T12** — RED/GREEN: audit all 13 `.technician-agenda__*` selectors against
  the promotion rule (D3, D10, D14) and record the verdict for each. Promote at most
  what both a slice needs and a named second consumer actually uses — the operator
  surface renders the same `StateMessage` plus recovery-control shape, so that
  layout is the single candidate named here. Everything page-specific stays
  page-owned and keeps its tokens. Record the selector count before and after.
- [ ] **T13** — stories: extend the technician story matrix only for what T9–T12
  actually changed, with assertions. Invent no story for a state that did not move.
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
- [x] Doc amended before T0: D13 and the slice ordering for the time contract —
  the observable divergence is fixed in slice 1, and the shared module lands in
  slice 2 with its real second consumer.
- [x] T0–T8. T0 commit `05ff620f`; T1 `dea88fcf`; T2 `a7008a46`; T3
  `b164fe3e`; T4 `bf712125`; T5 `4647c19e`; T6 `c6a14141`; T7
  `890fae2d`; T8 documentation commit `a3aa7750`.

### Slice 1 implementation evidence

- T0 RED: not applicable (documentation-only). GREEN: `### Agenda` matches the
  neighbouring page-architecture shape and records the operator register,
  actions, states, and non-goals.
- T1 Graph nodes: `AgendaPage()`, `AgendaPage.test.tsx`, `PageFrame()`.
  RED: `Unable to find an element with the text: 1 visita`; the rendered
  header contained `1 visitas`. GREEN: focused test passed.
- T2 Graph nodes/edge: `AgendaPage()` → `DataTable()` (`AgendaPage.tsx`
  imports `DataTable`). RED: `Unable to find an element with the text: 14:00`;
  the rendered slot was `02:00 p. m.`. GREEN: focused test passed after the
  targeted `hourCycle: "h23"` pin.
- T3 Graph nodes: `AgendaPage()`, `DataTable()`, `EmptyState()`. RED:
  `expected document not to contain element, found <div class="empty-state">`
  in the empty `Hoy` section. GREEN: focused test passed after omitting the
  section table when it has no rows.
- T4 Graph nodes: `AgendaPage()`, `Dialog()`, `Textarea()`, `StateMessage()`.
  RED: the dialog lacked the consequence copy and field class; after submit,
  the dialog lacked `No se pudo cancelar`; sync failure was absent from the row.
  GREEN: four focused mutation tests passed; feedback is dialog-local for
  cancellation and row-local for sync retry.
- T5 Graph nodes: `AgendaPage()`, `Button()`, `StateMessage()`. RED:
  `toHaveClass("btn")` received an element with no class for the error retry.
  GREEN: focused recovery test passed and `grep -c "<button" AgendaPage.tsx`
  returned `0`.
- T6 Graph nodes/edge: `AgendaPage()` → `DataTable()`; `ClientesList` and
  `ClientFicha` were consulted for the `.data-region` contract. RED:
  `Unable to find an accessible element with the role "region" and name
  "Registro de agenda"`. GREEN: focused region test passed. The operator has
  no refresh control because refresh is not an existing operator action; no
  toolbar was invented. `.data-region` wraps `DataTable` only inside a section
  when `rows.length > 0`, so `DataTable`'s own `.empty-state` is never nested.
- T7 Graph nodes/edge: `AgendaPage.stories.tsx` → `AgendaPage()`; `Dialog()` and
  `StateMessage()` were consulted. RED: the new story assertion failed with
  `Cannot read properties of undefined (reading 'args')` before `SectionEmpty`
  existed. GREEN: the complete Storybook state matrix passed 9/9 tests,
  including section-empty, denied, cancel confirmation, and sync retry.
- T8 Graph nodes: `AgendaPage()`, `AgendaPage.stories.tsx`, `DataTable()`,
  `PageFrame()`, `Button()`, `Textarea()`, `Dialog()`. All four verification
  commands passed; see the final verification record below.

### Slice 1 verification record

- `cd web && npm run test` — passed: `Test Files 80 passed (80)`, `Tests 671
  passed (671)`. Existing React `act(...)` and jsdom navigation warnings were
  emitted; no test failed.
- `cd web && npx tsc -b --noEmit` — passed with no output.
- `cd web && npm run build` — passed: Vite transformed `332 modules` and
  emitted the production bundle. Vite reported the pre-existing large-chunk
  warning.
- `cd web && npm run build-storybook` — passed: Storybook `8.6.18` built the
  preview and emitted `storybook-static`. Storybook reported its existing
  `eval` and large-chunk warnings.

### Slice 1 independent verification (FAIL → correction pass)

- Tier: `gentle-ai review assess --base-ref 9b83e27f` → `risk: medium`
  (`executable_change` on `AgendaPage.test.tsx`; 6 paths, 563 changed lines,
  `slice_budget_reached`). Receipt-driven development is **off** for this clone
  (`review mode status`: global on, clone-local off), so this ran as the ODD
  verification gate, not a native review, and no review lifecycle was opened. The
  runtime profile is a flash model, so the tier was biased up one step and an
  independent verifier was run in addition to the writer's self-verification.
- Parent spot check (re-run, not trusted): `npx vitest run
  src/components/pages/AgendaPage.test.tsx` → 12/12 passing;
  `npx tsc -b --noEmit` → exit 0.
- One independent read-only verifier reviewed the diff against this document and
  returned **FAIL**. Accepted findings, now C1–C3: the `StateMessage` panel inside
  the actions cell; the confirmation's unestablished product guarantee and its
  missing affected-entity name (`DESIGN_SYSTEM.md:437`); the `CancelConfirmation`
  story that never opens the dialog, plus the loose substring assertion.
- Confirmed correct and kept: T1, T2, T3, T5, T6; the state matrix, the badges and
  the truly-empty page state are not regressed.
- Rejected as out of scope: the verifier flagged the technician address link
  (`TechnicianAgenda.tsx:115-117`) against acceptance 3. That is T10 — slice 2 —
  and is expected to be open until PR 2 lands.
- The verifier could not execute commands in its read-only interface, so its
  command claims were not reproduced by it; the two parent spot checks above and
  the writer's T8 record are the executed evidence.

### Correction pass evidence

- C1 Graph nodes/edges: `AgendaPage()` → `Badge.tsx` (import edge), with
  `StateMessage()` consulted as the rejected row-local contract. RED:
  `expected document not to contain element, found <h2 ...>
  No se pudo sincronizar el calendario</h2>` in the row alert. GREEN: focused
  AgendaPage test passed after replacing row outcomes with role-announced
  `Badge` elements. Commit `ba754904`.
- C2 Graph nodes/edge: `AgendaPage()` → `Dialog.tsx` (import edge), with
  `AgendaPage.test.tsx` consulted for the accessible-name assertion. RED:
  `Unable to find an accessible element with the role "dialog" and name
  "Cancelar visita de Camila Soto — Mantención"`; the dialog was still named
  `Cancelar visita`. GREEN: focused AgendaPage test passed with the named
  customer/service and exact panel-scoped consequence copy. Commit `9faa84c4`.
- C3 Graph nodes/edges: `CancelConfirmation` → `AgendaPage.tsx` (import edge)
  and `AgendaPage.stories.test.tsx` → `AgendaPage.tsx` through the story.
  RED: `expected undefined to be defined` for `CancelConfirmation.play`;
  the same run also exposed the stale story assertions for the old dialog name
  and consequence copy. GREEN: Storybook matrix passed 9/9 after adding the
  open-confirmation play interaction and asserting its dialog. Commit
  `59869eb9`.

### Correction pass verification record

- `cd web && npm run test` — passed: `Test Files 80 passed (80)`, `Tests 671
  passed (671)`. Existing React `act(...)` and jsdom navigation warnings were
  emitted; no test failed.
- `cd web && npx tsc -b --noEmit` — passed with no output.
- `cd web && npm run build` — passed: Vite transformed `332 modules` and
  emitted the production bundle. Vite reported the pre-existing large-chunk
  warning.
- `cd web && npm run build-storybook` — passed: Storybook `8.6.18` built the
  preview. Storybook reported its existing `eval` and large-chunk warnings.

### Slice 2 re-scoped before implementation

- T11 and T12 were rewritten after reading `odd/tasks/technician-surface.md`. The
  earlier framing — "the 13 page-owned selectors go to the shared register" — was
  wrong. That surface already had its own design pass, with decisions backed by
  measurement, and the selectors are its documented output (D14). T12 is now an
  audit that applies the promotion rule per selector, and T11 requires evidence of
  real ambiguity before a single label is added (D15). This is the same correction
  the Clientes/KB handoff warned about: re-diagnose, never transfer conclusions.

## Size

Slice 1 (`9b83e27f..HEAD` under `web/`) changed **134 lines** (110 added, 24
deleted) across 5 files: `AgendaPage.test.tsx` 51, `AgendaPage.tsx` 43,
`AgendaPage.stories.test.tsx` 22, `AgendaPage.stories.tsx` 9, `DESIGN_SYSTEM.md`
9. Production code is 43 of those lines; the rest is tests, stories and the
page-architecture section. It fits the ~400 review-line budget with room for the
technician slice.

An earlier revision of this section recorded 90 lines (72 added, 18 deleted); that
number was measured before the C1–C3 correction pass and is superseded by the
figures above.

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
- **The two Agenda surfaces render their section headings differently.** The
  technician's section titles are uppercase and muted
  (`.technician-agenda__section-title`); the operator's `Hoy` and `Próximas` are
  plain `h2`. Each treatment was deliberate inside its own unit, so unifying them is
  a design decision for the owner rather than an obvious cleanup — recorded here for
  the visual review.
- **The row-local sync-failure detail rides inside the status pill.**
  `AgendaPage.tsx` renders the API message appended to the badge
  (`title: detail`), so a long server message will stretch the actions cell. It is
  compact and honest in the common case, and where a failure detail belongs is a
  design decision rather than an obvious fix, so it is reported here instead of
  being churned through another correction pass — a simpler form that changes the
  design is a finding, not an edit. The owner's visual review is what decides
  whether it needs a different home.
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

# ODD — agenda-refine

## Objective

Refine the Agenda section (list, visit detail, and its dialogs) to the iteration-2 reference and
close the 15 owner-validated findings `agenda-021..035` without changing backend behavior or opening
the token palette.

## Problem

The owner's second visual pass (2026-10-04) confirmed many iteration-1 fixes but flagged: calendar
"0 visitas" noise and the missing round mobile grid; the scheduled-visit card missing its clock icon,
an underlined title, and icons in the quick-actions menu; the detail back link off the client/
conversation standard; a redundant "DETALLE DE VISITA" eyebrow; a broken mobile detail header; the
Programación card not in the two-thirds left column; the history card missing its title separator; the
"Ver detalles" disclosure dumping raw JSON; Cliente + Resumen split into two cards with undersized
avatars; and the reschedule/closure dialogs off-reference.

## Why

The section must read as the reference and the design system intend, on desktop, tablet, and mobile,
before it is considered done. Parity matters because the panel is operator-facing.

## Scope (authorized by the owner)

**In:** `web/src/components/pages/AgendaPage.tsx`, `web/src/components/shared/AgendaCalendar.tsx`,
`web/src/components/pages/AppointmentDetail.tsx`, `web/src/components/primitives/Avatar.tsx` (only if
its API needs a size), Agenda/detail selectors in
`web/src/components/primitives/primitives.css`, the three component test files, and the section
capture selector in `web/scripts/capture-section.mjs`.

**Out:** backend/serializer work (technician name, calendar sync status), `TechnicianAgenda`, token
palette (`tokens.css`), and any new route.

## Decisions (owner, 2026-10-04)

- **D1 — Remove the "DETALLE DE VISITA" eyebrow.** Only title + subtitle + badge. This reverses the
  eyebrow part of `agenda-009` even though the reference shows an eyebrow; the owner's decision wins.
- **D2 — No Reprogramar / Cerrar visita buttons on the list visit card.** Those actions stay only in
  the quick-actions menu.
- **D3 — Merge the Cliente card (already holding the technician) with Resumen** into one elongated
  sidebar-style card.
- **D4 — Mobile calendar adapts to the reference's round, compact grid; follow the design system's
  air and spacing, do not copy the reference's compression.**
- **D5 — Palette:** where a reference differs, use the nearest existing token; no white element
  backgrounds; do not reopen `tokens.css`.

## Constraints

- **Strict TDD ON.** Runner: `cd web && npm test`. Observe RED before GREEN per work unit.
- Type check only via `cd web && npm run build` (`tsc -b`); no standalone linter/formatter.
- CSS contract tests read the stylesheet with `readFileSync`; precedent
  `web/src/components/pages/Dashboard.test.tsx:99-105`.
- Operator-facing copy is Spanish; code, identifiers, comments, tests, docs, and commit messages are
  English.
- Keep `aria`/accessibility affordances intact; no behavior change to mutations.
- Do not touch files outside the scope above.

## Graph check

`graphify query "agenda calendar visit card detail history dialog"` (worktree, graph current from
`83ed3e91`) consulted `AgendaPage.tsx`, `AgendaCalendar()`, `AppointmentDetail.tsx`, `Card()`,
`Dialog()`, `AgendaHistory`, `visitLabel()`, `Button.tsx`, `Avatar.tsx`, `ClientFicha.tsx`,
`ConversationThread.tsx`, and the `primitives.css` community. Earlier `graphify path AgendaPage
AppointmentDetail` found no direct edge (both reach through `api.ts` / `PageFrame`).

## Reference images

- List desktop `refs/Diseño Lumat/Agenda/Agenda.png`; list mobile+tablet
  `refs/Diseño Lumat/mobileTablet/Agenda/AgendaMobileTablet.png`.
- Detail desktop `refs/Diseño Lumat/Agenda/agendaVisita.png`; detail mobile+tablet
  `refs/Diseño Lumat/mobileTablet/Agenda/MobileTabletyVisitDetail.png`.
- Reschedule `refs/Diseño Lumat/Agenda/VisitReschedulingModal.png` +
  `refs/Diseño Lumat/mobileTablet/Agenda/ResponsiveVisitRescheduling.png`.
- Closure `refs/Diseño Lumat/Agenda/VisitClosureDialog.png` +
  `refs/Diseño Lumat/mobileTablet/Agenda/MobileTabletVisitClosure.png`.

## Tasks

| ID | Work unit | Findings | Route |
|----|-----------|----------|-------|
| T0 | Capture tooling: target `.agenda-page__visit-title a` in the section capture. | — | direct inline |
| T1 | Calendar: hide the zero-count legend; round compact mobile grid. | agenda-021, agenda-025 | delegated writer |
| T2 | List visit card: clock icon, no title underline, quick-action icons. | agenda-022, agenda-023, agenda-024 | delegated writer |
| T3 | Detail header: back link to the client/conversation standard; remove eyebrow; fix mobile header. | agenda-028, agenda-029, agenda-030 | delegated writer |
| T4 | Detail layout: Programación two-thirds left; merge Cliente+Resumen; larger avatars. | agenda-031, agenda-034, agenda-035 | delegated writer |
| T5 | Detail history: title separator; format the "Ver detalles" content. | agenda-032, agenda-033 | delegated writer |
| T6 | Reschedule and closure dialogs to the reference. | agenda-026, agenda-027 | delegated writer |

## Delivery

Forecast ≈ 450–650 authored lines (tests included) → above the ~400 advisory; plan **chained PRs**
when the human requests delivery. No push or PR until the owner asks. One writer thread; atomic
commits per work unit.

## Progress / Evidence

- [x] Extension pass complete: `agenda-021..035` validated (validator gate `PASS`).
- [x] Re-captured `refs/current/agenda/` at `83ed3e91` (base + visit-detail + new-visit-dialog).
- [x] T0 capture tooling fix (commit `e2ff008e`): the section capture now targets `.agenda-page__visit-title a` instead of the removed `a.table__link`, so the visit-detail extra screen captures at `83ed3e91`.
- [x] T1 calendar (`agenda-021`, `agenda-025`): tests observed RED (3 focused failures), then GREEN (11/11 focused); full Vitest suite 94 files / 978 tests passed; `npm run build` passed with the existing chunk-size advisory. Calendar visit-count labels are omitted for zero-count cells, and mobile day controls use round, compact cells while retaining accessible visit counts and button state. Graph check: `AgendaCalendar()`, `AgendaCalendar.tsx`, `agendaTime.ts`, `primitives.css`, and `Mobile`; graph path from `AgendaCalendar()` to `primitives.css` reported no directed path (ambiguous stylesheet match).
- [x] T2 scheduled-visit card (`agenda-022..024`): tests observed RED (3 focused failures), then GREEN (41/41 focused); full Vitest suite 94 files / 980 tests passed; `npm run build` passed with the existing chunk-size advisory. Added a clock glyph beside the time, removed the default title underline (retaining hover underline), and added decorative icons to available visit quick actions. D2 remains intact: Reprogramar/Cerrar visita are only in the quick-actions menu, not standalone card buttons. Graph check: `AgendaPage()`, `AgendaPage.tsx`, `Menu()`, `Card()`, `AgendaPage.test.tsx`, `primitives.css`; `AgendaPage()` contains and imports Menu via `AgendaPage.tsx` (path query). Runtime harness: N/A; UI-only styling/affordance change with existing component tests exercising menu activation. Rollback boundary: revert T2 changes in `AgendaPage.tsx`, `AgendaPage.test.tsx`, `primitives.css`, and this progress entry.
- [x] T3 visit detail header (`agenda-028..030`): tests observed RED (eyebrow and mobile CSS contract failed), then GREEN (8/8 focused); full Vitest suite 94 files / 981 tests passed; `npm run build` passed with the existing chunk-size advisory. Removed the eyebrow; moved “Volver a agenda” into the shared `PageFrame` header actions as a secondary `Button`, preserving mutation action handlers; mobile header copy is allowed to shrink and actions wrap at full width. Graph check: `AppointmentDetail()`, `AppointmentDetail.tsx`, `PageFrame()`, `ClientFicha.tsx`, `ConversationThread.tsx`, `AppointmentDetail.test.tsx`, `primitives.css`; graph confirms `AppointmentDetail.tsx` imports `PageFrame()`. Runtime harness: N/A; header markup and mobile CSS contract are covered by focused component tests. Rollback boundary: revert T3 changes in `AppointmentDetail.tsx`, `AppointmentDetail.test.tsx`, `primitives.css`, and this progress entry.
- [x] T4 visit detail layout (`agenda-031`, `agenda-034`, `agenda-035`): tests observed RED (3 focused failures), then GREEN (10/10 focused); full Vitest suite 94 files / 983 tests passed; `npm run build` passed with the existing chunk-size advisory. Programación and Historial now form the two-thirds left column; one Cliente sidebar card contains client, technician, and Resumen; CSS enlarges both avatars using existing spacing/type tokens without changing Avatar API. Tablet/mobile continue to stack schedule, sidebar, and history. Graph check: `AppointmentDetail()`, `AppointmentDetail.tsx`, `Avatar()`, `AppointmentDetail.test.tsx`, and `primitives.css`; path confirms AppointmentDetail imports Avatar. Runtime harness: N/A; this is layout-only, tested through DOM structure and CSS contracts. Rollback boundary: revert T4 changes in `AppointmentDetail.tsx`, `AppointmentDetail.test.tsx`, `primitives.css`, and this progress entry.
- [x] T5 visit history (`agenda-032`, `agenda-033`): tests observed RED (2 focused failures), then GREEN (11/11 focused); first full suite run had one unrelated transient `ConversationsList.test.tsx` empty-state timing failure, rerun passed (94 files / 984 tests); `npm run build` passed with the existing chunk-size advisory. Added a divider below the history header, timeline connectors between event icons, and labelled key/value disclosure rows with humanized known history keys and scalar/nested values instead of a raw JSON `<pre>`. Graph check: `AppointmentDetail()`, `AppointmentDetail.tsx`, `AppointmentDetail.test.tsx`, and `primitives.css`; graph path confirms the page/test import relationship; stylesheet path query found no graph path. Runtime harness: N/A; presentation-only changes covered by component/CSS contract tests. Rollback boundary: revert T5 changes in `AppointmentDetail.tsx`, `AppointmentDetail.test.tsx`, `primitives.css`, and this progress entry.
- [x] T6 reschedule and closure dialogs (`agenda-026`, `agenda-027`): tests observed RED (3 focused failures), then GREEN (19 tests across `AppointmentDetail.test.tsx` and `AppointmentDetail.stories.test.tsx`); full Vitest suite 94 files / 984 tests passed; `npm run build` passed with the existing chunk-size advisory. Both dialogs now reuse the shared icon/description header; reschedule shows current scheduling, editable replacement fields, local-time helper, and Cancelar/Confirm actions; closure shows selected appointment, accessible selectable outcomes, irreversible-action warning, and Cancelar/Confirm actions. Existing mutation semantics and error StateMessage are retained; closure confirm and outcome inputs disable while mutating. Updated the Storybook test to the approved “Fecha” field label. Graph check: `AppointmentDetail()`, `Dialog()`, `AppointmentDetail.tsx`, `AppointmentDetail.test.tsx`, `AppointmentDetail.stories.test.tsx`, and `primitives.css`; path confirms AppointmentDetail imports Dialog. Runtime harness: N/A; dialog flows and mutation outcomes are exercised by component tests. Rollback boundary: revert T6 changes in `AppointmentDetail.tsx`, both AppointmentDetail test files, `primitives.css`, and this progress entry. **Implementation units T1–T6 are complete.**
- [x] WU11 create dialog (`agenda-038`; commit follows): focused tests observed RED (new create-form contract failed on missing group/icon/primary action rules and reference labels); then GREEN (55 tests across AgendaPage component and Storybook files passed); full Vitest suite 94 files / 988 tests passed; `npm run build` passed with existing chunk-size advisory. Sectioned the form, paired identity fields and service/technician, added leading icons and responsive field rows, and gave create a primary footer action with Cancelar. Validation/data mutations remain unchanged. Graph: `AgendaPage()`, `Dialog()`, `AgendaPage.tsx`, both AgendaPage test files, `primitives.css`; AgendaPage imports Dialog. Runtime: existing create flow tested; no separate browser harness. Rollback: revert WU11 changes in AgendaPage source/component test/story test, primitives CSS and this progress entry.
- [x] WU12 reschedule dialog reuse (`agenda-039`; `cc7b6501`): focused Agenda/AppointmentDetail component and Storybook tests passed; full Vitest suite 94 files / 988 tests passed; `npm run build` passed with the existing chunk-size advisory. Extracted and reused `AppointmentRescheduleDialog` from the list and detail routes while preserving mutation behavior and feedback. Graph/rollback details are retained in the commit-level task evidence.
- [x] WU7 — Selected-day heading (`agenda-036`, `agenda-037`; `ef33455a`): tests observed RED (4 focused failures: lowercase period label, missing heading class/gap, and downstream assertions for lower-case day names), then GREEN (`agendaTime.test.ts` + `AgendaPage.test.tsx`: 56 tests passed); full suite 94 files / 985 tests passed; `npm run build` passed with the existing chunk-size advisory. `agendaPeriodLabel` uppercases only the initial localized letter; the selected-day heading uses a flex gap between date and Hoy badge. Updated calendar accessibility-name test expectations for sentence-initial uppercase. Graph check: `agendaPeriodLabel()`, `AgendaPage()`, `AgendaPage.tsx`, `agendaTime.ts`, `agendaTime.test.ts`, `AgendaPage.test.tsx`; graph path shows agendaPeriodLabel is called by AgendaPage. Runtime harness: N/A; pure date formatting, DOM behavior, and CSS contract covered by tests. Rollback boundary: revert WU7 changes in these four source/test files and this progress entry.
- [x] WU8 — Closure non-completion wording (`agenda-042`; `a9658d1c`): tests observed RED (2 focused failures because the old “No asistió” option was still rendered), then GREEN (11/11 `AppointmentDetail.test.tsx` tests); full suite 94 files / 985 tests passed; `npm run build` passed with the existing chunk-size advisory. Changed the visible option to “No completada” / “La visita no se completó.” while retaining its `no_show` outcome value and request semantics. Graph check: `AppointmentDetail()`, `closeOutcome`, `AppointmentDetail.tsx`, `AppointmentDetail.test.tsx`; query consulted the closure component community; path query found no `closeOutcome` node. Runtime harness: N/A; existing component tests verify the selected outcome submits `no_show` and preserves the mutation contract. Rollback boundary: revert the wording/test expectation changes in `AppointmentDetail.tsx`, `AppointmentDetail.test.tsx`, and this progress entry.
- [x] WU9 — History detail UX (`agenda-043`; `20c974e4`): tests observed RED (the `rescheduled` heading, ISO timestamps, and bare technician IDs failed the readable-output assertions), then GREEN (11/11 `AppointmentDetail.test.tsx` tests); full suite 94 files / 985 tests passed; `npm run build` passed with the existing chunk-size advisory. Added Spanish action labels, reused appointment status labels in descriptions/disclosure, localized ISO date/time detail values, and labelled unresolved technician IDs explicitly. Graph check: `AppointmentDetail()`, `appointmentStatusLabel()`, `AppointmentDetail.tsx`, `toneMaps.ts`, `AppointmentDetail.test.tsx`; path confirms AppointmentDetail calls appointmentStatusLabel. Runtime harness: N/A; history payload rendering covered by component test with rescheduled timestamp/ID details. Rollback boundary: revert WU9-only changes in `AppointmentDetail.tsx`, `AppointmentDetail.test.tsx`, and this progress entry.
- [x] WU10 — Detail mobile header (`agenda-044`; `5d1638ab`): tests observed RED (mobile CSS contract lacked compact row alignment and explicit flex sizing), then GREEN (12/12 `AppointmentDetail.test.tsx` tests); full suite 94 files / 986 tests passed; `npm run build` passed with the existing chunk-size advisory. Mobile detail header copy/actions now occupy explicit stacked full-width flex rows with a normal tokenized row gap and top alignment, avoiding stretch from the desktop 30rem copy basis. Graph check: `AppointmentDetail.tsx`, `PageFrame()`, `PageHeader()`, `primitives.css`, `AppointmentDetail.test.tsx`; graph path confirms AppointmentDetail -> PageFrame -> PageHeader. Runtime harness: N/A; CSS-contract test validates mobile flex layout. Rollback boundary: revert WU10 CSS, CSS contract test, and this progress entry.
- [x] WU-opt — Technician-name mitigation (`agenda-014`, `agenda-043`): tests observed RED (focused component test showed only the numeric fallback, not the lookup result), then GREEN (13/13 `AppointmentDetail.test.tsx` tests); full suite 94 files / 987 tests passed; `npm run build` passed with the existing chunk-size advisory. The detail now fetches `/panel/api/technicians` asynchronously by assigned ID, displays the endpoint's username when present, and retains `Técnico #<id>` when the request fails or has no match; no detail fetch is blocked and no API/serializer contract changed. Graph check: `AppointmentDetail()`, `fetchTechnicians()`, `api.ts`, `types.ts`, `AppointmentDetail.test.tsx`, and `AppointmentDetail.stories.test.tsx`; graph path reaches fetchTechnicians via `api.ts` (ambiguous source included `closeAppointment`). Runtime harness: N/A; component test verifies asynchronous resolution and failure fallback; Storybook API mock updated to supply fetchTechnicians. Rollback boundary: revert WU-opt effect/display/test/mock changes in `AppointmentDetail.tsx`, component/story tests, and this progress entry.
- [ ] WU11 — Create dialog (`agenda-038`): tests observed RED (6 focused failures for the missing reference group/field labels, icons, and primary footer styling), then GREEN (55 tests across `AgendaPage.test.tsx` and `AgendaPage.stories.test.tsx` passed); full suite 94 files / 988 tests passed; `npm run build` passed with the existing chunk-size advisory. Grouped customer/case and service/technician fields, added leading icons to applicable form controls, used the sectioned responsive layout and a secondary Cancelar / primary Crear visita footer. Existing create validation, APIs, and mutation flow remain intact; Storybook test updated for “Caso vinculado”. Graph check: `AgendaPage()`, `Dialog()`, `AgendaPage.tsx`, `AgendaPage.test.tsx`, `AgendaPage.stories.test.tsx`, and `primitives.css`; graph path confirms AgendaPage imports Dialog. Runtime harness: N/A; current create flow and create dialog structure are exercised in component/story tests. Rollback boundary: revert WU11 changes in `AgendaPage.tsx`, its component and Storybook tests, `primitives.css`, and this progress entry.
- [x] WU13 — Closure dialog reuse (`agenda-041`; `0ed4b9e7`): focused RED exposed that the list still rendered the old two-button closure modal and lacked the shared visit summary/outcome controls; GREEN passed `AgendaPage.test.tsx` (43 tests) and `AgendaPage.stories.test.tsx` (12 tests). Full Vitest suite: 94 files / 988 tests passed; `npm run build` passed with the existing chunk-size advisory. Extracted `AppointmentClosureDialog` and reused it from the detail and list routes; the list resets the selected outcome to `completed`, shows local date/time and customer, and retains its existing `closeAppointment` call and success/error feedback. Graph check: `AgendaPage()`, `AgendaPage.tsx`, `AppointmentDetail.tsx`, `AgendaPage.test.tsx`, `Dialog.tsx`; the graph confirmed AgendaPage imports Dialog and AgendaPage.test.tsx imports AgendaPage. The graph does not yet include the new shared component. Runtime harness: N/A; the closure mutation flow and rendered dialog were exercised by focused component and Storybook tests. Rollback boundary: revert WU13 changes in `AppointmentClosureDialog.tsx`, `AgendaPage.tsx`, `AppointmentDetail.tsx`, `AgendaPage.test.tsx`, `AgendaPage.stories.test.tsx`, and this progress entry.
- [x] WU14 — List cancellation dialog design (`agenda-040`; commit pending): focused RED failed because the dialog still had a dynamic customer/service title and no shared icon/description, selected-visit summary, warning, or Cancelar action; GREEN passed the focused cancellation case, then both Agenda tests passed (55 tests across component and Storybook files). Full Vitest suite: 94 files / 988 tests passed; `npm run build` passed with the existing chunk-size advisory. Added the icon-tile/description header, selected customer and local date/time, retained the cancellation-reason textarea and optional trimmed reason forwarding, displayed an irreversible-action warning, and added the shared Cancelar/primary Confirmar cancelación footer. The cancel API semantics and list refresh path are unchanged; shared footer styles stack at the mobile breakpoint and selected-visit/warning styles are reused. Graph check: `AgendaPage()`, `AgendaPage.tsx`, `Dialog()`, `Dialog.tsx`, `AgendaPage.test.tsx`; graph confirms AgendaPage imports Dialog and the component test imports AgendaPage. Runtime harness: N/A; user-event component and Storybook tests cover cancellation/reason/refresh behavior; the responsive footer uses existing shared CSS. Rollback boundary: revert WU14 changes in `AgendaPage.tsx`, `AgendaPage.test.tsx`, `AgendaPage.stories.test.tsx`, and this progress entry; leave the WU13 shared closure component untouched.
## Next step

All work units T0–T6 are implemented and committed. RDD review (medium, lineage
`review-751415fdd96e5a0c`, lens `review-reliability`): **approved, no findings; authority burned**
(`gentle-ai.review-acknowledged/v1`). Remaining: owner visual validation of the built section against
the references (desktop/tablet/mobile) — dev server `http://localhost:5177/panel/app/agenda` — and,
when the owner requests delivery, chained PRs (forecast ≈453 authored lines, above the 400 advisory).

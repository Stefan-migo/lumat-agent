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
- [ ] T0 capture tooling fix.
- [x] T1 calendar (`agenda-021`, `agenda-025`): tests observed RED (3 focused failures), then GREEN (11/11 focused); full Vitest suite 94 files / 978 tests passed; `npm run build` passed with the existing chunk-size advisory. Calendar visit-count labels are omitted for zero-count cells, and mobile day controls use round, compact cells while retaining accessible visit counts and button state. Graph check: `AgendaCalendar()`, `AgendaCalendar.tsx`, `agendaTime.ts`, `primitives.css`, and `Mobile`; graph path from `AgendaCalendar()` to `primitives.css` reported no directed path (ambiguous stylesheet match).
- [x] T2 scheduled-visit card (`agenda-022..024`): tests observed RED (3 focused failures), then GREEN (41/41 focused); full Vitest suite 94 files / 980 tests passed; `npm run build` passed with the existing chunk-size advisory. Added a clock glyph beside the time, removed the default title underline (retaining hover underline), and added decorative icons to available visit quick actions. D2 remains intact: Reprogramar/Cerrar visita are only in the quick-actions menu, not standalone card buttons. Graph check: `AgendaPage()`, `AgendaPage.tsx`, `Menu()`, `Card()`, `AgendaPage.test.tsx`, `primitives.css`; `AgendaPage()` contains and imports Menu via `AgendaPage.tsx` (path query). Runtime harness: N/A; UI-only styling/affordance change with existing component tests exercising menu activation. Rollback boundary: revert T2 changes in `AgendaPage.tsx`, `AgendaPage.test.tsx`, `primitives.css`, and this progress entry.
- [ ] T0 capture tooling fix; T3–T6.

## Next step

Commit the task record and the capture fix, then implement T1–T6 in order with RED/GREEN per unit.

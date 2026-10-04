# ODD task — agenda panel redesign

## Objective
Match the agenda section to the owner-approved references, implementing the validated findings
`agenda-001..020` across its three surfaces:
- list (`/panel/app/agenda`, `web/src/components/pages/AgendaPage.tsx`),
- visit detail (`/panel/app/agenda/:id`, `web/src/components/pages/AppointmentDetail.tsx`),
- new-visit dialog (`AgendaPage.tsx`).

## Problem
The agenda list renders four loose calendar buttons and "Hoy"/"Próximas" data tables; the header,
visit detail and dialog deviate from the references. The owner ran the image-first analysis
(machine v2): capture, owner visual analysis (the gate), read-only code analysis, and a
fresh-context validator that returned `PASS` over 20 rows on 2026-10-02
(`odd/analysis/agenda/findings.md`). The reference governs geometry/layout; the design system
governs palette; the references are AI-generated and compressed, so mobile/tablet must follow the
design system's air and spacing instead of the reference density.

## Why now
Owner authorized implementation on 2026-10-04 and closed the only open question: more than one
active visit in the day-detail card renders as stacked large cards.

## Scope
In:
- `web/src/components/pages/AgendaPage.tsx`: page header (subtitle + count chip + action icon),
  register as a day-detail card surface, row actions as a kebab menu, responsive card list,
  new-visit dialog title/sections/actions.
- `web/src/components/pages/AppointmentDetail.tsx`: header (eyebrow/subject/badge/actions),
  Programación / Cliente / Técnico / Resumen cards, history timeline.
- `web/src/components/shared/AgendaCalendar.tsx`: segmented Mes/Semana toolbar, legend + period footer.
- `web/src/components/shared/PageHeader.tsx`: optional subtitle/eyebrow props if needed by 001/009.
- `.agenda-page__*`, `.agenda-calendar*`, `.agenda-create-form` rules in
  `web/src/components/primitives/primitives.css`.
- Tests for every touched file.

Out:
- `web/src/tokens/tokens.css`: palette is settled; no `token-palette` finding on agenda.
- Backend (`app/…`): the agenda API already returns the needed fields.
- Other panel sections and `TechnicianAgenda.tsx` (a separate technician surface).

## Constraints
- Tokens only. Do NOT touch `tokens.css`. No white element backgrounds; use `var(--surface)` /
  `var(--brand-bg-elevated)`.
- Follow the design system's air/spacing on mobile/tablet; do not copy the reference's compressed
  density.
- UI copy neutral Chilean Spanish; code, comments, commits and artifacts English.
- Preserve every existing behavior: cancel, close ("Completar"/"No asistió"), reschedule, calendar
  sync retry, create visit, manual case creation, permissions, and API calls.
- Tests and docs stay with the behavior in the same commit.

## Authorized scope
- Worktree: `/home/stefan/repos/lumat-agent-odd-agenda-redesign`
- Branch: `odd/agenda-redesign`
- No push, PR, or merge without explicit owner approval.

## Checks (run in the worktree, from `web/`)
- `npm run test`
- `npx tsc -b --noEmit`
- `npm run build`

## TDD mode
`openspec/config.yaml` declares `testing.strict_tdd: true` for the backend (`uv run pytest tests/`).
This pass is web-only with runner `cd web && npm run test` (vitest). Consistent with the usuarios
pass: tests required alongside each behavior, full suite green before each work-unit commit. Every
behavioral change (kebab actions, responsive selection, dialog submit) carries a test; pure
layout/CSS findings assert structure.

## Graph nodes consulted (graphify)
`AgendaPage()` (AgendaPage.tsx:51), `AppointmentDetail.tsx`, `AgendaCalendar`, `Dialog()`
(Dialog.tsx:18), `PageFrame()` (PageFrame.tsx:14), `Badge`, `Button`, `shared/toneMaps.ts`,
`agendaTime.ts`, `pathForRoute()` (panelRoutes.ts:61). Community `AgendaPage.tsx` groups
`AppointmentDetail.tsx` and `agendaTime.ts`.

## Decision
`agenda-006` multi-visit = stacked large cards, one per visit, vertical scroll. Recorded in Engram
`#5621` (`design/agenda-multi-visit-layout`).

## Work units
### WU1 — shared-primitive roll-up (findings 004, 005, 018, 019)
- `AgendaCalendar.tsx` + `.agenda-calendar*`: replace the four loose buttons with a `‹ Hoy ›`
  stepper plus a single segmented `Mes`/`Semana` control; add a footer row with a "Visitas" legend
  dot (left) and a period count ("N visitas en <mes>", right).
- `AgendaPage.tsx` + `.dialog*`: pass `icon` + `description` to the new-visit `Dialog` (primitive
  already supports both).
- `AgendaPage.tsx` + `.agenda-create-form`: section the form into "Datos de la visita" (Cliente,
  Caso vinculado, Servicio | Técnico) and "Fecha y horario" (Fecha | Hora | Duración, Zona horaria)
  with a multi-column layout.
- Update `AgendaCalendar.test.tsx`, `AgendaPage.test.tsx`, stories.

### WU2 — agenda list (findings 001, 002, 003, 006, 007, 008)
- Header: subtitle sentence under the title (001), visit count as a chip beside the title (002),
  leading `+` icon on "Nueva visita" (003).
- Register: replace the "Hoy"/"Próximas" data tables with a day-detail card surface showing the
  selected day's visits as stacked large cards (date + "Hoy" chip, time, service, state, client,
  technician, calendar sync, actions) (006).
- Row actions: single kebab (`…`) menu instead of the stacked text buttons (007).
- Responsive: card layout for mobile/tablet that fits the viewport, no horizontal clipping (008).
- Update `AgendaPage.test.tsx`, stories.

### WU3 — visit detail (findings 009–016)
- Header: eyebrow "DETALLE DE VISITA", subject as title, subtitle "Información y seguimiento de la
  visita.", state badge beside the title, icon actions ("Reprogramar", "Cerrar visita") and a
  separate "Volver a agenda" back link (009, 010, 011).
- Cards: "Programación" (day/date block + start-time block + "Calendario sincronizado") (012),
  "Cliente" (circular avatar + "Ver ficha del cliente →") (013), "Técnico asignado" (avatar +
  "Responsable de la visita") (014), "Resumen" ("Motivo" / "Estado") (015).
- History: timeline with event icon, title, date, description, "Registro inicial" tag and a "Ver
  detalles" disclosure (016).
- Update `AppointmentDetail.test.tsx`, stories.

### WU4 — new-visit dialog (findings 017, 020)
- Title "Nueva visita" (017); action row "Cancelar" alongside "Crear visita" (020).
- Update `AgendaPage.test.tsx`.

## Delivery
- Forecast: ~700–900 authored changed lines → over the 400-line review budget.
- Planned slices: PR1 = WU1 (roll-up); PR2 = WU2 (list); PR3 = WU3 (detail); PR4 = WU4 (dialog).
- Chain strategy: pending owner decision (default `ask-on-risk`); decide before the first PR.
- Local work-unit commits are allowed on the branch without a chain decision.

## Acceptance criteria
- [ ] Findings `agenda-001..020` implemented.
- [ ] `npm run test`, `npx tsc -b --noEmit`, `npm run build` all green.
- [ ] Mobile/tablet register fits the viewport with no horizontal clipping.
- [ ] Existing agenda behaviors preserved.

## Progress
- [x] WU1 — shared-primitive roll-up (`26e94b16`; findings 004, 005, 018, 019)
- [ ] WU2 — agenda list
- [ ] WU3 — visit detail
- [ ] WU4 — new-visit dialog

## Verification evidence
### WU1 (`26e94b16`, 2026-10-04)
- `npm run test` → 94 files, 973 tests passed.
- `npx tsc -b --noEmit` → exit 0 (parent spot check re-confirmed).
- `npm run build` → passed (existing >500 kB chunk advisory only).
- RDD assess (base `42c8c5ae`, committed-only): risk `medium`, 229 changed lines, `review_due: false` (`under_budget`) — no review due yet; boundary stays pending in the slice.
- Applied change: the calendar toolbar/segmented control, calendar footer, create-form sections, and the new-visit Dialog icon+description.

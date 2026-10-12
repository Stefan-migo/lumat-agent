# agenda-technician-schedule-tab

## Objective

Replace the ad-hoc "Horarios de técnicos" disclosure in the Agenda page with a first-class register
tab ("Técnicos") whose list and inline weekly editor follow the Lumat design system and the existing
`HoursEditor` interaction pattern.

## Problem

T5 (PR #560) shipped the per-technician weekly schedule editor as a bare `<details>` block below the
Agenda layout plus a modal dialog. It uses tokens and primitives, but the integration does not read as
part of the panel: an unstyled-feeling disclosure, a modal editor, and no alignment with the register
tabs. The owner asked for the configuration to live in a dedicated tab beside "Activas / No activas"
and to follow the current Lumat design logic.

## Scope

**In:**
- A third register tab in Agenda ("Técnicos"), shown beside "Activas" / "No activas".
- A technician list in the Lumat row idiom (name + weekly summary + "Editar horario").
- An inline weekly editor (NO modal) per technician, reusing the `HoursEditor` interaction pattern
  (`DayToggle` + time inputs, one window per weekday) with a per-technician "Guardar horario".
- Complete states: roster loading / empty / error+retry; technician schedule loading / saving / saved /
  validation / server error.
- Vitest + Storybook coverage. The old `agenda-page__schedules*` `<details>` markup + CSS and the
  `TechnicianScheduleDialog` modal are removed.

**Out (deliberate):**
- No backend change; `app/services/technician_schedule.py` and the schedule API contract are untouched.
- No change to the `api.ts` / `types.ts` client contract (reuse `getTechnicianSchedule` /
  `saveTechnicianSchedule`).
- Not moved to Settings (owner chose the Agenda tab; Option B rejected).
- No changes to the visit create / reschedule / cancel / close flows.

## Authorized scope

- Worktree: `lumat-agent-odd-agenda-technician-schedule-tab`
- Branch: `odd/agenda-technician-schedule-tab`
- Base: `0046e4c6` (`origin/main`)
- Files (expected):
  - `odd/tasks/agenda-technician-schedule-tab.md` (this record)
  - `web/src/components/pages/AgendaPage.tsx` (+ `.test.tsx`)
  - `web/src/components/shared/TechnicianScheduleEditor.tsx` (+ `.test.tsx` + `.css`) — replaces
    `TechnicianScheduleDialog.tsx` / `.css` / `.test.tsx`, which are deleted.
  - `web/src/components/primitives/primitives.css` (remove the old `.agenda-page__schedules*` rules;
    add the new tab/list styles, or a page-scoped CSS).
  - `web/src/stories/pages/AgendaPage.stories.tsx` (+ `.test.tsx`)

Any file outside this list needs a scope update here first.

## Constraints

- **Strict TDD: ON.** Web runner `cd web && npx vitest run`; type check `cd web && npm run build`.
  Observe RED before the source change. Never invent RED evidence.
- **Design:** follow `web/DESIGN_SYSTEM.md`. Reuse primitives and semantic tokens; add NO dependency;
  keep NO raw hex outside `tokens.css`. One `PageFrame` header. UI copy neutral Chilean Spanish;
  code, comments, and commits in English.
- The schedule API contract and its operator role stay unchanged.

## Design (target)

- Register `Tabs`: `Activas` | `No activas` | `Técnicos`.
- `Técnicos` tab: a list of technicians, each row in the `.settings-hours__item` idiom (name, a weekly
  summary such as "Lun–Vie 09:00–18:00 · Sáb 09:00–14:00", or "Sin horario"), with an "Editar horario"
  control that reveals an inline editor for that technician only.
- Inline editor: 7 rows Lun→Dom; a day toggle (`Button` with `aria-pressed`, styled like the
  `DayToggle` selected state, tokens only) + `Inicio` / `Fin` `Input type="time"`; validation
  `inicio < fin`; one primary "Guardar horario"; controls disabled when off/saving/invalid. Load the
  technician's schedule on first expand.

## Work units (stable IDs)

### W1 — Roster tab shell
- [x] Add the "Técnicos" register tab beside "Activas" / "No activas".
- [x] Roster states: loading, empty, error + retry (es-CL copy, `StateMessage`).

### W2 — Technician row list
- [x] Rows with name, weekly summary, and "Editar horario".

### W3 — Inline editor (replaces the modal)
- [x] Load/save/validation/states inline; no dialog.

### W4 — Remove the old surface
- [x] Delete the `<details>` roster, the modal, and their CSS.

### W5 — Coverage
- [x] Vitest for the tab, list, editor behavior, and states.
- [x] Storybook variants; focused suite + `npm run build` green.

## Acceptance criteria

1. Agenda shows a "Técnicos" tab beside "Activas" / "No activas".
2. Expanding a technician shows an inline editor; saving persists and the row summary updates.
3. Invalid interval blocks save with an inline es-CL message; a server error stays beside the action.
4. No schedule modal remains; the old disclosure markup/CSS is gone.
5. Focused web suite green; `npm run build` green.

## Checks

- `cd web && npx vitest run src/components/pages/AgendaPage.test.tsx src/components/shared/TechnicianScheduleEditor.test.tsx src/stories/pages/AgendaPage.stories.test.tsx`
- `cd web && npm run build`
- `git diff --check`

**Environment caveat:** the full `npx vitest run` is not a usable local signal (5s timeouts under
load); use focused runs. `AgendaPage.test.tsx` is green in isolation.

## Graph Check (consulted)

`graphify query "technician weekly schedule editor agenda register tab settings hours DayToggle"`:
nodes `AgendaPage.tsx` (community `AgendaPage.tsx`), `HoursEditor()` / `Settings()` (community
`Settings.tsx`), `DayToggle()`, `Tabs.tsx`, `StateMessage()`, `Button()`, `api.ts` / `apiFetch()` /
`postJson()`, `types.ts`. Affected communities: `AgendaPage.tsx` and `Settings.tsx`.

## Declared debt (carried in)

- **R3-001 (from the T5 review, non-blocking):** the editor can overwrite the draft with stale data if
  the selected technician changes with an in-flight schedule load. The inline refactor removes the
  modal remount; re-check and repair while touching the editor if cheap, otherwise keep this recorded.

## Progress log

- Worktree created from `origin/main` = `0046e4c6`; branch `odd/agenda-technician-schedule-tab`.
  Env: `uv sync`, `infra/.env`, worktree test DB up, `npm install`. No source changes yet.
- W1–W5 implemented in the authorized files. First focused RED captured before component changes:
  `npx vitest run src/components/pages/AgendaPage.test.tsx -t "loads technician roster|removes the old disclosure|shows roster errors"`
  failed (3 tests) because the `Técnicos` tab did not exist. GREEN:
  `npx vitest run src/components/pages/AgendaPage.test.tsx src/components/shared/TechnicianScheduleEditor.test.tsx src/stories/pages/AgendaPage.stories.test.tsx`
  passed (3 files, 65 tests). `npm run build` and `git diff --check` passed. Added an additional
  RED/GREEN test for compact weekday-range summaries: the first run failed because it rendered each
  weekday separately; the formatter now combines consecutive days with identical hours.

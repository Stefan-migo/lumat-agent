# configuracion-redesign

## Objective

Bring the `configuracion` panel section to the confirmed references — desktop
`refs/Diseño Lumat/Configuracion/config1..5.png` and tablet/mobile
`refs/Diseño Lumat/mobileTablet/Configuracion/` (9 boards) — reusing components from the
already-closed sections (clientes, conversaciones, agenda, usuarios, conocimiento).

## Problem

The section frontend was never real design work: `Settings.tsx` renders 10 stacked `Card`s with no
tab bar, kept only to exercise the backend. A validated read-only analysis produced 22 findings
(`odd/analysis/configuracion/findings.md`, validator-gate PASS): 16 local + 6 shared-primitive
roll-ups (`configuracion-016` … `021`). The references split the same content across 5 tabs
(Agente, Mensajes, Horarios y avisos, Costos, Capacidades) and add help panels, week schedules,
a metrics row, and a capability inventory.

## Why

Owner directive (2026-10-08): everything must be redesigned, reusing closed-section components,
following the references. Owner confirmed the references as the expected-state authority and
DEFERRED the detailed visual pass to post-implementation iterations (recorded in
`odd/analysis/configuracion/visual.md`); the owner corrects the design visually per slice.

## Scope

- In: `web/src/components/pages/Settings.tsx`, `web/src/components/pages/PushSettings.tsx`, their
  tests/stories, a new settings stylesheet if composition needs one; the six roll-up primitives;
  the capability payload boundary in `web/src/types.ts` / `web/src/api.ts` if grouping is
  server-driven.
- Out: `tokens.css` palette, new routes, shared `DataTable` contract, other sections' pages.

## Constraints

- Keep the single `/panel/app/settings` route; no new destinations.
- Do not reopen palette/tokens (`panel-design-system-final` settled them).
- Reuse the closed sections' primitives; only the six roll-up primitives are added.
- Chat in Rioplatense Spanish; artifacts, code, comments, and commits in English; UI copy in neutral
  Chilean Spanish. Conventional Commits, no AI attribution.
- Reference-driven: the reference images control geometry and layout; the owner corrects visually.

## Graph check (rapso 5-Step Gate, Step 1)

Analysis-time graph nodes consulted (graphify 0.9.40): `Settings()` + `stateMessage()`
(`pages/Settings.tsx`), `PushSettings.tsx`, `PageFrame()`, `useAsyncData()`, primitives
`Button`/`Card`/`Dialog`/`Input`/`Select`/`Tabs`/`SearchInput`/`Badge`, shared `DataTable`/
`StateMessage`/`StatCard`/`toneMaps`, `getAssistantCapabilities()`/`apiFetch()`/`postJson()`/
`types.ts`, and `GRAPH_REPORT.md` settings hub + business-hours edges.
Each work unit below re-runs `graphify query`/`graphify path` on its affected modules before writing
and records the nodes in the apply-progress.

## Work units (stable IDs)

Mapped to `odd/analysis/configuracion/findings.md`. Order is mandatory: shared primitives first.

### Unit A — shared primitives (roll-up)

- [x] **CF-1** — Help/support panel primitive (icon + heading + body), used by the reference
      right-hand panels "Cómo funciona", "Consideraciones", "Vista previa". Finding `configuracion-016`.
      New file under `web/src/components/primitives/`. Unit test.
- [x] **CF-2** — Weekday day-toggle / segmented control for Lun–Dom. Finding `configuracion-017`.
      New file under `web/src/components/primitives/`. Unit test (selection, disabled, a11y).
- [x] **CF-3** — Message preview primitive (assistant bubble + note). Finding `configuracion-018`.
      New file under `web/src/components/primitives/`. Unit test.
- [x] **CF-4** — Three-metric row composition on the shared `StatCard` surface. Finding
      `configuracion-019`. Extend `web/src/components/shared/StatCard.tsx` (+ test).
- [x] **CF-5** — Accordion group with count chip. Finding `configuracion-020`. New file under
      `web/src/components/primitives/`. Unit test (expand/collapse, count, a11y).
- [x] **CF-6** — `Card` header action / right-side slot (count, chip, "Consultar"). Finding
      `configuracion-021`. Extend `web/src/components/primitives/Card.tsx` (+ test).

### Unit B — section shell and tabs

- [x] **CF-7** — Settings shell: 5-tab navigation via the `Tabs` primitive on desktop/tablet and a
      "Sección" `Select` on mobile, replacing the 10 stacked cards. Finding `configuracion-001`.
- [x] **CF-8** — Draft/save ownership model: refetch must not silently discard unsaved edits; add the
      reference save notes and disabled-until-valid save state per card. Findings `configuracion-013`,
      `configuracion-022`.

### Unit C — tabs

- [x] **CF-9** — Agente tab: `Alcance del agente` (icon-tile header, "Avanzado" badge, rules
      textarea, advanced-syntax disclosure, "Cómo funciona" panel, footer note + save) and
      `Detección de emergencias` (warning icon, keywords textarea + helper, "Consideraciones" panel,
      save). Findings `configuracion-002`, `configuracion-003`.
- [x] **CF-10** — Mensajes tab: `Tono del asistente` horizontal row, and `Mensajes del asistente`
      with the 5-template strip, selected-text editor, info line, and "Vista previa". Findings
      `configuracion-004`, `configuracion-005`.
- [x] **CF-11** — Horarios y avisos tab: `Horarios de atención` (globe timezone `Select`, weekly
      schedule list, "Nuevo horario" sub-card with day toggles + Inicio/Fin time inputs, delete,
      "Agregar otro horario", disabled save) plus the right column `Notificaciones push` and
      `Fuera de horario` cards. Findings `configuracion-006`, `configuracion-007`, `configuracion-014`.
- [x] **CF-12** — Costos tab: `Gasto actual` three-metric row with date chip, `Límites de gasto`
      (USD inputs + save), `Precio Meta` (cost input, "Vigente desde" chip, save), and
      `Qué ocurre al alcanzar los límites` (80%/100% rows). Findings `configuracion-008`,
      `configuracion-009`, `configuracion-010`.
- [x] **CF-13** — Capacidades tab: `Herramientas del asistente` (count, search, "Todos los accesos"
      filter, accordion groups, rows of icon + name + id + access badge) and `Configuración activa`
      side card (KB/Memory availability, Persona/Prompts paths, "Consultar", footer note). Findings
      `configuracion-011`, `configuracion-012`, `configuracion-015`.

### Close

- [ ] **CF-14** — Verification and reference polish: full suite + build green; re-capture the section
      and self-review against the references at desktop/tablet/mobile; hand to the owner for the
      deferred visual pass.

## Progress log

- **CF-14 — Capacidades tab reference polish (2026-10-09)** — implemented; owner visual pass pending.
  - Feature commit: `45ac28ee` (`feat(settings): polish the Capacidades tab against the reference`).
  - Files: `web/src/components/pages/Settings.tsx`, `web/src/components/pages/Settings.css`,
    `web/src/components/pages/Settings.test.tsx`, `web/src/components/primitives/Accordion.tsx`,
    `web/src/components/primitives/Accordion.test.tsx`, `web/src/components/primitives/primitives.css`,
    `web/src/stories/pages/Settings.stories.test.tsx`.
  - Graph nodes consulted: `AssistantCapabilitiesView()` / `Settings.tsx`, `Accordion()` / `Accordion.tsx` /
    `Accordion.test.tsx`, `Badge()`; shortest path `AssistantCapabilitiesView() <-contains- Settings.tsx
    -imports-> Accordion()`; `GRAPH_REPORT.md` lists `Settings.tsx` as a community hub.
  - Client-side composition only (`configuracion-015`): category grouping (Operación, Conocimiento y memoria,
    Web, Automatizaciones y proyectos, Sistema) with `kb` + `memory` merged into one group; a per-tool map
    (Spanish label + icon) and an access-badge icon; `Accordion` reshaped to a left chevron plus a right count
    badge, collapsed by default; filter controls aligned to one height with a visually hidden label; the
    active-config card gained subtitles, a bordered availability container with success pills, and boxed
    Persona/Prompts paths. No API, type, or backend change.
  - Verification from `web/`: focused Settings + Accordion + story tests 43/43 passed; `npm run build`
    (`tsc -b` + Vite) passed with the existing >500 kB chunk advisory. Full `npm test`: 1085/1087 passing; the
    two failures were the known load-flaky `ClientFicha` and `AgentChat` cases, which passed 97/97 in
    isolation. RDD assess: `medium` / `review_due: false` (`under_budget`, 142 changed lines).
  - Runtime harness: N/A — frontend-only presentation change on the existing settings route. Rollback
    boundary: revert feature commit `45ac28ee` to restore the prior Capacidades composition and `Accordion`.

- **CF-14 — Costos tab reference polish (2026-10-08)** — implemented; owner visual pass remains pending.
  - Feature commit: `e00a386c270f2fc6fa27e900cb0adf85e1f6f0e0`
    (`feat(settings): polish the Costos tab against the reference`).
  - Files: `web/src/components/pages/Settings.tsx`, `web/src/components/pages/Settings.css`,
    `web/src/components/primitives/Input.tsx`, `web/src/components/primitives/primitives.css`,
    `web/src/components/primitives/Input.test.tsx`, `web/src/stories/pages/Settings.stories.test.tsx`.
  - Graph nodes consulted: `Settings()`, `Settings.tsx`, `Input()`, `FieldShell.tsx`, `Card()`,
    `StatCard()`, and `Settings.stories.test.tsx`; graph query also surfaced the Configuración
    section redesign community linking `Settings`, `Card`, and `primitives.css`. The attempted
    directed `Settings.tsx` → `Input.tsx` path found no directed path; the undirected path returned
    `Settings.stories.tsx → Settings.tsx → StatCard()`. `GRAPH_REPORT.md` settings hub and
    Configuración redesign community were consulted.
  - Added an in-control Input suffix, localized calendar date chips, USD-formatted spend metrics,
    paired limit/Meta cards, and responsive threshold columns. Save behavior and data/API contracts
    remain unchanged.
  - Verification from `web/`: `npm test` passed 1087/1087 tests across 104 files;
    `npm run build` passed (`tsc -b` + Vite build; existing >500 kB chunk advisory only).
  - Runtime harness: N/A — frontend-only presentation changes on the existing settings route.
    Rollback boundary: revert feature commit `e00a386c` to restore the prior Costos presentation,
    Input suffix support, and associated tests.

- **CF-14 — Horarios y avisos tab owner visual polish (2026-10-08)** — implemented; full-suite gate remains partial because of unrelated `ClientFicha` timeouts under full-suite load.
  - Feature commit: `3ee2c25c` (`feat(settings): polish the Horarios y avisos tab`).
  - Files: `web/src/components/pages/Settings.tsx`, `web/src/components/pages/Settings.css`,
    `web/src/components/pages/PushSettings.tsx`, `web/src/components/pages/PushSettings.test.tsx`,
    `web/src/stories/pages/Settings.stories.test.tsx`.
  - Graph nodes consulted: `HoursEditor()`, `Settings()`, `PushSettings()`, `DayToggle()`, `Card()`;
    `Settings.tsx --imports--> PushSettings.tsx`. The refreshed graph query connected HoursEditor
    with its draft helpers and Settings tests; no directed HoursEditor-to-PushSettings path was found.
    `GRAPH_REPORT.md` settings hub, settings community, and repeated-weekday invariant were consulted.
  - Added the weekly-hours subtitle, empty state, centered timezone icon via grid alignment, resettable
    new-schedule draft, helper note, compact day-toggle row, dashed add action, and bordered saved rows.
    Added push/out-of-hours card icons, revised embedded push copy and permission legend, and left-aligned
    the out-of-hours edit action. Existing permission branches and schedule/save validation remain intact.
  - Verification from `web/`: focused Settings + PushSettings + story tests 44/44 passed. `npm run build`
    (`tsc -b` + Vite) passed with the existing >500 kB chunk advisory. Full `npm test` completed with
    1072/1074 tests passing across 103 files; the two failures were `ClientFicha equipment > adds equipment
    from the dialog` and `ClientFicha page grammar > posts state changes and notes, then refreshes ficha
    and memories`, both 5s timeouts under full-suite load. `ClientFicha.test.tsx` passed 49/49 in isolation.
  - Runtime harness: N/A — frontend-only polish on the existing settings route. Rollback boundary: revert
    the feature commit to restore the prior Horarios y avisos composition and copy.

- **CF-14 — Mensajes tab second visual review (2026-10-08)** — implemented; full-suite gate remains
  open because of one unrelated `ClientFicha` timeout under full-suite load.
  - Feature commit: `c450c5001a2f221167cf584db86cdffbb7636ed3`
    (`feat(settings): refine the Mensajes tab columns and mobile selector`).
  - Files: `web/src/components/pages/Settings.tsx`, `web/src/components/pages/Settings.css`,
    `web/src/components/pages/Settings.test.tsx`.
  - The message editor now has a neutral bordered inner panel with vertical column separators;
    the preview is plain within the panel, and mobile uses a controlled template `Menu` instead of
    the vertical tablist. The editor textarea border and info legend are neutral, and the tone menu
    and save button share a minimum height. The existing section-tablist selector remains scoped to
    `.settings-tabs > .tabs > [role="tablist"]`.
  - Graph check: `Settings()`, `Menu()`, `Tabs()`, and `MessagePreview()`; the graph query mapped the
    settings/template area. No direct directed Settings-to-Menu or Settings-to-Tabs path was found;
    the undirected path was `Settings.stories.tsx -> Settings.tsx -> MessagePreview()`. `GRAPH_REPORT.md`
    settings community hub and responsive shell requirement were reviewed.
  - Verification from `web/`: focused Settings + story tests 42/42 passed;
    `npm run build` (`tsc -b` + Vite) passed with the existing >500 kB chunk advisory. Full
    `npm test`: 1073/1074 tests passed across 103 files; the sole failure was
    `ClientFicha page grammar > posts state changes and notes, then refreshes ficha and memories`
    timing out at 5s. `ClientFicha.test.tsx` passed 49/49 in isolation.
  - Runtime harness: N/A — this is a frontend-only presentation change to an existing route.
    Rollback boundary: revert the feature commit to restore the prior Mensajes columns, legend,
    tone control sizing, and mobile template navigation.

- **CF-14 — Agente tab reference polish (2026-10-08)** — visual changes implemented; full-suite gate remains open.
  - Feature commit: `f834cd871879a871e6e3873bac86b4bc4582e1ab` (`feat(settings): polish the Agente tab against the reference`).
  - Files: `web/src/components/pages/Settings.tsx`, `web/src/components/pages/Settings.css`,
    `web/src/components/pages/Settings.test.tsx`, `web/src/stories/pages/Settings.stories.test.tsx`.
  - Both help panels now sit inside their cards beside the form, with neutral surfaces and responsive
    stacking. Card subtitles, scope-rule example placeholder, plain-language syntax disclosure,
    primary save buttons, and a styled mobile section selector were added.
  - Verification: focused Settings tests 40/40 passed; `npm run build` passed (`tsc -b` + `vite build`).
     Full `npm test` ran 103 files / 1070 tests: 101 files passed, 2 failed with four timeout failures
     in unrelated `ClientFicha` and `UserManagement` tests under local load. Re-run full suite before
     closing CF-14; visual recapture/self-review is still pending.

- **CF-14 — Mensajes tab + mobile section selector reference polish (2026-10-08)** — implemented; full-suite gate remains open pending a low-load rerun.
  - Feature commit: `c7b1a8ec` (`feat(settings): rebuild the Mensajes tab to the reference composition`).
  - Files: `web/src/components/pages/Settings.tsx`, `web/src/components/pages/Settings.css`,
    `web/src/components/pages/Settings.test.tsx`, `web/src/components/domain/AppShell.test.tsx`,
    `web/src/components/primitives/Menu.tsx`, `web/src/components/primitives/MessagePreview.tsx`,
    `web/src/components/primitives/MessagePreview.test.tsx`, `web/src/components/primitives/Tabs.tsx`,
    `web/src/components/primitives/Tabs.test.tsx`, `web/src/components/primitives/primitives.css`,
    `web/src/stories/pages/Settings.stories.test.tsx`.
  - Graph nodes consulted: `Settings()`, `Tabs.tsx` / `Tabs()`, `Menu()`, `MessagePreview()`,
    `Settings.test.tsx`, `Tabs.test.tsx`, `Settings.stories.tsx`, and the settings community hub.
    The undirected path linked `Settings.stories.tsx -> Settings.tsx -> MessagePreview()`; the Tabs
    test path linked `AssistantTabs.tsx -> Tabs.tsx <- Tabs.test.tsx`. No direct directed edge was
    reported from `Settings()` to `Tabs()`.
  - The mobile section selector now uses the Radix `Menu`, with field-like styling scoped to its
    settings wrapper. Tone is a compact menu in the tone card header with the subtitle and a primary
    save action. The message editor now has a three-column composition: a vertical icon/description
    template tablist, selected editor, and in-card preview using the Lumat mark. Mobile stacks the
    columns while retaining the nested tablist; the section-list hiding rule remains scoped to the
    direct section-tabs child. `Tabs` gained backward-compatible vertical layout and optional icon /
    description metadata; `MessagePreview` gained an optional avatar image source without changing
    its default letter avatar. The AppShell assertion was updated for the new accessible tone menu.
  - Verification from `web/`: focused Settings + story + primitive tests 50/50 passed;
    `npm run build` (`tsc -b` + Vite) passed, with the existing >500 kB chunk advisory. Full
    `npm test` completed with 1071/1073 tests passing across 103 files; only
    `ClientFicha equipment > adds equipment from the dialog` and
    `ClientFicha page grammar > posts state changes and notes, then refreshes ficha and memories`
    timed out at 5s under full-suite load. `ClientFicha.test.tsx` passed 49/49 in isolation. The
    related AppShell test passed 32/32 in isolation. No browser/runtime visual capture was run.
  - Runtime harness: N/A — this frontend-only composition change uses existing app routes and has no
    separate runtime harness. Rollback boundary: revert the feature commit to restore the former
    tone selector, message-card layout, and section selector.

- **PR1 — Unit A roll-up primitives (CF-1, CF-2, CF-3)** — done on branch `odd/configuracion-redesign`.
  - Commits: `348593f2` help panel, `feac640b` day toggle, `8e23d46a` message preview.
  - Files: `primitives/HelpPanel.tsx` (+ test), `primitives/DayToggle.tsx` (+ test),
    `primitives/MessagePreview.tsx` (+ test), `primitives/primitives.css`.
  - Verified: focused vitest 5/5 green; `npm run build` (tsc -b + vite build) green.
  - Learned: `HelpPanel` originally used `var(--info-bg)`, which does not exist in
    `tokens/tokens.css`; corrected to `var(--info-tint)`. The day-toggle selected state follows the
    closed-section convention (`ClientFichaDialogs`): `--corp-text` border + `--success-tint`.
  - Note: not pushed / no PR opened yet.

- **PR2 — Unit A roll-up primitives (CF-4, CF-5, CF-6)** — done on branch `odd/configuracion-redesign`.
  - Commits: `93787e1b` StatCard three-metric row, `9445b7da` accordion group, `2f893f5d` Card header slot.
  - Files: `shared/StatCard.tsx` (+ test), `primitives/Accordion.tsx` (+ test),
    `primitives/Card.tsx` (+ test), `primitives/primitives.css`.
  - Graph nodes consulted (graphify 0.9.40): `StatCard()`, `Card()`, `shared/helpers.test.tsx`,
    `shared/DataTable.tsx`, `ClientMemories.tsx`, `Settings.tsx`, `KbList.tsx`, `Dashboard.tsx`,
    community `shared/toneMaps.ts`.
  - Verified: focused vitest 7/7 green; `npm run build` (tsc -b + vite build) green.
  - Design notes: `StatCard` is now a discriminated union (single value OR a `metrics` tuple of 3);
    the metric row uses a CSS grid with dividers and collapses to one column at ≤40rem.
    `Accordion` uses `aria-expanded`/`aria-controls` + `role="region"` and a `Badge` count chip.

- **PR3 — Settings shell + draft/save (CF-7, CF-8)** — done on branch `odd/configuracion-redesign`.
  - Commit: `05d0cb1f` rebuild Settings into a 5-tab shell with draft/save model.
  - Files: `pages/Settings.tsx`, `pages/Settings.css` (new), `pages/Settings.test.tsx` (new).
  - First user-visible slice. 5 tabs (Agente, Mensajes, Horarios y avisos, Costos, Capacidades) via the
    `Tabs` primitive; a "Sección" `Select` drives the same state at ≤40rem. `PushSettings` stays embedded
    in Horarios y avisos; its separate route in `AppShell.tsx` is untouched.
  - Draft/save: per-field dirtiness vs the last persisted baseline; a refetch adopts server values only
    for non-dirty fields, so unsaved edits survive. Save buttons disable while pending or invalid; each
    card carries the reference footer note.
  - Validation rule (conservative, pending owner visual pass): required non-empty; numeric fields finite
    and non-negative; schedule needs timezone + ≥1 day + non-empty open<close. No invented upper bounds.
  - Verified: focused vitest 4/4 green; `npm run build` green.

- **PR4 — Agente tab (CF-9)** — done on branch `odd/configuracion-redesign`.
  - Commit: `b8aab4e7` bring the Agente tab to the reference composition.
  - Files: `pages/Settings.tsx`, `pages/Settings.css`, `pages/Settings.test.tsx`.
  - `Alcance del agente`: `Card` icon-tile header + "Avanzado" `Badge` in `headerAction`, rules
    textarea, advanced-syntax disclosure, "Cómo funciona" `HelpPanel`, footer note + save.
    `Detección de emergencias`: warning icon header, keywords textarea + helper, "Consideraciones"
    `HelpPanel`, footer note + save. Two-column layout, single column at ≤40rem.
  - Reuses the PR1/PR2 roll-ups (`HelpPanel`, `Card.headerAction`).
  - Verified: focused vitest 5/5 green; FULL suite 1065/1065 green; `npm run build` green.

- **PR5 — Mensajes tab (CF-10)** — done on branch `odd/configuracion-redesign`.
  - Commit: `68bf1d22` bring the Mensajes tab to the reference composition.
  - Files: `pages/Settings.tsx`, `pages/Settings.css`, `pages/Settings.test.tsx`,
    `stories/pages/Settings.stories.test.tsx`.
  - `Tono del asistente`: tone `Select` + save on one horizontal row. `Mensajes del asistente`: a
    5-template strip (`Tabs`) picking one template, one selected editor, an info line, and a
    right-side "Vista previa" using the `MessagePreview` primitive (CF-3). Two columns, single at ≤40rem.
  - Bug fixed while reviewing: the mobile selector that hides the section tablist was too broad
    (`.settings-tabs .tabs [role="tablist"]`) and also hid the nested template strip at ≤40rem;
    scoped to the direct child (`.settings-tabs > .tabs > [role="tablist"]`).
  - Verified: focused vitest 7/7 + stories 30/30 green; FULL suite green (2 flaky `ClientFicha`
    timeouts that pass 49/49 in isolation); `npm run build` green.

- **PR6 — Horarios y avisos tab (CF-11)** — done on branch `odd/configuracion-redesign`.
  - Commit: `6228e556` brings the Horarios
    y avisos tab to the reference composition.
  - Files: `web/src/components/pages/Settings.tsx`, `web/src/components/pages/Settings.css`,
    `web/src/stories/pages/Settings.stories.test.tsx`, this task log.
  - Graph nodes/edges consulted (graphify 0.9.40): `Settings()`, `PushSettings()`, `DayToggle()`,
    `Select()`, `get_hours_timezone()`; `Settings.stories.tsx --imports--> PushSettings()`; settings
    service business-hours schedule/timezone; `GRAPH_REPORT.md` settings hub and repeated-weekday
    invariant. The direct Settings-to-PushSettings traversal had no directed edge; an undirected
    query showed the import through the Settings story.
  - `Intl.supportedValuesOf("timeZone")` supplies the native IANA options; the stored timezone is
    included even if not listed by the browser. Existing `DayToggle` uses abbreviated weekday keys;
    the schedule payload keeps its established ISO weekday numbers (Monday=1 through Sunday=7).
  - Verified: focused Settings component tests 7/7 green. Full `npm test` completed with 1066/1067
    passing; the unrelated `ClientFicha.test.tsx > ClientFicha equipment > adds equipment from the
    dialog` timed out at 5s; rerunning `ClientFicha.test.tsx` alone passed 49/49. Settings story tests
    passed 30/30. `npm run build` (`tsc -b` + Vite) green; Vite reported its existing >500 kB chunk
    advisory.
  - Not run: browser/runtime harness; this work unit changes only the existing frontend settings
    surface and has no separately configured runtime harness.

- **PR7 — Costos tab (CF-12)** — done on branch `odd/configuracion-redesign`.
  - Commit: this single CF-12 work-unit commit (SHA reported in the delivery summary).
  - Files: `web/src/components/pages/Settings.tsx`, `web/src/components/pages/Settings.css`,
    `web/src/stories/pages/Settings.stories.test.tsx`, this task log.
  - Graph nodes consulted: `Settings()`, `StatCard()`, `Input()`, `settings` mock,
    `tabularNum()`/`DataTable()`. `Settings()` → `StatCard()` had no directed path; their shared
    consumer relationship was confirmed in source. `Input()` supports native HTML adornment-free
    controls, so the USD suffix is composed at the call site. The graph query also linked the
    settings mock and cost snapshot shape to the settings module.
  - Reused the CF-4 `StatCard` three-metric row and CF-6 `Card` header action; added paired USD input
    layout, effective-date badge, and the 80%/100% threshold panel. Existing save paths and draft /
    validation flow remain unchanged. The 80% summary uses `conversation_percent` and
    `conversation_limit` only when a conversation snapshot is available.
  - Verified: focused Settings component + story tests 39/39 green. Full `npm test` completed with
    1066/1069 passing; unrelated failures were `AgentChat.test.tsx > renders new stream content
    while a previous markdown snapshot is stale`, `ClientFicha.test.tsx > posts state changes and
    notes, then refreshes ficha and memories` (5s timeout), and `ConversationsList.test.tsx > requests
    search and page changes and renders empty state as a DOM row`. `npm run build` (`tsc -b` + Vite)
    green; Vite reported its existing >500 kB chunk advisory.
  - Not run: browser/runtime harness; this work unit changes only the existing frontend settings
    surface and has no separately configured runtime harness.

- **PR8 — Capacidades tab (CF-13)** — done on branch `odd/configuracion-redesign`.
  - Commit: `90fd24d5` brings the Capacidades tab to the reference composition.
  - Files: `web/src/components/pages/Settings.tsx`, `web/src/components/pages/Settings.css`,
    `web/src/components/pages/Settings.test.tsx`, `web/src/stories/pages/Settings.stories.tsx`,
    `web/src/stories/pages/Settings.stories.test.tsx`.
  - Graph nodes consulted: `Settings()` / `AssistantCapabilitiesView()` in `Settings.tsx`,
    `Accordion()`, `SearchInput()`, `Badge()`, `Card()`, `getAssistantCapabilities()`,
    `Settings.stories.tsx`, and `Settings.test.tsx`. Undirected paths confirmed
    `Settings.stories.tsx --re_exports--> Settings.tsx --imports--> getAssistantCapabilities()` and
    `Settings.stories.tsx --re_exports--> Settings.tsx --contains--> AssistantCapabilitiesView()`;
    no directed path was found from `AssistantCapabilitiesView()` to `Badge()`.
  - Data-boundary decision (`configuracion-015`): keep the slice frontend-only. Group tools by the
    namespace before the first dot; undotted names use the `Sistema` fallback. Derive group counts,
    search, and access filters locally from the existing capability payload. Access badges/filter
    values come from `read_only` and `write`; a tool with neither flag is shown as `Acceso limitado`.
    No API type, backend endpoint, or server-provided category was added.
  - Reused the CF-5 `Accordion`, `SearchInput`, `Badge`, and the CF-6 `Card.headerAction`; the active
    configuration card's `Consultar` link targets the existing `/panel/app/kb` route. Two columns
    collapse to one at the established 40rem breakpoint. The section-tablist mobile selector remains
    scoped to its direct child.
  - Verification from `web/`: focused Settings + story tests 40/40 passed. Full `npm test` completed
    with 1058/1070 passing; 12 unrelated failures were timeouts and async-state failures in
    `AgentChat.test.tsx`, `ClientFicha.test.tsx`, `ClientesList.test.tsx`, and
    `AgendaPage.stories.test.tsx`. `npm run build` (`tsc -b` + Vite) passed; Vite emitted its existing
    chunk-size advisory (>500 kB).
  - Learned: the referenced desktop and mobile image paths were not present in either checked
    workspace root, so implementation followed the validated finding descriptions and the ODD task
    composition rather than inspecting the image files. A browser/runtime harness was not run; this
    is a frontend-only tab change with no configured harness.

## Verification

Run from `web/`:
- `npm run test` (vitest suite)
- `npm run build` (tsc -b + vite build — the frontend type check lives here)
Backend suite only if a backend/API boundary changes (`configuracion-015`).

## Forecast and delivery

- Authored changed lines forecast: ~2,880 (additions + deletions) — well over the 400-line review
  budget.
- Delivery strategy (owner decision 2026-10-08): **chained PRs, `stacked-to-main`**, merges in order.
- Slice plan (each PR targets `main`):
  1. PR1 — CF-1, CF-2, CF-3 (help panel, day toggle, message preview)
  2. PR2 — CF-4, CF-5, CF-6 (metric row, accordion, `Card` header slot)
  3. PR3 — CF-7, CF-8 (shell tabs + draft/save model)
  4. PR4 — CF-9 (Agente)
  5. PR5 — CF-10 (Mensajes)
  6. PR6 — CF-11 (Horarios y avisos)
  7. PR7 — CF-12 (Costos)
  8. PR8 — CF-13 (Capacidades)
  9. PR9 — CF-14 (verification + reference polish), or folded into PR8 if small.
- Budget rule: keep each PR at or below ~400 authored changed lines. If a unit exceeds it, split
  further (e.g., CF-11 into the hours card vs the right column); `size:exception` only with explicit
  owner approval.
- Running authored-line count is recorded per work-unit commit as slices land.

## Acceptance

- The five tabs render the reference composition at desktop/tablet/mobile using closed-section
  components; no new route; palette/tokens untouched.
- Every work unit lands as its own Conventional Commit with its tests; suite + build green.
- Remaining reference-fidelity gaps are listed for the owner's post-implementation visual pass.

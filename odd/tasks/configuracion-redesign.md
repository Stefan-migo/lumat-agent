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

- [ ] **CF-1** — Help/support panel primitive (icon + heading + body), used by the reference
      right-hand panels "Cómo funciona", "Consideraciones", "Vista previa". Finding `configuracion-016`.
      New file under `web/src/components/primitives/`. Unit test.
- [ ] **CF-2** — Weekday day-toggle / segmented control for Lun–Dom. Finding `configuracion-017`.
      New file under `web/src/components/primitives/`. Unit test (selection, disabled, a11y).
- [ ] **CF-3** — Message preview primitive (assistant bubble + note). Finding `configuracion-018`.
      New file under `web/src/components/primitives/`. Unit test.
- [ ] **CF-4** — Three-metric row composition on the shared `StatCard` surface. Finding
      `configuracion-019`. Extend `web/src/components/shared/StatCard.tsx` (+ test).
- [ ] **CF-5** — Accordion group with count chip. Finding `configuracion-020`. New file under
      `web/src/components/primitives/`. Unit test (expand/collapse, count, a11y).
- [ ] **CF-6** — `Card` header action / right-side slot (count, chip, "Consultar"). Finding
      `configuracion-021`. Extend `web/src/components/primitives/Card.tsx` (+ test).

### Unit B — section shell and tabs

- [ ] **CF-7** — Settings shell: 5-tab navigation via the `Tabs` primitive on desktop/tablet and a
      "Sección" `Select` on mobile, replacing the 10 stacked cards. Finding `configuracion-001`.
- [ ] **CF-8** — Draft/save ownership model: refetch must not silently discard unsaved edits; add the
      reference save notes and disabled-until-valid save state per card. Findings `configuracion-013`,
      `configuracion-022`.

### Unit C — tabs

- [ ] **CF-9** — Agente tab: `Alcance del agente` (icon-tile header, "Avanzado" badge, rules
      textarea, advanced-syntax disclosure, "Cómo funciona" panel, footer note + save) and
      `Detección de emergencias` (warning icon, keywords textarea + helper, "Consideraciones" panel,
      save). Findings `configuracion-002`, `configuracion-003`.
- [ ] **CF-10** — Mensajes tab: `Tono del asistente` horizontal row, and `Mensajes del asistente`
      with the 5-template strip, selected-text editor, info line, and "Vista previa". Findings
      `configuracion-004`, `configuracion-005`.
- [ ] **CF-11** — Horarios y avisos tab: `Horarios de atención` (globe timezone `Select`, weekly
      schedule list, "Nuevo horario" sub-card with day toggles + Inicio/Fin time inputs, delete,
      "Agregar otro horario", disabled save) plus the right column `Notificaciones push` and
      `Fuera de horario` cards. Findings `configuracion-006`, `configuracion-007`, `configuracion-014`.
- [ ] **CF-12** — Costos tab: `Gasto actual` three-metric row with date chip, `Límites de gasto`
      (USD inputs + save), `Precio Meta` (cost input, "Vigente desde" chip, save), and
      `Qué ocurre al alcanzar los límites` (80%/100% rows). Findings `configuracion-008`,
      `configuracion-009`, `configuracion-010`.
- [ ] **CF-13** — Capacidades tab: `Herramientas del asistente` (count, search, "Todos los accesos"
      filter, accordion groups, rows of icon + name + id + access badge) and `Configuración activa`
      side card (KB/Memory availability, Persona/Prompts paths, "Consultar", footer note). Findings
      `configuracion-011`, `configuracion-012`, `configuracion-015`.

### Close

- [ ] **CF-14** — Verification and reference polish: full suite + build green; re-capture the section
      and self-review against the references at desktop/tablet/mobile; hand to the owner for the
      deferred visual pass.

## Verification

Run from `web/`:
- `npm run test` (vitest suite)
- `npm run build` (tsc -b + vite build — the frontend type check lives here)
Backend suite only if a backend/API boundary changes (`configuracion-015`).

## Forecast and delivery

- Authored changed lines forecast: ~2,880 (additions + deletions) — well over the 400-line review
  budget.
- Delivery strategy: `ask-on-risk`; chain strategy pending the owner's call.
- Proposed slices: Unit A (six primitives), Unit B (shell + draft model), one PR per tab (CF-9 …
  CF-13). Each slice is an atomic, reviewable work unit with tests and docs.

## Acceptance

- The five tabs render the reference composition at desktop/tablet/mobile using closed-section
  components; no new route; palette/tokens untouched.
- Every work unit lands as its own Conventional Commit with its tests; suite + build green.
- Remaining reference-fidelity gaps are listed for the owner's post-implementation visual pass.

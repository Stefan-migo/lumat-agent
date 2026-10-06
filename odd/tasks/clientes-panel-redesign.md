# clientes-panel-redesign

## Objective

Bring the `clientes` panel section to the confirmed references (`refs/Diseño Lumat/Clientes/` and
`refs/Diseño Lumat/mobileTablet/Clientes/`): the list, the client ficha, and the section's dialogs.

## Problem

The section predates the v2 reference pass. A validated read-only analysis produced 32 findings
(`odd/analysis/clientes/findings.md`): 2 blocker, 28 major, 2 minor; all `local`. The list lacks
tabs, consent filter, `Creado` sort, selection/bulk, pagination, and the export dropdown. The ficha
lacks its identity header and the Resumen/Casos/Visitas/Conversaciones tabs.

## Why

The owner confirmed the references as the expected-state authority and skipped the owner visual pass
for this section (recorded in `odd/analysis/clientes/visual.md`). Implementation is reference-driven;
the owner corrects the design visually per work unit.

## Scope

- In: `web/src/components/pages/ClientesList.tsx`, `web/src/components/pages/ClientFicha.tsx`, their
  tests/stories, the clientes-specific list params in `app/services/customers.py` and
  `app/panel/api/routes/clients.py`, and the frontend request type in `web/src/types.ts`.
- Out: shared primitives (`Dialog`, `Input` already expose the needed props), `DataTable` contract,
  `tokens.css` palette, and other sections.

## Constraints

- No new shared primitive is required (findings 020/022 are local wiring).
- Do not reopen palette/tokens (`panel-design-system-final` settled them).
- Do not change the shared `DataTable` contract; selection/pagination are page-composable.
- Chat in Rioplatense Spanish; artifacts, code, comments, and commits in English; UI copy in neutral
  Chilean Spanish. Conventional Commits, no AI attribution.
- Reference-driven: the reference images control geometry and layout; the owner corrects visually.

## Work units (stable IDs)

### CL-1 — Backend customer list params
- [x] Extend `search_customers` (`app/services/customers.py:604`) with a consent filter and a sort
      parameter; keep the current default (newest-first) and the existing `q`/`include_archived`.
- [x] Wire the params through the clientes list route (`app/panel/api/routes/clients.py`).
- [x] API tests: consent filter, sort, and unchanged default ordering.
- Findings: `clientes-003`, `clientes-004`.

### CL-2a — Clientes list surface (first pass)
- [x] Reference title composition: count badge/accent bar + subtitle (`clientes-001`).
- [x] Todos/Agendados/Finalizados tabs with per-state counts (`clientes-002`).
- [x] Consent filter control wired to the CL-1 param (`clientes-003`).
- [x] `Creado ↓` sort control wired to the CL-1 param (`clientes-004`).
- [x] Row selection + "Seleccionar todos" + bulk affordance (`clientes-005`).
- [x] "Mostrando N de N clientes" caption + pagination (`clientes-006`).
- [x] "Exportar" dropdown in place of the two CSV links (`clientes-007`).
- [x] Dedicated Teléfono column (`clientes-008`).
- [x] Consent check/minus icon treatment (`clientes-009`).
- [x] ~~Row chevron `>` ficha affordance~~ — **REVERSED by the owner (2026-10-05): remove the row chevron.**

### CL-2a-r1 — list reference-fidelity refinement (owner visual review 2026-10-05)
Owner verdict: the first pass is still far from the reference. Concrete corrections:
- [x] Move "Exportar" + "Nuevo cliente" to the page header (top-right); remove them from the table toolbar.
- [x] Wrap the search toolbar + table + footer in one card.
- [x] Toolbar composition: search input ("Buscar por nombre o teléfono...") + "Consentimiento" dropdown + "Mostrar archivados" toggle switch.
- [x] Column order: Cliente | Registro | Teléfono | Estado | Consentimiento | Creado ↓ (actions last).
- [x] Remove the row chevron `>` (owner reversal of `clientes-010`).
- [x] Style the client-name link (no browser underline; plain name per the reference).
- [x] Date format "20 sep 2026" (day month year).
- [x] Match the estado/consent badges and the pagination active-page button to the reference.
- [x] CL-2a-r2 polish: reuse shared Tabs/list patterns, make archived toggle readable, remove the dead bulk-action label, and reset pagination on search.

### CL-2b — Clientes list dialogs
- [x] Dialog headers: pass existing `Dialog` `icon`/`description` (`clientes-020`, list call sites).
- [x] New-client form: icon header + description, "Datos de contacto" (Teléfono * + Nombre),
      Correo, "Ubicación" (Comuna + Dirección), "* Campo obligatorio", Cancelar/Crear cliente
      (`clientes-021`, `clientes-022`).
- [x] Change-state dialog: client/current-state row, three radio cards, summary (`clientes-023`).
- [x] Archive confirmation label/danger tone and client information block on the list entry point (`clientes-032`, list side).
- [x] Owner decision: **Transiciones válidas** — change-state radio cards contain only the customer's CR-3 `allowed_transitions`; terminal states show no state cards or save action.
- [x] Owner decision: **Solo archivados** — enabling "Mostrar archivados" filters the list to archived clients only; disabling it shows active clients only.
- [x] Owner decision: **Reinicio de ciclo por re-contacto** — inbound WhatsApp from a `finalizado`, `postventa`, or `cancelado` customer resets only the customer state to `nuevo` and audits `customer.cycle_restarted`; manual CR-3 transitions remain unchanged, and conversation/case history is preserved.
- [x] Owner corrections (2026-10-06): state-option cards inherit the official UI font; list tabs show Todos plus all eight customer states in canonical order with client-side counts and filtering.

### CL-2a-mobile
- [x] R3-001: reset pagination and selection when the archived filter changes (`ae0459d5`).
- [x] Shared button primitive inherits the UI font (`b7a7f2d1`).
- [x] Render paginated cliente cards on mobile, preserving selection and row actions; retain the horizontally scrollable nine-tab strip (`f19a051d`).

### CL-3 — Client ficha shell
- [ ] Identity header: avatar, name, "Cliente desde [date]", Agendar visita/Ver conversación
      (`clientes-011`, blocker).
- [ ] Resumen/Casos/Visitas/Conversaciones tabs replacing the single `Historial` disclosure
      (`clientes-012`, blocker).
- [ ] Active-case card + "Editar caso" action (`clientes-013`).
- [ ] "Memoria del cliente" card heading/count + "Ver todo →" (`clientes-014`).
- [ ] Notes card + "+ Agregar nota" entry point (`clientes-015`).
- [ ] "Próximas visitas" card + "Ver agenda →" (`clientes-016`).
- [ ] "Datos del cliente" card + Editar action/contact facts (`clientes-017`).
- [ ] Equipment card + empty state (`clientes-018`).
- [ ] "Historial del cliente" summary card (`clientes-019`).

### CL-4 — Client ficha dialogs
- [ ] Edit-data dialog: title/fields/order/editability (`clientes-024`).
- [ ] Change-consent confirmation dialog (`clientes-025`).
- [ ] Archive dialog: "Información del cliente" grouping + warning (`clientes-026`).
- [ ] Edit-case dialog: context + "Guardar cambios" (`clientes-027`).
- [ ] Define-amount dialog: context + CLP presentation (`clientes-028`).
- [ ] Add-equipment dialog: fields + "Agregar equipo" (`clientes-029`).
- [ ] Add-note dialog: context + "Guardar nota" (`clientes-030`).
- [ ] Merge dialog: two-client comparison + responsive single column (`clientes-031`).
- [ ] Dialog headers `icon`/`description` at ficha call sites (`clientes-020`, ficha side).
- [ ] Archive confirmation label/danger tone on the ficha entry point (`clientes-032`, ficha side).

## Acceptance criteria

- Each work unit's findings are visually matched to their reference image and region.
- No regression in existing clientes behavior (create, edit, consent, archive, merge, case, notes,
  equipment) or in other sections rendering through shared primitives.
- Frontend checks green: `cd web && npm run test`, `npx tsc -b --noEmit`, `npm run build`.
- Backend checks green for CL-1: the project's pytest suite for the clientes list route.

## Checks

- `cd web && npm run test`
- `cd web && npx tsc -b --noEmit`
- `cd web && npm run build` (typecheck lives only in build)
- Backend: pytest for `app/services/customers.py` / clients route.

## Graph nodes consulted (Step 1)

- Query `clientes list customers`: `ClientesList()`, `ClientesList.tsx`, `ClientFicha.tsx` community,
  `shared/DataTable.tsx`, `primitives/Dialog.tsx`, `primitives/Input.tsx`, `primitives/Badge.tsx`,
  `primitives/Avatar.tsx`, `shared/PageFrame.tsx`, `shared/StateMessage.tsx`, `shared/toneMaps.ts`,
  `api.ts`, `types.ts`, `useAsyncData.ts`, `panelRoutes.ts`.
- Community hubs (GRAPH_REPORT): `ClientFicha.tsx`, `api.ts`, `shared/toneMaps.ts`, `clients.py`,
  `serializers.py`, `Customer`.
- Graph refreshed to commit `072660fb` (this branch base).

## Evidence

- Findings ledger: `odd/analysis/clientes/findings.md` (32 rows, validator PASS).
- Visual record: `odd/analysis/clientes/visual.md` (lifecycle `validated`).
- Current captures: `refs/current/clientes/` (30 shots, `app_commit=83ed3e91`).
- Base: `odd/panel-analysis-v2-records` (commit `072660fb`).

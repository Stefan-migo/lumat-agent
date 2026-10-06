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
- [x] Owner decision (reversed 2026-10-06): **Mostrar archivados es aditivo** — enabling the toggle includes active and archived clients together via `include_archived`; disabling it shows active clients only (`20fcd369`). This replaces the earlier **Solo archivados** behavior.
- [x] Owner decision: **Reinicio de ciclo por re-contacto** — inbound WhatsApp from a `finalizado`, `postventa`, or `cancelado` customer resets only the customer state to `nuevo` and audits `customer.cycle_restarted`; manual CR-3 transitions remain unchanged, and conversation/case history is preserved.
- [x] Owner corrections (2026-10-06): state-option cards inherit the official UI font; list tabs show Todos plus all eight customer states in canonical order with client-side counts and filtering.

### CL-2a-mobile
- [x] R3-001: reset pagination and selection when the archived filter changes (`ae0459d5`).
- [x] Shared button primitive inherits the UI font and uses the tokenized semibold control-label weight (`b7a7f2d1`, `acc74c34`).
- [x] Render paginated cliente cards on mobile, preserving selection and row actions; retain the horizontally scrollable nine-tab strip (`f19a051d`).
- [x] Constrain mobile card/table descendants to the viewport, move selection and actions into the identity row, and compact the detail grid (`bc9c6216`).
- [x] Restore the clientes caption and pagination controls in the mobile footer without changing Usuarios (`862ee7ec`).
- [x] Add selected-client bulk archive/restore, including mixed-selection subsets and partial-failure recovery (`0d06865a`).
- [x] Rename the archive-status column to "Archivo", move it last, and show "Disponible" / "Archivado" badges in desktop and mobile (`f06c8105`).

### CL-3 — Client ficha shell
- [x] Identity header: avatar, name, "Cliente desde [date]", Agendar visita/Ver conversación
      (`clientes-011`, blocker; `ebe2edd8`).
- [x] Resumen/Casos/Visitas/Conversaciones tabs replacing the single `Historial` disclosure
      (`clientes-012`, blocker; `ebe2edd8`).
- [x] Active-case card + "Editar caso" action (`clientes-013`; `7e484635`).
- [x] "Memoria del cliente" card heading/count + "Ver todo →" (`clientes-014`; `7e484635`).
- [x] Notes card + "+ Agregar nota" entry point (`clientes-015`; `7e484635`).
- [x] "Próximas visitas" card + "Ver agenda →" (`clientes-016`; `7e484635`).
- [x] "Datos del cliente" card + Editar action/contact facts (`clientes-017`; `7e484635`).
- [x] Equipment card + empty state (`clientes-018`; `7e484635`).
- [x] "Historial del cliente" summary card (`clientes-019`; `7e484635`).

### CL-3-r1 — ficha reference-fidelity (owner visual review 2026-10-06)
Owner verdict: CL-3's first pass is structurally right (title/subtitle/actions/tabs and the Resumen grid), but not reference-faithful. **CONFIRMED scope expansion**: the Casos/Visitas/Conversaciones tab bodies ARE in scope for this unit.

- [x] Avatar: match the reference identity size (large initials circle), not the current small default (`0754a728`).
- [x] Identity subtitle copy: "Cliente desde el 11 sep 2026" (the reference includes "el") (`0754a728`).
- [x] Restyle every Resumen card to `ClientFicha.png` (`0754a728`):
  - [x] Caso activo: green status dot + `CASO ACTIVO` eyebrow + ⋮ menu; case title; Abierto/Prioridad alta badges; summary; divider; Responsable (avatar + name + chevron) and Monto del servicio ("Sin registrar" + "Definir monto" link); **Editar caso** button.
  - [x] Datos del cliente: **Editar** button; Teléfono/Correo/Dirección rows with copy icons; divider; Estado del cliente badge + Consentimiento value.
  - [x] Memoria del cliente: title + count badge + "Ver todo →"; memo row with accent bar, `CONVERSACIÓN #n` eyebrow, status badge.
  - [x] Notas: title + **⊕ Agregar nota**; note row with author avatar, author/date, text, ⋮.
  - [x] Próximas visitas: title + "Ver agenda →"; rows with date tile (28 SEP), service, clock + time, status badge.
  - [x] Equipos: title + **＋ Agregar equipo**; illustrated empty state + centered "Agregar equipo" button.
  - [x] Historial del cliente: compact row card (clock icon + title + subtitle + chevron).
- [x] Rebuild the **Casos / Visitas / Conversaciones** tab bodies to the desktop references and mobile/tablet variants (`ed641d05`).
- [x] Owner decision (2026-10-06): the "Historial del cliente" card opens a **combined history panel/dialog** (casos anteriores + visitas + conversaciones), not a tab jump. Mensajes stays in the Conversaciones tab (`68dff135`).

### CL-3-r2 — Resumen tab layout + reference fidelity (owner visual review 2026-10-06 #2)
Owner verdict: the Resumen cards still do not match `ClientFicha.png`, and the owner asked for a **deliberate layout deviation**. Scope: the Resumen tab only (the Casos/Visitas/Conversaciones tab bodies stay as they are for now).

- [x] **Swap the primary column** (owner decision — conscious deviation from the reference, which shows the case large): `Datos del cliente` becomes the large/primary card (left); `Caso activo` becomes the smaller secondary card (right) (`ee306798`).
- [x] Card style to the reference: card header with the large title and its action aligned **right** (`Editar` pill, `Ver todo →`, `⊕ Agregar nota`, `+ Agregar equipo`, `Ver agenda →`); use pill/outlined buttons and underlined links instead of full-width secondary buttons (`Definir monto` = underlined link; `Editar caso` = right-aligned pill) (`ee306798`).
- [x] `Datos del cliente`: `Editar` pill + `...` menu in the header; Teléfono/Correo/Dirección rows with copy icons; Estado del cliente badge; Consentimiento value. **No inline state editor**. Cambiar estado / Cambiar consentimiento / Fusionar / Archivar remain in the `...` menu and open their dialogs (`ee306798`).
- [x] `Memoria del cliente`, `Notas`, `Próximas visitas`, `Equipos`, `Historial del cliente` restyled to the reference (header-action placement, date tiles, illustrated empty state, pill buttons/link rows) (`ee306798`).

### CL-4 — Client ficha dialogs
Reference pattern (clientes-020 already notes `Dialog` exposes `icon`/`description`; `Input` exposes `icon`/`helper`): header = icon tile + title + supporting subtitle; a client-context row (avatar + name + "Cliente desde [date]"); fields with leading icons; footer = `Cancelar` (outlined) + the action (filled; danger for archive/merge). References: `ClientFichaDialogs.png`, `ClientFichaDialogs2.png`, `ClientFichaCustomerMerge.png` + mobile equivalents.
- [x] Change-state dialog (ficha): client/current-state row, allowed-transition radio cards, "Cambio de estado" summary (`ClientFichaDialogs.png`). Replaces the inline state select (`da5bcf33`).
- [x] Edit-data dialog: title/fields/order/editability (`clientes-024`; `8bde2851`). Phone remains read-only because the profile API does not support changing it.
- [x] Change-consent confirmation dialog (`clientes-025`; `da5bcf33`).
- [x] Archive dialog: "Información del cliente" grouping + warning (`clientes-026`; `2a06a356`).
- [x] Edit-case dialog: context + "Guardar cambios" (`clientes-027`; `8bde2851`).
- [x] Define-amount dialog: context + CLP presentation (`clientes-028`; `8bde2851`).
- [x] Add-equipment dialog: fields + "Agregar equipo" (`clientes-029`; `c01ee56e`).
- [x] Add-note dialog: context + "Guardar nota" (`clientes-030`; `c01ee56e`).
- [x] Merge dialog: two-client comparison + responsive single column (`clientes-031`; `2a06a356`).
- [x] Dialog headers `icon`/`description` at ficha call sites (`clientes-020`, ficha side; `ee306798`).
- [x] Archive confirmation label/danger tone on the ficha entry point (`clientes-032`, ficha side; `2a06a356`).

### CL-3-r3 / CL-4-r1 — owner visual review 2026-10-06 #3 (Resumen cards + dialogs)
- [x] `Datos del cliente`: move `Editar` into the `...` menu (no standalone Editar pill); add an **icon to every `...` item**; remove the **copy-button borders** (`cdea3671`).
- [x] `Caso activo`: move `Editar caso` + `Definir monto` into the `...` menu (no visible buttons); add an icon to every `...` item; **remove the `⌄` arrow** next to the responsible name; proper small-card adaptation (`cdea3671`).
- [x] Dialog **Editar datos del cliente**: more width; lighter field borders scoped to the ficha dialogs (`daca9d9e`).
- [x] Dialog **Cambiar estado del cliente**: FIX — allowed transition radio cards now render; terminal states retain no cards or save action (`daca9d9e`).
- [x] Dialog **Cambiar consentimiento**: Sí/No are selectable radio cards with visible selection; save persists through `updateCustomerConsent` (`daca9d9e`).
- [x] Dialog **Editar caso**: increase internal spacing and padding; apply ficha-scoped lighter borders to the dialog and controls; retain case context and the Cancelar/Guardar cambios footer (`ec79e4ab`).
- [x] Dialog **Definir monto del caso**: increase padding and spacing and apply ficha-scoped lighter borders; retain case context/current amount, CLP field presentation, helper, and Cancelar/Guardar monto footer (`ec79e4ab`).
- [ ] Cards **Memoria / Notas / Próximas visitas**: fix the broken vertical spacing.
- [ ] Cards **Equipos / Historial del cliente**: design details per the reference.

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
- CL-3 query `ClientFicha ficha cliente tabs cards`: `ClientFicha()`, `ClientFicha.tsx`, `Tabs()`/`Tabs.tsx`,
  `ClientFicha.test.tsx`, `stories/pages/ClientFicha.stories.tsx`, `Avatar()`, `Badge()`, `DataTable()`.
- Path `ClientFicha.tsx` ↔ `Tabs.tsx` (undirected): `ClientFicha.tsx <--imports_from-- AppShell.tsx
  --imports_from--> PanelShell.tsx --imports_from--> Tabs.tsx`; directed query returned no path.
- CL-3-r1 query `ClientFicha summary cards client identity notes equipment visits cases conversations`:
  `ClientFicha()`, `ClientFicha.tsx`, `ClientMemories.tsx`, `Tabs.tsx`, `ClientFicha.test.tsx`,
  `ClientFicha.stories.test.tsx`, `Card()`, `Dialog()`, `DataTable()`.
- CL-3-r1 path `ClientFicha.tsx` ↔ `ClientMemories.tsx`: direct extracted edge
  `ClientFicha.tsx --imports_from--> ClientMemories.tsx` (one hop).
- Graph `graph.json` current at commit `7e484635` (HEAD at CL-3-r1 start); `GRAPH_REPORT.md` header remains at `2cea04a7` because incremental refresh regenerates the report only at session close. No graph rebuild was needed.
- CL-4 dialog graph query `ClientFicha archive merge dialog`: `ClientFicha()`, `ClientFicha.tsx`, `Dialog()`, `ClientesList.tsx`, `ClientFicha.test.tsx`, `ClientFicha.stories.tsx`, `archiveCustomer()`, `mergeClient()`, `previewClientMerge()`, `fetchClients()`, and the related API operations. Path `ClientFicha.tsx` → `Dialog()` is a direct `imports` edge; no directed path exists between `ClientFicha.tsx` and `ClientesList.tsx`. `GRAPH_REPORT.md` identifies `ClientFicha.tsx` as a community hub; its header lags the current graph by design.
- CL-3-r3 query `ClientFicha dialogs estado consentimiento editar datos`: `ClientFicha()`, `ClientFicha.tsx`, `ClientFicha.test.tsx`, `ClientesList.tsx`, `Dialog()`, `Button.tsx`, `api.ts`, `updateCustomerConsent()`, `updateCustomerProfile()`, `changeClientState()`, and `Customer`. Path `ClientFicha.tsx` → `ClientesList.tsx` has no directed path. `ClientFicha.tsx` uses customer `allowed_transitions`; the ficha serializer (`to_customer_dict`) provides this same field as the list endpoint. Radio-role attributes were previously dropped by `Button`, preventing the CSS `radiogroup` selectors from styling either dialog's controls.
- CL-3-r3 card-menu query `ClientFicha Datos del cliente Caso activo menu`: `ClientFicha()`, `Menu()`, `ClientFicha.tsx`, `Menu.tsx`, `ClientesList.tsx`, `ClientFicha.test.tsx`, `ClientesList.test.tsx`, and `clientes-panel-redesign Task`; path `ClientFicha()` → `Menu()` has no directed path. The graph already exposes optional Lucide icons per `MenuItem`; no primitive change was required. `GRAPH_REPORT.md`'s header still lags the current graph as expected.

## Evidence

- Findings ledger: `odd/analysis/clientes/findings.md` (32 rows, validator PASS).
- Visual record: `odd/analysis/clientes/visual.md` (lifecycle `validated`).
- Current captures: `refs/current/clientes/` (30 shots, `app_commit=83ed3e91`).
- Base: `odd/panel-analysis-v2-records` (commit `072660fb`).

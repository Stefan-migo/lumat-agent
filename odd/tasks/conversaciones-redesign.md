# conversaciones-redesign

## Objective

Bring the panel **Conversaciones** section to the confirmed references:

- Desktop list → a real **table** matching the table pattern already shipped for clientes
  (`ClientesList`) and usuarios (`UserManagement`), i.e. the shared `DataTable` + `.table-card`
  composition.
- Conversation **thread** → design/UX improvement to `ConversationThread.png` (desktop) and
  `MobileTabletConversationThread.png` (mobile/tablet).

## Problem

`ConversationsList.tsx` still renders a legacy `<ul className="conversations-queue">` of row cards,
not the reference table. `ConversationThread.tsx` has a generic header (no customer identity, no
"Ver ficha del cliente" action) and a flat context inspector, instead of the reference's card
layout (Cliente / Caso vinculado / Datos capturados).

Validated read-only analysis already exists: `odd/analysis/conversaciones/findings.md` and
`odd/analysis/conversaciones/visual.md`. Owner visual input (2026-10-07) confirms: the desktop list
must be a table reusing the clientes/usuarios table style; the thread needs its design/UI/UX
improved to the reference.

## Why

The section predates the v2 reference pass. The references are the expected-state authority; the
owner corrects the design visually per work unit (same workflow that closed clientes).

## Scope

- **In:** `web/src/components/pages/ConversationsList.tsx`, `web/src/components/pages/ConversationThread.tsx`,
  their CSS/tests/stories, and the conversaciones-specific CSS patterns. Shared `DataTable` is
  **reused as-is**; only the page-local CSS and the shared-primitive CSS additions the findings flag
  (mobile filters, tablet workspace) are in scope.
- **Out:** `DataTable` contract, `tokens.css` palette, backend routes/services, other sections.

## Constraints

- Linear top-to-bottom, identical spacing and radius to the shipped clientes table.
- Do not reopen palette/tokens (`panel-design-system-final` settled them).
- Do not change the shared `DataTable` contract.
- Chat in Rioplatense Spanish; artifacts, code, comments, and commits in English; UI copy in
  neutral Chilean Spanish. Conventional Commits, no AI attribution.
- Reference-driven: reference images control geometry and layout.

## TDD resolution

No `strict_tdd` config exists in the repo (checked `sdd-init` memory, `.rapsodia-code/`, `odd/`,
`AGENTS.md`). Effective mode: **not enabled** → ordinary functional checks per slice (component
tests written/updated + typecheck), not no checks. Runner: `npx vitest run`.

## Delivery strategy

- Forecast: ~900–1300 authored changed lines across two components + tests/stories. **Exceeds the
  ~400-line budget** → chained/stacked PRs.
- `delivery_strategy`: `ask-on-risk` (owner already chose chained PRs; recorded here).
- `chain_strategy`: `stacked-to-main` (handoff-confirmed; each slice PR targets `main` in order).
- Slice boundaries below; each slice is one work unit with its own commit and verification.

## Work units (stable IDs)

### CV-1 — ConversationsList desktop table
- [x] Title composition: count badge + subtitle "Revisa y gestiona la atención de tus clientes."
- [x] Tab labels/counts to the reference (`Atención humana`, `Con caso`); keep client-side filtering and existing ordering.
- [x] Wrap search toolbar + table + footer in one `.table-card`, reusing `DataTable`.
- [x] Five columns: `Cliente y conversación` | `Estado y prioridad` | `Caso` | `Última actividad` | `Acciones`.
- [x] Row: avatar + name + phone + `#id` + summary; distinct status and priority badges; case cell; recency; `Tomar conversación` + `...` overflow action.
- [x] Responsable filter control in the toolbar.
- [x] Footer: "Mostrando N de M conversaciones" + pagination.
- [x] Retain mobile card list (`.table-cards--mobile`) with unique test IDs.
- [x] Preserve behavior: ordering, search, tabs, actions (`takeConversation`, `acknowledgeCase`), realtime/recovery.
- [x] Update `ConversationsList.test.tsx` + stories/tests.
- [x] CV-1 evidence: commit `8f844391`; `npx tsc -b --force --noEmit` clean; `vitest` 40/40 (ConversationsList, stories, ConversationThread); RDD assess `medium` / `under_budget` (236 lines).
- Graph nodes: `ConversationsList()`, `DataTable()`, `ClientesList.tsx`, `UserManagement.tsx`, `takeConversation()`, `acknowledgeCase()`; `path ConversationsList→DataTable` has no directed edge (both page-level).
- Owner-confirmable: the priority label mapping (`alta`→"Prioridad alta"/warning, `media`→"Prioridad normal", `baja`→"Prioridad baja") is inferred — the reference only shows normal/alta.

### CV-1-r1 — owner visual review 2026-10-07
Owner verdict: title/subtitle/badge and tabs OK; table needs design detail work.
- [x] R1 Responsable filter: bordered control with leading person icon + muted `Responsable:` prefix + bold value + chevron (option label `Todas`→`Todos`).
- [x] R2 Client name no longer renders browser button chrome; reads as plain bold text (desktop + mobile), hover affordance kept.
- [x] R3 Última actividad: stacked `23 sep 2026` (date) + `16:20` (muted 24h time) instead of `dateStyle: short`.
- [x] R4 Acciones: `UserRoundPlus` icon on `Tomar conversación`; actions right-aligned; `...` trigger styled as a bordered rounded square.
- [x] R5 `...` dropdown: `MessageSquare` icon on `Abrir conversación`.
- [x] Evidence: commit `ebd7cc20`; `tsc -b --force --noEmit` clean; `vitest` 17/17 (ConversationsList + stories).

### CV-1-r2 — owner visual review 2026-10-07 #2
- [x] Offline banner restyled to the reference: neutral surface, `WifiOff` icon, bold headline "Sin conexión en tiempo real." + muted "Los datos guardados siguen disponibles." (page-local `.conversations-list__offline`; shared `.realtime-status` untouched).
- [x] Responsable filter: replaced the native `<select>` (OS-styled popup) with a page-local Radix dropdown — styled panel, radio items with a check indicator, keyboard a11y. New test covers open + select + request.
- [x] Mobile cards redistributed: identity head (avatar + name + meta), summary, badges + facts row (caso ↔ actividad), right-aligned actions.
- [x] Evidence: commit `8572326b`; `tsc -b --force --noEmit` clean; `vitest` 18/18.

### CV-1-r3 — owner visual review 2026-10-07 #3
- [x] Mobile row menu no longer sits flush against the viewport edge: measured with Playwright, the panel's right edge moved from 390px (flush) to 348px. Added optional `align`/`collisionPadding` props to the shared `Menu` primitive (additive, defaults unchanged) and used `align="end" collisionPadding={8}`.
- [x] Responsable filter shrunk to its content (332px → 224px): `justify-self: end` on desktop, `start` when the toolbar stacks, and the chevron pinned right (`margin-left: auto`).
- [x] Evidence: commit `46046a06`; `tsc -b --force --noEmit` clean; `vitest` 18/18; Playwright measurement `docScrollWidth 390 = docClientWidth 390` (no horizontal overflow).

### CV-2 — ConversationThread header + history card
- [ ] Header: avatar + customer name + `Conversación #id · Iniciada el [date]` + state badge + `Ver ficha del cliente` action.
- [ ] Offline banner copy to the reference.
- [ ] `Historial de mensajes` card heading + freshness (`Actualizada el [date] · [time]`) + `Tomar conversación` + `...` menu.
- [ ] Message bubbles to the reference (author, time, media/failure details).
- [ ] Update `ConversationThread.test.tsx` + stories/tests.

### CV-3 — ConversationThread context inspector + responsive
- [ ] `Cliente` card: avatar, name, phone + copy action.
- [ ] `Caso vinculado` card: title, `Abierto`/`Prioridad alta` badges, summary, `Ver caso →`, Emergencia/Reconocimiento rows.
- [ ] `Datos capturados` disclosure (reference shows it open by default).
- [ ] Tablet/mobile workspace layout per `MobileTabletConversationThread.png` (shared-primitive CSS scope; regression check on clientes/usuarios).
- [ ] Update thread tests/stories.

### CV-4 — ConversationThread composer + states + a11y
- [ ] 24h-window warning banner + disabled composer to the reference.
- [ ] Closed-conversation presentation (`Conversación cerrada`, "Respuesta no disponible").
- [ ] Human-attention handoff presentation and state actions.
- [ ] Accessibility pass (labels, disabled semantics, focus) + final behavior coverage.

## Authorized scope

Work **only** in `/home/stefan/repos/lumat-agent-odd-conversaciones-redesign` on branch
`odd/conversaciones-redesign`. Do not modify the main worktree or another worktree.

## Acceptance criteria

- Each work unit visually matches its reference image and region.
- No regression in existing conversaciones behavior (ordering, search, tabs, pagination, actions,
  realtime recovery, 24h window, closed state) or in other sections through shared primitives.
- Frontend checks green per slice; full suite + build at the design checkpoint.

## Checks

- `cd web && npx tsc -b --force --noEmit` (incremental lies — always `--force`)
- `cd web && npx vitest run --no-file-parallelism --testTimeout=20000 <component test>`
- Design checkpoint: `npx vitest run --no-file-parallelism --testTimeout=20000` + `npm run build`

## Graph nodes consulted (Step 1)

- Query `ConversationsList ConversationThread panel conversations list usages`: `ConversationsList()`
  and `ConversationThread()` (`web/src/components/pages/`), community `ConversationThread.tsx`;
  `ConversationsList.stories.tsx`, `ConversationThread.stories.tsx`, both component tests,
  `listConversations()`, `getConversation()`, `listActiveConversations()`, `coalesceSnapshotRefresh()`,
  `conversationLabel()`, `types.ts`.
- `graphify path "ConversationsList" "ConversationThread"`: ambiguous match; no directed path
  (not evidence of disconnection — both are page components under the same shell).
- `GRAPH_REPORT.md` hubs: `ConversationThread.tsx`, `api.ts`, `types.ts`, `shared/toneMaps.ts`;
  god nodes `Conversation` (134 edges), `Message` (124), `Case` (123); `DataTable` + the
  "Clientes Pilot Dense Surface" community owns the table pattern.

## Evidence

- Findings ledger: `odd/analysis/conversaciones/findings.md` (validated).
- Visual record: `odd/analysis/conversaciones/visual.md`.
- Current captures: `refs/current/conversaciones/` (`desktop.png`, `tablet.png`, `mobile.png`).
- Reused table pattern: `web/src/components/shared/DataTable.tsx`, `ClientesList.css`,
  `primitives/primitives.css`.
- Base: `main` = `32ebb4b5` (clientes section merged).

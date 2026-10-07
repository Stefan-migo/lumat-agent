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

### CV-1-r4 — close the toolbar gap (owner 2026-10-07 #4)
- [x] The search fills the toolbar so it meets the filter: desktop/tablet grid `minmax(0,1fr) auto auto` (scoped to `min-width: 40rem` so the ≤40rem stacking rule still wins). Measured gap is 12px = the grid gap, not dead space.
- [x] Evidence: commit `71a39676`; `tsc` clean; `vitest` 18/18; Playwright `GAP_PX 12`.
- **CV-1 status: owner-approved and closed** (commits `8f844391`, `ebd7cc20`, `8572326b`, `46046a06`, `71a39676`). 6 changed paths / 236 authored lines at `8f844391`; RDD assess `medium` / `under_budget`.

### CV-2 — ConversationThread header + history card
- [x] Page identity header (reusing the ClientFicha pattern: `PageFrame title=""` + a page-local header): large avatar, name, state badge, `Conversación #id · Iniciada el [date]`, and `Ver ficha del cliente` (rendered only in the interactive view, gated so the read-only view stays button-free).
- [x] Offline banner uses the shared `.conversations-offline` (moved from the list's page CSS into `primitives.css`; list copy "Los datos guardados siguen disponibles." vs thread copy "El histórico guardado sigue disponible.").
- [x] `Historial de mensajes` card header: title + `Actualizada el [date] · [time]` on the left, state controls on the right. The state badge moved to the page header (single `role=status`); the reply-window span now renders only in the read-only view (the composer owns it when interactive).
- [x] Message bubbles: author above the bubble, timestamp below and outside it (`.ai-agent-grammar__bubble-stack`); outbound stack right-aligned.
- [x] Updated `ConversationThread.test.tsx` (scoped the duplicated name assertions), `ConversationThread.stories.test.tsx` (heading is now the customer name), and `AppShell.test.tsx`.
- [x] Evidence: commits `56c69b73` + `68c21e99`; `tsc -b --force --noEmit` clean; full suite **1034/1034**; `npm run build` green.

#### Regression found and fixed while validating CV-2
The CV-1 tab-label change (`Humanas`→`Atención humana`, `Casos`→`Con caso`) and the dual-render table broke 8 `AppShell.test.tsx` specs. Fixed in `56c69b73`. **Lesson: run the FULL frontend suite after a shared-label or dual-render change — the targeted component tests do not catch cross-page specs.**

### CV-2-r1 — owner visual review 2026-10-07 (thread)
- [x] `Ver ficha del cliente` moved onto the same row as `Volver a conversaciones` (new `.conversation-thread__actions-row`, space-between).
- [x] Card header actions collapsed to a visible `Tomar conversación` (with icon) plus a `...` menu holding `Devolver al agente` (`Bot`), `Cerrar conversación` (`CircleCheck`) and `Reconocer emergencia` (`ShieldAlert`), each with an icon.
- [x] Activity chip de-jargoned: `classified`/`intent:<x>` → "Intención detectada: {intent}", `kb_retrieved`/`chunks:<n>` → "Se consultó la base de conocimiento (n resultados)", `escalation` → "Derivado a atención humana" (maps derived from `app/services/realtime.py`).
- [x] Handoff separator restyled as a solid amber rule above/below the text.

### CV-3 — ConversationThread context inspector + responsive
- [x] `Cliente` card: avatar + name + phone + copy action.
- [x] `Caso vinculado` card: title, status/priority badges, summary, `Ver caso →`, Emergencia/Reconocimiento rows.
- [x] `Datos capturados` disclosure stays open by default with dt/dd rows (CSS contract kept: `.ai-agent-grammar__detail`).
- [ ] Tablet/mobile workspace layout per `MobileTabletConversationThread.png` — NOT yet reviewed by the owner.
- [x] Updated thread tests/stories.

### CV-4 — ConversationThread composer + states + a11y
- [x] 24h-window warning banner (clock icon + bold headline + muted note) replacing the old inline hint/reason text.
- [x] Locked composer row: lock glyph, disabled `Respuesta` field with the "Respuesta no disponible" placeholder, disabled send button (`SendHorizonal`), `Conversación cerrada` note.
- [x] Human-attention handoff presentation kept; state actions now live in the `...` menu.
- [x] Accessibility kept: the field keeps its `Respuesta` accessible name and disabled semantics; the warning keeps `role=status` + `aria-label="Fuera de la ventana de 24 horas"`; the send button has `aria-label="Enviar respuesta"`.

### CV-2/3/4 evidence (owner review 2026-10-07)
- Commit `7e4dadd0`; `tsc -b --force --noEmit` clean; full suite **1034/1034**; `npm run build` green.

### CV-2-r2 — owner visual review 2026-10-07 #2 (thread)
- [x] Action row buttons share one height (`.conversation-thread__actions-row .btn { min-height: var(--space-8) }`).
- [x] Bubble avatars enlarged (`calc(var(--space-8) + var(--space-2))`).
- [x] **Bug fixed:** message bubbles ignored `conversation.customer`, so inbound messages and the header fell back to `Cliente #<id>` even though the thread payload carries the customer (the route does `session.get(Customer, conversation.customer_id)`). Bubbles now resolve `conversation.customer?.name` first.
- [x] Composer row realigned: lock centred on the field (`top: 50%` + translate), send button `align-self: center`, field wrapped in `.ai-agent-grammar__composer-field`; the closed/locked state hides the visible label but keeps it accessible and uses `rows=1`.
- [x] Inspector `Cliente`: larger avatar; copy action right-aligned.
- [x] Inspector `Caso vinculado`: breathing room (`gap: var(--space-3)`), larger case title, badges with a top margin, separator line per detail row.
- [x] `Datos capturados`: internal markers filtered (`_`-prefixed keys, e.g. the real `_pending` in conversation #10) and keys humanized (`name`→Nombre, `urgencia_informada`→Urgencia informada, generic fallback capitalizes + de-underscores); separator line per row.
- [x] Evidence: commit `0b64a05c`; `tsc` clean; full suite **1034/1034**; `npm run build` green.

#### Owner decisions (2026-10-07) — all resolved
- **`Ver caso` destination:** owner chose the client ficha Casos tab. Implemented as a `tab` route param: `PanelRoute.clientTab`, `pathForRoute` + `parsePanelPath`, `AppShell` → `ClientFicha.initialTab`. The link now targets `/panel/app/clients/{customer_id}?tab=cases`.
- **Case badge colour:** owner decided the badges stay as they are (design-system `caseStatusTone`); no divergence.
- **Backend follow-up:** owner accepted the frontend filter; the capture pipeline should still stop persisting `_pending` in `captured_data` (not addressed here).

### CV-2-r3 / CV-3-r1 / CV-5 — mobile chat-first thread (owner 2026-10-07)
- [x] Locked-composer breathing room: the field's left padding now clears the lock glyph (`space-3 + icon-md + space-2`).
- [x] `Datos capturados` falls back to the customer profile: `Comuna` / `Dirección` come from the ficha when the capture flow left them unanswered (`CustomerSummary` widened with optional `comuna`/`address`; the API already sends them via `to_customer_dict`).
- [x] Mobile is chat-first: the inline inspector is hidden inside the workspace and the conversation actions collapse into a **`…` menu** that also carries `Tomar conversación`.
- [x] New **`Información del chat`** button opens the inspector (Cliente / Caso vinculado / Datos capturados) in a **bottom sheet**, implemented as an additive `Dialog` `variant="sheet"` (rises from the bottom edge ≤40rem, centred dialog above; reduced-motion respected).
- [x] Verified with Playwright at 390×844: info button visible, inline inspector hidden, sheet `x=0 width=390 y=196 height=647` (bottom-anchored) with full content, `scrollWidth == clientWidth` (no overflow).
- [x] Evidence: commits `fc84bb75` + `64a1063d`; `tsc` clean; full suite **1034/1034**; `npm run build` green.

#### Environment gotcha (recurring, worth remembering)
The Vite dev server **missed a file edit**: it served a stale transform of `Dialog.tsx` (the watcher never logged an HMR update for it), so `variant="sheet"` silently did nothing in the browser while the source was correct. `touch`ing the file re-triggered the watcher and fixed it. When a fresh page load clearly runs old code in this worktree, `touch` the file before debugging the logic.

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

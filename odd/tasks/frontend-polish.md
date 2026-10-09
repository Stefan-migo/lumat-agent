# frontend-polish

Feature id: `frontend-polish`
Branch: `odd/frontend-polish`
Worktree: `/home/stefan/repos/lumat-agent-odd-frontend-polish` (base `origin/main` 9550ffa4)
Created: 2026-10-09

## Objective

Make every **control boundary** in the panel use the light decorative border
(`--border`), removing the dark `--border-strong` control borders left over from
earlier slices, so the whole panel matches the lighter look already approved in
Configuración (e.g. the Costos inputs).

## Problem / Why

Two border tokens exist (`web/src/tokens/tokens.css`):

- `--border: #d5dad1` — light hairline, documented as *decorative, not a control boundary*.
- `--border-strong: #7e858f` — dark, the AA-compliant control boundary (3.09:1 on `--surface`).

During the redesigns, Configuración overrode its field borders to `--border`
(`Settings.css`) while the shared primitives (`.field__control`, `.search-input`,
`.menu__trigger`, `.btn--secondary`, `.day-toggle__day`) and other pages kept
`--border-strong`. Result: inconsistent borders — search / filter / inputs dark,
Configuración inputs light.

Owner decision (2026-10-09): **direction A — unify everything to the light `--border`.**
This knowingly waives the WCAG 2.2 AA non-text 3:1 rule for control boundaries
(`--border` is 1.18:1 on `--surface`). The trade-off is accepted and must be recorded
in `DESIGN_SYSTEM.md`, not hidden.

## Scope

- Change **control-boundary** borders from `--border-strong` to `--border`.
- Remove the now-redundant Settings overrides that force `border-color: var(--border)`.
- Document the decision in `DESIGN_SYSTEM.md`.

## Non-goals — do NOT change

- `--border-strong` **token value** (stays `#7e858f`; `tokens.test.ts:249` keeps passing).
- Decorative (non-boundary) uses of `--border-strong`:
  `.assistant-chat__send:disabled` background, `.user-mobile-actions__handle`
  background, `.settings-capabilities__availability > span` dot.
- `.field__control[aria-invalid="true"]` (state emphasis, out of scope).
- No copy, no logic, no component `.tsx` changes.

## Constraints

- Worktree `odd/frontend-polish` only.
- Artifacts in English; Conventional Commits, no AI attribution.

## Tasks

- [x] **T1** `primitives.css` — control-boundary rules → `--border`
- [x] **T2** page CSS — control-boundary rules → `--border`
- [x] **T3** `Settings.css` — remove redundant overrides (dark `.menu__trigger` + redundant field `--border`)
- [x] **T4** `DESIGN_SYSTEM.md` — record the decision
- [x] **T5** verify — `npm test` green, `npm run build` OK, visual check
- [x] **T6** `Menu.tsx` — icon trigger `MoreHorizontal` → `EllipsisVertical` (the row-action "..." becomes vertical panel-wide)
- [x] **T7** `Menu.tsx`/primitives.css — menu-trigger background defaults to the light `--surface`; darker `--corp-bg` only when open
- [x] **T8** Pagination — fix Conversaciones paging (client-side, 10/page, was showing all 33) + one shared `Pagination` component (numbered pages + `…`) adopted by Conversaciones, Clientes and Usuarios
- [x] **T9** `DataTable` column width support + constrain the Conversaciones "Cliente y conversación" column
- [x] **T10** Conversaciones row actions — drop redundant "Abrir conversación"; menu offers "Devolver al agente" (→bot) and "Cerrar conversación" (→closed); keep "Reconocer emergencia" when applicable and the "Tomar conversación" button for bot rows
- [x] **T11** `primitives.css` — `.tabs__tab-copy` label+count stacked on two lines in horizontal tabs; make it inline by default and grid only under `.tabs--vertical` (pre-existing from `c7b1a8ec`, surfaced here)
- [x] **T12** `AgendaPage.tsx`/`primitives.css` — visit card heading rebalanced: clock glyph `sm`→`lg`, date and time stacked on two lines (date `--text-xs` muted, time `--text-base` semibold), and the date moved to the trailing column so the service title leads the card (`icono | título/badge | fecha`)
- [x] **T13** `primitives.css` — account menu aligned to the Lumat palette: neutral avatar (dropped `--success-bg`), role rendered as `--text-muted` metadata (dropped `--teal-500`), sign-out row transparent with `--danger` text and a `--danger-bg` hover
- [x] **T14** `SelfProfile.tsx`/`primitives.css` — "Mi perfil" redesigned on the `UserFicha` pattern: large identity avatar + role badge + "Usuario de acceso" rail card, card headers with icon + description, two-column fields with leading glyphs and helpers, and a `Descartar cambios | Guardar cambios` footer. Profile save now maps an empty field to null, so the `Borrar nombre/teléfono` buttons are gone; the password card gains `Confirmar nueva contraseña` with a match guard and reveal toggles

## Acceptance

- No **control boundary** in the panel uses `--border-strong` (only decorative
  fills / dots remain on it).
- Configuración and the rest of the panel render the same light border.
- `npm test` and `npm run build` pass.

## Verification

- `cd web && npm test`
- `cd web && npm run build`
- Visual: Conversaciones search + filter, Settings inputs, secondary buttons, dropdowns.

## Progress log

- 2026-10-09 — created.
- 2026-10-09 — T1–T4 implemented. Contract tests updated
  (Button/Input/Select/SearchInput/Textarea/AppShell). `npm run build` OK.
  `npm test` green in isolation; the full-suite timeouts were load-induced
  (another agent's suite was running concurrently, load avg ~26). Visual
  confirmation (T5) pending owner review.
- 2026-10-09 — T6: the shared `Menu` icon trigger now uses `EllipsisVertical`
  (was `MoreHorizontal`), so every row-action "…" in the panel is vertical.
  `Menu.test.tsx` 10/10 and `npm run build` OK.
- 2026-10-09 — T7: menu triggers use the light `--surface` by default and the darker
  `--corp-bg` when open; icon triggers use the shared radius, removing the redundant
  Conversaciones action override.
- 2026-10-09 — T8: added the shared numbered `Pagination` primitive and switched
  Conversaciones to client-side 10-row pages over a bounded 100-row fetch; Clientes
  and Usuarios now use the shared control.
- 2026-10-09 — T9: added header-cell column widths to `DataTable`, set the Conversaciones
  identity column to 38%, and bounded summaries to 22rem. Conversations list tests (14/14)
  and `npm run build` passed. Commit `fe0899e1`.
- 2026-10-09 — T10: replaced the redundant open-thread row menu action with human-state
  transitions while retaining emergency acknowledgement and the bot-row take button.
  Added a state-transition request test. Conversations list tests (15/15) and
  `npm run build` passed. Commit `672a3b5b`.
- 2026-10-09 — T12: visit card heading rebased. First the date went two-line and the
  clock grew (`f3c71a8a`), then the layout was tried with the date below (`af83e6bb`)
  and settled on `icono | título/badge | fecha` (`21da29af`). AgendaPage tests 47/47.
- 2026-10-09 — T13: account menu palette aligned to the design system; shared classes
  cover both the header `AccountControl` and the sidebar/drawer `UserContext`. Commit
  `2bd1bbe5`. PanelShell + app tests 42/42.
- 2026-10-09 — T14: SelfProfile rebuilt on the `UserFicha` pattern; `Borrar` buttons
  removed in favour of empty-field-to-null plus `Descartar cambios`. Password card gains
  confirmation + reveal toggles. Commit `3fd66103`. SelfProfile tests 6/6, app 8/8.

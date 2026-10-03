# ODD task — usuarios detail page + dialogs

## Objective
Match the `usuarios` detail page (`/panel/app/users/:id`, `UserFicha.tsx`) and the create-user /
reset-password dialogs (`UserManagement.tsx`) to the owner-approved references, implementing the
validated findings `usuarios-019..041`.

## Problem
The list pass was redesigned and shipped (PRs #469/#470). The detail page and both dialogs were never
visually matched. The owner ran the image-first analysis (machine v2): capture, owner visual analysis
(the gate), read-only code analysis, and a fresh-context validator that returned `PASS` over rows
`019–041` (2026-10-02). The owner ruled the reference governs geometry/layout; the design system
governs palette.

## Why now
Owner authorized implementation on 2026-10-03 after the validator gate passed.

## Scope
In:
- Shared primitives `Card`, `Dialog`, `Input` (+ private `FieldShell`, `primitives.css`): header icon
  + supporting subtitle; input leading icon, trailing password toggle, helper line.
- `web/src/components/pages/UserFicha.tsx`: two-column detail layout, "Cuenta del usuario" summary
  card, "Datos del usuario" card, footer, "Seguridad de la cuenta" status row.
- `web/src/components/pages/UserManagement.tsx`: create-user and reset-password dialog composition.
- Tests for every touched primitive and page.

Out:
- Backend (`app/…`): the admin serializer already returns the needed fields.
- `web/src/tokens/tokens.css`: palette is settled; no reopen.
- The list pass (already implemented).

## Constraints
- Tokens only. Do NOT touch `tokens.css`. No white element backgrounds (design-system surfaces).
- Preserve behavior contracts: role options stay `Operador` / `Técnico` / `Administrador`; the
  username stays immutable; forms keep their validation and API calls.
- Tests and docs stay with the behavior in the same commit.

## Authorized scope
- Worktree: `/home/stefan/repos/lumat-agent-odd-usuarios-detail-dialogs`
- Branch: `odd/usuarios-detail-dialogs`
- No push, PR, or merge without explicit owner approval.

## Checks (run in the worktree, from `web/`)
- `npm run test`
- `npx tsc -b --noEmit`
- `npm run build`

## TDD mode
Standard mode (no strict-TDD config found in the project). Tests are required alongside each
behavior; the full suite must be green before each work-unit commit. Runner: `cd web && npm run test`.

## Graph nodes consulted (graphify)
`UserFicha()` (UserFicha.tsx:16), `UserManagement.tsx`, `Card()` (Card.tsx:10), `Dialog()`
(Dialog.tsx:16), `Input()` (Input.tsx:16), `PageFrame()` (PageFrame.tsx:14), `FieldShell`,
`Select()`. Consumed by `AgendaPage.tsx`, `ClientFicha.tsx`, `Dashboard.tsx` — confirms the header /
input changes are `shared-primitive` and high-impact.

## Work units
### WU1 — shared-primitive roll-up (findings 019, 020, 021, 022, 023, 040, 041)
- `Card`: optional leading `icon` (lucide) + `description` (subtitle) in the header.
- `Dialog`: optional leading `icon` + `description` in the header.
- `Input`: optional leading `icon`, `revealable` (password show/hide toggle), `helper` line.
- `FieldShell`: render the helper line (no error) — private helper.
- `primitives.css`: icon tile, header subtitle, input adornments, helper.
- Update `Card.test.tsx`, `Dialog.test.tsx`, `Input.test.tsx`.

### WU2 — detail page (findings 024–030)
- `UserFicha.tsx`: header title/subtitle, back button with chevron, two-column layout, "Cuenta del
  usuario" card, "Datos del usuario" card (icon + subtitle + two-up form grid), footer with
  "Descartar cambios" / "Guardar cambios", "Seguridad de la cuenta" status row.
- Update `UserFicha.test.tsx`.

### WU3 — dialogs (findings 031–039)
- `UserManagement.tsx`: create dialog (icon + subtitle, "Datos de acceso" / "Permisos" sections,
  username label/placeholder, confirm-password field, role label + shield icon, footer
  "Cancelar"/"Crear usuario"); reset dialog ("Usuario de acceso" card, "Generar contraseña", footer
  "Cancelar"/"Restablecer contraseña").
- Update `UserManagement.test.tsx`.

## Delivery
- Forecast: ~550–650 authored changed lines → over the 400-line review budget.
- Planned slices: PR1 = WU1 (upstream primitives); PR2 = WU2 + WU3 (usuarios local UI).
- Chain strategy: pending owner decision (default `ask-on-risk`); decide before the first commit
  beyond the budget / before any PR.
- Local work-unit commits are allowed on the branch without a chain decision.

## Acceptance criteria
- [ ] WU1 primitives support icon/subtitle/toggle/helper with tests green.
- [ ] WU2 detail matches the reference structure at desktop/tablet/mobile.
- [ ] WU3 dialogs match the reference structure.
- [ ] `npm run test`, `npx tsc -b --noEmit`, `npm run build` all green.
- [ ] Findings `usuarios-019..041` implemented.

## Progress
- [ ] WU1 — shared-primitive roll-up
- [ ] WU2 — detail page
- [ ] WU3 — dialogs

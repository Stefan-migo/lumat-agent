# Section visual analysis — clientes

Lifecycle: `captured → owner-review → owner-done → code-analysis → validated → implementing → done`

Status: `captured → owner-skipped → code-analysis → validated` (2026-10-05). Validator PASS over 32 findings rows on 2026-10-05.
Owner decision (2026-10-05): skip the owner visual pass for this section; the code analysis is
reference-driven, and the owner will correct the design visually during implementation.
Reference set confirmed by the owner on 2026-10-05: everything under
`refs/Diseño Lumat/Clientes/` and `refs/Diseño Lumat/mobileTablet/Clientes/`.

## Sources

Current images (`refs/current/clientes/`), 10 screens × desktop/tablet/mobile:
- List (`/panel/app/clients`): `desktop.png`, `tablet.png`, `mobile.png`
- Client ficha Resumen (`/panel/app/clients/<id>`): `detail.*.png`
- New-client dialog: `new-client-dialog.*.png`
- Change-state dialog (list row action): `change-state-dialog.*.png`
- Archive dialog (list row action): `archive-dialog.*.png`
- Edit-data dialog (ficha, "Editar identidad"): `edit-data-dialog.*.png`
- Ficha archive dialog (ficha actions menu): `ficha-archive-dialog.*.png`
- Merge dialog (ficha actions menu): `merge-dialog.*.png`
- Equipment dialog (ficha, "Agregar equipo"): `equipment-dialog.*.png`
- Case-amount dialog (ficha, "Editar monto del caso"): `amount-dialog.*.png`

Capture tooling note: `web/scripts/capture-section.mjs` now captures the client ficha and its dialogs as
extra screens for `clientes` (same mechanism as `agenda`/`usuarios`), added in this pass. `ClientesList`
does not use the `.table-card` wrapper (that is Usuarios); its row actions live under `.table__actions`.
Captures ran against `CAPTURE_URL=http://127.0.0.1:5173` (vite must be started with `--host 127.0.0.1`;
the default IPv6-only bind does not answer on `127.0.0.1`).

Reference images (confirmed 2026-10-05):

Desktop — `refs/Diseño Lumat/Clientes/`:
- List: `Clients.png`
- Ficha Resumen: `ClientFicha.png`
- Ficha Casos: `ClientFichaTabCases.png`
- Ficha Visitas: `ClientFichaTabVisits.png`
- Ficha Conversaciones: `ClientFichaTabConversaciones.png`
- New-client dialog: `NewClientDialog.png`
- Change-state dialog: `ClientStatusDialog.png`
- Dialog board (Edit data · Change status · Change consent · Archive): `ClientFichaDialogs.png`
- Dialog board (Edit case · Define case amount · Add equipment · Add note): `ClientFichaDialogs2.png`
- Merge dialog: `ClientFichaCustomerMerge.png`

Mobile + tablet — `refs/Diseño Lumat/mobileTablet/Clientes/`:
- List: `LUMAT clients list_ mobile and tablet.png`
- Ficha Resumen: `LUMAT responsive client profile-2.png`
- Ficha Casos: `LUMAT client cases on mobile and tablet-3.png`
- Ficha Visitas: `LUMAT client visits across mobile and tablet-4.png`
- Ficha Conversaciones: `LUMAT client conversations on mobile and tablet-5.png`
- Edit data + Change status dialogs: `LUMAT client data and status dialogs-6.png`
- Change consent + Archive dialogs: `LUMAT consent and archive dialogs-7.png`
- Edit case + Define case amount dialogs: `LUMAT case and amount dialogsburugburu-8.png`
- Add equipment + Add note dialogs: `LUMAT team and note dialog board-9.png`
- Merge modal: `LUMAT client merge modal, mobile and tablet-10.png`
- Change-state modal: `LUMAT responsive client status modal-11.png`
- New-client form: `LUMAT new client form_ mobile and tablet-12.png`
- Merge modal (mobile single column): `Single-column mobile fusion dialog redesign-13.png`
- Profile + conversation board: `Marcela Fuentes Profile and Conversation Board-14.png`
- New-client bottom sheet (mobile): `Mobile Client Form Bottom Sheet-15.png`

App commit: `83ed3e912ff3aedf0e6b7d2b2ec40e4ca91b4cb5`
Capture date: `2026-10-05`

## Coverage gaps

Reference screens with no current capture, because the app has no such screen/control today.
These are structural findings for phase 3, not missing captures:
- Ficha tabs (Casos / Visitas / Conversaciones): the app renders one "Historial" block, not tabs.
- Change-consent dialog: the app toggles consent directly from the ficha actions menu (no dialog).
- Edit-case dialog: the app edits the case inline (`CaseActions` selects + "Actualizar"), no dialog.
- Add-note dialog: the app adds a note inline (Card + textarea + "Agregar nota"), no dialog.

## Owner analysis

SKIPPED (owner decision, 2026-10-05): the owner did not fill the blocks below. The reference images
are the source of truth for expected/actual, and the owner will correct visually during implementation.
The blocks stay as a placeholder for that later pass.

### clients list — desktop|tablet|mobile

screen: clients list
breakpoints: desktop, tablet, mobile
expected:
actual:
severity:

### client ficha · Resumen — desktop|tablet|mobile

screen: client ficha (Resumen)
breakpoints: desktop, tablet, mobile
expected:
actual:
severity:

### client ficha · Casos — desktop|tablet|mobile

screen: client ficha (Casos tab)
breakpoints: desktop, tablet, mobile
expected:
actual:
severity:

### client ficha · Visitas — desktop|tablet|mobile

screen: client ficha (Visitas tab)
breakpoints: desktop, tablet, mobile
expected:
actual:
severity:

### client ficha · Conversaciones — desktop|tablet|mobile

screen: client ficha (Conversaciones tab)
breakpoints: desktop, tablet, mobile
expected:
actual:
severity:

### new-client dialog — desktop|tablet|mobile

screen: new-client dialog
breakpoints: desktop, tablet, mobile
expected:
actual:
severity:

### change-state dialog — desktop|tablet|mobile

screen: change-state dialog
breakpoints: desktop, tablet, mobile
expected:
actual:
severity:

### edit-data dialog — desktop|tablet|mobile

screen: edit-data dialog
breakpoints: desktop, tablet, mobile
expected:
actual:
severity:

### change-consent dialog — desktop|tablet|mobile

screen: change-consent dialog
breakpoints: desktop, tablet, mobile
expected:
actual:
severity:

### archive dialog — desktop|tablet|mobile

screen: archive dialog
breakpoints: desktop, tablet, mobile
expected:
actual:
severity:

### edit-case dialog — desktop|tablet|mobile

screen: edit-case dialog
breakpoints: desktop, tablet, mobile
expected:
actual:
severity:

### define-case-amount dialog — desktop|tablet|mobile

screen: define-case-amount dialog
breakpoints: desktop, tablet, mobile
expected:
actual:
severity:

### add-equipment dialog — desktop|tablet|mobile

screen: add-equipment dialog
breakpoints: desktop, tablet, mobile
expected:
actual:
severity:

### add-note dialog — desktop|tablet|mobile

screen: add-note dialog
breakpoints: desktop, tablet, mobile
expected:
actual:
severity:

### merge dialog — desktop|tablet|mobile

screen: merge dialog
breakpoints: desktop, tablet, mobile
expected:
actual:
severity:

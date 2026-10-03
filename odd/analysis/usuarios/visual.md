# Section visual analysis — usuarios

Lifecycle: `captured → owner-review → owner-done → code-analysis → validated → implementing → done`

Status: `validated` (detail-page + dialogs pass; the list pass is implemented). Validator PASS over findings rows 019–041 on 2026-10-02.

## Sources

Current images (`refs/current/usuarios/`):
- List (`/panel/app/users`): `desktop.png`, `tablet.png`, `mobile.png`
- User detail (`/panel/app/users/<id>`): `detail.desktop.png`, `detail.tablet.png`, `detail.mobile.png`
- New-user dialog (list + "Nuevo usuario"): `new-user-dialog.desktop.png`, `new-user-dialog.tablet.png`, `new-user-dialog.mobile.png`
- Reset-password dialog (row actions + "Restablecer contraseña"): `reset-password-dialog.desktop.png`, `reset-password-dialog.tablet.png`, `reset-password-dialog.mobile.png`

Capture tooling note: `web/scripts/capture-section.mjs` now captures the user detail and both
dialogs as extra screens for `usuarios` (same mechanism already used by `agenda`), added in this pass.
The list images were re-captured at the current commit; the shell-collapse fix changed the framing,
not the list UI (PR #471 touched only the capture script).

Reference images:
- List, desktop: `refs/Diseño Lumat/Users/Usuarios.png`
- List, tablet: `refs/Diseño Lumat/mobileTablet/Users/LUMATtabletUsers.png`
- List, mobile: `refs/Diseño Lumat/mobileTablet/Users/LUMATMobileUsers.png`
- Detail, desktop: `refs/Diseño Lumat/Users/LumatUsersdetailpage.png`
- Detail, tablet: `refs/Diseño Lumat/mobileTablet/Users/TabletUserPage.png`
- Detail, mobile: `refs/Diseño Lumat/mobileTablet/Users/MobileUserPage.png`
- New-user dialog, desktop: `refs/Diseño Lumat/Users/LUMATNewUserDialog.png`
- New-user dialog, tablet + mobile: `refs/Diseño Lumat/mobileTablet/Users/new user mobile and tablet.png`
- Reset-password dialog, desktop + tablet + mobile: `refs/Diseño Lumat/Users/Responsive password reset board.png`

App commit: `dffe7d66c0b041e2a1528dc87eac9a6849bc69b9`
Capture date: `2026-10-02`

## Owner analysis

Source: owner analysis delivered in chat on 2026-10-02 and transcribed verbatim below.
Severity values marked `(agent)` were inferred because the owner did not state one; owner may correct.

Owner decision (chat, 2026-10-02): "creo que deber se inmutable el username. la lista y ficha deben mostrar el name."

### Users list — desktop

screen: users list
breakpoint: desktop
expected: the reference governs the whole screen. Polished table styling per the reference. "Nuevo usuario" opens a dialog — the create-user form must leave the main page. `username` is immutable (login identity); the list and the ficha must display the profile `name`, falling back to `username`.
actual: stylistically very basic versus the reference. The create-user form is still inline on the main page. The table is not redesigned to the reference's table style. The list and the ficha display the login `username`, so editing "Nombre" to `Stefan` still shows `admin`.
severity: blocker (agent — the stale-name behavior is a functional error; the missing redesign is major)

### Users list — tablet

screen: users list
breakpoint: tablet
expected: redesign everything based on the reference, similar to desktop. The header must show the breadcrumb — its absence makes the header look incomplete.
actual: the tablet header shows no breadcrumb, so it looks like something is missing. Layout otherwise to be brought in line with the reference.
severity: major (agent)

### Users list — mobile

screen: users list
breakpoint: mobile
expected: the reference design absolutely governs this breakpoint. The LUMAT logo in the mobile header must be smaller and centered.
actual: completely broken. The logo in the mobile header is too large and not centered.
severity: blocker (agent — broken layout; the logo issue alone is minor)

### Global — all breakpoints

screen: all
breakpoint: desktop|tablet|mobile
expected: where a reference disagrees on palette, the design system wins — use the nearest color the reference shows. No white background for elements (respect the design system surfaces).
actual: current build shows white element backgrounds that the design system does not sanction.
severity: minor (agent) — potential `token-palette` escalation; do not reopen tokens without owner decision.

## Owner analysis — detail page + dialogs (second pass, 2026-10-02)

Source: owner visual analysis delivered in chat on 2026-10-02, transcribed below. The owner also supplied
the missing dialog references (reset-password board and the mobile/tablet new-user dialog), now recorded
under `## Sources`.

Owner's words (verbatim, Spanish):
"Analisis UserDetailPage: desktop: Mayormente la referencia tiene razon / Titulo/subtitulo -> referencia /
boton volver a usuarios -> referencia / Layout -> referencia. / tarjetas Cuenta de usuario -> referencia. /
tarjeta datos del usuario -> referencia / botones descartar y guardar cambis -> referencia / tarjeta
informativa -> referencia. Mobiel/Table: [same list]. Analisis New user dialog: Desktop: Estado actual
minimo / Mayormente la referencia tiene razon / Titulo/subtitulo -> referencia con icono user / boton cerrar
-> referencia / Layout -> referencia. / Formulario -> referencia. / dropdown permisos -> referencia /
botones cancelar y guardar -> referencia. Mobile/Tablet: [same]. Analisis DialogResetPassword: Desktop:
Estado actual minimo / Mayormente la referencia tiene razon / Titulo/subtitulo -> referencia con icono keys /
boton cerrar -> referencia / Layout -> referencia. / Formulario -> referencia. / boton generar contraseña ->
referencia / botones cancelar y reestablecer contraseña -> referencia. Mobile/Tablet: [same]. Incluye en la
evaluacion de ambos el diseño del dialog. para el dialog la referencia tiene la razon. las referencias pueden
discrepar en paleta de colores, pero siempre se respeta en cuanto a la paleta de colores el system design y
se utiliza el color mas cercano al que muestra la referencia. no color blanco como background de elementos."

Severity values marked `(agent)` were inferred because the owner did not state one; owner may correct.
Every element is redirected to the reference ("-> referencia"): the owner rules the reference governs
geometry, layout and composition; the design system governs palette.

### User detail — desktop

screen: user detail
breakpoint: desktop
expected: the reference governs. Title/subtitle, the "volver a usuarios" button, layout, the "Cuenta de usuario" card, the "Datos del usuario" card, the "Descartar"/"Guardar cambios" buttons, and the informational card all follow the reference.
actual: the current ficha is minimal versus the reference; the owner ruled the reference governs every element above.
severity: major (agent)

### User detail — tablet + mobile

screen: user detail
breakpoint: tablet|mobile
expected: same as desktop — the reference governs the title/subtitle, the back button, layout, the "Cuenta de usuario" and "Datos del usuario" cards, the "Descartar"/"Guardar cambios" buttons, and the informational card.
actual: same as desktop; the owner ruled the reference governs every element above.
severity: major (agent)

### New-user dialog — desktop

screen: new-user dialog
breakpoint: desktop
expected: the reference governs the dialog design. Title/subtitle with a user icon, close button, layout, form, permissions dropdown, and the "Cancelar"/"Guardar" buttons follow the reference.
actual: the current state is minimal; the owner ruled the reference governs the dialog.
severity: major (agent)

### New-user dialog — tablet + mobile

screen: new-user dialog
breakpoint: tablet|mobile
expected: the reference governs the same elements as desktop; keep the design system's air and spacing at these breakpoints.
actual: the current state is minimal.
severity: major (agent)

### Reset-password dialog — desktop

screen: reset-password dialog
breakpoint: desktop
expected: the reference governs the dialog design. Title/subtitle with a keys icon, close button, layout, form, the "Generar contraseña" button, and the "Cancelar"/"Restablecer contraseña" buttons follow the reference.
actual: the current state is minimal; the owner ruled the reference governs the dialog.
severity: major (agent)

### Reset-password dialog — tablet + mobile

screen: reset-password dialog
breakpoint: tablet|mobile
expected: the reference governs the same elements as desktop; keep the design system's air and spacing at these breakpoints.
actual: the current state is minimal.
severity: major (agent)

### Global — detail page and dialogs

screen: user detail + both dialogs
breakpoint: desktop|tablet|mobile
expected: where a reference disagrees on palette, the design system wins — use the nearest color the reference shows. No white background for elements (respect the design system surfaces).
actual: to be confirmed in code analysis.
severity: minor (agent) — potential `token-palette` escalation; do not reopen tokens without owner decision.

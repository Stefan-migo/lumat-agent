# Section visual analysis — usuarios

Lifecycle: `captured → owner-review → owner-done → code-analysis → validated → implementing → done`

## Sources

Current images:
- `refs/current/usuarios/desktop.png`
- `refs/current/usuarios/tablet.png`
- `refs/current/usuarios/mobile.png`

Reference images:
- `refs/Diseño Lumat/Users/Usuarios.png`
- `refs/Diseño Lumat/mobileTablet/Users/LUMATtabletUsers.png`
- `refs/Diseño Lumat/mobileTablet/Users/LUMATMobileUsers.png`

App commit: `31291cfc908e55793e75ed32f8410129dd444bcd`
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

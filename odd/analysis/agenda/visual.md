# Section visual analysis — agenda

Lifecycle: `captured → owner-review → owner-done → code-analysis → validated → implementing → done`

## Sources

Current images (`refs/current/agenda/`):
- List (`/panel/app/agenda`): `desktop.png`, `tablet.png`, `mobile.png`
- Visit detail (`/panel/app/agenda/<id>`): `visit-detail.desktop.png`, `visit-detail.tablet.png`, `visit-detail.mobile.png`
- New-visit dialog (agenda list + "Nueva visita"): `new-visit-dialog.desktop.png`, `new-visit-dialog.tablet.png`, `new-visit-dialog.mobile.png`

Capture tooling note: the previous capture hid `#panel-shell-sidebar` with `display:none`, which
removed the occupant of the shell's rail grid track. At tablet and desktop the shell lays out as
`grid-template-columns: <rail> minmax(0,1fr)`, so the content area auto-placed into the rail column:
the tablet shot collapsed into a ~64 px sliver and the desktop shot kept a 240 px empty gutter
(owner-reported defect, agent-verified against `configuracion` and `usuarios` at older commits).
`web/scripts/capture-section.mjs` now collapses the shell to one column when it hides the chrome, and
captures the visit detail and the new-visit dialog as extra screens. All images above are post-fix.

Reference images:
- List, desktop: `refs/Diseño Lumat/Agenda/Agenda.png`
- Visit detail, desktop: `refs/Diseño Lumat/Agenda/agendaVisita.png`
- New-visit dialog, desktop: `refs/Diseño Lumat/Agenda/DialogStyle.png`
- List, mobile + tablet: `refs/Diseño Lumat/mobileTablet/Agenda/AgendaMobileTablet.png`
- New-visit dialog, mobile + tablet: `refs/Diseño Lumat/mobileTablet/Agenda/MobileTabletNewVisitDialog.png`
- Visit detail, mobile + tablet: `refs/Diseño Lumat/mobileTablet/Agenda/MobileTabletyVisitDetail.png`

App commit: `5fcf26e001c174cfbdc0fb8fbe9ab26e22a154ec`
Capture date: `2026-10-02`

## Owner analysis

Source: owner visual analysis delivered in chat on 2026-10-02, transcribed and structured below.
Owner's words (verbatim, Spanish): "Mayormente la referencia tiene razón"; "Referencia tiene razón en
todo. a ratos siento que la referencia está muy comprimida. esto por que está hecha con IA
generativa. por tanto no puede crear scroll. nuestro diseño tiene que seguir el system design con el
aire y espacio establecidos para mobile y tablet. así el diseño respira y no se ve tan comprimido
como en la referencia."; "para el dialog la referencia tiene la razón."; "las referencias pueden
discrepar en paleta de colores, pero siempre se respeta en cuanto a la paleta de colores el system
design y se utiliza el color más cercano al que muestra la referencia."; "no color blanco como
background de elementos."

Severity values marked `(agent)` were inferred because the owner did not state one; owner may correct.

### Agenda list — desktop

screen: agenda list
breakpoint: desktop
expected: the reference governs. Title/subtitle per the reference. Tabs "Activas / No activas" per the reference. "Nueva visita" button per the reference. Calendar style per the reference. Visit cards per the reference.
actual: current desktop deviates from the reference on header (missing subtitle/visit badge and the `+` icon), calendar controls (four loose buttons instead of the reference's segmented Mes/Semana + arrows), the right panel (two "Hoy"/"Próximas" tables instead of the reference's day-detail card), and the visit cards. Desktop capture has a capture defect but most of the design is visible.
severity: major (agent)

### Agenda list — tablet

screen: agenda list
breakpoint: tablet
expected: the reference governs everything. Because the reference is AI-generated and compressed, our build must follow the design system's established air and spacing for tablet so the design breathes, instead of copying the reference's density.
actual: not assessable — the tablet capture is a tooling artifact (content collapsed to a left sliver). Owner still rules the reference governs this breakpoint.
severity: major (agent)

### Agenda list — mobile

screen: agenda list
breakpoint: mobile
expected: the reference governs everything, but adapted: follow the design system's air and spacing for mobile so the design breathes instead of the reference's compressed density.
actual: current mobile falls back to the same non-reference structure as desktop (loose calendar buttons, "Hoy"/"Próximas" tables) and overflows horizontally, clipping the Técnico value and the Acciones column.
severity: major (agent)

### New-visit dialog — desktop

screen: new-visit dialog
breakpoint: desktop
expected: the reference governs (owner: "para el dialog la referencia tiene la razón").
actual: not captured by current tooling; owner did not flag a specific deviation beyond "reference governs".
severity: major (agent)

### New-visit dialog — tablet

screen: new-visit dialog
breakpoint: tablet
expected: the reference governs the contents; follow the design system's air and spacing for tablet so the dialog breathes rather than matching the reference's compressed density.
actual: not captured by current tooling.
severity: major (agent)

### New-visit dialog — mobile

screen: new-visit dialog
breakpoint: mobile
expected: the reference governs the contents; follow the design system's air and spacing for mobile so the full-screen dialog breathes rather than matching the reference's compressed density.
actual: not captured by current tooling.
severity: major (agent)

### Visit detail — desktop

screen: visit detail
breakpoint: desktop
expected: the reference governs. Title/subtitle per the reference. Status badge per the reference. "Reprogramar" / "Cerrar visita" buttons per the reference. Cards and information per the reference.
actual: not captured by current tooling; owner ruled the reference governs.
severity: major (agent)

### Visit detail — tablet

screen: visit detail
breakpoint: tablet
expected: the reference governs everything; follow the design system's air and spacing for tablet so the design breathes instead of the reference's compressed density.
actual: not captured by current tooling.
severity: major (agent)

### Visit detail — mobile

screen: visit detail
breakpoint: mobile
expected: the reference governs everything; follow the design system's air and spacing for mobile so the design breathes instead of the reference's compressed density.
actual: not captured by current tooling.
severity: major (agent)

### Global — all screens, all breakpoints

screen: all
breakpoint: desktop|tablet|mobile
expected: where a reference disagrees on palette, the design system wins — use the nearest color the reference shows. No white background for elements (respect the design system surfaces).
actual: to be confirmed in code analysis; consistent with the usuarios finding of unsanctioned white element backgrounds.
severity: minor (agent) — potential `token-palette` escalation; do not reopen tokens without owner decision.

## Open questions (not findings)

- Multiple active visits (owner): the reference shows only one active visit, and it is large. How do we
  present more than one visit in that surface without breaking the design? Needs an owner/product
  decision before implementation; do not invent a design in this pass.

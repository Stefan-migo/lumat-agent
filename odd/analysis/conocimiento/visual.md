# Section visual analysis — conocimiento

Lifecycle: `captured → owner-review → owner-done → code-analysis → validated → implementing → done`

Status: `implementing` (2026-10-05)

## Sources

Current images (`refs/current/conocimiento/`):
- Landing / documents list (`/panel/app/kb`): `desktop.png`, `tablet.png`, `mobile.png`
- Document detail (`/panel/app/kb/1`): `document-detail.desktop.png`, `document-detail.tablet.png`, `document-detail.mobile.png`

Reference images:
- Landing, desktop: `refs/Diseño Lumat/BaseDeConocimineto/BaseDeConocimiento.png`
- Landing, mobile + tablet:
  `refs/Diseño Lumat/mobileTablet/BaseDeConocimineto/MobileTabletBaseDeConocimiento.png`
  (composite: mobile list, mobile add sheet, tablet)
- Document detail, desktop: `refs/Diseño Lumat/BaseDeConocimineto/Kbpage.png`
- Document detail, mobile + tablet:
  `refs/Diseño Lumat/mobileTablet/BaseDeConocimineto/MobileTabletKbPage.png`
  (composite: mobile resumen, tablet resumen)

Note: `refs/Diseño Lumat/mobileTablet/BaseDeConocimineto/BaseDeConocimiento.png` and `Kbpage.png` are stale
byte-identical duplicates of the two desktop files (md5 verified); the `MobileTablet*` composites are the
real mobile/tablet references.

Capture tooling note: the previous tool did not cover this section's document detail. The `document-detail`
screen (opens the first `a.table__link`, i.e. `/panel/app/kb/1`) was added to `web/scripts/capture-section.mjs`,
same pattern as `agenda`'s `visit-detail` and `usuarios`'s `detail`.

App commit: `42c8c5aee5d295d487ba270d3a08792f4a00b603`
Capture date: `2026-10-02`

Note: re-captured after `main` advanced from `dffe7d66` (PR #472 merge). The KB render is byte-identical
before and after that merge, so the primitive changes it carried did not affect this section.

## Owner analysis

Source: owner visual analysis delivered in chat on 2026-10-02, transcribed and structured below.
Owner's words (verbatim, Spanish): "El diseño actual es muy básico"; "la referencia tiene razón en la
mayoría de las cosas."; "layout -> referencia"; "Titulo/Subtitulo -> referencia"; "Card Documentos ->
referencia"; "Card Probar recuperacion -> referencia"; "Card Agregar documento -> referencia.";
"las referencias pueden discrepar en paleta de colores, pero siempre se respeta en cuanto a la paleta de
colores el system design y se utiliza el color más cercano al que muestra la referencia."; "no color
blanco como background de elementos."

The owner delivered desktop and mobile/tablet together per screen. Severity values marked `(agent)` were
inferred because the owner did not state one; owner may correct.

### Landing — desktop

screen: landing
breakpoint: desktop
expected: the reference governs. Layout (two columns) per the reference. Title/subtitle per the reference. Card Documentos per the reference. Card Probar recuperación per the reference. Card Agregar documento per the reference.
actual: current design is very basic and does not follow the reference.
severity: major (agent)

### Landing — tablet

screen: landing
breakpoint: tablet
expected: the reference governs. Layout (two columns) per the reference. Title/subtitle per the reference. Card Documentos per the reference. Card Probar recuperación per the reference. Card Agregar documento per the reference.
actual: current design is very basic (single flat column) and does not follow the reference.
severity: major (agent)

### Landing — mobile

screen: landing
breakpoint: mobile
expected: the reference governs. Layout per the reference (list + full-width primary "Agregar documento" button; the add form is a bottom sheet; the document renders as a card row). Title/subtitle per the reference. Card Documentos per the reference. Card Probar recuperación per the reference. Card Agregar documento per the reference.
actual: current design is very basic (inline add form, seven-column table that overflows/clips) and does not follow the reference.
severity: major (agent)

### Document detail — desktop

screen: document detail
breakpoint: desktop
expected: the reference governs. Layout per the reference. Title/subtitle/badge per the reference. "Editar contenido" button per the reference. Tabs per the reference. Card Información del documento per the reference. Card Detalles técnicos per the reference. Card Audiencia per the reference.
actual: current design is very basic and does not follow the reference.
severity: major (agent)

### Document detail — tablet

screen: document detail
breakpoint: tablet
expected: the reference governs. Layout per the reference. Title/subtitle/badge per the reference. "Editar contenido" button per the reference. Tabs per the reference. Card Información del documento per the reference. Card Detalles técnicos per the reference. Card Audiencia per the reference.
actual: current design is very basic and does not follow the reference.
severity: major (agent)

### Document detail — mobile

screen: document detail
breakpoint: mobile
expected: the reference governs. Layout per the reference. Title/subtitle/badge per the reference. "Editar contenido" button per the reference. Tabs per the reference. Card Información del documento per the reference. Card Detalles técnicos per the reference. Card Audiencia per the reference.
actual: current design is very basic and does not follow the reference.
severity: major (agent)

### Global — all screens, all breakpoints

screen: all
breakpoint: desktop|tablet|mobile
expected: where a reference disagrees on palette, the design system wins — use the nearest color the reference shows. No white background for elements (respect the design system surfaces).
actual: to be confirmed in code analysis; consistent with the usuarios finding of unsanctioned white element backgrounds.
severity: minor (agent) — potential `token-palette` escalation; do not reopen tokens without owner decision.

## Owner coverage note

`landing`: the owner named the three cards (Documentos, Probar recuperación, Agregar documento) as
reference-governed, plus layout and title/subtitle.

`document detail`: the owner named title/subtitle/badge, the "Editar contenido" button, the tabs, and the
cards Información del documento, Detalles técnicos and Audiencia. The detail reference also shows a
**Versión activa** surface and a **Disponibilidad** card; the owner did not name them, so any finding
touching them carries the literal `owner did not flag` per the evidence bar.

# Section visual analysis — configuracion

Lifecycle: `captured → owner-review → owner-done → code-analysis → validated → implementing → done`

Status: `captured → owner-deferred → code-analysis` (2026-10-08). The owner reviewed the captures and
deferred the detailed visual pass to post-implementation iterations (same pattern as `clientes`), with
an explicit redesign directive recorded below.

## Sources

Current images — full page (`refs/current/configuracion/`):
- `desktop.png` (1280×4262)
- `tablet.png` (768×4334)
- `mobile.png` (390×5341)

Current images — per-section crops, desktop only (`refs/current/configuracion/sections/`):
1. `01-alcance-del-agente.desktop.png`
2. `02-deteccion-de-emergencias.desktop.png`
3. `03-tono.desktop.png`
4. `04-mensajes.desktop.png`
5. `05-horarios-de-atencion.desktop.png`
6. `06-limites-de-gasto.desktop.png`
7. `07-precio-meta.desktop.png`
8. `08-gasto-actual.desktop.png`
9. `09-notificaciones-push.desktop.png`
10. `10-capacidades-del-asistente.desktop.png`

Reference images — desktop (`refs/Diseño Lumat/Configuracion/`):
- Agente: `config1.png`
- Mensajes: `config2.png`
- Horarios y avisos: `config3.png`
- Costos: `config4.png`
- Capacidades: `config5.png`

Reference images — tablet/mobile (`refs/Diseño Lumat/mobileTablet/Configuracion/`, owner-supplied
2026-10-08):
- `LUMAT agent settings and emergency alerts-1.png`
- `LUMAT Scheduling and Alerts Settings-2.png`
- `LUMAT messaging configuration responsive board-3.png`
- `LUMAT responsive cost settings dashboard-4.png`
- `LUMAT assistant capabilities configuration board-5.png`
- `LUMAT responsive board with complete mobile layout-6.png`
- `LUMAT responsive hours and notices-7.png`
- `LUMAT responsive cost settings board-8.png`
- `LUMAT Mobile Alerts and Schedules-9.png`

Reference section designs to follow for composition (already-closed sections): the panel section
analysis records under `odd/analysis/` (`clientes`, `conversaciones`, `agenda`, `usuarios`,
`conocimiento`) and their implemented components.

App commit: `1c8f8802e5f574cd4c3437ff76c6ea41ce4abb1b`
Capture date: `2026-10-07`
Capture origin: `http://127.0.0.1:5175/panel/app/` (this worktree's vite; ports 5173/5174 serve other
worktrees).

Capture tooling note: the previous captures (`ffedd99a`, 2026-10-02) were stale and were re-captured
against this worktree on port 5175. `web/scripts/capture-section.mjs` has no `extraScreens` entry for
`configuracion`; there is nothing to navigate because all settings render on one route. The 10 section
crops above came from a one-off clip pass, not from the shared tool. Extending the shared tool for
`configuracion` is still open.

## Coverage gaps

Structural facts for phase 3, not missing captures:

- The app has **no settings tab bar**. All settings render stacked on one route
  (`/panel/app/settings`) as 10 `section.card` blocks. The reference splits the same content across
  5 tabs.
- Reference tab → current section mapping:
  - Agente → 01 `Alcance del agente` + 02 `Detección de emergencias`
  - Mensajes → 03 `Tono` + 04 `Mensajes`
  - Horarios y avisos → 05 `Horarios de atención` + 09 `Notificaciones push`
  - Costos → 06 `Límites de gasto` + 07 `Precio Meta` + 08 `Gasto actual`
  - Capacidades → 10 `Capacidades del asistente` (contains `Herramientas` + `Configuración activa`)
- Reference-only content with no current section: the `Fuera de horario` card, the
  `Qué ocurre al alcanzar los límites` panel, the right-hand help panels (`Cómo funciona`,
  `Consideraciones`, `Vista previa`), and the tab bar itself. `Fuera de horario` exists only as a
  field label inside section 04.
- Tablet/mobile have current captures but no references.

## Owner analysis

DEFERRED to post-implementation iterations (owner decision, 2026-10-08). The owner's detailed
expected/actual/severity pass runs against the implementation, not the pre-change captures. The blocks
below stay as placeholders for that later pass.

Owner directive (2026-10-08), verbatim intent:
- The `configuracion` frontend was never really built. What exists is generic scaffolding kept only to
  exercise the backend ("generico y necesario para testear el backend"), not real design work.
- **Everything must be redesigned**, reusing components from the already-closed sections.
- Follow the design references (desktop `config1..5.png`, tablet/mobile set above).
- Reference the completed sections' designs too when composing the new `configuracion` design.
- Iterations will be driven by the owner's visual analysis after the first implementation.

### Agente — desktop|tablet|mobile

screen: Agente (reference `config1.png`; current sections 01+02)
breakpoint: desktop (reference available)
expected:
actual:
severity:

breakpoint: tablet (no reference)
expected:
actual:
severity:

breakpoint: mobile (no reference)
expected:
actual:
severity:

### Mensajes — desktop|tablet|mobile

screen: Mensajes (reference `config2.png`; current sections 03+04)
breakpoint: desktop (reference available)
expected:
actual:
severity:

breakpoint: tablet (no reference)
expected:
actual:
severity:

breakpoint: mobile (no reference)
expected:
actual:
severity:

### Horarios y avisos — desktop|tablet|mobile

screen: Horarios y avisos (reference `config3.png`; current sections 05+09)
breakpoint: desktop (reference available)
expected:
actual:
severity:

breakpoint: tablet (no reference)
expected:
actual:
severity:

breakpoint: mobile (no reference)
expected:
actual:
severity:

### Costos — desktop|tablet|mobile

screen: Costos (reference `config4.png`; current sections 06+07+08)
breakpoint: desktop (reference available)
expected:
actual:
severity:

breakpoint: tablet (no reference)
expected:
actual:
severity:

breakpoint: mobile (no reference)
expected:
actual:
severity:

### Capacidades — desktop|tablet|mobile

screen: Capacidades (reference `config5.png`; current section 10)
breakpoint: desktop (reference available)
expected:
actual:
severity:

breakpoint: tablet (no reference)
expected:
actual:
severity:

breakpoint: mobile (no reference)
expected:
actual:
severity:

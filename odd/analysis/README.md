# Panel section analysis

Per-section image-first analysis records. Contract: `.opencode/skills/panel-section-analysis/SKILL.md`.
Analyze sections independently; roll up shared-primitive findings into one upstream unit before
implementing any section. The v1 dashboard record predates this flow and has no capture or `visual.md`.

## Section index

| Section | Status | visual.md | findings.md |
| --- | --- | --- | --- |
| `dashboard` | analyzed (predates v2) | — | [findings.md](dashboard/findings.md) |
| `clientes` | validated | [clientes/visual.md](clientes/visual.md) | [clientes/findings.md](clientes/findings.md) |
| `conversaciones` | validated (27) | [conversaciones/visual.md](conversaciones/visual.md) | [conversaciones/findings.md](conversaciones/findings.md) |
| `agenda` | implementing (48) | [agenda/visual.md](agenda/visual.md) | [agenda/findings.md](agenda/findings.md) |
| `usuarios` | done | [visual.md](usuarios/visual.md) | [findings.md](usuarios/findings.md) |
| `conocimiento` | done | [conocimiento/visual.md](conocimiento/visual.md) | [conocimiento/findings.md](conocimiento/findings.md) |
| `configuracion` | validated (22) | [configuracion/visual.md](configuracion/visual.md) | [configuracion/findings.md](configuracion/findings.md) |

## Legend

- **Class** — `local` (only this section's files) · `shared-primitive` (a primitive or shell file
  other sections render through → one upstream unit) · `token-palette` (`tokens.css` → escalate to
  the owner, do not reopen).
- **Severity** — `blocker` · `major` · `minor` · `nit`.
- **Evidence** — every row carries reference evidence, a code anchor, and the owner note (or the
  literal `owner did not flag`).

## Shared-primitive roll-up

Findings that belong to one upstream unit. Implement these **before** per-section work.

| ID | Section | Finding | Shared file |
| --- | --- | --- | --- |
| dashboard-004 | dashboard | "Hoy" ops cards lack the reference footer links | `web/src/components/primitives/primitives.css` |
| dashboard-005 | dashboard | Assistant is a 2×2 tile, not a full-width banner | `web/src/components/primitives/primitives.css` |
| dashboard-007 | dashboard | Desktop renders an "Atajos" heading the reference omits | `web/src/components/primitives/primitives.css` |
| dashboard-008 | dashboard | Shortcut set needs "Configuración" in place of "Casos" | `web/src/components/primitives/primitives.css` |
| dashboard-010 | dashboard | No period selector nor "Desde el …" caption | `web/src/components/primitives/primitives.css` |
| dashboard-012 | dashboard | Motivos render as chips, not rows with a count badge | `web/src/components/primitives/primitives.css` |
| usuarios-016 | usuarios | Tablet header hides the breadcrumb (and back control) | `web/src/components/primitives/primitives.css` |
| usuarios-017 | usuarios | Mobile header logo too large and not centered | `web/src/components/primitives/primitives.css` |
| usuarios-019 | usuarios | Card header lacks the reference icon tile | `web/src/components/primitives/Card.tsx` |
| usuarios-020 | usuarios | Dialog header lacks the reference icon tile (same upstream unit as agenda-018) | `web/src/components/primitives/Dialog.tsx` |
| usuarios-021 | usuarios | Input lacks a leading-icon slot | `web/src/components/primitives/Input.tsx` |
| usuarios-022 | usuarios | Input lacks a trailing toggle (password show/hide) | `web/src/components/primitives/Input.tsx` |
| usuarios-023 | usuarios | Input lacks a helper line | `web/src/components/primitives/Input.tsx` |
| usuarios-040 | usuarios | Card header lacks the reference supporting subtitle | `web/src/components/primitives/Card.tsx` |
| usuarios-041 | usuarios | Dialog header lacks the reference supporting subtitle | `web/src/components/primitives/Dialog.tsx` |
| agenda-004 | agenda | Calendar toolbar: loose buttons instead of a segmented Mes/Semana control | `web/src/components/primitives/primitives.css` |
| agenda-005 | agenda | Calendar lacks the reference legend + period-count footer | `web/src/components/primitives/primitives.css` |
| agenda-018 | agenda | Dialog header lacks the reference icon + supporting sentence | `web/src/components/primitives/primitives.css` |
| agenda-019 | agenda | Create-form layout: flat single column vs the reference's sectioned, multi-column form | `web/src/components/primitives/primitives.css` |
| agenda-023 | agenda | Scheduled-visit title link renders with the browser-default underline | `web/src/components/primitives/primitives.css` |
| agenda-025 | agenda | Mobile calendar needs the reference's round, compact day grid | `web/src/components/primitives/primitives.css` |
| agenda-026 | agenda | Rescheduling dialog off-reference (layout + content) | `web/src/components/primitives/primitives.css` |
| agenda-027 | agenda | Closure dialog off-reference (layout + content) | `web/src/components/primitives/primitives.css` |
| agenda-030 | agenda | Mobile detail header title/subtitle layout is broken | `web/src/components/primitives/primitives.css` |
| agenda-031 | agenda | Programación card must sit left at two-thirds width, like Historial | `web/src/components/primitives/primitives.css` |
| agenda-032 | agenda | History card lacks the separator line beneath its title | `web/src/components/primitives/primitives.css` |
| agenda-034 | agenda | Cliente + Resumen must merge into one elongated card | `web/src/components/primitives/primitives.css` |
| agenda-035 | agenda | Detail client/technician avatars are too small | `web/src/components/primitives/Avatar.tsx` |
| conversaciones-012 | conversaciones | Mobile filter controls stack vertically instead of the reference compact filter card | `web/src/components/primitives/primitives.css` |
| conversaciones-023 | conversaciones | Tablet conversation workspace collapses to one column instead of the reference two-column layout | `web/src/components/primitives/primitives.css` |
| configuracion-016 | configuracion | Reference help/support panels ("Cómo funciona", "Consideraciones", "Vista previa") have no primitive | `web/src/components/primitives/` (new help-panel primitive) |
| configuracion-017 | configuracion | No segmented weekday/day-toggle control | `web/src/components/primitives/` (new day-toggle primitive) |
| configuracion-018 | configuracion | No chat message preview primitive | `web/src/components/primitives/` (new message-preview primitive) |
| configuracion-019 | configuracion | `StatCard` is single-value; the Costos reference needs a three-metric row | `web/src/components/shared/StatCard.tsx` |
| configuracion-020 | configuracion | No accordion group with count chips | `web/src/components/primitives/` (new accordion primitive) |
| configuracion-021 | configuracion | `Card` lacks header action / right-side slot | `web/src/components/primitives/Card.tsx` |

## Token/palette escalations

Findings that touch `tokens.css`. Owner decision required; do not reopen per section.

| ID | Section | Finding | Owner decision |
| --- | --- | --- | --- |
| _(none yet)_ | | | |

The old `odd/analysis/findings-ledger.md` was migrated here and to
[`dashboard/findings.md`](dashboard/findings.md); the deleted source remains in Git history.

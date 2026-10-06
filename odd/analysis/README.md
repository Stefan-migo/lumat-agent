# Panel section analysis

Per-section image-first analysis records. Contract: `.opencode/skills/panel-section-analysis/SKILL.md`.
Analyze sections independently; roll up shared-primitive findings into one upstream unit before
implementing any section. The v1 dashboard record predates this flow and has no capture or `visual.md`.

## Section index

| Section | Status | visual.md | findings.md |
| --- | --- | --- | --- |
| `dashboard` | analyzed (predates v2) | — | [findings.md](dashboard/findings.md) |
| `clientes` | pending | — | — |
| `conversaciones` | pending | — | — |
| `agenda` | validated | [agenda/visual.md](agenda/visual.md) | [agenda/findings.md](agenda/findings.md) |
| `usuarios` | done | [visual.md](usuarios/visual.md) | [findings.md](usuarios/findings.md) |
| `conocimiento` | done | [conocimiento/visual.md](conocimiento/visual.md) | [conocimiento/findings.md](conocimiento/findings.md) |
| `configuracion` | pending | — | — |

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

## Token/palette escalations

Findings that touch `tokens.css`. Owner decision required; do not reopen per section.

| ID | Section | Finding | Owner decision |
| --- | --- | --- | --- |
| _(none yet)_ | | | |

The old `odd/analysis/findings-ledger.md` was migrated here and to
[`dashboard/findings.md`](dashboard/findings.md); the deleted source remains in Git history.

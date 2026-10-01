---
name: panel-section-analysis
description: "Trigger: section analysis, analizar sección, panel findings, reference vs code review, findings ledger. Read-only per-section analysis of the Lumat panel against the design references and the owner's visual analysis, emitting classified findings into one shared ledger so sections stay comparable and deduplicable."
license: MIT
metadata:
  author: Stefan-migo
  version: "1.0"
---

## When to Load

Load for **read-only analysis of one panel section** before any implementation, and for
**validating** that analysis. Never load it to implement, edit, or execute anything.

Why this contract exists: parallel analysis is safe (read-only, no merge collision); serial
implementation is mandatory (sections share `PanelShell.tsx`, `primitives.css`, `tokens.css`,
`AppShell.tsx`, `panelRoutes.ts`). This contract is what makes N parallel analyses comparable
instead of N private opinions.

## Adjudication Rule (fixed — do not re-litigate)

**The archived canonical spec beats the reference image, except where the owner explicitly
rules the reference right.** References control **geometry and layout, not palette**. Palette
and tokens were settled by `panel-design-system-final` and are not reopened per section.

## The Job

Analyze ONE section. Compare three sources on the same axis:

1. the **reference images** (`refs/Diseño Lumat/…`, read from the primary worktree),
2. the **landed code** (the section's components and what they actually render),
3. the **owner's visual analysis** (structured input, below).

Emit findings as rows in the shared ledger. Read-only: no edits, no execution, no code.

## Inputs

- **Section slug** — one of `dashboard`, `clientes`, `conversaciones`, `agenda`, `usuarios`,
  `conocimiento`, `configuracion`.
- **Reference images** for that section.
- **The owner's visual analysis**, in this shape (one block per screen/breakpoint):

  ```
  screen: <name>            (e.g. Dashboard desktop)
  breakpoint: <desktop|tablet|mobile>
  expected: <what the owner expects to see>
  actual:   <what the owner saw>
  severity: <blocker|major|minor|nit>
  ```

- **The section's code map** — a graphify query for the section plus the files it renders through.

## Classification — the only question that matters

Ask: **"who else uses what this fix touches?"**

| Class | Rule |
| --- | --- |
| `local` | The fix touches only files this section owns. |
| `shared-primitive` | The fix touches anything other sections also render through — any `web/src/components/primitives/*`, or the shell (`PanelShell.tsx`, `AppShell.tsx`, `panelRoutes.ts`). **Never fixed here.** Goes to one upstream unit. |
| `token-palette` | The fix touches `web/src/tokens/tokens.css`. **Do not reopen.** Escalate to the owner. |

A row whose fix scope includes a shared primitive or a token is **not** local, no matter how
local it feels.

## Severity

| Level | Meaning |
| --- | --- |
| `blocker` | The screen is functionally wrong or unusable vs the reference. |
| `major` | Clearly wrong and user-visible, but the screen still works. |
| `minor` | Polish; noticeable, not disruptive. |
| `nit` | Subjective/cosmetic; the owner may decline. |

## Evidence Bar (every row, no exceptions)

1. **Reference evidence** — `<file> — <region>`.
2. **Code anchor** — `<path>:<line>` that resolves.
3. **Owner note** — the owner's verbatim observation, or the literal `owner did not flag`.

A row missing any of the three is **invalid** and the validator rejects it. Weak evidence is
not evidence.

## Output — the exact row

Append to `odd/analysis/findings-ledger.md`. Do not create per-section files.

```
| ID | Section | Class | Severity | Finding | Reference evidence | Code anchor | Owner note | Fix scope |
```

- `ID`: `<section>-NNN` (e.g. `dashboard-001`), unique across the ledger.
- `Fix scope`: the files/units the fix would touch — **not the fix itself**.

## Prohibitions

- No edits, no writes outside the ledger, no execution, no code snippets.
- No design proposal beyond the finding. No new routes or destinations.
- Do not reopen palette/tokens. If the reference demands a palette change, mark it
  `token-palette` and escalate — do not decide it.

## Validation Gate (mandatory)

After an analyst returns, a **fresh-context, read-only** validator checks the rows before the
orchestrator accepts them. Contract: `references/validator-gate.md`. The validator does not fix
rows; it rejects them back to the analyst.

## After N Sections

Collapse every `shared-primitive` row across sections into **one** upstream unit before any
per-section implementation. Implementation order is dependency order: upstream first, then
sections one at a time.

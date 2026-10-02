---
name: panel-section-analysis
description: "Trigger: section analysis, analizar sección, panel findings, reference vs code review, findings ledger. Read-only per-section analysis of the Lumat panel using an image-first flow and the owner's visual analysis, writing validated findings per section."
license: MIT
metadata:
  author: Stefan-migo
  version: "2.0"
---

## When to Load

Load for read-only analysis and validation of one panel section before implementation. Parallel
section analyses are safe; implementation is serial because sections share primitives and shell
surfaces. Load only for analysis, never to implement or execute.

## Hard Rules

- Run phases in order. Do not skip the owner gate.
- Do not read code before phase 3. Do not edit files or execute commands during analysis.
- Walk the whole section, not single labels; the v1 first pass was materially incomplete.
- Section slugs: `dashboard`, `clientes`, `conversaciones`, `agenda`, `usuarios`, `conocimiento`,
  `configuracion`.
- Capture images are obtained through the six paths declared in `visual.md`'s `## Sources`; do not
  rely on chat attachments.

## Image-First Phases

0. **Capture** — If `refs/current/<section>/` is missing or stale, run
   `npm run capture:section -- <section>` from `web/`. Read
   `refs/current/<section>/manifest.json` for the app commit.
1. **Compare** — Load the three current images and three reference images from `## Sources`, then
   present them side by side. **Do not read code in this phase.**
2. **Owner analysis** — The owner writes `expected`, `actual`, and `severity` per breakpoint in
   `odd/analysis/<section>/visual.md`, using `references/visual-template.md`. **Stop and wait.**
   Phase 3 must not start until the owner's block exists.
3. **Code analysis (read-only)** — Only now read code, guided by the owner's analysis. Every finding
   cites the owner note as evidence. Make no edits and execute nothing.
4. **Validator gate** — A fresh-context, read-only validator checks the rows using
   `references/validator-gate.md`.
5. **Implementation** — Implement sequentially per section. Complete the shared-primitive roll-up
   first, then implement sections one at a time.

## Adjudication Rule

The archived canonical spec beats the reference, except where the owner rules the reference right.
References control geometry and layout, not palette. Palette and tokens were settled by
`panel-design-system-final`; do not reopen them per section.

## Classification

Ask: **who else uses what this fix touches?**

| Class | Rule |
| --- | --- |
| `local` | The fix touches only files this section owns. |
| `shared-primitive` | The fix touches shared primitives or shell surfaces used by other sections; roll up to one upstream unit. |
| `token-palette` | The fix touches `web/src/tokens/tokens.css`; escalate to the owner, do not reopen. |

## Evidence Bar

Every finding must include all three:

1. Reference image path and region.
2. Resolving code anchor (`path:line`).
3. Owner note, or the literal `owner did not flag`.

Missing or weak evidence invalidates the row.

## Output

Append validated rows to `odd/analysis/<section>/findings.md`. Keep the cross-section index and
roll-ups in `odd/analysis/README.md`. Do not create per-run files or use a single shared ledger.
Use the row schema:

```text
| ID | Section | Class | Severity | Finding | Reference evidence | Code anchor | Owner note | Fix scope |
```

Use IDs `<section>-NNN`. Record each section's lifecycle in the `visual.md` header:
`captured → owner-review → owner-done → code-analysis → validated → implementing → done`.

## Prohibitions

- No edits, no execution, and no code snippets during analysis or validation.
- No design proposal beyond the finding; no new routes or destinations.
- Do not reopen palette or tokens. Mark a demanded palette change `token-palette` and escalate.

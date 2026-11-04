---
name: design-system
description: Lumat panel UI — implement and review panel surfaces against web/DESIGN_SYSTEM.md, tokens.css, the existing primitives and Storybook
license: MIT
compatibility: pi
metadata:
  workflow: design
  audience: implementing agent
---

# Lumat panel design system

## What this skill is

`web/DESIGN_SYSTEM.md` is the authority for how the Lumat panel looks, reads and
behaves. This skill exists to make an agent read it and apply it instead of
inventing a surface. It is not a generic design primer and it does not describe a
different stack.

Historical warning, because it cost a production panel: an earlier version of
this file told agents to read `DESIGN.md` and to use Tailwind. Neither exists
here. `DESIGN.md` was never in this repository, and the panel has no Tailwind. An
agent that followed it produced surfaces with no styles at all, which is exactly
how the "Visitas vencidas" band shipped unstyled.

## When to load

- Building, extending or restyling any surface under `web/src/` (page, section,
  band, dialog, table, empty/error state).
- Reviewing a UI diff, including a diff that only "adds a small panel".
- Adding a section to an existing page: the page's page-architecture entry in
  `web/DESIGN_SYSTEM.md` decides how it composes.

## Read, in this order

1. `web/DESIGN_SYSTEM.md` — the page-architecture section of the page you touch,
   then `## Implementation rules for coding agents` and `## Acceptance checklist`.
2. `web/src/tokens/tokens.css` — the executable token values. Raw hex outside this
   file is a defect.
3. `web/src/components/primitives/` and `primitives.css` — the grammar that
   already exists (`Card`, `Badge`, `Button`, `Tabs`, `Dialog`, `Menu`, `Tabs`,
   `EmptyState`, `StateMessage`).
4. The page's Storybook story (`web/src/stories/pages/…`) — the demonstrated
   states are the contract you must keep.

## Stack, as this repo actually is

- React + TypeScript SPA under `web/src/`, plain CSS, no CSS framework.
- Global rules in `web/src/components/primitives/primitives.css`; a component with
  substantial styling gets its own `Component.css` next to it and imports it.
- Class names are BEM (`agenda-page__visit-card`, `overdue-visits__row`). A block
  owns its elements; do not reach into another block's classes.
- `web/DESIGN_SYSTEM.md` must stay true: a new page section adds or amends its
  page-architecture entry in the same change.
- Copy is neutral Chilean Spanish; code, identifiers and class names are English.

## Non-negotiables

- A list of entities is not bare `<ul>`/`<li>`. It uses the card/table grammar of
  the page it sits in and declares its own block classes. Markup with no classes
  is an unfinished surface, not a minimal one.
- Every state the requirement names exists and is visible: loading, empty,
  filtered-empty, stale, disabled, error, success, permission. Action failures
  stay beside the action that caused them.
- Colour is never the only channel: a status carries text or a labelled indicator
  as well as a tone.
- Destructive or irreversible actions name the affected object and confirm before
  they run.
- Reuse a primitive before writing markup; add a token only for a repeated
  semantic role with a real consumer.

## Verification

- `cd web && npm run build` (the `tsc -b` type check lives there; Vitest passing
  does not prove the tree type-checks) and `npm test`.
- Open the page's Storybook story at representative widths (≥1280, 1024, 768,
  ≤480), with keyboard navigation, zoom/reflow and the failure states.
- Tests do not read CSS, so a green suite never proves a surface is designed. The
  structural check in `web/src/components/**/*.test.tsx` only proves that page
  components declare their own classes; whether those classes look right is a
  rendering check, not a unit test.

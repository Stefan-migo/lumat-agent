---
name: design-agent-lead
description: "Conversational design agent that analyzes a project's design system and emits token proposals mapped onto existing tokens. Trigger: aesthetic brief, design direction, redesign intent, improve the design system, create design tokens."
license: MIT
metadata:
  author: Stefan-migo
  version: "1.0"
source: github.com/Stefan-migo/cortex
---

# Skill: design-agent-lead

> Port of the CortexDesign design-agent-lead (portable-cortex-core). This
> project (Lumat) already has an executable token system at
> `web/src/tokens/tokens.css` and a design direction at
> `web/DESIGN_SYSTEM.md` — read BOTH as authoritative project context before
> any conversation/emission.

Orchestrator-facing design agent with two modes: **conversational-design** and
**visual-architecture**. Operates as a synchronous delegate — each conversation
turn is one invocation cycle.

## Synchronous Protocol

Every turn returns a structured response:

```json
{
  "needsInput": true,
  "state": "<conversation-state>",
  "prompt": "<message-to-user>"
}
```

The orchestrator presents `prompt` to the user, collects their response, and
re-invokes with the user's text + the previous `state`.

On the final turn (user accepts), return the token set CSS and component
selection — no `needsInput` — marking the conversation complete.

ponytail: Synchronous turns avoid streaming and websocket complexity. Ceiling:
no parallel conversation capability. If parallel turns are needed (e.g., compare
two refinements side by side), upgrade to async delegate with merge logic.

## Mode: conversational-design

Trigger: User describes an aesthetic direction or design intent.

Four phases, each advancing when the user signals completion:

1. **Brief** — collect aesthetic direction: brand tone, visual references,
   constraints, target feel.
2. **Propose** — generate 2-3 distinct visual options with contrasting palette
   seeds. Present each with rationale and a mini token set.
3. **Refine** — accept feedback (global: "too dark") or per-token ("keep
   typography tight"). Per-token overrides global for that domain. Regenerate
   and re-present.
4. **Finalize** — on acceptance, emit the full token set + pass to
   `component-adapter` for component selection.

The LLM drives phase transitions naturally through conversation. The phases
exist to structure the output, not to implement a state machine.

## Mode: visual-architecture

Trigger: Emit project design tokens as CSS custom properties. Runs after
conversation finalizes, or can be invoked directly with an aesthetic brief.

### Canonical Token Namespace

Tokens live in exactly 5 domains (VA-001). The canonical namespace is
`--{domain}-{property}`, bounded to 11 canonical properties, capped at 12.

| Domain | Canonical tokens | Count |
|--------|------------------|-------|
| Palette | `--palette-primary`, `--palette-secondary`, `--palette-background`, `--palette-text` | 4 |
| Typography | `--typography-heading`, `--typography-body`, `--typography-mono` | 3 |
| Rhythm | `--rhythm-base`, `--rhythm-radius` | 2 |
| Animation-tone | `--animation-duration`, `--animation-easing` | 2 |
| Scroll-narrative | reserved (DRL narrative concept, VA-005) | 0 |

The legacy `--od-*` namespace is NON-canonical and frozen as aliases: every
`--od-{group}-{name}` SHALL be aliased to its canonical
`--{domain}-{property}` equivalent and SHALL NEVER be deleted (VA-001/CP-005).

### Live Emitter

Token emission integrates with this project's existing
`web/src/tokens/tokens.css`. The conversation produces the canonical
`--{domain}-{property}` set as a proposal; the project's token file is the
executable source. Map proposed tokens onto the existing Lumat token names
where they overlap (e.g. palette-primary ↔ --primary-800), and only propose
NEW tokens when no existing token covers the need.

ponytail: 12-token cap prevents explosion (VA-004); palette 4 is mandatory and
never dropped (VA-006). Scroll behavior is a DRL narrative concept stored in
`redesign-intent.json`, not a per-project token (VA-005).

### Deterministic Heuristics

Named patterns that map brief keywords to token values:

- **cold/technical** → blue hues, compact spacing (4px), fast duration (150ms), sharp corners
- **warm/editorial** → amber/red hues, generous spacing (12px), slow duration (500ms), round corners
- **dark mode** → bg luminance < 0.3, text luminance > 0.7
- **playful** → saturated primary, wide type scale, bouncy easing
- **minimal** → neutral palette, comfortable spacing (8px), medium duration (300ms), moderate corners (8px)

ponytail: ~15-20 named heuristics is the rough ceiling before this becomes
unwieldy. Upgrade: `refs/design/heuristics.yaml` with weighted matching.

### Output Format

The emitter writes the canonical `:root { }` block (see Live Emitter). It
declares the 11 canonical `--{domain}-{property}` tokens plus the frozen
`--od-*` alias declarations pointing at their canonical equivalents
(VA-001/CP-005), for example:

```css
:root {
  --palette-primary: #6b56f0;
  --palette-secondary: #0f0f23;
  --palette-background: #0b0b16;
  --palette-text: #f5f0ff;
  --typography-heading: 'Space Grotesk';
  --typography-body: 'Inter';
  --typography-mono: 'monospace';
  --rhythm-base: 0.5rem;
  --rhythm-radius: 1rem;
  --animation-duration: 0.3s;
  --animation-easing: cubic-bezier(0.4, 0, 0.2, 1);
  --od-color-primary: var(--palette-primary); /* alias, never deleted */
}
```

### Catalog Contract

Component selection returns DC-004 object-form entries from the canonical
catalog `web/.storybook/component-catalog.json`. Each component carries `id`,
`storyFile|null`, `visualContext[]`, `moodTags[]`, and
`adaptationRules` with object-form `variants` (map of variant name to prop
override), plus `tokenSlots[]`/`defaultProps`/`defaults`. Query by
`visualContext` + OR-`moodTags` via the CA-001 helper (see `component-adapter`);
an unmatched query returns an empty array, never an error.

### Final Output Contract

After Finalize, return all three:
1. **CSS tokens** — the `:root { ... }` block above
2. **Component adaptation list** — component IDs + selected variants (from `component-adapter`)
3. **Design rationale** — 2-4 sentences explaining the decisions

## DRL Integration

Read `web/DESIGN_SYSTEM.md` as the project's taste authority (DRL replacement).
If a reference contradicts a heuristic, the DESIGN_SYSTEM.md wins.

## Skills Loaded by This Skill

- `component-adapter` — for component selection + token adaptation after finalize
- `ponytail-review` — review generated component code for over-engineering

## Self-review

After finalize: verify the token set matches the brief. If the user asked for
"warm" and the output is blue, refine before returning.

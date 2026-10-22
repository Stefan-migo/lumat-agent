---
name: component-adapter
description: "Deterministic catalog query + token adaptation engine. Queries the CortexDesign global component catalog by visualContext/moodTags and adapts components to project tokens. Trigger: select a component, adapt component to tokens, catalog query, map tokens to a component."
license: MIT
metadata:
  author: Stefan-migo
  version: "1.0"
source: github.com/Stefan-migo/cortex
---

# Skill: component-adapter

> Port of the CortexDesign component-adapter (portable-cortex-core). Catalog is
> the CortexDesign global catalog (v1.2.0, 90 entries) — components live in the
> CortexDesign repo and are adapted to this project's tokens.

Deterministic catalog query + token adaptation engine. Reads
`web/.storybook/component-catalog.json` and produces structured output with no
generative AI — all rules are applied by the LLM following this spec.

## Data Source

`web/.storybook/component-catalog.json` — static JSON, git-tracked. Regenerated
via `npx storybook extract` or a Node script parsing CSF3 stories.

### Schema (DC-004 canonical)

The catalog SHALL conform to the DC-004 canonical shape (`web/.cortex/schema.json`),
which resolves the prior three-way drift. Each component carries `id`,
`storyFile|null`, `visualContext[]`, `moodTags[]`, and `adaptationRules` with
object-form `variants` (map of variant name to prop override — never an array),
`tokenSlots[]`, `defaultProps`, and `defaults`:

```json
{
  "version": "1.0.0",
  "components": [
    {
      "id": "glitch-text",
      "storyFile": "TextAnimations/GlitchText.stories.jsx",
      "visualContext": ["hero", "callout", "feedback"],
      "moodTags": ["edgy", "tech", "playful"],
      "adaptationRules": {
        "tokenSlots": ["--palette-primary", "--palette-secondary"],
        "defaultProps": { "glitchSpeed": 300 },
        "variants": {
          "Default": {},
          "HoverOnly": { "trigger": "hover" },
          "SlowMotion": { "glitchSpeed": 800 },
          "WithShadows": { "showShadows": true }
        },
        "defaults": {
          "--palette-primary": "#6b56f0",
          "--palette-secondary": "#0f0f23"
        }
      }
    }
  ]
}
```

Token slots use the canonical `--{domain}-{property}` namespace (`--palette-*`,
`--typography-*`, `--rhythm-*`, `--animation-*`; VA-001). Legacy `--od-*`
tokens remain as frozen ALIASES to their canonical equivalent and are never
deleted (CP-005/VA-001). The canonical catalog (`web/.storybook/component-catalog.json`)
and the local catalog emitted by the `.cortex` capsule share ONE canonical
source (CP-003).

ponytail: Flat JSON, no DB, no MCP server. If the catalog grows past 500
components, add an index map (component id → `visualContext` + `moodTags`)
to avoid O(n) scans. YAGNI for now.

## Operations

### 1. Query by Context

```
Input:  { operation: "query", visualContext: "hero", moodTags: ["dramatic", "bold"] }
Output: { componentId, visualContext, moodTags, adaptationRules }
```

Query logic (CA-001):
1. Load `web/.storybook/component-catalog.json` (DC-004 canonical shape)
2. Filter components where `component.visualContext` matches the query value
   AND `component.moodTags` intersects `query.moodTags` (OR semantics within
   the set — any matching tag is sufficient)
3. Return all matches (empty array if none — no error)

This is the CA-001 catalog query — implemented as a pure helper at
`web/.cortex/catalog-query.js` (`queryComponents`) shared by this skill's consumers
(one canonical source, CP-003). The helper reads any DC-004 catalog object and
returns an empty array without throwing for a `visualContext` no component
declares.

### 2. Map Tokens

```
Input:  { operation: "map-tokens", componentId: "glitch-text", projectTokens: { ... } }
Output: { componentId, tokenMap: { "--palette-primary": "...", ... }, warnings: [] }
```

Mapping logic:
1. Find component in catalog by `id`
2. For each slot in `component.tokenSlots` (canonical `--{domain}-{property}`
   names; `--od-*` alias values come from the emitter, never defined here):
   - If `projectTokens` defines it → use the project value
   - Else → use `component.adaptationRules.defaults[slot]`
3. If any slot falls back to defaults, record a warning

### 3. Apply Variant

```
Input:  { operation: "apply-variant", componentId: "glitch-text", variantName: "SlowMotion" }
Output: { componentId, adaptedProps: { ... }, warnings: [] }
```

Variant logic:
1. Find component in catalog by `id`
2. If `variantName` exists in `adaptationRules.variants`:
   - Deep-merge variant overrides with `defaultProps` (variant wins)
3. Else: return `defaultProps` as-is and log an unknown-variant warning

### 4. Combined: adapt

```
Input:  { operation: "adapt", visualContext, moodTags, projectTokens, variantName }
Output: { componentId, adaptedProps, tokenMap, warnings }
```

Runs query → map-tokens → apply-variant sequentially on the first matching
component. This is the most common invocation — called by `design-agent-lead`
after Finalize phase.

## Output Contract

Every successful operation returns JSON with:

| Key | Type | Always | Description |
|-----|------|--------|-------------|
| `componentId` | string | yes | Catalog component id |
| `adaptedProps` | object | yes | Merged props (defaults + variant) |
| `tokenMap` | object | yes | CSS variable key/value pairs |
| `warnings` | string[] | yes | Non-empty if fallbacks or errors |

## Dependencies

- `web/.storybook/component-catalog.json` — MUST exist before first invocation;
  DC-004 canonical catalog validated against `web/.cortex/schema.json` (SB-GLOBAL-000)
- `web/.cortex/catalog-query.js` — canonical CA-001 query helper (one source, CP-003)
- No NPM packages, no MCP servers, no runtime dependencies

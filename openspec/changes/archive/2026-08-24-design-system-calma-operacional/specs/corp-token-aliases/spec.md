# Corp Token Aliases Specification

## Purpose

Define the `--corp-*` alias layer — 17 slots in `web/src/tokens/tokens.css` that map CortexDesign DC-004 catalog slots onto the frozen Lumat token set. This layer lets slice-1 primitives consume a stable catalog contract without any color, font, or value change: every slot resolves to an existing token, never raw hex.

## Requirements

### Requirement: CST-ALIAS-1 — All Slots Map to Existing Tokens

All 17 `--corp-*` slots MUST resolve to existing token custom properties; the alias layer MUST NOT introduce any new hex literal. This satisfies `DS-TKN-1` (single token source) and the hex-guard drift walk.

#### Scenario: Every slot resolves to a token

- GIVEN `tokens.css` with the `--corp-*` blocks
- WHEN each `--corp-*` value is resolved
- THEN it references an existing `var(--*)` token and no hex literal appears in the alias declarations

#### Scenario: Hex guard stays green

- GIVEN the extended `tokens.css`
- WHEN `npm test` runs in `web/`
- THEN the no-hard-coded-hex walk passes with the alias layer included

### Requirement: CST-ALIAS-2 — Additive-Only Alias Evolution

The alias layer MUST evolve additively under `DS-TKN-2`: the 17 slots map the flavor slots (`--corp-primary`, `--corp-primary-fg`, `--corp-accent`, `--corp-border`) and reference slots (`--corp-fg`, `--corp-fg-muted`, `--corp-text`, `--corp-muted`, `--corp-surface`, `--corp-surface-hover`, `--corp-bg`, `--corp-size`, `--corp-w`, `--corp-h`, `--corp-value`, `--corp-radius`, `--corp-gap`), and adding them MUST not alter any pre-existing declaration.

#### Scenario: Pre-existing declarations pinned

- GIVEN the pre-change `tokens.css`
- WHEN the `--corp-*` layer is appended
- THEN every pre-existing `--*` declaration keeps its exact value byte-identical

### Requirement: CST-ALIAS-3 — Frozen Alias Principle

Each `--corp-*` slot MUST be defined once and MUST mirror the frozen Lumat value it maps (the same frozen-alias discipline `DS-TKN-2` applies to `--od-*`). Consumers MUST reference the `--corp-*` slot, not twin a value.

#### Scenario: Single definition, no value twins

- GIVEN the alias layer
- WHEN aliases are scanned
- THEN each `--corp-*` slot is declared once and no consumer re-declares its value

### Requirement: CST-ALIAS-4 — Size-Slot Warning Fallback Semantics

`--corp-size`, `--corp-w`, and `--corp-h` MAY not map to a single frozen token when the catalog slot is dimensional; when unmapped, components MUST fall back to their default sizing. A build-time warning SHALL document the fallback; it MUST NOT block `npm test` or `build-storybook`.

#### Scenario: Dimensional slot falls back

- GIVEN a catalog component that requests `--corp-size`
- WHEN the alias resolves to no single frozen token
- THEN the component uses its default sizing and the fallback is documented, never a hardcoded value

#### Scenario: Build stays green with warnings

- GIVEN the alias layer with documented fallbacks
- WHEN `npm run build-storybook` runs
- THEN it completes successfully and warnings appear as documentation, not errors

### Requirement: CST-ALIAS-5 — Tabular Numerals for Data Values

Roles representing data (KPIs, timestamps, IDs, values) MUST render with `font-variant-numeric: tabular-nums` via the `--corp-value` and related slots; non-data decorative text MAY omit it.

#### Scenario: Data roles use tabular numerals

- GIVEN a KPI, timestamp, ID, or value role
- WHEN it renders
- THEN `font-variant-numeric: tabular-nums` is applied and digits align in columns

#### Scenario: Decorative text unaffected

- GIVEN a non-data label or heading
- WHEN it renders
- THEN it is not forced into tabular-nums

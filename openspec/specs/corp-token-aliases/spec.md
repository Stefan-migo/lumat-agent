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

### Requirement: CST-ALIAS-2 — Approved Palette Alias Evolution

The `--corp-*` slots MUST remain stable semantic indirections as required by DS-TKN-1 and MUST NOT duplicate raw values. The canonical target value for a color slot MAY change only through an explicitly approved palette revision such as DS-TKN-13; non-palette token stability and alias target integrity remain required. This narrowly removes the former dependency on immutable DS-TKN-2 values.
(Previously: adding aliases could not alter any prior token value under DS-TKN-2.)

#### Scenario: Approved target value changes without alias duplication
- GIVEN a corp slot maps to a canonical color role explicitly revised by DS-TKN-13
- WHEN that canonical role changes value
- THEN the alias continues to resolve through the role without duplicating a literal value

#### Scenario: Unapproved or non-palette changes remain prohibited
- GIVEN a target outside the approved palette roles or a non-palette target
- WHEN its value changes without separate approval
- THEN the alias contract does not authorize the change

### Requirement: CST-ALIAS-3 — Canonical Alias Principle

Each `--corp-*` slot MUST be defined once and MUST resolve to one canonical semantic role or permitted existing token. Consumers MUST reference the `--corp-*` slot where the catalog contract applies, not twin its value. A target's approved canonical value MAY evolve under DS-TKN-13; aliases themselves MUST NOT encode a second palette.
(Previously: each alias mirrored a frozen Lumat value.)

#### Scenario: Single definition and canonical indirection
- GIVEN the alias layer and its consumers
- WHEN declarations and references are inspected
- THEN each slot is defined once, resolves to a declared canonical role, and consumers do not re-declare its value

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
### Requirement: CST-ALIAS-6 — Palette Revision Compatibility

Every corp slot MUST target a declared token and resolve successfully. A canonical color target value MAY change only through the approved palette revision; alias declarations MUST remain hex-free and consumers MUST remain token-only. Any new or updated chrome/surface aliases MUST target canonical semantic roles rather than defining parallel roles or destinations.

#### Scenario: All slots resolve after palette revision
- GIVEN the revised canonical palette and corp aliases
- WHEN every slot is resolved
- THEN each target is declared and resolves through token indirection

#### Scenario: Alias and consumer values remain single-source
- GIVEN updated aliases and production consumers
- WHEN their declarations and styles are scanned
- THEN aliases contain no hex literals and consumers use token references rather than duplicated color values

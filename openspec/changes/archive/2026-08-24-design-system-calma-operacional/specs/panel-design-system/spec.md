# Delta for panel-design-system

## ADDED Requirements

### Requirement: DS-TKN-10 — Aliases Stay Inside the Hex Guard

The `--corp-*` alias layer and any primitives that consume it MUST keep the no-hard-coded-hex walk green: aliases map to existing tokens, and `tokens.test.ts` MUST extend its drift guard to assert the alias layer resolves only to `var(--*)` references with zero hex literals.

#### Scenario: Alias layer under the hex guard

- GIVEN the `--corp-*` block in `tokens.css`
- WHEN the drift-guard walk runs in `npm test`
- THEN it covers the alias layer and reports zero hex literals in aliases or consuming primitives

#### Scenario: Guard spot-checks aliases

- GIVEN the extended `tokens.test.ts`
- WHEN the guard runs
- THEN spot-checks assert the `--corp-*` slots resolve to existing tokens and no existing assertion is removed

### Requirement: DS-TKN-11 — Tabular Numerals for Data Values

Data values rendered by the panel (KPIs, timestamps, IDs, percentages, money) MUST apply `font-variant-numeric: tabular-nums` so comparable digits align; non-data text MAY omit it. This codifies the `DESIGN_SYSTEM.md` tabular-numerals rule.

#### Scenario: KPIs and metrics align

- GIVEN a KPI or StatCard value
- WHEN it renders
- THEN `tabular-nums` is applied and digits align in columns

#### Scenario: Sparsely formatted text unaffected

- GIVEN a label or status text
- WHEN it renders
- THEN it is not forced into tabular-nums

### Requirement: DS-TKN-12 — Corrected Canvas Background Documentation

`web/DESIGN_SYSTEM.md` MUST state the canvas `--bg` value as `#F1F1E8` (matching the executable `tokens.css`), replacing the stale `#F4F5F7`; the executable token source remains authoritative.

#### Scenario: Doc matches executable token

- GIVEN `DESIGN_SYSTEM.md` line 120
- WHEN the Canvas row is read
- THEN it shows `--bg` `#F1F1E8` and matches `tokens.css`

## MODIFIED Requirements

### Requirement: DS-TKN-1 — Single Token Source (PDW-TKN-1)

The panel design system MUST declare all design tokens as CSS custom properties in the single `:root` block of `web/src/tokens/tokens.css`, and MUST NOT hard-code color hex values outside `tokens.css` anywhere under `web/src`.
(Previously: covered `tokens.css` and consuming components; now explicitly including the `--corp-*` alias layer added by `corp-token-aliases`.)

#### Scenario: Components consume tokens

- GIVEN a component or story needs a color or spacing value
- WHEN it is implemented
- THEN it references a `var(--*)` custom property from `tokens.css` and no hex color literal appears in component or story source

#### Scenario: Alias layer is single-source

- GIVEN the `--corp-*` alias blocks in `tokens.css`
- WHEN they are implemented
- THEN they reference existing `var(--*)` tokens (never raw hex), preserving the single token source

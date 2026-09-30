# Delta for corp-primitives

## MODIFIED Requirements

### Requirement: CST-PRIM-1 — Catalog Contract Consumption

Slice-1 primitives MUST consume the catalog contract through `--corp-*` slots in `tokens.css`; no slice-1 component MAY reference raw hex or twin a token value. Newly revised surface and action roles MAY be consumed through an existing alias or a declared canonical semantic token while preserving the single-source and no-hard-coded-color guarantees.
(Previously: consumption was restricted to `--corp-*` slots and existing tokens without explicitly covering revised semantic roles.)

#### Scenario: Components resolve through semantic tokens
- GIVEN any slice-1 primitive (Button, Badge, Card, Input, Select, Textarea, Alert, StatusBadge)
- WHEN its styles are inspected
- THEN each color/space value references a `--corp-*` slot or declared design token and no hex literal appears

#### Scenario: Hex guard covers primitives
- GIVEN the applied change
- WHEN the no-hard-coded-hex walk runs in the token test
- THEN no slice-1 component source contains a hex literal

### Requirement: CST-PRIM-2 — WCAG AA Contrast for Links and Actions

Links and primary actions MUST meet WCAG 2.2 AA text contrast of at least 4.5:1 for normal-size text on their actual surfaces. The implementation MUST select semantic foreground/action roles based on measured pairs; the former fixed `--primary-700` link and white-on-`--primary-800` action pair are not presumed compliant or required solely from the prior palette. Pure white MUST NOT be used as a surface. Every changed pair MUST be measured; a palette value is not contrast evidence.
(Previously: links were fixed to `--primary-700`, and primary action text was fixed to white on `--primary-800` with a pinned ratio.)

#### Scenario: Link pair is measured
- GIVEN a customer-name or inline link on its rendered surface
- WHEN its contrast is checked
- THEN the actual pair measures at least 4.5:1 or is explicitly recorded as unresolved with its ratio and authority

#### Scenario: Primary action pair is measured
- GIVEN a primary Button on its actual action background
- WHEN foreground/background contrast is checked
- THEN the actual text pair is measured and meets at least 4.5:1 or is explicitly recorded as unresolved

## ADDED Requirements

### Requirement: CST-PRIM-8 — No Pure-White Primitive Surface

Card, Input, Select, Textarea, Alert/StateMessage, DataTable, Dialog, and other light primitive surfaces MUST resolve to approved non-white surface roles. Pure white foreground text MAY be used on dark chrome only when the actual pair has measured applicable contrast. Derived or aliased surface values MUST also be evaluated; string matching for a white hex spelling alone is insufficient.

#### Scenario: Light primitive surfaces resolve to non-white roles
- GIVEN the listed light primitives
- WHEN their computed or canonical surface colors are evaluated
- THEN none resolves to pure white

#### Scenario: Dark chrome foreground is verified
- GIVEN white foreground text on dark shell chrome
- WHEN its actual contrast is measured
- THEN it is retained only when it meets the applicable WCAG 2.2 AA threshold

### Requirement: CST-PRIM-9 — Flat Card Separation

Cards MUST use the approved light surface with approximately 10px radius at the reference scale and a hairline boundary rather than material elevation shadow. Existing primitive APIs, state behavior, and accessibility contracts MUST remain intact. Radius MUST use the existing global `--radius-*` token scale, tuned so cards resolve to approximately 10px; no new semantic radius alias taxonomy is introduced.

#### Scenario: Card geometry and separation
- GIVEN a rendered card in a light primitive surface
- WHEN its fill, boundary, radius, and elevation are inspected
- THEN it uses a non-white light surface, hairline boundary, approximately 10px radius, and essentially no material shadow

#### Scenario: Existing primitive behavior is preserved
- GIVEN an existing card API, state, keyboard, or focus contract
- WHEN its visual treatment changes
- THEN that behavior and accessibility contract remain unchanged

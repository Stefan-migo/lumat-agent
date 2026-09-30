# Delta for corp-token-aliases

## MODIFIED Requirements

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

## ADDED Requirements

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

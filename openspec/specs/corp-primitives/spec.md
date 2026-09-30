# Corp Primitives Specification

## Purpose

Define the slice-1 primitive contract: Button, Badge, Card, Input, Select, Textarea, StatusBadge (mapped to Badge), and StateMessage (mapped to Alert) consume the catalog via `--corp-*` slots only, honor WCAG AA contrast, enforce ergonomic touch/control sizing, keep complete states first-class, and never hardcode hex.

## Requirements

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

### Requirement: CST-PRIM-3 — Control Height and Touch Target

Interactive slice-1 controls MUST render at a 40px control height with 44px touch targets on touch devices, so buttons, inputs, selects, and textareas are comfortably tappable without visual over-scaling.

#### Scenario: Dense panels keep 40px controls

- GIVEN a dense form row with controls
- WHEN the layout renders
- THEN each control is 40px tall and touch-hit target is at least 44px on touch devices

#### Scenario: Compact option exceeds touch target

- GIVEN a compact button below 40px
- WHEN the touch target is inspected
- THEN its hit area is padded to ≥44px regardless of visual height

### Requirement: CST-PRIM-4 — Complete States First-Class

Each slice-1 primitive MUST expose its complete state set — loading, empty, error, disabled — as first-class variants; a state MUST NOT be representable only by color alone. Disabled MUST rely on the documented muted semantics, never `--text-muted` alone.

#### Scenario: States are renderable variants

- GIVEN Badge, Card, Button, or Alert
- WHEN its variant matrix renders
- THEN loading, empty, error, and disabled render as first-class variants

#### Scenario: Disabled pairs semantics with label

- GIVEN a disabled control
- WHEN it renders
- THEN a visible label or `aria-disabled` pairs with the muted surface (never color alone)

### Requirement: CST-PRIM-5 — StatusBadge and StateMessage Mapping

`StatusBadge` MUST map to `Badge` tones (neutral/warning/success, per `DS-UI-LABELS`), and `StateMessage` MUST map to `Alert` semantics that pair a visible label, a semantic color, and `role="status"|"alert"`, never color alone.

#### Scenario: StatusBadge maps to Badge

- GIVEN a conversation/customer/case status
- WHEN it renders through `StatusBadge`
- THEN it uses the `Badge` tone map with approved Spanish labels

#### Scenario: StateMessage maps to Alert

- GIVEN an error or stale state rendered by `StateMessage`
- WHEN an Alert renders
- THEN it pairs a visible Spanish label, semantic color, and `role="alert"|"status"`

### Requirement: CST-PRIM-6 — No Decorative Animation

Slice-1 MUST NOT add decorative animation components (glitch, gradient-text, magnet, marquee, blob-cursor, scroll-reveal, text-pressure) from the DC-004 catalog; such components violate `DESIGN_SYSTEM.md` and are non-goals.

#### Scenario: No decorative catalog components

- GIVEN the applied change
- WHEN the diff is reviewed
- THEN no decorative-animation component is added under `primitives/`

### Requirement: CST-PRIM-7 — First-Slice Interaction Ownership

The contract MUST assign native/platform ownership to popover, tooltip, dropdown presentation/positioning/dismissal/focus, modal, and combobox-class controls using native input plus listbox semantics; CSS-only ownership to sidebar rail/skeleton; and Radix-backed ownership to menu using `@radix-ui/react-dropdown-menu`. Radix has no combobox primitive, so no package is justified. Resizable/uncertain primitives remain deferred. Each MUST use `--corp-*` or existing tokens, expose keyboard behavior, honor 40px/44px sizing, and expose complete states.

#### Scenario: Ownership and contracts

- GIVEN a first-slice interaction
- WHEN inspected
- THEN owner, tokens, accessibility, sizing, and states are testable

#### Scenario: Deferred adoption is rejected

- GIVEN resizable panels or incomplete control
- WHEN tested
- THEN it fails; color alone is rejected

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
## Non-Goals

- Palette changes, web fonts, icon packages, dark mode, and the full 39-component catalog adoption (Table, Tabs, Accordion, Pagination et al.) are chained to later slices.
- Jinja panel migration and backend are explicitly out of scope.

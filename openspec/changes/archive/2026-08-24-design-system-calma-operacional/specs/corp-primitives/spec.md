# Corp Primitives Specification

## Purpose

Define the slice-1 primitive contract: Button, Badge, Card, Input, Select, Textarea, StatusBadge (mapped to Badge), and StateMessage (mapped to Alert) consume the catalog via `--corp-*` slots only, honor WCAG AA contrast, enforce ergonomic touch/control sizing, keep complete states first-class, and never hardcode hex.

## Requirements

### Requirement: CST-PRIM-1 — Catalog Contract Consumption

Slice-1 primitives MUST consume the catalog contract exclusively through `--corp-*` slots in `tokens.css`; no slice-1 component MAY reference raw hex or twin a token value.

#### Scenario: Components resolve through aliases only

- GIVEN any slice-1 primitive (Button, Badge, Card, Input, Select, Textarea, Alert, StatusBadge)
- WHEN its styles are inspected
- THEN every color/space value references a `--corp-*` slot or existing token and no hex literal appears

#### Scenario: Hex guard covers primitives

- GIVEN the applied change
- WHEN the no-hard-coded-hex walk runs in the token test
- THEN no slice-1 component source contains a hex literal

### Requirement: CST-PRIM-2 — WCAG AA Contrast for Links and Actions

Links and primary actions MUST meet WCAG AA (≥4.5:1) on their surfaces. Normal-size links MUST use `--primary-700`, MUST NOT use `--primary-600` on light surfaces; primary action text MUST be white on `--primary-800` (measured 12.26:1).

#### Scenario: Link contrast honored

- GIVEN a customer-name or inline link on a light surface
- WHEN its color is measured
- THEN it is `--primary-700` at ≥4.5:1 and never `--primary-600`

#### Scenario: Primary action text passes

- GIVEN a primary Button
- WHEN its foreground/background contrast is measured
- THEN white text on `--primary-800` passes AA (12.26:1)

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

## Non-Goals

- Palette changes, web fonts, icon packages, dark mode, and the full 39-component catalog adoption (Table, Tabs, Dialog, Tooltip, Popover, DropdownMenu, Accordion, Pagination et al.) are chained to later slices.
- Jinja panel migration and backend are explicitly out of scope.

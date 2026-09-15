# Delta for Corp Primitives

## ADDED Requirements

### Requirement: CST-PRIM-7 — First-Slice Interaction Ownership
The contract MUST assign native/platform ownership to popover, tooltip, dropdown presentation/positioning/dismissal/focus, modal, and combobox-class controls using native input plus listbox semantics; CSS-only ownership to sidebar rail/skeleton; and Radix-backed ownership to menu using `@radix-ui/react-dropdown-menu`. Radix has no combobox primitive, so no package is justified. Resizable/uncertain primitives remain deferred. Each MUST use `--corp-*` or existing tokens, expose keyboard behavior, honor 40px/44px sizing, and expose complete states. This lifts the Non-Goals deferral; that prose MUST be updated at archive.
#### Scenario: Ownership and contracts
- GIVEN a first-slice interaction
- WHEN inspected
- THEN owner, tokens, accessibility, sizing, and states are testable
#### Scenario: Deferred adoption is rejected
- GIVEN resizable panels or incomplete control
- WHEN tested
- THEN it fails; color alone is rejected

# Panel Visual Foundation Delta

## MODIFIED Requirements

### Requirement: DS-STORY-1 — Doc-Level Coverage for All Existing Stories

Every existing primitive story file and the `domain/AppShell` story MUST be
doc-level. Each MUST provide a component description, usage guidance,
interactive controls where meaningful, a variant matrix story, and
accessibility notes, while preserving its existing named stories and args.
The requirement intentionally names no fixed story count: the repository has
grown beyond the historical ten-file foundation inventory.

#### Scenario: Story coverage follows the repository

- GIVEN the current `web/src/stories/**/*.stories.tsx` inventory
- WHEN the design-system coverage is reviewed
- THEN every existing primitive and AppShell story has the required docs
  contract without relying on a stale fixed count

### Requirement: DS-TKN-3 — Typography Scale (PDW-TKN-3)

The type system MUST extend the existing `--text-*` scale with
`--text-xs`, `--text-base`, `--text-xl`, and `--text-3xl` as rem values, MUST
add line-height and font-weight tokens, and MUST preserve the pre-existing
`--font-sans: system-ui, sans-serif` declaration byte-identically. The UI font
MUST be Inter through a new additive `--font-ui` token that composes Inter with
the existing fallback stack. `clamp()` MAY be used only by the display tokens
`--text-xl`, `--text-2xl`, and `--text-3xl`; body sizes MUST remain static rem
values.

#### Scenario: Font collision is resolved additively

- GIVEN the pre-change `--font-sans` declaration
- WHEN Inter is adopted
- THEN `--font-sans` remains unchanged and `--font-ui` provides the UI stack

#### Scenario: Fluid display scale is bounded

- GIVEN the type tokens
- WHEN their values are inspected
- THEN only the three named display tokens may use `clamp()`, while body sizes
  remain static rem values

### Requirement: DS-DOC-1 — Platform-First Interaction Policy

`DESIGN_SYSTEM.md` MUST document platform-first mechanics where the platform
still owns the behaviour, and MUST approve Radix for menu, Dialog, Popover,
Tabs, Tooltip, and Select only as headless behaviour/ARIA primitives. The
document MUST state that Radix supplies no visual styling and that the
tokenized primitives retain the visual contract.

#### Scenario: Approved Radix scope is explicit

- GIVEN the interaction policy
- WHEN it is read
- THEN the five approved composites plus the existing menu package are named,
  and platform-first ownership remains documented for native mechanics

#### Scenario: Visual ownership remains local

- GIVEN a Radix-backed interaction
- WHEN it is styled
- THEN the visual output resolves through the panel tokenized stylesheet, not
  through Radix defaults

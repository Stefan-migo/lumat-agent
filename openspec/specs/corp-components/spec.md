# Corporate Components Specification (Table / Tabs / Dialog)

## Purpose

Define the port contract for the first three Corporate-family components from the CortexDesign catalog: retarget the `.table` primitive to `--corp-*` slots, add a WAI-ARIA `Tabs` primitive (Default + Controlled), and add a `Dialog` primitive that honors the DESIGN_SYSTEM.md §Dialog disclosure contract (initial focus, focus trap, Escape, focus restore). Palette stays frozen: no token value changes, aliases only.

## Requirements

### Requirement: CORP-TABLE-1 — Table Contract Alignment

The `.table` primitive MUST consume the catalog table slots (`--corp-border`, `--corp-text`) for its color values. Their canonical roles MAY have the values specified by the approved palette revision; table semantics and the DataTable component API and its consumers MUST remain unchanged. Table text and boundary pairs MUST be measured against applicable WCAG 2.2 AA thresholds and MUST NOT be assumed compliant from alias names alone.
(Previously: aliases had to resolve to old values and provide zero visual change.)

#### Scenario: Table resolves through aliases
- GIVEN the applied change
- WHEN `.table` styles are inspected in `primitives.css`
- THEN border and text colors reference `--corp-border` and `--corp-text` without duplicated raw values

#### Scenario: Table consumers and contrast remain valid
- GIVEN current DataTable consumers (ClientesList, KbList, ConversationsList, ClientFicha)
- WHEN the revised table is evaluated
- THEN API and semantics remain unchanged and actual text/boundary pairs have measured applicable contrast evidence

### Requirement: CORP-TABS-1 — Tabs Primitive

A `Tabs` primitive MUST exist with `role="tablist"`, `tab`, and `tabpanel` semantics, `aria-selected` on the active tab, click activation, and the catalog `tabs` slots (`--corp-border`, `--corp-text`, `--corp-muted`, `--corp-accent`, `--corp-surface`) for styling. Default variant: uncontrolled with the first tab active.

#### Scenario: Renders tablist with active tab

- GIVEN a Tabs with two panels
- WHEN it renders
- THEN a `tablist` with two `tab` roles exists, the first tab has `aria-selected="true"`, and its `tabpanel` is visible

#### Scenario: Click activates a tab

- GIVEN a Tabs with two panels
- WHEN the second tab is clicked
- THEN `aria-selected` moves to the second tab and the second `tabpanel` becomes visible while the first hides

### Requirement: CORP-TABS-2 — Controlled Variant

The `Tabs` primitive MUST expose a controlled variant where the active tab is driven by props (`activeTab` + `onTabChange`), matching the catalog `Controlled` variant.

#### Scenario: Controlled tab state

- GIVEN a controlled Tabs with `activeTab="b"`
- WHEN it renders
- THEN tab `b` has `aria-selected="true"` regardless of click order, and `onTabChange` fires with the clicked tab id

### Requirement: CORP-DIALOG-1 — Dialog Rendering

A `Dialog` primitive MUST render an overlay with `role="dialog"`, `aria-modal="true"`, and catalog dialog slots (`--corp-border`, `--corp-bg`, `--corp-radius`, `--corp-fg`) using revised non-white semantic surface roles. Its radius MUST be approximately 14px at the reference scale. Overlays and dialogs MAY use `--shadow-3` for affordance; cards carry no material shadow. A close control MUST carry an accessible label (`Cerrar`). Dialog text and boundary contrast MUST be measured against applicable WCAG 2.2 AA thresholds; the palette alone is not proof.
(Previously: the dialog used prior palette assumptions, `--shadow-2`/`--shadow-3`, and `--radius-md`.)

#### Scenario: Dialog renders with semantics and revised surface
- GIVEN an open Dialog
- WHEN it renders
- THEN a `role="dialog"` node with `aria-modal="true"` and a close button labeled `Cerrar` exists, and its surface is non-white

#### Scenario: Dialog geometry and contrast are verified
- GIVEN an open Dialog at its reference scale
- WHEN its radius and actual text/boundary pairs are evaluated
- THEN its radius is approximately 14px and each applicable pair has measured WCAG 2.2 AA evidence

#### Scenario: Dialog uses overlay-only shadow
- GIVEN an open Dialog
- WHEN dialog elevation is specified
- THEN the dialog MAY use `--shadow-3` for affordance while cards carry no material shadow

### Requirement: CORP-DIALOG-2 — Escape Closes

An open Dialog MUST close on Escape (where safe — no nested input capture), calling the onClose handler.

#### Scenario: Escape dismisses

- GIVEN an open Dialog
- WHEN Escape is pressed inside the dialog
- THEN `onClose` is called and the dialog unmounts

### Requirement: CORP-DIALOG-3 — Focus Management

A Dialog MUST set meaningful initial focus on open (first focusable element or the dialog itself), MUST trap focus while open (Tab cycles within the dialog), and MUST restore focus to the previously focused element on close.

#### Scenario: Focus moves in and is restored on close

- GIVEN a button that opens the Dialog and holds focus
- WHEN the Dialog opens
- THEN focus moves into the dialog (initial focusable element)
- WHEN the Dialog closes
- THEN focus returns to the opening button

### Requirement: CORP-DIALOG-4 — No Unapproved Token Value Changes

Token value changes MUST NOT occur except for the exact color roles explicitly authorized by the approved palette revision. The single token source, alias integrity, and non-palette token stability MUST remain enforced. The drift guard MUST assert the revised palette and its resolved non-white surfaces, alias integrity, affected-pair contrast measurements, and non-palette stability; it MUST NOT enforce the superseded blanket byte-identical palette freeze.
(Previously: no token value could change and the existing drift guard had to pass unchanged.)

#### Scenario: Approved palette roles are guarded
- GIVEN the approved palette revision
- WHEN the token test suite runs
- THEN revised role values and the resolved surface, alias, and contrast invariants are checked

#### Scenario: Unapproved token drift is rejected
- GIVEN a changed token outside the explicitly authorized palette roles
- WHEN the drift guard runs
- THEN the unapproved change is rejected

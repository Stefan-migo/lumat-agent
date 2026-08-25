# Corporate Components Specification (Table / Tabs / Dialog)

## Purpose

Define the port contract for the first three Corporate-family components from the CortexDesign catalog: retarget the `.table` primitive to `--corp-*` slots, add a WAI-ARIA `Tabs` primitive (Default + Controlled), and add a `Dialog` primitive that honors the DESIGN_SYSTEM.md §Dialog disclosure contract (initial focus, focus trap, Escape, focus restore). Palette stays frozen: no token value changes, aliases only.

## Requirements

### Requirement: CORP-TABLE-1 — Table Contract Alignment

The `.table` primitive MUST consume the catalog `table` slots (`--corp-border`, `--corp-text`) for its color values, replacing the raw `--border` / `--text` references, with zero visual change (aliases resolve to the same values). The DataTable component API and its consumers MUST remain unchanged.

#### Scenario: Table resolves through aliases only

- GIVEN the applied change
- WHEN `.table` styles are inspected in `primitives.css`
- THEN border and text colors reference `--corp-border` and `--corp-text` and no raw `--border` / `--text` value appears in the table block

#### Scenario: Existing table consumers stay green

- GIVEN the current DataTable consumers (CasesList, ClientesList, KbList, ConversationsList, ClientFicha)
- WHEN the full test suite runs
- THEN all existing table assertions pass unchanged

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

A `Dialog` primitive MUST render an overlay with `role="dialog"`, `aria-modal="true"`, and the catalog `dialog` slots (`--corp-border`, `--corp-bg`, `--corp-radius`, `--corp-fg`) plus `--shadow-2`/`--shadow-3` and `--radius-md` per DESIGN_SYSTEM.md. A close control MUST carry an accessible label (`Cerrar`).

#### Scenario: Dialog renders with semantics

- GIVEN an open Dialog
- WHEN it renders
- THEN a `role="dialog"` node with `aria-modal="true"` and a close button labeled `Cerrar` exists

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

### Requirement: CORP-DIALOG-4 — No Token Value Changes

This change MUST NOT modify any token value in `tokens.css`; only alias consumption in component CSS is allowed. The drift guard (`tokens.test.ts`) MUST keep passing unchanged.

#### Scenario: Drift guard green

- GIVEN the applied change
- WHEN the token test suite runs
- THEN `tokens.test.ts` passes with no modifications to its assertions
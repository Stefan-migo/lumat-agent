# Delta for panel-design-system

## RENAMED Requirements

### Requirement: DS-TKN-2 — Additive-Only Token Evolution → DS-TKN-2 — Approved Palette Revision and Token Integrity

(Reason: the requirement now governs the approved palette revision, narrowly superseding the former additive-only byte-identical ban.)

## MODIFIED Requirements

### Requirement: DS-TKN-2 — Approved Palette Revision and Token Integrity

A specifically approved palette revision MAY change or remove prior color-token declarations only where this delta names their replacement. This narrowly supersedes the former additive-only byte-identical value ban; it does not relax DS-TKN-1. All tokens MUST remain defined in the single `:root` source in `web/src/tokens/tokens.css`; `--corp-*` aliases MUST remain indirections to canonical roles and MUST NOT duplicate raw values. Alias integrity, the no-hard-coded-color guarantee, applicable WCAG 2.2 AA contrast obligations, and the exact stability of every non-palette token MUST be preserved. Non-palette values may change only under a separately approved delta.
(Previously: every pre-existing token value had to remain byte-identical, prohibiting approved palette changes.)

#### Scenario: Approved color revision is narrowly permitted
- GIVEN a color role explicitly revised by this approved palette delta
- WHEN its canonical value changes
- THEN the change is permitted without permitting unrelated color or non-palette token changes, and single-source and alias-integrity rules remain in force

#### Scenario: Non-palette tokens remain stable
- GIVEN a token outside the palette roles explicitly named in this delta
- WHEN the revised token set is reviewed
- THEN its declaration and value remain byte-identical unless separately approved

#### Scenario: Alias and contrast guarantees remain
- GIVEN the revised token set and its `--corp-*` aliases
- WHEN alias resolution and affected foreground/background and boundary pairs are checked
- THEN aliases resolve to canonical tokens without raw values, and every affected pair has measured applicable WCAG 2.2 AA evidence

### Requirement: DS-TKN-7 — Elevation Tokens (PDW-TKN-3)

The design system MUST retain `--shadow-1`, `--shadow-2`, and `--shadow-3` tokens, with `--shadow-3` available for overlays/drawers. Cards MUST carry no material elevation shadow; `--shadow-3` MUST remain available for overlay, drawer, and dialog affordance.
(Previously: `--shadow-3` was added for overlays/drawers while the first two values remained unchanged.)

#### Scenario: Shadow tokens remain available
- GIVEN `tokens.css`
- WHEN the shadow group is inspected
- THEN `--shadow-1`, `--shadow-2`, and `--shadow-3` exist

#### Scenario: Card elevation stays flat
- GIVEN a card rendered under the final surface contract
- WHEN its elevation is inspected
- THEN it has no material shadow

#### Scenario: Overlay shadow remains available for affordance
- GIVEN an overlay, drawer, or dialog
- WHEN overlay elevation is specified
- THEN `--shadow-3` remains available for affordance

### Requirement: DS-TKN-8 — Drift Guard Stays Green (PDW-TKN-2)

`web/src/tokens/tokens.test.ts` MUST assert the exact locked palette roles in DS-TKN-13, resolved non-white surfaces, `tokens.ts` mirror equality, alias resolution/integrity, contrast measurements for affected pairs, and the no-hard-coded-hex walk. It MUST retain unchanged-value checks for non-palette tokens and MUST NOT preserve obsolete old-palette assertions as acceptance criteria.
(Previously: the guard pinned the prior palette and required all pre-existing assertions to remain.)

#### Scenario: Revised palette and guard invariants pass
- GIVEN the revised `tokens.css` and token test
- WHEN the token guard runs
- THEN exact locked values, mirror equality, alias integrity, resolved non-white surfaces, measured affected-pair contrast, and the no-hex walk are checked

#### Scenario: Non-palette drift remains rejected
- GIVEN a non-palette token changes without separate approval
- WHEN the token guard runs
- THEN the drift is rejected

### Requirement: DS-TKN-12 — Corrected Canvas Background Documentation

`web/DESIGN_SYSTEM.md` MUST document `--bg` as `#dbe1d6`, matching the canonical role in DS-TKN-13; role-based documentation/token consistency MUST be checked without relying on a source line number.
(Previously: the document recorded the former `#F1F1E8` canvas.)

#### Scenario: Documentation matches canvas token
- GIVEN the Canvas role in `DESIGN_SYSTEM.md`
- WHEN it is compared with the canonical token
- THEN it states `--bg` as `#dbe1d6`

### Requirement: DS-UI-LINK — Accessible link color

Normal-size links on light surfaces MUST use a semantic link role whose actual foreground/background pair is measured at not less than 4.5:1 under WCAG 2.2 AA. `--primary-700` MUST NOT be required solely by its former palette association; the palette alone MUST NOT be treated as contrast evidence.
(Previously: normal-size links were fixed to `--primary-700` and prohibited from using `--primary-600`.)

#### Scenario: Customer link contrast is measured
- GIVEN a ClientesList customer-name link on its actual light surface
- WHEN its foreground/background contrast is measured
- THEN the semantic link role is at least 4.5:1, or the failing pair is explicitly recorded as unresolved with its measured ratio and authority

#### Scenario: Palette is not treated as proof
- GIVEN a proposed link role and the locked palette values
- WHEN compliance is evaluated
- THEN the actual rendered pair is measured rather than inferred from palette membership

### Requirement: DS-RESP-1 — Mobile-First Shell Tiers

The shell MUST support tiers `<640`, `640–1023`, `1024–1279`, and `≥1280` (reference values 640/1024/1280). Drawer/rail controls MUST provide at least 44px touch targets; an open modal drawer MUST contain and restore focus, make background interaction inert, lock page scroll, reconcile on resize, and honor reduced motion. Content MUST retain usable overflow rather than clip critical actions.
(Previously: the tier contract specified the earlier shell layout without the final responsive navigation surfaces.)

#### Scenario: Drawer interaction
- GIVEN a narrow or intermediate viewport with the overlay drawer open
- WHEN keyboard, Escape, outside interaction, or resize occurs
- THEN focus and visibility remain contained, background interaction is inert, scroll is locked, and focus returns on close

#### Scenario: Tier review
- GIVEN shell stories at 390/640/768/1024/1280px
- WHEN each tier renders
- THEN navigation, header actions, and content remain reachable with no critical clipping

### Requirement: DS-SHELL-1 — Collapse Toggle Sizing and Placement

The desktop sidebar collapse toggle MUST remain operable in expanded and collapsed states, have a visible focus indicator and an adequately sized hit target, and stay anchored within the sidebar. Its hover/focus styling MUST use semantic tokens and MUST NOT assume a palette-specific `--primary-700` value.
(Previously: fixed 32–36px visual sizing, ≥40px hit target, and palette-specific lime focus/primary hover were prescribed.)

#### Scenario: Toggle remains reachable
- GIVEN the desktop sidebar in either state
- WHEN the collapse toggle is rendered and keyboard-focused
- THEN it remains within the sidebar, operable, and visibly focused

### Requirement: DS-SHELL-2 — Sidebar Hover Containment

Desktop sidebar navigation paint MUST remain within its allocated expanded or collapsed sidebar region; long labels, hover, and current-route states MUST NOT cause critical content or controls to become unreachable.
(Previously: fixed 192px/96px columns and specific overflow CSS declarations were mandated.)

#### Scenario: Hover and current route remain contained
- GIVEN an expanded or collapsed desktop sidebar
- WHEN a long navigation label is hovered or marked current
- THEN its visual state remains contained and the navigation remains usable

### Requirement: DS-SHELL-3 — Tokenized Shell Styles Without Injection (Slice 2)

Shell layout, navigation, drawer, focus, motion, and responsive styles MUST consume semantic design tokens or `--corp-*` aliases, MUST contain no hard-coded hex values, and MUST use the shared tokenized stylesheet boundary. PanelShell MUST NOT inject component-owned `<style>` content. The shell MUST satisfy DS-SHELL-8 and DS-RESP-1; this requirement does not freeze prior shell appearance or responsive behavior.
(Previously: existing shell visual and responsive behavior was required to remain unchanged.)

#### Scenario: Stylesheet boundary is tokenized
- GIVEN PanelShell is rendered
- WHEN its DOM and source are inspected
- THEN no shell-owned injected `<style>` exists and shell values resolve through tokens

#### Scenario: Responsive surfaces use shared styles
- GIVEN desktop, tablet, and mobile shell states
- WHEN navigation and drawer styles are inspected
- THEN the DS-SHELL-8 surfaces use the shared tokenized stylesheet boundary

### Requirement: DS-SHELL-4 — Primitive Reuse

The panel header status-badge slot MUST reuse `Badge` where applicable, and the user avatar MUST reuse `Avatar`. Shell regions MAY use additional existing production primitives where their contracts apply; they MUST NOT duplicate an existing primitive's behavior.
(Previously: no new primitive was allowed in the prior shell slice.)

#### Scenario: Shared badge and avatar remain reused
- GIVEN the header badge and user avatar render
- WHEN their component ownership is inspected
- THEN the existing `Badge` and `Avatar` contracts are reused

### Requirement: DS-SHELL-6 — Coherent Tokenized Chrome

Shell icons MUST remain semantically distinct and use the existing icon contract without adding a dependency. PanelShell and PageHeader MUST consume design tokens or `--corp-*` aliases, preserve the PWA boundary, and provide the DS-SHELL-8 chrome surfaces. Dark chrome MUST NOT be represented as dark mode.
(Previously: tokenized shell styles and PWA boundary were required, without the final surface contract.)

#### Scenario: Shell chrome remains tokenized and light-system based
- GIVEN the shell source and rendered states
- WHEN styles and theme behavior are inspected
- THEN styles resolve through tokens, no new icon dependency or PWA change exists, and dark chrome is not a dark-mode theme

#### Scenario: Shell destinations retain existing authority
- GIVEN the shell at any supported responsive tier
- WHEN destination visibility and role filtering are evaluated
- THEN they derive from `NAVIGATION` in `PanelShell.tsx` and `panelRoutes` / `pathForRoute()` in `panelRoutes.ts`, without an invented route or parallel navigation model

### Requirement: DS-CC-5 — Accessibility and Primitive Reuse

The surface MUST reuse existing primitives and semantic tokens, add no dependency, and support keyboard operation, visible focus, 200% zoom reflow, reduced motion, and non-color-only state communication. Every contrast pair introduced or revised by this change MUST be measured against its applicable WCAG 2.2 AA threshold; the locked palette alone MUST NOT be asserted as evidence. A pair that fails or cannot be verified MUST be recorded with its measured ratio (or explicit unmeasured status), threshold, and authority; it MUST NOT be silently dropped or claimed compliant.
(Previously: token values could not change in this change, so inherited pairs were attributed as pre-existing debt rather than remediated.)

#### Scenario: Keyboard and responsive accessibility
- GIVEN a user operates the assistant by keyboard, at 200% zoom, or with reduced motion enabled
- WHEN history, context, planning, composer, approval, or retry is used
- THEN focus remains visible and ordered, actions reflow without loss, and motion is reduced without removing meaning

#### Scenario: Revised contrast pairs have measured evidence
- GIVEN a state or action whose foreground, surface, or boundary role is revised
- WHEN its actual rendered pair is evaluated
- THEN its ratio is measured against the applicable WCAG 2.2 AA threshold and any failure or missing evidence is explicitly recorded

#### Scenario: Inherited contrast debt is recorded
- GIVEN a reused pair whose token value is not revised by this change and whose contrast is not verified
- WHEN contrast is reviewed
- THEN the pair, ratio or unmeasured status, and threshold are recorded in `contrast-verification.md` without a claim of compliance

## ADDED Requirements

### Requirement: DS-TKN-13 — Final Palette Revision

The panel MUST define the following exact canonical role values in its single token source: chrome `--chrome-950: #012f1d`, `--chrome-900: #073d2b`, `--chrome-active: #012214`; `--bg: #dbe1d6`, `--header-bg: #dee4db`, `--surface: #e8ebe4`, `--border: #d5dad1`; lime `--lime-500: #c6d529`, `--lime-600: #d3e41d`, `--lime-700: #a2c312`; teal `--teal-500: #52babb`, `--teal-400: #6adbdf`; text `--text: #111a2e`, `--text-muted: #5a6469`, `--text-on-dark: #e9f0e9`, `--text-on-dark-2: #88a599`. Pure white MUST NOT be used as any resolved surface value, including aliases or derived surface values. Every actual foreground/background and applicable non-text boundary pair introduced or revised MUST have measured contrast against its applicable WCAG 2.2 AA threshold; palette values alone MUST NEVER be asserted as proof. `--text-muted` MUST meet at least 4.5:1 against `--bg`, `--surface`, and `--header-bg` (measured 4.55:1, 5.04:1, 4.69:1). `--text-on-dark-2` MUST meet at least 4.5:1 against `--chrome-900` as the lightest chrome surface, and against `--chrome-950` and `--chrome-active` (measured 4.61:1, 5.53:1, 6.36:1). The `--warning` foreground MUST meet at least 4.5:1 against `--bg`, `--surface`, and `--warning-bg` (measured 4.58:1, 5.07:1, 5.48:1). `--border` is a decorative container hairline and MUST NOT be the sole boundary of an interactive control; control boundaries MUST resolve through `--border-strong`, which meets at least 3:1 against `--surface` (measured 3.09:1) and MUST NOT be relied on against `--bg` (2.79:1). The `--lime-700` title accent rule is decorative non-text. Semantic status badge borders are decorative reinforcement and MUST NOT be the only channel conveying status. Inter remains the typography direction. Dark shell chrome is not dark mode; dark mode remains a non-goal. `--primary-*` action/brand semantics MUST NOT be silently repurposed as chrome or lime roles.

#### Scenario: Exact palette is present
- GIVEN the canonical tokens
- WHEN the locked roles are inspected
- THEN every role has exactly the value specified in this requirement

#### Scenario: Resolved surfaces exclude pure white
- GIVEN canonical, aliased, and derived surface roles
- WHEN their resolved colors are evaluated
- THEN none resolves to pure white

#### Scenario: Contrast is measured for actual pairs
- GIVEN an actual text or non-text pair introduced or revised by the palette
- WHEN its contrast is evaluated
- THEN its ratio is measured against the applicable WCAG 2.2 AA threshold and not inferred from the palette alone

#### Scenario: Chrome is not a theme switch
- GIVEN dark-green shell chrome over light application surfaces
- WHEN theme behavior is described
- THEN the system remains light and does not claim to implement dark mode

#### Scenario: Adjusted tokens meet their measured thresholds
- GIVEN the adjusted `--text-muted`, `--text-on-dark-2`, and `--warning` values
- WHEN each is evaluated against every surface it is used on
- THEN each meets its applicable WCAG 2.2 AA threshold, and decorative-only pairs are identified as decorative rather than silently accepted

### Requirement: DS-SURFACE-1 — Flat Sage Surface Separation

Cards MUST use the light system surface, approximately 10px radius at the reference scale, and a hairline boundary with essentially no material shadow. Dialogs MUST use approximately 14px radius at their reference scale. Radius MUST use the existing global `--radius-*` token scale with values tuned so cards resolve to approximately 10px and dialogs to approximately 14px; no new semantic radius alias taxonomy is introduced. Cards carry no material shadow; overlays and dialogs may use `--shadow-3` for affordance.

#### Scenario: Card separation is flat
- GIVEN a card on the light panel canvas
- WHEN its shape and elevation are inspected
- THEN it uses the light surface, approximately 10px radius, hairline separation, and essentially no shadow

#### Scenario: Dialog geometry is distinct
- GIVEN a dialog at its reference scale
- WHEN its radius is inspected
- THEN it is approximately 14px and uses a non-white surface

#### Scenario: Resolved radius and overlay elevation are applied
- GIVEN the owner resolved the global radius scale and overlay shadow on 2026-09-30
- WHEN the design is specified
- THEN the existing `--radius-*` scale is tuned to the specified geometry and overlays/dialogs may use `--shadow-3` for affordance

### Requirement: DS-SHELL-8 — Responsive Lumat Shell Surfaces

The panel shell MUST expose these responsive surfaces at requirement level: desktop expanded and collapsed sidebar with in-sidebar search, grouped navigation, and user footer; desktop top header with back control, breadcrumb, notification bell, avatar/account control, and chevron; dark mobile header; five-destination mobile bottom tab bar; tablet icon rail; and an overlay drawer for applicable mobile/tablet navigation. Every destination and role-filtering decision MUST derive from the existing navigation authority (`NAVIGATION` in `PanelShell.tsx`, and `panelRoutes` / `pathForRoute()` in `panelRoutes.ts`). The shell MUST NOT invent destinations or routes or establish a parallel navigation model. The five primary mobile tab destinations MUST be Panel, Conversaciones, Asistente, Agenda, and Clientes; every other authorized destination MUST remain reachable through the overlay drawer. The shell MUST render the committed brand assets `web/public/brand/lumat-logo.png` (horizontal lockup) and `web/public/brand/lumat-mark.png` (mark); this change produces no new asset and requires no placeholder. Dark shell chrome MUST NOT imply dark mode.

#### Scenario: Desktop shell surfaces are present
- GIVEN the shell at a desktop tier
- WHEN expanded and collapsed states are rendered
- THEN the sidebar provides in-sidebar search, grouped navigation, and user footer, and the top header provides back, breadcrumb, notification, avatar/account, and chevron controls

#### Scenario: Tablet navigation surface is usable
- GIVEN the shell at a tablet tier
- WHEN the navigation is rendered and the drawer is opened
- THEN an icon rail and overlay drawer expose only authorized existing destinations with accessible names

#### Scenario: Mobile navigation surfaces are present
- GIVEN the shell at a mobile tier
- WHEN the page is rendered
- THEN a dark header and a bottom tab bar with the five destinations Panel, Conversaciones, Asistente, Agenda, and Clientes are present, and the applicable overlay drawer is available without inventing route entries

#### Scenario: Navigation and role filtering use existing authority
- GIVEN a role and current route
- WHEN shell destinations are derived at any tier
- THEN visibility and route targets derive from `NAVIGATION`, `panelRoutes`, and `pathForRoute()` only

#### Scenario: Resolved destinations and brand assets are used
- GIVEN the owner resolved the tab destinations and confirmed the committed brand assets on 2026-09-30
- WHEN shell acceptance is described
- THEN the five named destinations and the committed logo assets are used, and dark chrome is not called dark mode

### Requirement: DS-DASH-3 — Dashboard as Palette Consumer

The Dashboard MUST consume the revised semantic design roles at desktop, tablet, and mobile widths while preserving its existing data, permissions, and dense control-room physiology under DS-GRAMMAR-1. Its actual text, accent, surface, and boundary pairs introduced or revised by this change MUST be measured against applicable WCAG 2.2 AA thresholds; neither the palette nor a static layout claim is contrast evidence. The unified panel Dashboard MUST NOT expose "Casos" as a quick-access destination, shortcut, or card; this is an explicit owner override of the design references, which do show it. The Casos queue remains reachable through its existing separate surface.

#### Scenario: Dashboard adapts without changing its product contract
- GIVEN the Dashboard at desktop, tablet, and mobile widths
- WHEN it renders using the revised design system
- THEN its data and permission behavior remain unchanged, dense control-room content remains intact, and content/actions remain reachable

#### Scenario: Dashboard contrast uses measured pairs
- GIVEN a Dashboard text, accent, surface, or boundary pair revised by this change
- WHEN the rendered pair is evaluated
- THEN its contrast is measured against the applicable WCAG 2.2 AA threshold and any failure or missing evidence is recorded explicitly

#### Scenario: Casos is absent from the unified dashboard
- GIVEN the unified panel Dashboard at any of desktop, tablet, or mobile widths
- WHEN the quick-access destinations are rendered
- THEN no "Casos" destination, shortcut, or card is present, and the Casos queue remains reachable through its existing separate surface

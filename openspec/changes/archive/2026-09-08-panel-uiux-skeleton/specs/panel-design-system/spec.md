# Delta for panel-design-system

## MODIFIED Requirements

### Requirement: DS-UI-LOGIN — Lockup and Spanish auth

Login MUST preserve the full Lumat lockup, `Usuario`/`Contraseña`/`Iniciar sesión`, username-preserving non-destructive errors, and existence-safe authentication. It MUST render a tokenized two-region brand/welcome and form frame on desktop and stack those regions on mobile; it MUST NOT depend on the phantom `card--auth` class or introduce a new styling dependency.
(Previously: login required the lockup and auth copy but had a centered, unframed layout.)

#### Scenario: Responsive login frame
- GIVEN the login is rendered at desktop and mobile widths
- WHEN the viewport crosses the mobile breakpoint
- THEN desktop shows two regions and mobile shows brand above the form without clipped controls.

#### Scenario: Failed login remains safe
- GIVEN a failed login with a valid username
- WHEN the inline error renders
- THEN the username persists and no account-existence information appears.

## ADDED Requirements

### Requirement: DS-RESP-1 — Mobile-First Shell Tiers

Shell layout MUST use the design-system tiers `<640`, `640–1023`, `1024–1279`, and `≥1280` (reference values 640/1024/1280). Drawer/rail controls MUST provide at least 44px touch targets, trap and return focus while open, make the background inert, lock page scroll, reconcile on resize, and honor reduced motion. Content MUST retain usable overflow rather than clip critical actions.

#### Scenario: Drawer interaction
- GIVEN a narrow or intermediate viewport with the drawer open
- WHEN keyboard, Escape, outside interaction, or resize occurs
- THEN focus and visibility remain contained, background interaction is inert, scroll is locked, and focus returns on close.

#### Scenario: Tier review
- GIVEN shell stories at 390/640/768/1024/1280px
- WHEN each tier renders
- THEN navigation, header actions, and content remain reachable with no critical clipping.

### Requirement: DS-SHELL-6 — Coherent Tokenized Chrome

Shell icons MUST be semantically distinct and inline/native with no new dependency. PanelShell, PageHeader, and login frame styles MUST consume existing tokens or `--corp-*` aliases, remove the phantom auth class, and preserve the PWA boundary.

#### Scenario: Source review
- GIVEN the shell and login diff
- WHEN dependencies, classes, and styles are inspected
- THEN no icon library, `card--auth`, hard-coded color, or PWA architecture change appears.

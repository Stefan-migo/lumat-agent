# Panel Design System Specification

## Purpose

Provide the foundation of a professional, standard design system for the Lumat agent-facing panel (`web/`, package `lumat-panel`): a complete, single-source token set in `web/src/tokens/tokens.css`, a Tokens reference page in Storybook, and doc-level stories (description + usage guidance, interactive controls, variant matrix, a11y notes) for all 10 existing story files. Foundation-first: domain patterns, dark mode, dynamic theming, new components, component code changes, and the backend are explicit non-goals of this slice — later slices consume this foundation.

## Requirements

### Requirement: DS-TKN-1 — Single Token Source (PDW-TKN-1)

The panel design system MUST declare all design tokens as CSS custom properties in the single `:root` block of `web/src/tokens/tokens.css`, and MUST NOT hard-code color hex values outside `tokens.css` anywhere under `web/src`.
(Previously: covered `tokens.css` and consuming components; now explicitly including the `--corp-*` alias layer added by `corp-token-aliases`.)

#### Scenario: Components consume tokens

- GIVEN a component or story needs a color or spacing value
- WHEN it is implemented
- THEN it references a `var(--*)` custom property from `tokens.css` and no hex color literal appears in component or story source

#### Scenario: Alias layer is single-source

- GIVEN the `--corp-*` alias blocks in `tokens.css`
- WHEN they are implemented
- THEN they reference existing `var(--*)` tokens (never raw hex), preserving the single token source

### Requirement: DS-TKN-2 — Additive-Only Token Evolution

The token set in `tokens.css` MUST evolve additively: every custom property that exists before this change MUST keep its exact value byte-identical, and new tokens MUST be appended without modifying or removing any pre-existing declaration.

#### Scenario: Pre-existing palette is pinned

- GIVEN the pre-change `tokens.css`
- WHEN the foundation tokens are added
- THEN each pre-existing `--*` declaration keeps its exact value and the spot-checked palette (brand `#143c2c`, background `#f4f5f7`, text `#1a202c`, radii `6px`/`8px`) is unchanged

### Requirement: DS-TKN-3 — Typography Scale (PDW-TKN-3)

The type system MUST extend the existing `--text-*` scale with `--text-xs`, `--text-base`, `--text-xl`, and `--text-3xl` as static rem values (no fluid `clamp()` in this slice), MUST add line-height tokens (`--leading-*`) and font-weight tokens (`--weight-*`), and MUST keep the `system-ui` font stack (`--font-sans`).

#### Scenario: Full scale available

- GIVEN the Tokens page or `tokens.css`
- WHEN the type group is inspected
- THEN `--text-xs`, `--text-base`, `--text-xl`, `--text-3xl`, `--leading-*`, and `--weight-*` exist alongside the pre-existing `--text-sm`/`--text-md`/`--text-lg`/`--text-2xl` tokens

#### Scenario: Static rem, no fluid type

- GIVEN the type tokens
- WHEN their values are inspected
- THEN all values are static rem and no `clamp()` appears in the type scale

### Requirement: DS-TKN-4 — Focus-Ring Token Set (PDW-TKN-3)

The design system MUST provide one composable focus-visible indicator set: `--focus-ring` (color), `--focus-ring-width`, and `--focus-ring-offset`, for use by all interactive primitives.

#### Scenario: Focus tokens available

- GIVEN `tokens.css` or the Tokens page
- WHEN the focus group is inspected
- THEN all three `--focus-ring*` custom properties exist with non-empty values

#### Scenario: Focus ring uses tokens

- GIVEN an interactive component shows a focus-visible outline
- WHEN the outline is styled
- THEN it uses the `--focus-ring*` tokens rather than hard-coded color, width, or offset values

### Requirement: DS-TKN-5 — Motion Tokens (PDW-TKN-3)

The design system MUST provide a minimal motion scale: a `--duration-*` group with three steps at 100 ms, 150 ms, and 250 ms, plus two `--ease-*` tokens.

#### Scenario: Motion scale rendered

- GIVEN the Tokens page
- WHEN the motion group is rendered
- THEN three `--duration-*` tokens (100/150/250 ms) and two `--ease-*` tokens are listed

### Requirement: DS-TKN-6 — Breakpoint Tokens (PDW-TKN-3)

The design system MUST provide reference breakpoint tokens `--bp-sm` (640 px), `--bp-md` (1024 px), and `--bp-lg` (1280 px) on a desktop-first scale, and MUST NOT wire them into layout code in this slice.

#### Scenario: Reference values present

- GIVEN `tokens.css`
- WHEN the breakpoint group is inspected
- THEN `--bp-sm`, `--bp-md`, and `--bp-lg` exist with the reference values 640 px, 1024 px, and 1280 px

#### Scenario: Not consumed by layout yet

- GIVEN the applied change
- WHEN the diff is reviewed
- THEN no layout component consumes the `--bp-*` tokens (Storybook viewports + reference only in this slice)

### Requirement: DS-TKN-7 — Elevation Tokens (PDW-TKN-3)

The design system MUST add `--shadow-3` for overlays/drawers while keeping `--shadow-1` and `--shadow-2` unchanged.

#### Scenario: Shadow scale extended

- GIVEN `tokens.css`
- WHEN the shadow group is inspected
- THEN `--shadow-3` exists and `--shadow-1`/`--shadow-2` values are byte-identical to their pre-change values

### Requirement: DS-TKN-8 — Drift Guard Stays Green (PDW-TKN-2)

`web/src/tokens/tokens.test.ts` MUST keep the drift-guard green after the token additions: the pinned palette spot-checks (brand `#143c2c`, background `#f4f5f7`, text `#1a202c`, radii `6px`/`8px`), the `tokens.ts` mirror equality checks, and the no-hard-coded-hex walk MUST all keep passing, and the suite SHOULD add spot-checks for the new token groups (type, focus, motion, breakpoints, `--shadow-3`) without removing any existing assertion.

#### Scenario: Guard passes after additions

- GIVEN the extended `tokens.css` and `tokens.test.ts`
- WHEN `npm test` runs in `web/`
- THEN the drift-guard spec passes including pinned palette spot-checks, mirror equality, and the no-hard-coded-hex walk

#### Scenario: New groups pinned

- GIVEN the new token groups
- WHEN the guard is extended
- THEN spot-checks cover the new groups (e.g. breakpoint and duration values) and no existing assertion is removed

### Requirement: DS-TKN-9 — tokens.ts Mirror Constraint

`web/src/tokens/tokens.ts` MUST NOT gain new JS exports in this slice; it MUST continue to mirror only the JS-consumed subset (spacing, radius, zIndex) and MUST remain drift-equal to `tokens.css` (PDW-TKN-2).

#### Scenario: Export surface unchanged

- GIVEN the applied change
- WHEN `tokens.ts` is reviewed
- THEN its export surface (spacing, radius, zIndex) is unchanged and the mirror equality test passes

### Requirement: DS-TOKENS-1 — Tokens Reference Page

The design system MUST provide a Tokens page as a CSF story at `web/src/stories/tokens/Tokens.stories.tsx` that renders token groups (colors, typography, spacing, radius, shadows, motion, focus) by parsing `tokens.css?raw` with a custom render, without duplicating token values in the story source and without adding dependencies.

#### Scenario: Groups render from the single source

- GIVEN the Tokens page opens in Storybook
- WHEN it renders
- THEN the color, typography, spacing, radius, shadow, motion, and focus groups are displayed with values read from `tokens.css`

#### Scenario: No duplication

- GIVEN a token value changes in `tokens.css`
- WHEN the Tokens page re-renders
- THEN the displayed value reflects `tokens.css` without any story-side value edit

### Requirement: DS-TOKENS-2 — Readable in the Static Build

The Tokens page MUST be present and render correctly in the static Storybook build: `npm run build-storybook` MUST succeed and the built output MUST include the Tokens page.

#### Scenario: Static build renders Tokens page

- GIVEN `npm run build-storybook` completes without errors
- WHEN the built Storybook is served
- THEN the Tokens page is present and renders its token groups

### Requirement: DS-STORY-1 — Doc-Level Coverage for All Stories (PDW-CMP-2)

All 10 existing story files MUST be doc-level: `primitives/Avatar`, `primitives/Badge`, `primitives/Button`, `primitives/Card`, `primitives/Input`, `primitives/SearchInput`, `primitives/Select`, `primitives/StatusBadge`, `primitives/Textarea`, and `domain/AppShell`. Each MUST provide a component description, usage guidance, interactive controls where meaningful, a variant matrix story, and accessibility notes, while preserving its existing named stories and their args.

#### Scenario: Every docs page is complete

- GIVEN a reviewer opens any of the 10 docs pages
- WHEN they view the page
- THEN description, usage guidance, a11y notes, and a matrix story are present

#### Scenario: Existing stories preserved

- GIVEN the pre-change stories (e.g. Button Primary/Secondary/Link/Disabled, AppShell Admin/Operador)
- WHEN the doc-level upgrade is applied
- THEN those named stories still exist and render with their pre-change args

### Requirement: DS-STORY-2 — Description and Usage Guidance (PDW-CMP-2)

Each of the 10 docs pages MUST include a terse component description and usage guidance stating when the component should and should not be used.

#### Scenario: Guidance visible

- GIVEN a docs page
- WHEN it is read
- THEN it states the component's purpose and usage guidance

#### Scenario: Shell docs reference the contract

- GIVEN the `AppShell` docs after the port
- WHEN brand/styling references are read
- THEN they describe the shell as consuming `--corp-*` slots, no hardcoded v1 token values

### Requirement: DS-STORY-3 — Interactive Controls (PDW-CMP-2)

Where meaningful, each of the 10 docs pages MUST expose argTypes controls (e.g. variant, size, disabled, placeholder, label, options) so stories are interactive in the Storybook UI.

#### Scenario: Controls drive the story

- GIVEN a story with meaningful props
- WHEN a user edits a control in the Storybook UI
- THEN the rendered component updates accordingly

### Requirement: DS-STORY-4 — Variant Matrix Story (PDW-CMP-2)

Each of the 10 docs pages MUST include a variant matrix story rendering all variants in a single grid using a local helper, with no new component and no new dependency.

#### Scenario: Matrix rendered

- GIVEN a docs page
- WHEN the matrix story is opened
- THEN all variants of the component render in one grid view

### Requirement: DS-STORY-5 — Accessibility Notes (PDW-CMP-2)

Each of the 10 docs pages MUST include accessibility notes covering focus-ring visibility (referencing the `--focus-ring*` tokens), label requirements, and color-contrast expectations.

#### Scenario: A11y notes present

- GIVEN a docs page
- WHEN the accessibility section is read
- THEN it covers focus indication, labeling, and contrast expectations

### Requirement: DS-STORY-6 — Autodocs Enabled (PDW-CMP-1)

Storybook MUST enable autodocs (`docs.autodocs: true` in `web/.storybook/preview.ts`, per-meta tags only where needed), and the `main.ts` stories glob `../src/stories/**/*.stories.tsx` MUST stay unchanged so the Tokens page and all 10 stories are discovered by the existing glob.

#### Scenario: Autodocs without MDX

- GIVEN a story file without an MDX companion
- WHEN its docs page opens
- THEN autodocs renders the args table and controls

#### Scenario: Glob unchanged

- GIVEN the applied change
- WHEN `web/.storybook/main.ts` is reviewed
- THEN the stories glob is unchanged

### Requirement: DS-SHELL-7 — Real Storybook Shell Harness

Storybook MUST apply shared `withPanelShell` context and `primitives.css` to every story.

#### Scenario: Production

- GIVEN a story
- WHEN rendered
- THEN both apply

#### Scenario: Shared

- GIVEN stories
- WHEN preview is inspected
- THEN no local shell or duplicate import

### Requirement: DS-DOC-1 — Platform-First Interaction Policy

`DESIGN_SYSTEM.md` MUST record platform-first popover/CSS anchors/native dialog; Radix only for menu/combobox ARIA composites; package names; and line-480 justification.

#### Scenario: Documented

- GIVEN the document
- WHEN read
- THEN defaults, scope, packages, justification appear

#### Scenario: Platform

- GIVEN a platform-covered interaction
- WHEN reviewed
- THEN platform precedes Radix

### Requirement: DS-STORY-7 — Viewports Aligned to Breakpoints

Presets MUST align to `--bp-*`: 640px, 1024px, and 1280px. A test MUST detect drift without excluding other widths.

#### Scenario: Viewport presets

- GIVEN the Storybook viewport toolbar
- WHEN a viewport preset is selected
- THEN the preset matches one of the `--bp-*` reference values

#### Scenario: Drift rejected

- GIVEN a preset or token changes
- WHEN tested
- THEN drift fails; 390px and 768px remain permitted

### Requirement: DS-VER-1 — Web Verification Gates

The change MUST keep `npm test` green in `web/` (all existing and updated tests, including the token drift-guard and no-hard-coded-hex walk) and MUST keep `npm run build-storybook` green, and the diff MUST NOT modify backend (`app/`, `db/`, `infra/`) or component-code files.

#### Scenario: Test suite green

- GIVEN the applied change
- WHEN `npm test` runs in `web/`
- THEN all tests pass, including the token drift-guard

#### Scenario: Storybook build green

- GIVEN the applied change
- WHEN `npm run build-storybook` runs
- THEN the build completes without errors

#### Scenario: Web-only diff

- GIVEN the change diff
- WHEN it is reviewed
- THEN it touches only `web/` files (tokens, Storybook config, stories) and no `app/`, `db/`, or `infra/` files

---

## Page-First Storybook Workflow (R-PRD-PG-1..7) — added 2026-08-19

### Requirement: R-PRD-PG-1 — Page Stories

CSF page stories MUST exist at `web/src/stories/pages/*.stories.tsx` for Dashboard, Clientes list/ficha, Conversations list/thread, Cases, KB, Settings, and Login, composed from shared patterns. The page-story restriction applies only to `web/src/stories/pages/**`; harness, primitive, and closure work MAY modify components. Triage MUST delete `concept/AiAgentGrammar`, quarantine `pages/ChatWithAgent`, and document `pages/InboxThread`.

#### Scenario: Glob unchanged

- GIVEN `main.ts`
- WHEN reviewed
- THEN the glob is unchanged

#### Scenario: Scope

- GIVEN page-story-only diff
- WHEN reviewed
- THEN no component changes

#### Scenario: Triage

- GIVEN targeted stories
- WHEN inspected
- THEN grammar absent, ChatWithAgent quarantined, InboxThread disposed

### Requirement: R-PRD-PG-2 — Production Helper Boundary (Slice 2)

The helper closure MUST include EmptyState, DataTable, PageHeader, StatCard, PageFrame, StateMessage, and toneMaps under components. Production pages MUST import components, not stories. The boundary test MUST permit only two compatibility tests to import wrappers.

#### Scenario: Component imports
- GIVEN production imports a helper
- WHEN scanned
- THEN it resolves from components

#### Scenario: Compatibility
- GIVEN a story imports a wrapper
- WHEN the suite runs
- THEN the export remains available and renders the same contract

#### Scenario: Boundary

- GIVEN either compatibility test imports a wrapper
- WHEN tested
- THEN it passes; production imports fail

#### Scenario: Closure
- GIVEN production uses a closure helper
- WHEN inspected
- THEN it is in the closure

### Requirement: R-PRD-PG-3 — Typed Mocks

The change MUST provide per-page mocks at `web/src/stories/pages/_shared/mockData/{dashboard,clients,cases,kb,settings,conversations}.ts`, typed against `web/src/types.ts` and matching serializer shapes.

#### Scenario: Typechecks

- GIVEN `web/src/types.ts`
- WHEN typecheck runs
- THEN mocks conform to `Kpis`, `Customer`, `Case`, `Doc`, `Settings`, `Conversation`

#### Scenario: Shape fidelity

- GIVEN serializer shapes in `app/panel/api/serializers.py`
- WHEN a mock is compared
- THEN field names and types match (snake_case, ISO dates, nullables)

#### Scenario: Per-page isolation

- GIVEN `_shared/mockData/`
- WHEN a page mock is loaded
- THEN it imports only its own mock module, no cross-page coupling

### Requirement: R-PRD-PG-4 — Tests Green

The change MUST keep `npm test` (vitest) green in `web/`, including story-helper tests.

#### Scenario: Suite green

- GIVEN the applied change
- WHEN `npm test` runs in `web/`
- THEN all tests pass, including helper and tone-map specs

### Requirement: R-PRD-PG-5 — Storybook Build Green

The change MUST keep `build-storybook` green, and the built index MUST include all 8 pages and Login.

#### Scenario: Build green

- GIVEN the applied change
- WHEN `npm run build-storybook` runs
- THEN it completes without errors

#### Scenario: Pages present

- GIVEN the built Storybook
- WHEN its navigation is inspected
- THEN all 9 page stories appear in the index
### Requirement: R-PRD-PG-6 — Page Content Fidelity

Each page story MUST render its Jinja authority fields: Dashboard (3 KPIs + Motivos + window caption); Clientes list (search + export CSV + table); ficha (customer card + state form + notes + history); thread (header + messages + no-reply note); Cases (table + inline update + acknowledge); KB (add-doc + docs table + disable/restore); Settings (6 form cards + spend snapshot); Conversations list (from `Customer`/`Conversation` types).

#### Scenario: Dashboard and lists fields render

- GIVEN the Dashboard and ClientesList stories
- WHEN they render
- THEN KPI cards, Motivos, window caption, search, export CSV, and the customer table appear

#### Scenario: Drill-down fields render

- GIVEN the ficha and thread stories
- WHEN they render
- THEN customer card, state form, notes, history, message table, and no-reply note appear

#### Scenario: Remaining pages render

- GIVEN the Cases, KB, Settings, and ConversationsList stories
- WHEN they render
- THEN their required fields appear

### Requirement: R-PRD-PG-7 — StatusBadge/Case Tone Maps

The change MUST define tone maps for Case statuses (abierto/escalado/en_evaluacion/cerrado) and Customer states (nuevo/activo/inactivo/bloqueado) to `Badge` tones; a test MUST assert the map covers every status.

#### Scenario: Map covers every status

- GIVEN the tone-map module in `_shared/`
- WHEN a test iterates all Case statuses and Customer states from `types.ts`
- THEN each maps to a valid `Badge` tone, none unmapped

### Requirement: R-PRD-PG-14 — Conversation State Domain

`Conversation.state` SHALL be constrained to the `bot|human|closed` domain in every story mock and related rendering. The shipped H1 mock's invalid `"open"` value SHALL NOT recur (R1); `Conversation.state` in `types.ts` remains a plain `string` (typecheck-safe, no type change), so the domain is enforced by mock values and tests. This aligns with the shipped `StatusBadge` `Status` subset (`bot|human|closed`) and its tone map (S1, S2).

#### Scenario: Mock domain is valid

- GIVEN all `Conversation` mock rows under `_shared/mockData/conversations.ts`
- WHEN the test iterates every `state` value
- THEN each is exactly `bot`, `human`, or `closed`, and no `"open"` value appears

#### Scenario: StatusBadge renders every domain state

- GIVEN a mock conversation in any of the three states
- WHEN its state renders through `StatusBadge`
- THEN it maps to the `bot`/`human`/`closed` tone as defined by `statusTone` (neutral/warning/success)

---

## Storybook Redesign — added 2026-08-20

### Requirement: DS-UI-LABELS — Approved Spanish status labels

`StatusBadge` and `toneMaps` MUST map raw conversation/customer/case/KB states to approved Spanish labels: `Agente atendiendo`/`Atención humana`/`Cerrada`; `Nuevo`/`Activo`/`Inactivo`/`Bloqueado`; `Abierto`/`En evaluación`/`Escalado`/`Cerrado`; `Activo`/`Deshabilitado`/`Procesando`/`Error`. Raw values MUST NOT appear on non-technical views; `category=mode`/provider/model MUST stay separated from ordinary controls.

#### Scenario: List renders approved state

- GIVEN a story renders a conversation state
- WHEN the label renders
- THEN it is approved Spanish, never raw `bot`/`human`/`closed`

#### Scenario: Map covers every domain state

- GIVEN a test iterating all `types.ts` states
- WHEN each resolves through the maps
- THEN every state gets a tone and a non-empty label

### Requirement: DS-UI-LINK — Accessible link color

Normal-size links on light surfaces MUST use `--primary-700` and MUST NOT use `--primary-600`.

#### Scenario: Customer link passes contrast

- GIVEN a ClientesList customer-name link
- WHEN its color is measured
- THEN it is `--primary-700` at ≥4.5:1

### Requirement: DS-UI-FRAME — Shared page shell and banner language

A shared titlebar shell (lime rail + forest tint) and `StateMessage` MUST be promoted into `_shared/` and consumed by all 9 old page stories. Loading/empty/stale/partial-error/fatal-error banners MUST pair a semantic color with a visible label and `role="status"|"alert"`, never color alone.

#### Scenario: Banners announce meaning

- GIVEN an error or stale state
- WHEN a banner renders
- THEN it pairs a visible label, semantic color, and `role="alert"|"status"`

#### Scenario: Dashboard unchanged

- GIVEN the shared frame is adopted
- WHEN Dashboard renders
- THEN its proven look and tests stay green

### Requirement: DS-UI-STATES — Complete domain-state matrix

Each page MUST cover the states relevant to its workflow: lists (loading/empty/stale/error/permission), KB (processing/error/disable-confirmation), Settings (saved/saving/validation/server-error/stale), Login (error preserves username), Ficha (saving/validation/disabled).

#### Scenario: Workflow matrix renders

- GIVEN a list, Settings, KB, Ficha, or Login story
- WHEN its states are inspected
- THEN the full workflow matrix renders

### Requirement: DS-UI-PRIMS — Token-correct focus and motion

`primitives.css` MUST use `--focus-ring-width`/`--focus-ring` for outlines, `--duration-*`/`--ease-*` for transitions, and a `--info` spinner top with a duration token, with no hard-coded hex or magic values.

#### Scenario: Tokens replace magic values

- GIVEN a focused control and a spinner
- WHEN their outline and motion are inspected
- THEN they use the tokens and the drift guard stays green

### Requirement: DS-UI-LOGIN — Lockup and Spanish auth

Login MUST preserve the full Lumat lockup, `Usuario`/`Contraseña`/`Iniciar sesión`, username-preserving non-destructive errors, and existence-safe authentication. It MUST render a tokenized two-region brand/welcome and form frame on desktop and stack those regions on mobile; it MUST NOT depend on the phantom `card--auth` class or introduce a new styling dependency.
(Previously: login required the lockup and auth copy but had a centered, unframed layout.)

#### Scenario: Responsive login frame
- GIVEN the login is rendered at desktop and mobile widths
- WHEN the viewport crosses the mobile breakpoint
- THEN desktop shows two regions and mobile shows brand above the form without clipped controls.

#### Scenario: Failed login keeps the username

- GIVEN a failed login with a valid username
- WHEN the inline error renders
- THEN the username persists, no existence leak appears

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

### Requirement: DS-UI-TABLES — Tabular numerals and Spanish tables

DataTable/StatCard MUST render comparable numbers with tabular numerals/right alignment, Spanish empty/action labels (`No hay registros`, `Acciones`), and loading/stale variants.

#### Scenario: Numbers align in Spanish

- GIVEN a numeric column or KPI
- WHEN it renders
- THEN numbers have tabular/right alignment and Spanish empty/action text

### Requirement: DS-UI-TONEFIX — Correct case tone on ClientFicha

ClientFicha MUST render case statuses via `caseStatusTone`, never `customerStateTone`.

#### Scenario: Case status uses case map

- GIVEN ClientFicha case rows
- WHEN a case status renders
- THEN its tone comes from `caseStatusTone`

### Requirement: DS-UI-COPY — Neutral Chilean Spanish

No English or voseo MAY appear on any Storybook surface (pages, helpers, primitives, mock copy).

#### Scenario: Scan finds no English or voseo

- GIVEN any rendered story surface
- WHEN its copy is scanned
- THEN only approved labels appear

### Requirement: DS-UI-STORY — Storybook contract per story

Each story MUST state purpose/guidance and meaningful controls, render representative states, and be verified at 390/640/768/1024/1280px with honest production-shaped mocks.

#### Scenario: Viewports verified

- GIVEN a defined story layout
- WHEN rendered at 390/640/768/1024/1280 px
- THEN no critical content or action is clipped

---

## Calma Operacional (corp-*) — added 2026-08-24

### Requirement: DS-TKN-10 — Aliases Stay Inside the Hex Guard

The `--corp-*` alias layer and any primitives that consume it MUST keep the no-hard-coded-hex walk green: aliases map to existing tokens, and `tokens.test.ts` MUST extend its drift guard to assert the alias layer resolves only to `var(--*)` references with zero hex literals.

#### Scenario: Alias layer under the hex guard

- GIVEN the `--corp-*` block in `tokens.css`
- WHEN the drift-guard walk runs in `npm test`
- THEN it covers the alias layer and reports zero hex literals in aliases or consuming primitives

#### Scenario: Guard spot-checks aliases

- GIVEN the extended `tokens.test.ts`
- WHEN the guard runs
- THEN spot-checks assert the `--corp-*` slots resolve to existing tokens and no existing assertion is removed

### Requirement: DS-TKN-11 — Tabular Numerals for Data Values

Data values rendered by the panel (KPIs, timestamps, IDs, percentages, money) MUST apply `font-variant-numeric: tabular-nums` so comparable digits align; non-data text MAY omit it. This codifies the `DESIGN_SYSTEM.md` tabular-numerals rule.

#### Scenario: KPIs and metrics align

- GIVEN a KPI or StatCard value
- WHEN it renders
- THEN `tabular-nums` is applied and digits align in columns

#### Scenario: Sparsely formatted text unaffected

- GIVEN a label or status text
- WHEN it renders
- THEN it is not forced into tabular-nums

### Requirement: DS-TKN-12 — Corrected Canvas Background Documentation

`web/DESIGN_SYSTEM.md` MUST state the canvas `--bg` value as `#F1F1E8` (matching the executable `tokens.css`), replacing the stale `#F4F5F7`; the executable token source remains authoritative.

#### Scenario: Doc matches executable token

- GIVEN `DESIGN_SYSTEM.md` line 120
- WHEN the Canvas row is read
- THEN it shows `--bg` `#F1F1E8` and matches `tokens.css`

### Requirement: DS-SHELL-1 — Collapse Toggle Sizing and Placement

The desktop sidebar collapse toggle MUST render 32–36px (`--space-8`), MUST escape the shared 44px control `min-height` while keeping a ≥40px hit target by its own sizing, MUST anchor consistently in the sidebar rhythm (expanded and collapsed), and MUST keep lime focus-visible + `--primary-700` hover in both states.

#### Scenario: Shared rule overridden

- GIVEN the desktop sidebar expanded
- WHEN the toggle renders
- THEN it measures 32–36px (own `min-height` beats 44px), ≥40px hit target

#### Scenario: Anchored in both states

- GIVEN expanded and collapsed
- WHEN placement is inspected
- THEN it stays anchored, keeps lime focus + `--primary-700` hover

### Requirement: DS-SHELL-2 — Sidebar Hover Containment

The desktop sidebar MUST NOT widen beyond its fixed grid column (192px expanded, 96px collapsed). `.sidebar-inner` and `.navigation` MUST set `min-width: 0`; `.sidebar` MUST set `overflow: hidden` as a safety net, so hover/`aria-current` paint stays inside.

#### Scenario: Hover never spills

- GIVEN a nav item in the desktop sidebar
- WHEN hovered or marked `aria-current`
- THEN paint stays within the fixed column, verified at 390/640/768/1024/1280px × expanded/collapsed in a real Storybook render (jsdom cannot test media-query overflow)

### Requirement: DS-SHELL-3 — Tokenized Shell Styles Without Injection (Slice 2)

Shell layout, navigation, drawer, focus, motion, and responsive styles MUST consume `--corp-*` or existing design tokens, MUST contain no hard-coded hex values, and MUST be loaded through the tokenized stylesheet boundary. PanelShell MUST NOT inject the former `PANEL_SHELL_STYLES` `<style>` block. Existing visual, responsive, focus, collapse, drawer, and reduced-motion behavior MUST remain unchanged.
(Previously: the injected `PANEL_SHELL_STYLES` block was the shell style boundary and was only required to be hex-free.)

#### Scenario: Stylesheet boundary is tokenized
- GIVEN PanelShell is rendered
- WHEN its DOM and source are inspected
- THEN no shell-owned injected `<style>` exists and all shell values resolve through tokens

#### Scenario: Accessibility behavior is preserved
- GIVEN desktop, mobile, expanded, collapsed, and reduced-motion states
- WHEN navigation and drawer interactions are tested
- THEN focus, roles, keyboard behavior, responsive collapse, and motion preferences remain valid

### Requirement: DS-SHELL-4 — Primitive Reuse

The panel header `statusBadge` slot MUST reuse `Badge`; the user avatar MUST reuse `Avatar`. No new primitive in this slice.

#### Scenario: Badge and avatar reuse primitives

- GIVEN the header badge and sidebar avatar render
- WHEN inspected
- THEN they resolve to `primitives/Badge` / `primitives/Avatar`, no new primitive added

### Requirement: DS-SHELL-5 — Tests and Typecheck Green

The two pre-existing tsc errors in `AppShell.test.tsx` MUST be fixed (TS6133 unused `s` ~:110; TS2345 `HTMLButtonElement | undefined` → `Element` ~:118). `AppShell.stories.test.tsx` (untracked) assertions MUST update in lockstep with the re-target. `npx tsc -b` and `npm test` MUST stay green (incl. hex walk).

#### Scenario: tsc clean

- GIVEN the applied diff
- WHEN `npx tsc -b` runs in `web/`
- THEN it passes with no TS6133/TS2345 in `AppShell.test.tsx`

#### Scenario: Suite green incl. hex guard

- GIVEN the applied diff
- WHEN `npm test` runs in `web/`
- THEN all tests pass incl. the hex walk and updated story assertions

### Requirement: DS-DASH-1 — Dashboard Data Roles Resolve Through var(--corp-value)

Dashboard story data roles (KPI values, activity times, comparable numbers) MUST resolve `font-variant-numeric` through `var(--corp-value)` and MUST NOT use literal `tabular-nums` (extends DS-TKN-11/CST-ALIAS-5 to the dashboard story).

#### Scenario: KPI values use the contract token

- GIVEN the dashboard story KPI cards
- WHEN the `.kpi__value` renders
- THEN tabular-nums comes from `var(--corp-value)` (primitives rule), with no literal inline override

#### Scenario: Activity times use the contract token

- GIVEN `.dashboard-activity__time`
- WHEN rendered
- THEN `font-variant-numeric` is `var(--corp-value)`, not the literal

### Requirement: DS-DASH-2 — Dashboard Story and Tests Derive from Mock Data

The dashboard story MUST render KPI cards from the `kpis` mock export, and the story tests MUST derive assertions from the same `kpis`/`activity` sources (no hardcoded literals).

#### Scenario: Story renders from mock

- GIVEN the dashboard story
- WHEN KPI cards render
- THEN label/value/delta come from the `kpis` mock export

#### Scenario: Tests derive from mock

- GIVEN the dashboard story test
- WHEN KPI assertions run
- THEN they read from `kpis` (and activity rows from `activity`), so a mock change updates both story and test together

### Requirement: DS-GRAMMAR-1 — Agent-App Appearance, Control-Room Physiology

The production panel MUST make `PanelShell`, `ConversationThread`, `ConversationsList`, and `AgentChat` expose the agent-app grammar through named DOM regions for rail, active threads, bubbles, status/handoff, composer, and optional inspector. `Dashboard`, `ClientesList`, `ClientFicha`, `CasesList`, `AgendaPage`, `AutomationRulesPage`, `Settings`, and `KbList` MUST retain control-room `DataTable`, KPI, `Badge`, filter, and state primitives.

#### Scenario: Grammar is structurally testable
- GIVEN the approved `AiAgentGrammar.stories.tsx` states are rendered
- WHEN production DOM is compared by semantic labels/classes and roles
- THEN conversation surfaces expose the agent regions while dense pages retain control-room primitives

### Requirement: DS-GRAMMAR-2 — Tokenized Shared Style Boundary

Grammar styles MUST be implemented in `web/src/components/primitives/primitives.css` or another existing tokenized stylesheet boundary, MUST reuse existing `tokens.css`/`--corp-*` roles before adding any token, MUST add no dependency, and MUST contain no hard-coded color values. Components under `web/src/components` and `web/src/stories` MUST NOT inject component-owned `<style>` content.
(Previously: the no-injection rule named only `PanelShell` and its shell-owned `<style>` content.)

#### Scenario: Source and DOM contract
- GIVEN the grammar is rendered by `PanelShell` or a production page
- WHEN source and computed stylesheet ownership are inspected
- THEN styles come from the shared stylesheet, colors resolve through `var(--*)`, and no injected shell style or new dependency exists

#### Scenario: No component injects its own stylesheet

- GIVEN any component under `web/src/components` or `web/src/stories` renders
- WHEN its source and DOM are inspected
- THEN no `<style>` element is injected and all values resolve through tokens

#### Scenario: Existing token validation
- GIVEN rail, bubble, inspector, activity, and composer states
- WHEN token drift/no-hex tests and Storybook states run
- THEN existing token values remain valid and any new semantic token is justified by a repeated consumer

### Requirement: DS-GRAMMAR-3 — Primitive Reuse and Accessibility

Grammar surfaces MUST reuse existing `Avatar`, `Badge`/`StatusBadge`, `Button`, `Textarea`, `DataTable`, `StateMessage`, and `EmptyState` primitives where their contracts apply; they MUST preserve visible labels, semantic `status`/`alert` roles, focus-visible behavior, reduced-motion behavior, and keyboard operation.

#### Scenario: Shared primitives are present
- GIVEN a conversation header, message, composer, or dense page state
- WHEN its component tree is inspected
- THEN the applicable existing primitive is rendered rather than a duplicate equivalent

#### Scenario: Accessibility and motion
- GIVEN expanded/compact, loading/error, and reduced-motion states at approved Storybook viewports
- WHEN keyboard and DOM assertions run
- THEN labels, roles, focus indicators, and no-essential-motion behavior remain verifiable without clipped critical actions

### Requirement: DS-RT-1 — Realtime State Grammar

Realtime conversation, active-rail, token-streaming, disconnected, loading, and error states MUST reuse existing tokenized primitives and MUST expose visible labels with `role="status"` or `role="alert"` as appropriate. Styling MUST add no hard-coded colors, new dependency, or duplicate primitive.

#### Scenario: Live activity is accessible
- GIVEN a conversation receives a persisted activity or token update
- WHEN the activity surface renders
- THEN its label is visible, status is announced, and existing tokenized styles are used

#### Scenario: Connection error is actionable
- GIVEN the WebSocket is disconnected or reconnecting
- WHEN the panel renders the state
- THEN a visible status explains the condition without hiding existing conversation content

### Requirement: DS-RT-2 — Realtime Responsive Surfaces

The active-conversation rail and live thread MUST preserve existing keyboard focus, compact/expanded rail behavior, reduced-motion behavior, and approved responsive layout. Realtime updates MUST NOT reserve empty inspector space on unrelated pages.

#### Scenario: Compact rail remains usable
- GIVEN the rail is compact and the connection changes state
- WHEN keyboard navigation is used
- THEN labels/tooltips and focus-visible behavior remain available

### Requirement: DS-CC-1 — Command Center Responsive Zones

The assistant surface MUST use the existing light Lumat grammar: one centered readable conversation column, progressive-disclosure history popover, and context drawer closed by default. The zone tablist and persistent three-zone contract SHALL be removed without changing token values.
(Previously: the design system defined three desktop zones and narrow active-zone switching.)

#### Scenario: Disclosure and hierarchy

- GIVEN the assistant is rendered on desktop
- WHEN the user inspects the page
- THEN conversation is visually dominant, `Historial` opens history, `Contexto` opens operational detail, and no zone tablist is present

#### Scenario: Narrow assistant layout

- GIVEN the assistant is rendered below 1024px
- WHEN the user switches between history and context disclosures
- THEN the conversation remains primary and send, approval, retry, and attachment actions remain reachable without horizontal overflow

### Requirement: DS-CC-2 — Focus Visibility and Restoration

`PanelShell` MUST provide a reusable focus-mode and region-visibility contract with an accessible name, visible keyboard focus, Escape exit, and restoration of the prior route, selected thread, focus target, and shell visibility state.

#### Scenario: Focus mode keyboard contract

- GIVEN a user activates focus mode from a keyboard-operable control
- WHEN focus mode opens and Escape is pressed
- THEN secondary regions are minimized, an escape path remains available, and focus returns to the initiating control

#### Scenario: Responsive restoration

- GIVEN focus mode is active during a resize across a responsive tier
- WHEN it closes
- THEN the previous shell and zone visibility state is restored without losing selection

### Requirement: DS-CC-3 — Accessible, Production-Owned States

Assistant states MUST use existing primitives and semantic tokens for loading, empty, error, streaming, disabled, permission, approval, connection, and recovery. Product copy MUST be neutral Chilean Spanish and MUST NOT expose English labels or raw backend state values.
(Previously: states covered loading, streaming, disconnected, approval, error, and recovery but not the complete assistant state model or localization boundary.)

#### Scenario: State and language semantics

- GIVEN the assistant is loading, empty, streaming, disabled, denied, or failed
- WHEN the surface renders
- THEN a visible Spanish label and appropriate status/alert semantics explain the state and next action

#### Scenario: Ownership boundary

- GIVEN a production story or route renders a Command Center surface
- WHEN its imports are inspected
- THEN it uses production components and API data rather than `InboxThread`, `ChatWithAgent`, or fabricated catalog entries

### Requirement: DS-CC-5 — Accessibility and Primitive Reuse

The surface MUST reuse existing primitives and semantic tokens, add no dependency, and preserve token values. It SHALL support keyboard operation, visible focus, 200% zoom reflow, reduced motion, and non-color-only state communication. Every contrast pair the surface introduces or modifies SHALL meet the applicable WCAG 2.2 AA threshold.

Contrast of an inherited token pair is outside this change's authority: the change MAY NOT alter token values, so a pair whose ratio predates it cannot be remediated here. Such a pair SHALL be recorded with its computed ratio rather than silently dropped or silently tolerated.

#### Scenario: Keyboard and responsive accessibility
- GIVEN a user operates the assistant by keyboard, at 200% zoom, or with reduced motion enabled
- WHEN history, context, planning, composer, approval, or retry is used
- THEN focus remains visible and ordered, actions reflow without loss, and motion is reduced without removing meaning

#### Scenario: Contrast and semantics
- GIVEN a state or action the surface introduces or modifies is shown
- WHEN it is inspected or announced
- THEN its text and boundary contrasts meet the applicable WCAG 2.2 AA threshold, and accessible names plus status/alert semantics identify the action and result

#### Scenario: Inherited contrast debt is recorded, not hidden
- GIVEN the surface reuses a token pair whose contrast ratio predates this change and whose token value this change may not alter
- WHEN contrast is verified
- THEN the pair is listed with its computed ratio and threshold in `contrast-verification.md`, and it is attributed to a design-system change rather than to this one

### Requirement: DS-CC-4 — Narrow Browser Contract

The design system MUST support narrow Playwright verification of zone presence/order, breakpoint visibility, focus behavior, keyboard access, and resolved token/layout invariants. Screenshot baselines, visual regression, CI integration, PWA behavior, and catalog completion are explicitly out of scope.

#### Scenario: Browser invariants

- GIVEN a Playwright run at `<640px`, `640–1023px`, and `>=1024px`
- WHEN the Command Center is inspected
- THEN the declared visibility, geometry, focus, and keyboard invariants are testable and pass

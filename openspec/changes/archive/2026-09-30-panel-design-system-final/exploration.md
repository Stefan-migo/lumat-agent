# Exploration: Final Lumat Operations Panel Design System

## Current State

The owner-confirmed desktop reference palette intentionally replaces the current cream/white visual system. Current executable tokens in `web/src/tokens/tokens.css` declare `--bg: #F1F1E8`, `--surface: #fff`, `--border: #d8dde3`, `--text: #1a202c`, and the mint `--primary-500..900` scale (`#47c291`, `#349d73`, `#256f51`, `#143c2c`, `#0d261c`). The locked reference instead requires a muted sage canvas, no white surface, dark-green shell chrome, and separate lime/teal accents. It also adds responsive shell forms absent from the current documented component vocabulary. Inter already exists as `--font-ui`, although `--font-sans` remains system-ui.

### Verified specification drift and blocker

`DS-TKN-2 — Additive-Only Token Evolution` currently states verbatim:

> The token set in `tokens.css` MUST evolve additively: every custom property that exists before this change MUST keep its exact value byte-identical, and new tokens MUST be appended without modifying or removing any pre-existing declaration.

Its spot-check scenario also states verbatim:

> - THEN each pre-existing `--*` declaration keeps its exact value and the spot-checked palette (brand `#143c2c`, background `#f4f5f7`, text `#1a202c`, radii `6px`/`8px`) is unchanged

That MUST directly forbids the requested changes to `--bg`, `--surface`, `--text`, and `--border`; this change must supersede/revise DS-TKN-2. The explicitly pinned values disagreeing with the executable `tokens.css` are: spec background `#f4f5f7` versus actual `#F1F1E8` (case-insensitive difference is not the issue; the RGB values differ). The other values in that pinned tuple agree: `#143c2c` appears at `--primary-800`, `#1a202c` at `--text`, and radii are `6px`/`8px`. The wider spec also calls `--surface` `#FFFFFF` in the contrast record and design-system policy, while executable `--surface` is `#fff`; those agree as colors but are explicitly incompatible with the owner's no-white rule. DS-TKN-12 already records the corrected old canvas value `#F1F1E8`, exposing the internal inconsistency between DS-TKN-2 and DS-TKN-12.

The orphan `openspec/changes/panel-visual-foundation/` contains only `specs/panel-design-system/spec.md`; its delta content is already represented in the canonical spec, but the change has no proposal, design, tasks, or archive report. It is context, not a live change to continue.

`panel-grammar-global` is an active, un-applied (0/5) change whose proposal amends the same canonical `DS-GRAMMAR-1`. It broadens *agent-app appearance across every production page* while retaining control-room physiology for dense data. The final-design change addresses the visual system and shell implementation, and its shared appearance/first-dense-surface work intersects directly with that amendment; task T3 explicitly applies the appearance axis to `ClientesList` and `ClientFicha`. Recommended declared relationship: **amends** `panel-grammar-global` (rather than independent or conflictsWith), with explicit coordination of requirement ownership and tasks. It is not a clean supersedes relationship because the grammar amendment's separate whole-panel-vs-dense-content contract remains valid; the final visual palette/shell should provide its appearance and first-page consumer. If sequencing cannot preserve T3 as a distinct deliverable, consolidate/retarget T3 before either change is proposed. Do not silently duplicate or override DS-GRAMMAR-1.

## Affected Areas

- `openspec/specs/panel-design-system/spec.md` — primary delta authority: revise token evolution and coherent shell/chrome requirements; preserve unrelated page behavior contracts.
- `openspec/specs/panel-design-system/contrast-verification.md` — current measured inherited contrast record uses the old white/sage surfaces and must be recalculated for affected pairs, preserving method and attribution honestly.
- `openspec/specs/corp-token-aliases/spec.md` — current “frozen Lumat token set” / additive-only relationship is incompatible with a palette revision; keep alias indirection, revise frozen-value premise.
- `openspec/specs/corp-primitives/spec.md` — color/contrast and button foreground assumptions bind to existing primary tokens and white; align primitive contracts to revised semantic slots.
- `openspec/specs/corp-components/spec.md` — dialog claims palette frozen and has surface/shadow assumptions; update only those that conflict with reference design.
- `web/src/tokens/tokens.css`, `web/src/tokens/tokens.test.ts`, `web/src/components/primitives/primitives.css` — executable palette, alias mappings, contrast enforcement, card radius/depth, and component token consumers.
- `web/src/components/domain/AppShell.tsx`, `PanelShell.tsx`, shell stories/tests, and existing primitives — shell composition, route/nav, responsive behavior, primitive reuse.
- `web/DESIGN_SYSTEM.md` — human-facing direction, token tables, shell, elevations, acceptance conditions, and logo limitations need alignment.

## Full Delta-Spec Plan

Only requirements that materially describe this visual/token/shell change are in scope; unrelated product contracts remain unchanged.

### `openspec/specs/panel-design-system/spec.md`

**MODIFY**
- **DS-TKN-2 — Additive-Only Token Evolution:** replace with **DS-TKN-2 — Approved Palette Revision and Token Integrity**. A named, owner-approved palette revision MAY change or remove prior color declarations; the revision MUST keep one executable `:root` source, preserve `--corp-*` as aliases to canonical roles (never duplicate raw values), and keep contrast and no-hard-coded-color guarantees. Non-palette token values remain stable unless explicitly listed in the approved delta. This explicitly supersedes the byte-identical-value ban, not DS-TKN-1 single-source.
- **DS-TKN-8 — Drift Guard Stays Green:** replace old pinned palette checks with exact checks for the locked new palette and preserve JS/CSS mirror, alias resolution, contrast, and hex-walk checks; add a no-pure-white surface assertion.
- **DS-TKN-12 — Corrected Canvas Background Documentation:** update requirement/scenario from `#F1F1E8` to `#dbe1d6`, and replace its historical “line 120” locator with role-based doc-to-token consistency.
- **DS-TKN-3 — Typography Scale:** retain Inter requirement and amend `--font-sans` language only if implementation changes the actual base font token; do not unnecessarily remove the static scale guarantee.
- **DS-TKN-7 — Elevation Tokens:** replace shadow-forward card expectation with explicit near-zero/no card elevation; overlay/dialog elevation remains a separate decision verified against supplied geometry.
- **DS-UI-LINK / CST-PRIM-2 linkage:** revise color role language and contrast examples where old `--primary-700` on the former surface is invalid under new token mappings; retain ≥4.5:1 requirement.
- **DS-SHELL-1/2/3/4/6 and DS-RESP-1:** revise old desktop-sidebar widths, palette-specific hover/focus, and “no new primitive” assumption as necessary to specify responsive expanded/collapsed desktop sidebar, tablet rail, mobile header/tab bar, and overlay drawer. Keep keyboard/focus, reduced-motion, 44px touch target, tokenized CSS, no injected styles, and PWA boundaries.
- **DS-GRAMMAR-1:** coordinate with `panel-grammar-global`; retain that change's global appearance/control-room physiology contract. Add final palette/shell appearance as a compatible implementation of the shared appearance axis, not a competing rewrite.
- **DS-CC-5:** remove the blanket “MAY NOT alter token values” inherited-pair constraint only for pairs explicitly revised by this approved palette change; require every introduced or revised foreground/surface/boundary pair to meet the stated WCAG threshold or be explicitly recorded as accepted/unresolved with ratio and authority.

**ADD**
- **DS-TKN-13 — Final Palette Revision:** define required exact color role families (`--chrome-*`, `--bg`, `--header-bg`, `--surface`, `--border`, lime/teal roles, `--text`, `--text-muted`, and dark-chrome text roles), prohibit pure white as any surface value, retain a single `tokens.css` source and token-only consumption, and require measured contrast verification for all affected semantic pairs. Scenarios use Given/When/Then and state that every new/revised pair must be verified.
- **DS-SHELL-7 (new ID only if existing DS-SHELL-7 is verified unused; otherwise use next available ID): Responsive Lumat Shell Surfaces:** specify desktop sidebar with collapse/search/grouped nav/user footer; desktop top header; mobile dark header and five-destination bottom bar; tablet icon rail; overlay drawer for mobile/tablet. Preserve navigation/role behavior and accessible keyboard/touch/focus behavior. (The canonical currently uses DS-SHELL-7 for the Storybook harness, so do not reuse it; assign the next available shell identifier after confirming the complete ID inventory.)
- **DS-SURFACE-1 — Flat Sage Surface Separation:** cards use the lightest system surface, approximately 10px radius, hairline boundary and no material shadow; dialogs approximately 14px radius at reference scale. No `#fff` surface.

**REMOVE**
- Remove the *additive-only value-preservation semantics* of DS-TKN-2 and obsolete palette-specific clauses in DS-TKN-8/12, replacing them as above. Do not remove the requirement IDs themselves if their history/traceability can be retained through modification.

### `openspec/specs/corp-token-aliases/spec.md`

**MODIFY**
- **CST-ALIAS-2 — Additive-Only Alias Evolution:** remove dependency on immutable DS-TKN-2; alias slots remain stable indirections while target token values may change under approved DS-TKN-13 palette revisions.
- **CST-ALIAS-3 — Frozen Alias Principle:** replace “frozen Lumat value” with “single canonical semantic role”; aliases remain single-defined and consumers use slots rather than twin values.
- **CST-ALIAS-1 — All Slots Map to Existing Tokens:** keep; clarify that any added/updated chrome/surface aliases must target canonical color roles and must not add hex literals.

**ADD**
- **CST-ALIAS-6 — Palette Revision Compatibility:** every corp slot's target remains declared and resolves; changing the canonical target value is allowed only through the approved palette revision, and alias consumers stay token-only.

**REMOVE**
- Remove claims that the palette or mapped values are frozen/byte-identical; no alias-layer contract itself is removed.

### `openspec/specs/corp-primitives/spec.md`

**MODIFY**
- **CST-PRIM-2 — WCAG AA Contrast for Links and Actions:** retain thresholds but replace fixed white-on-`--primary-800` and old measured ratio with role-based pairs verified against the final palette; a literal white foreground is permitted only if the actual surface/action contract calls for it, not as a system surface.
- **CST-PRIM-1 — Catalog Contract Consumption:** keep token-only contract and clarify new shell/surface semantic tokens are valid through aliases or declared roles.
- **CST-PRIM-6 — No Decorative Animation:** unchanged (confirm no relevance; no delta expected).

**ADD**
- **CST-PRIM-8 — No Pure-White Surface:** Card, Input, Select, Textarea, Alert/StateMessage and other light primitive surfaces MUST resolve to approved non-white surface tokens; pure white foreground text may still be used on dark chrome where contrast verifies.
- **CST-PRIM-9 — Flat Card Separation:** card styles use fill and hairline border rather than elevation shadow; verify the requested approximate geometry while preserving existing semantic behavior.

**REMOVE**
- Remove exact `--primary-800` white-text ratio assertion, replacing it with palette-specific measured contrast evidence; do not remove the contrast guarantee.

### `openspec/specs/corp-components/spec.md`

**MODIFY**
- **CORP-DIALOG-1 — Dialog Rendering:** dialog fill/border/radius must use revised surface roles, approximately 14px radius per measured reference, with shadow only if the approved reference interpretation requires it; no white surface assumption.
- **CORP-DIALOG-4 — No Token Value Changes:** change to prohibit unapproved token mutations but permit the explicitly authorized final palette revision; its current “drift guard unchanged” scenario must be replaced with updated guard expectations.
- **CORP-TABLE-1:** retain semantics; confirm `--corp-border` and `--corp-text` mappings provide readable, low-salience table rules under the revised palette.

**ADD / REMOVE**
- No standalone new component requirement is needed here; add a dialog surface verification scenario under CORP-DIALOG-1. Remove only the obsolete blanket freeze in CORP-DIALOG-4.

## Token Architecture Proposal

- Keep `--primary-50..900` as the legacy brand/action scale, not as shell chrome and not as the new palette's lime scale. Do not repurpose the established names: `--corp-primary`, links, buttons, story content and existing consumers rely on them. Re-evaluate their values/consumers during implementation against contrast constraints; where the final visual needs a distinct action role, introduce an explicitly named semantic role rather than quietly redefining the entire scale.
- Add canonical role families for the exact approved values: `--chrome-950`, `--chrome-900`, `--chrome-active`; `--bg`, `--header-bg`, `--surface`, `--border`; `--lime-500/600/700`; `--teal-500/400`; `--text`, `--text-muted`, `--text-on-dark`, `--text-on-dark-2`. Preserve the supplied exact hex casing/value in CSS as authoritative.
- Keep `--corp-*` as the compatibility alias layer, mapping slots to these canonical roles where meanings match (for example `--corp-bg` → `--bg`, `--corp-surface` → `--surface`, `--corp-border` → `--border`, `--corp-fg`/`--corp-text` → `--text`). Do not map `--corp-primary` to chrome: action/brand and shell chrome are different roles. Add a small number of shell-specific aliases only where repeated consumption justifies them; avoid a second alias taxonomy duplicating every token.
- Keep `--danger*`, `--success*`, `--warning*`, and `--info` semantically independent from brand accents. Recompute their foreground/background/border pair contrast on changed surfaces. Retain existing spacing, typography, focus, motion, breakpoint, and z-index families unless reference geometry or implementation requires a specifically scoped adjustment.
- Avoid pure white in surfaces, including derived `color-mix()` outputs and aliases. A no-white test should evaluate all resolved surface role values rather than searching for `#fff` substring alone.

## Guard Assertions

- `web/src/tokens/tokens.test.ts`: replace the obsolete spot-check for primary/bg/text/danger/success/radii with exact locked palette role assertions; remove DS-TKN-2 byte-identical spot-checks for `--bg`, `--surface`, `--text`, `--border` while retaining unchanged-value checks for non-revised tokens and the `tokens.ts` JS-consumed subset parity. Keep the no-hard-coded-hex walk and `--corp-*` target/hex assertions. Update corp alias targets where `--corp-primary-fg`, `--corp-bg`, `--corp-surface`, border and text mapping change. Update brand-role assertions only for tokens intentionally superseded; retain semantic pairs but measure changed contrast contexts.
- `tokens.test.ts` contrast block: replace old `--brand-bg-elevated`/white-surface pair coverage that no longer models the primary surfaces; assert normal text ≥4.5:1 on `--bg`, `--header-bg`, and `--surface`, dark-chrome text on `--chrome-950/900`, active-nav label on `--chrome-active`, and meaningful border/active accents against their adjacent surfaces at applicable WCAG thresholds. Add an assertion that no canonical or resolved surface role equals pure white and ensure color-mix resolution is accounted for if retained. Avoid asserting lime as small text unless measured compliant.
- `tokens.test.ts` primitive consumption block: update radius/depth expectations from 12px-card-radius plus `--shadow-1` to ~10px radius, hairline and no material card shadow; dialog radius separately. Add representative shell token consumption checks for the new surfaces.
- `web/src/components/style-boundary.test.ts`: existing checks reject JSX `<style>`, inline component styles on ClientMemories, and inline SVG in five files. The palette itself does not break these assertions. Extend only if new shell components are added: include shell sources in the no-inline-style/no-inline-SVG lists as applicable, without asserting palette values here.
- `web/src/components/dependency-boundary.test.ts`: existing assertion only forbids component imports from stories except two compatibility tests. Palette changes do not break it. Keep it unchanged unless new primitives are placed in stories by mistake; ensure shell primitives import from the production primitive/shared boundary, never stories.

## Component and Primitive Inventory Impact

Restyle/revalidate existing shared primitives because their fills, text, borders, radius, shadow or focus colors currently derive from changed roles: `Card`, `Button`, `Input`, `SearchInput`, `Select`, `Textarea`, `Badge`/`StatusBadge`, `StateMessage`/`Alert`, `DataTable`, `Dialog`, `Avatar`, `Tabs`, `PageHeader`/`PageFrame`, `StatCard`, and `EmptyState`. Keep their API/state/accessibility behavior unless separately justified. Dashboard and all page content retain dense control-room physiology under DS-GRAMMAR-1.

New or promoted shell primitives/surfaces (do not invent component names as binding API yet):

| Reference surface | Recommended primitive boundary | Graph nodes/edges consulted |
|---|---|---|
| Dark desktop sidebar: expanded/collapsed, search, grouped nav, user footer | Extend `PanelShell` composition; isolate reusable navigation/sidebar pieces under production `components/domain` or `components/primitives` only if stable ownership demands it | `AppShell()`, `AppShell.tsx`, `PanelShell.tsx`, `NAVIGATION`, `panelRoutes`, `pathForRoute()`; AppShell community |
| Desktop top header: back, breadcrumb, notification, avatar/account/chevron | Shared shell header primitive/region; reuse `Avatar`, existing notification surface and icon contract | `PanelShell.tsx`, `NotificationCenter`, `Avatar`, `Icon`/`primitives` |
| Mobile dark header | Responsive shell header variant, not a separate route or theme | `PanelShell.tsx`, `AppShell.tsx`, `primitives.css` |
| Mobile bottom tab bar with five destinations | Shell navigation primitive/region driven by existing route and permissions | `NAVIGATION`, `panelRoutes`, `AppShell.tsx` |
| Tablet icon rail | Responsive navigation variant of sidebar, labels accessible via names/tooltips; not a separate navigation model | `PanelShell.tsx`, `AppShell.tsx`, shell story nodes |
| Tablet/mobile overlay drawer | Shared drawer primitive with focus trap/restore, inert background, scroll lock, Escape, resize reconciliation, reduced motion and touch sizing | `PanelShell.tsx`, `DS-RESP-1`, `primitives.css`, `Dialog` |

Storybook shell/page stories should cover breakpoint tiers and open/closed/expanded/collapsed states, with the reference images as visual authority. Existing primitives should be extended before introducing duplicate equivalents.

## Risks and Open Questions

- **Blocking spec change:** superseding DS-TKN-2 is mandatory; without it, modifying the pinned palette is a normative violation. Preserve the single-source and contrast guarantees in its replacement.
- **Concurrent change:** `panel-grammar-global` modifies DS-GRAMMAR-1 and has a T3 first-dense-page overlap. Declare `amends` and coordinate/retarget tasks before proposal/design; otherwise two active writers can race the same canonical requirement and `ClientesList`/`ClientFicha`.
- **Accessibility:** locked values are visual authority, not proof every text/accent combination passes contrast. Compute and record all actual foreground/background pairs. In particular lime and teal accents should not be presumed suitable for small text; dark text may be needed over them.
- **Logo (RESOLVED):** the reference's mountain monogram and two-tone wordmark match the already-committed brand assets `web/public/brand/lumat-logo.png` (1864x1264 RGBA, transparent) and `web/public/brand/lumat-mark.png` (2860x2736), added by commit `59d92428`. The owner confirmed these are the logo to consume. No placeholder is needed and this change produces no new asset. Note that `web/DESIGN_SYSTEM.md` still lists "obtain a production-ready logo asset" as convergence work and warns against a low-resolution original JPG; that guidance is stale and must be corrected in the docs slice.
- **Surface scope (RESOLVED):** dialogs are about 14px at their own reference scale while cards are ~10px. Keep the existing `--radius-*` values as global geometry and tune their values; no new semantic aliases are needed. Cards are flat, while `--shadow-3` is retained for overlay/drawer/dialog affordance.
- **Alias compatibility:** broad semantic remapping of `--primary-*` could unintentionally affect links/actions beyond shell. Preserve scale semantics and inventory consumers before changes.
- **Responsive behavior (RESOLVED):** the five mobile tabs are Panel, Conversaciones ("Chats"), Asistente, Agenda, and Clientes. Other authorized destinations remain reachable through the overlay drawer; do not invent destinations. "Casos" is removed from the unified dashboard despite appearing in the design references.
- **Token specification granularity:** use exact values for named locked tokens, but avoid freezing every unrelated token. The graph is structurally useful but not fresh.

## Scope Boundaries

This change deliberately does NOT introduce dark mode (dark shell chrome is not a theme), alter backend/API/permissions/business behavior, expand into contract M2 public website or M3 service catalog/scheduling/payments, redesign dense data physiology, change route inventory, add dependencies, re-catalog the 23 reference images, repeat pixel palette extraction, or produce a new logo asset (the committed brand assets in web/public/brand/ are consumed as-is). Only the canonical specs listed above should receive deltas; do not revive unrelated visual-foundation work.

## Approaches and Recommendation

1. **Recommended — explicit palette revision with compatibility aliases.** Supersede the additive-only value ban narrowly, add approved semantic roles, keep existing alias and semantic layers, and restyle shell/primitives through token roles. This honors the locked design without a parallel token source and makes changes auditable. Effort: medium/high because consumers and contrast pairs must be verified.
2. **Append-only new palette plus legacy values.** Keep old palette untouched and put the reference system behind separate names. Rejected: violates the reference requirement that established surface roles (`--bg`, `--surface`, `--text`, `--border`) represent the new system, creates parallel competing visual authorities, and still requires overcoming DS-TKN-2 to deliver the actual panel.

## Graph Check

Consulted `graphify-out/GRAPH_REPORT.md` and ran from repository root:
- `graphify query "web panel design system tokens primitives"` — `tokens`, `primitives`, `AppShell.tsx`, `Tokens.stories.tsx`, `tokens.test.ts`, `web/DESIGN_SYSTEM.md`; relevant AppShell/token communities and panel-design-system/spec nodes.
- `graphify query "panel shell AppShell primitives tokens css responsive navigation"` — `AppShell()`, `AppShell.tsx`, `PanelShell.tsx`, `NAVIGATION`, `cssVars`, `tokens`, `primitives`, `panelRoutes`, `pathForRoute()`, shell stories/tests.
- `graphify path "tokens.ts" "AppShell.tsx"` and `graphify path "AppShell.tsx" "primitives.css"` were attempted; both returned no directed path (the latter also warned of ambiguous source/target matches). This is recorded rather than inferred as a direct edge.
- Relevant communities: `AppShell.tsx`, `Dashboard.tsx`, `tokens.test.ts`, and the SDD `Panel Design System Specification`/`Panel Grammar Global Contract Amendment` hyperedge.
- Supplied graph provenance says built from `c0c78ebe` while HEAD is `dfb9eca2`; it is stale but usable structurally. The checked-in `GRAPH_REPORT.md` independently labels its report build as `96a6f69b`; therefore freshness metadata itself is inconsistent. No rebuild was attempted. Use graph results for navigation, then verify exact code/spec contents as done here.

## Ready for Proposal

**Yes, with explicit coordination condition.** Proposal should declare `amends` relationship to `panel-grammar-global`, identify the DS-TKN-2 replacement as a blocking delta, and avoid duplicate ownership of its DS-GRAMMAR-1 text/T3 dense-page consumer. Before design, compute palette contrast for every actual primitive pairing. The mobile five-destination set, the logo treatment, the radius strategy, and the overlay-shadow decision are now resolved by the owner — see "Resolved Owner Decisions" below.

## Resolved Owner Decisions (2026-09-30)

1. **Mobile five destinations:** Panel, Conversaciones ("Chats"), Asistente, Agenda, Clientes. Other authorized destinations stay reachable through the overlay drawer. **"Casos" is removed from the unified dashboard** — it is not a destination and not a dashboard shortcut, overriding the design references which do show it.
2. **Logo:** consume the committed assets `web/public/brand/lumat-logo.png` (horizontal lockup) and `web/public/brand/lumat-mark.png` (mark). No placeholder, no new asset.
3. **Radius:** keep the existing `--radius-*` scale as global geometry and tune the values so cards are approximately 10px and dialogs approximately 14px. No new semantic radius alias taxonomy.
4. **Shadow:** cards flat (fill + hairline, no elevation). Retain `--shadow-3` for overlay/drawer/dialog affordance only.
5. **WCAG token adjustments:** the owner approved adjusting the tokens that failed measured contrast rather than accepting the failures. `--text-muted` `#6e7a80` → `#5a6469`, `--text-on-dark-2` `#729486` → `#88a599`, `--warning` `#a05e07` → `#8f5406`. The `--border` container hairline, the `--lime-700` title accent rule, and the semantic status badge borders are declared decorative rather than adjusted; control boundaries resolve through `--border-strong` at 3.09:1 on `--surface`. The locked palette values recorded earlier in this document are the pre-adjustment measurements and are preserved as the historical record.

Impact of decision 1: `web/src/components/pages/Dashboard.tsx` currently exposes "Casos" in its quick-access cards, and `web/src/components/domain/AppShell.test.tsx` contains dashboard-to-Casos routing tests that the removal will affect.

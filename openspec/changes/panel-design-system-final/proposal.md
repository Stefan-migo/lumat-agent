# Proposal: Final Lumat Operations Panel Design System

## Intent

Replace the panel's current cream-and-white visual system with the owner-approved final palette, rebuild the shared primitives and responsive shell to use it, and deliver the dashboard as its first consuming surface. This change addresses verified normative drift, not a discretionary visual refresh: live `DS-TKN-2` requires every existing token value to remain byte-identical, directly prohibiting the approved updates to `--bg`, `--surface`, `--text`, and `--border`. Proceeding without revising that requirement would violate the current contract. Its pinned background `#f4f5f7` also disagrees with executable `#F1F1E8`, while `DS-TKN-12` records the latter; the current white-surface rule conflicts with the owner's explicit no-white requirement. The approved palette revision must therefore supersede the additive-only prohibition narrowly, while preserving single-source tokens and contrast guarantees.

## Scope

Deliver the work as four reviewable slices, each planned as a work unit within the auto-chain strategy's 400-changed-line review budget:

1. **Tokens, guards, and direction:** revise `web/src/tokens/tokens.css`, `web/src/tokens/tokens.test.ts`, and `web/DESIGN_SYSTEM.md`. Encode the exact approved palette below; assert the locked role values and that every resolved surface is not pure white (including aliases and any retained `color-mix()`); re-verify affected contrast pairs. Keep `--corp-*` as compatibility aliases to semantic roles, not duplicate values. Inventory `--primary-*` consumers before any broad remapping.

   | Role | Approved value |
   |---|---|
   | `--chrome-950`, `--chrome-900`, `--chrome-active` | `#012f1d`, `#073d2b`, `#012214` |
   | `--bg`, `--header-bg`, `--surface`, `--border` | `#dbe1d6`, `#dee4db`, `#e8ebe4`, `#d5dad1` |
   | `--lime-500`, `--lime-600`, `--lime-700` | `#c6d529`, `#d3e41d`, `#a2c312` |
   | `--teal-500`, `--teal-400` | `#52babb`, `#6adbdf` |
   | `--text`, `--text-muted`, `--text-on-dark`, `--text-on-dark-2` | `#111a2e`, `#5a6469`, `#e9f0e9`, `#88a599` |

Three tokens were adjusted on 2026-09-30 to close WCAG 2.2 AA failures found by measured contrast: `--text-muted` #6e7a80 → #5a6469, `--text-on-dark-2` #729486 → #88a599, and the `--warning` foreground #a05e07 → #8f5406. The remaining failing pairs are declared decorative rather than adjusted: the `--border` container hairline (1.07:1 on `--bg`, 1.18:1 on `--surface`) is decorative and MUST NOT be the sole boundary of an interactive control — control boundaries resolve through `--border-strong` (3.09:1 on `--surface`); the `--lime-700` title accent rule (1.52:1 on `--bg`) is decorative non-text; semantic status badge borders are decorative reinforcement and MUST NOT be the only channel conveying status.

   Typography remains Inter. The lightest system surface is `--surface`; cards use an approximately 10px radius, hairline separation, and essentially no shadow. Dialogs use approximately 14px radius at their reference scale. This is a light system with dark shell chrome, not dark mode.

2. **Primitive restyle:** update the existing styles and tests for `Card`, `Button`, `Input`, `SearchInput`, `Select`, `Textarea`, `Badge`/`StatusBadge`, `StateMessage`/`Alert`, `DataTable`, `Dialog`, `Avatar`, `Tabs`, `PageHeader`/`PageFrame`, `StatCard`, and `EmptyState` in `web/src/components/primitives/` and existing shared-component areas. Preserve their APIs, state behavior, and accessibility contracts unless a separately justified requirement says otherwise.

3. **Responsive shell:** update `web/src/components/domain/AppShell.tsx`, `PanelShell.tsx`, related production styles, tests, and shell stories. Deliver dark expanded/collapsed desktop sidebar with in-sidebar search, grouped navigation, and user footer; desktop top header with back, breadcrumb, notification bell, avatar/account, and chevron; dark mobile header; a five-destination mobile bottom tab bar; tablet icon rail; and overlay drawer. Derive all destinations and role filtering from existing navigation authority; do not invent routes or destinations.

4. **Dashboard consumer:** redesign the dashboard at desktop, tablet, and mobile in its existing page, styles, and story/test areas (including `web/src/components/pages/Dashboard.tsx` and its current Storybook coverage). Preserve data, permissions, and dense control-room physiology while making it the first end-to-end consumer of the revised system. The dashboard MUST NOT expose "Casos" as a quick-access destination or shortcut; the owner has removed it. Existing dashboard-to-Casos routing tests in web/src/components/domain/AppShell.test.tsx are expected to change with it.

The spec phase should create deltas only for the verified affected capabilities: `panel-design-system`, `corp-token-aliases`, `corp-primitives`, and `corp-components`. Do not revise unrelated requirements.

## Non-goals

- No dark mode; dark sidebar/header are shell chrome, not a theme.
- No backend, API, permission, business-behavior, route-inventory, or data changes.
- No expansion into contract M2 public website or M3 service catalog, scheduling, payments, or automation; do not revive shipped Hito 1–4 work.
- No redesign of dense-data physiology or conversion of dense data presentation into another form.
- No new dependencies and no re-cataloging or re-extraction of the 23 reference images.
- No logo design or asset production: the committed brand assets in web/public/brand/ are consumed as-is.

## Relationship to concurrent work

This change **amends** `panel-grammar-global`: that active change is un-applied (0/5 tasks), modifies the same canonical `DS-GRAMMAR-1`, and its T3 overlaps the first dense consumer (`ClientesList`/`ClientFicha`). Coordinate requirement ownership and task boundaries before design or implementation: retain the global appearance/control-room physiology contract and its intended consumer scope; do not duplicate or silently overwrite `DS-GRAMMAR-1`. If T3 cannot remain distinct, consolidate or retarget it before either change proceeds. The orphan `openspec/changes/panel-visual-foundation/` is context only, not a live change to continue.

## Approach

Use the approved semantic palette as one executable source in `tokens.css`, preserving alias indirection and semantic separation between shell chrome, actions, surfaces, and status colors. Replace only the obsolete palette freeze and affected contrast/surface assumptions. Validate resolved surface values (not textual hex substrings), and measure each actual foreground/background and non-text boundary pair against its applicable WCAG 2.2 AA threshold. Restyle existing primitives first, then compose responsive shell variants through the existing `AppShell`/`PanelShell` boundary and existing navigation authority, and finally apply the system to the dashboard. Keep the reference as visual authority without claiming unmeasured accessibility or missing-asset fidelity.

## Capabilities

### New Capabilities

- None. This changes requirements within existing panel design-system and corporate token/primitive/component capabilities.

### Modified Capabilities

- `panel-design-system`: replace the additive-only palette freeze with the approved revision; define final palette/surface constraints, revised guards, responsive shell, and affected contrast obligations while preserving unrelated behavior contracts.
- `corp-token-aliases`: permit approved canonical role value changes while keeping aliases single-defined, resolvable, and hex-free.
- `corp-primitives`: align surface and action roles with the revised palette and require measured contrast and flat card separation while retaining primitive behavior.
- `corp-components`: align dialog/table surface assumptions and remove only the obsolete blanket token freeze.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `openspec/changes/panel-design-system-final/specs/` | Added in spec phase | Deltas for the four modified capabilities above; proposal phase creates no delta files. |
| `openspec/specs/panel-design-system/spec.md` | Modified at archive | Supersede DS-TKN-2 narrowly; revise DS-TKN-8/12, DS-TKN-7 and relevant shell, contrast, and appearance clauses; add final palette/surface requirements. |
| `openspec/specs/corp-token-aliases/spec.md` | Modified at archive | Revise CST-ALIAS-2/3 freeze assumptions while retaining alias integrity. |
| `openspec/specs/corp-primitives/spec.md` | Modified at archive | Re-measure role-based contrast and specify no-white surfaces and flat cards. |
| `openspec/specs/corp-components/spec.md` | Modified at archive | Align dialog/table roles and revise obsolete no-token-change assumption. |
| `web/src/tokens/tokens.css`, `web/src/tokens/tokens.test.ts` | Modified | Executable palette, alias mappings, resolved-surface guard, and affected-pair contrast verification. |
| `web/src/components/primitives/`, `web/src/components/shared/` | Modified | Restyle listed primitives while preserving APIs, states, and accessibility behavior. |
| `web/src/components/domain/AppShell.tsx`, `PanelShell.tsx`, shell tests/stories | Modified | Responsive shell variants composed with current route and navigation authority. |
| `web/src/components/pages/Dashboard.tsx`, dashboard styles/stories/tests | Modified | First consuming surface, verified at desktop, tablet, and mobile. |
| `web/DESIGN_SYSTEM.md` | Modified | Replace superseded palette, surface, shape, shell, and acceptance guidance; record unresolved asset and contrast limitations honestly. |

## Resolved Owner Decisions (2026-09-30)

All four previously open questions were answered by the owner:

1. **Mobile five destinations:** Panel, Conversaciones ("Chats"), Asistente, Agenda, Clientes; other authorized destinations remain reachable through the overlay drawer. **"Casos" is removed from the unified dashboard** (owner override of the reference, which does show it).
2. **Logo:** consume the committed assets `web/public/brand/lumat-logo.png` and `web/public/brand/lumat-mark.png`. No placeholder; no new asset.
3. **Radius:** keep the existing `--radius-*` scale as global geometry and tune values to approximately 10px for cards and 14px for dialogs; no new semantic alias taxonomy.
4. **Shadow:** cards flat; retain `--shadow-3` for overlay/drawer/dialog affordance only.

No owner-gated value remains open. Design and tasks are unblocked.

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| DS-TKN-2 still forbids the approved change until superseded; changing tokens without that delta is a normative violation. | High | Make the narrowly scoped DS-TKN-2 replacement the blocking premise; preserve single-source and non-palette integrity guarantees. |
| `panel-grammar-global` races on DS-GRAMMAR-1 and its first dense-page T3 overlaps this work. | High | Declare the amendment and coordinate requirement/task ownership before design; consolidate or retarget T3 if needed. |
| Locked palette values do not prove every text/accent pair meets WCAG 2.2 AA. Lime and teal must be measured, not assumed compliant for small text. | High | Measure real foreground/background and required non-text pairs; use dark text on accents where required, and record any unresolved pair with its ratio and authority rather than claiming compliance. No WCAG pair is verified by this proposal. |
| A no-white guard that searches only for `#fff` misses aliases, equivalent notation, or `color-mix()` resolving to white. | Medium | Resolve computed/canonical surface values (including derived values and aliases) and assert against pure white. |
| Broad `--primary-*` remapping can alter links/actions outside the shell. | High | Inventory consumers before remapping; keep action/brand semantics distinct from shell chrome unless each consumer is explicitly validated. |
| Five mobile tabs may not map one-to-one to all authorized routes/roles. | Medium | Resolve selection and overflow behavior from `NAVIGATION`, `panelRoutes`, and `pathForRoute()`; do not create destinations. |
| The design references show "Casos" in the dashboard, but the owner removed it; a literal reference-fidelity reading would reintroduce it. | Low | Record the override explicitly in the spec and in the dashboard slice; do not re-add Casos for visual fidelity. |

## Rollback Plan

Revert the affected slice/work-unit commits in reverse dependency order, or revert the complete change if the token revision causes unacceptable regressions. The guard tests detect palette drift, alias/resolution errors, pure-white surfaces, and failed contrast assertions before re-release. Rollback restores the previous token declarations, primitive styles, shell, and dashboard together as needed. No data, persisted state, or migration is involved; rollback is source-only and recoverable.

## Dependencies

- The four owner decisions are resolved (2026-09-30); design is no longer blocked on them.
- Coordination with `panel-grammar-global` before design/task ownership of DS-GRAMMAR-1 and the overlapping dense-page work is finalized.
- The supplied reference images are visual authority; no external dependency is introduced.

## Graph Check

Consulted `graphify-out/GRAPH_REPORT.md` and queried from the repository root. The graph confirms the existing shell composition boundary: `AppShell.tsx` imports `PanelShell.tsx`; `PanelShell.tsx` contains `NAVIGATION`; `panelRoutes.ts` owns `panelRoutes` and `pathForRoute()`. These nodes support adapting shell presentation while reusing existing route authority, not creating a parallel route model. Token/primitives queries surfaced `tokens`, `tokens.test.ts`, `primitives.css`, and the token-alias specification, consistent with the single token source and shared stylesheet boundaries. Queries did not establish a directed navigation edge from `NAVIGATION` to `pathForRoute()`, nor from `tokens.css` to `tokens.test.ts`; no such direct edge is claimed. The report calls itself built from `96a6f69b`; exploration also recorded graph provenance `c0c78ebe` while HEAD was `dfb9eca2`. Freshness metadata is inconsistent and the graph is stale versus HEAD; it was not rebuilt. Use this graph as structural guidance only, not exact current-state proof.

## Success Criteria

- [ ] The spec phase replaces the DS-TKN-2 additive-only value ban narrowly, preserving DS-TKN-1 single-source tokens and explicit non-palette stability.
- [ ] Token guards assert exact locked role values, evaluate resolved surfaces against pure white, retain alias/hex protections, and measure affected contrast pairs without assuming lime/teal small-text compliance.
- [ ] Listed primitives preserve their existing APIs, states, keyboard/focus behavior, and accessibility contracts while adopting revised semantic roles.
- [ ] Desktop, tablet, and mobile shell plus dashboard stories/tests cover the specified responsive surfaces and states using only existing navigation authority.
- [ ] `panel-grammar-global` DS-GRAMMAR-1/T3 ownership is coordinated without duplicate or competing deltas.
- [ ] Rendered review confirms the reference direction using the committed brand assets, with no unmeasured WCAG conformance claim and no "Casos" entry on the dashboard.

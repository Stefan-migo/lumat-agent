# Design: Final Lumat Operations Panel Design System

## Technical Approach

Implement the approved sage-and-forest visual system through the existing `tokens.css` source, existing shared primitives, and `AppShell` → `PanelShell` composition; then apply it to Dashboard without changing route/data/permission behavior. The four deltas (`panel-design-system`, `corp-token-aliases`, `corp-primitives`, `corp-components`) authorize only named palette revisions and preserve alias, single-source, behavior, and contrast obligations. Reference images control geometry and layout, not palette values. The owner override removes the Dashboard “Casos” quick-access entry although it remains present in reference images.

## Architecture Decisions

### Decision: Supersede DS-TKN-2 narrowly
**Choice**: Replace its additive-only freeze with the delta's named-role exception; keep DS-TKN-1 single `:root`, exact non-palette stability, alias integrity, and color guards.
**Alternatives considered**: Append a parallel palette; leave the normative freeze untouched.
**Rationale**: The current requirement otherwise prohibits the approved edits to established surface roles. A parallel palette would split visual authority.
**Cost**: Existing tests/spec commentary that encode immutability must change, and regressions require explicitly scoped assertions.
**Trade-off accepted**: The old broad safety net for all colors is narrowed; named-role exact-value checks and non-palette stability replace it. This preserves integrity guarantees while allowing the required palette.

### Decision: Keep `--primary-*` unchanged
**Choice**: Preserve the mint brand/action scale and `--corp-primary: var(--primary-800)`; do not repurpose it for chrome/lime. Add the approved canonical roles separately. Before implementation, inventory all consumers: search evidence shows consumers in `primitives.css` (buttons, links, badges, shell legacy rules, assistant grammar/chat), `Dashboard.tsx` accents and KPIs, `tokens.css` aliases, and Storybook assertions/documentation.
**Alternatives considered**: Remap the scale to lime/forest; deprecate it immediately.
**Rationale**: Existing consumers extend well beyond shell and changing the scale has widespread semantic and contrast consequences. Dashboard's usages include `--primary-700`, `--primary-800`, `--primary-900` and a `color-mix`; primitive consumers include `--primary-100/200/700/800/900`.
**Cost**: Legacy mint remains available and some old consumers may retain distinct action appearance pending deliberate restyle.
**Trade-off accepted**: Avoid breaking action/brand meaning; accept temporary legacy usage, with changed components opting into new semantic roles only where measured and explicitly restyled.

### Decision: Keep shell composition at AppShell/PanelShell
**Choice**: `AppShell` remains route/page/data owner and passes current view, route navigation, user and notification data; `PanelShell` remains presentation and interaction owner. Extend `PanelShell` with responsive variants and smaller internal regions (sidebar search/grouping/user footer, desktop header, mobile header, tablet rail, bottom tabs, drawer) rather than creating another routing abstraction.
**Alternatives considered**: New parallel shell or navigation registry; migrate the native History API/router.
**Rationale**: Graph path confirms `AppShell.tsx --imports_from--> PanelShell.tsx`; `PanelShell.tsx` contains `NAVIGATION`; `panelRoutes.ts` references `PanelShell.tsx` and contains `PANEL_ROUTES`/`pathForRoute()`. Existing authority already filters admin-only nav. No route migration is in scope.
**Cost**: `PanelShell` has existing interaction complexity; internal decomposition must keep the focused ownership boundary without duplicating navigation policy.
**Trade-off accepted**: Preserve current route mechanics and build presentation around them; this forgoes a broad router/shell refactor.

### Decision: Use a native modal dialog for the drawer
**Choice**: Use browser-native `<dialog>` opened modally (`showModal`) for mobile/tablet drawer, with explicit React state and close lifecycle. Preserve menu trigger focus and restore it on dismissal; browser modal behavior supplies top-layer/inert background/focus containment, while code handles Escape/resize/scroll and explicit restoration consistently. If current browser support baseline cannot guarantee `showModal`, this is an implementation blocker to surface, not a reason to silently add a dependency.
**Alternatives considered**: Radix dialog (new dependency); hand-rolled `role=dialog` and focus trap (duplicates existing behavior and is currently implemented manually in PanelShell).
**Rationale**: No new dependency is allowed; native dialog is the minimum platform primitive for a modal drawer. The current hand-rolled implementation already uses refs, inert, scroll lock, Escape, and resize but duplicates complex focus machinery.
**Cost**: Native dialog styling and open/close synchronization need browser-level tests; native focus behavior varies slightly across engines and still requires verification.
**Trade-off accepted**: Prefer platform semantics and smaller maintenance surface; retain explicit lifecycle tests and fallback only if support evidence requires it.

### Decision: Resolve the no-white rule by computed role resolution
**Choice**: Token test resolves every canonical and `--corp-*` surface alias, plus supported derived `color-mix()` surface values, to RGB and rejects exact `(255,255,255)`. Keep the current derived brand-bg-elevated behavior only if its computed output stays non-white; otherwise retarget it to `--surface` or remove it from surface use.
**Alternatives considered**: Search for `#fff` spellings; ban all `color-mix()`.
**Rationale**: Equivalent white spellings, aliases, and derivations evade substring checks; banning useful derivation is unnecessary.
**Cost**: Resolver must support the finite CSS forms actually used and fail closed on unsupported surface expressions.
**Trade-off accepted**: A small purpose-built resolver in tests instead of broad CSS parsing; any new surface expression must extend tests before adoption.

### Decision: Keep tokens.ts mirror subset
**Choice**: No change to `tokens.ts` unless radius values are actually mirrored there; retain exact CSS parity assertions for spacing, radius, and z-index. Tune existing CSS `--radius-*` values only to achieve approximately 10px card and 14px dialog geometry; do not add a second semantic radius taxonomy. Keep `--shadow-1..3` declarations, remove card elevation use, reserve `--shadow-3` for dialog/drawer/overlay.
**Alternatives considered**: Add JS color tokens or new semantic radii; delete the lower shadows.
**Rationale**: Current JS mirror is the spacing/radius/z-index subset and colors stay CSS-authoritative. Owner explicitly locked radius naming strategy; spec requires all three shadows remain.
**Cost**: Existing visual-foundation aliases (`--elevation-raised`) and card tests must be adjusted to flat behavior.
**Trade-off accepted**: Keep compatibility tokens even if not used by cards, avoiding unrelated deletion while enforcing no material card elevation.

## Contrast Measurement

Computed using WCAG 2.x sRGB relative luminance: normalize each channel, linearize at 0.04045, calculate `0.2126R + 0.7152G + 0.0722B`, then `(Llighter + .05)/(Ldarker + .05)`. Results below are computed from the exact locked hex values. PASS is threshold-only and does not establish rendered-component compliance; semantic pairs use currently declared semantic values from `tokens.css` as listed below. “Open failure” means the locked pair cannot meet its required use without a token/foreground change.

| Foreground / boundary | Background | Ratio | Threshold and result / disposition |
|---|---|---:|---|
| `--text #111a2e` | `--bg #dbe1d6` | 13.01:1 | 4.5 PASS |
| `--text #111a2e` | `--surface #e8ebe4` | 14.40:1 | 4.5 PASS |
| `--text #111a2e` | `--header-bg #dee4db` | 13.40:1 | 4.5 PASS |
| `--text-muted #5a6469` | `--bg` | 4.55:1 | 4.5 PASS |
| `--text-muted #5a6469` | `--surface` | 5.04:1 | 4.5 PASS |
| `--text-muted #5a6469` | `--header-bg` | 4.69:1 | 4.5 PASS |
| `--text-on-dark #e9f0e9` | `--chrome-950 #012f1d` | 12.70:1 | 4.5 PASS |
| `--text-on-dark` | `--chrome-900 #073d2b` | 10.58:1 | 4.5 PASS |
| `--text-on-dark` | `--chrome-active #012214` | 14.60:1 | 4.5 PASS |
| `--text-on-dark-2 #88a599` | `--chrome-950` | 5.53:1 | 4.5 PASS |
| `--text-on-dark-2 #88a599` | `--chrome-900` | 4.61:1 | 4.5 PASS (lightest chrome surface; binding constraint) |
| `--text-on-dark-2 #88a599` | `--chrome-active` | 6.36:1 | 4.5 PASS |
| `--teal-500 #52babb` | `--chrome-950` | 6.38:1 | 4.5 PASS (label text) |
| `--teal-400 #6adbdf` | `--chrome-950` | 8.99:1 | 4.5 PASS (label text) |
| `--lime-500 #c6d529` | `--chrome-950` | 9.08:1 | 3.0 PASS (non-text active bar) |
| `--lime-700 #a2c312` title accent rule | `--bg` | 1.52:1 | DECORATIVE-ONLY non-text; title text carries meaning. |
| `--border #d5dad1` container hairline | `--bg` | 1.07:1 | DECORATIVE-ONLY; MUST NOT be the sole boundary of an interactive control. |
| `--border` container hairline | `--surface` | 1.18:1 | DECORATIVE-ONLY; MUST NOT be the sole boundary of an interactive control. |
| `--border-strong #7e858f` control boundary | `--surface` | 3.09:1 | 3.0 PASS; control boundaries resolve through this role. |
| `--border-strong` control boundary | `--bg` | 2.79:1 | 3.0 FAIL; MUST NOT be relied on for a control boundary placed directly on `--bg`. |
| Primary action: `--text-on-dark #e9f0e9` | `--chrome-950 #012f1d` action fill | 12.70:1 | 4.5 PASS; chosen semantic action pair. |
| `--danger #b71c1c` | `--bg / --surface` | 4.93 / 5.45:1 | 4.5 PASS |
| `--danger #b71c1c` | `--danger-bg #fdecea` | 5.74:1 | 4.5 PASS |
| `--danger-border #e57373` | `--danger-bg` | 2.61:1 | DECORATIVE-ONLY status reinforcement; MUST NOT be the only channel conveying status. |
| `--success #1b5e20` | `--bg / --surface` | 5.90 / 6.53:1 | 4.5 PASS |
| `--success #1b5e20` | `--success-bg #e8f5e9` | 7.00:1 | 4.5 PASS |
| `--success-border #81c784` | `--success-bg` | 1.79:1 | DECORATIVE-ONLY status reinforcement; MUST NOT be the only channel conveying status. |
| `--warning #8f5406` | `--bg` | 4.58:1 | 4.5 PASS |
| `--warning #8f5406` | `--surface` | 5.07:1 | 4.5 PASS |
| `--warning #8f5406` | `--warning-bg #fef3c7` | 5.48:1 | 4.5 PASS |
| `--warning-border #fcd34d` | `--warning-bg` | 1.29:1 | DECORATIVE-ONLY status reinforcement; MUST NOT be the only channel conveying status. |
| `--info #14788f` | `--info-tint #f0f9ff` | 4.79:1 | 4.5 PASS |

Semantic status badge borders are decorative reinforcement only and MUST NOT be the only channel conveying status. The `--border` container hairline is decorative and MUST NOT be the sole boundary of an interactive control; control boundaries resolve through `--border-strong`, which meets 3:1 on `--surface` but not `--bg`. Recompute all final primitive-specific pairs after implementation.

### Contrast Adjustments (Resolved 2026-09-30)

The owner approved adjusting the tokens that failed rather than accepting the failures. Adjusted values and their measured ratios:

| Token | Old | New | Measured |
|---|---|---|---|
| `--text-muted` | `#6e7a80` | `#5a6469` | 4.55:1 on `--bg`, 5.04:1 on `--surface`, 4.69:1 on `--header-bg` |
| `--text-on-dark-2` | `#729486` | `#88a599` | 4.61:1 on `--chrome-900`, 5.53:1 on `--chrome-950`, 6.36:1 on `--chrome-active` |
| `--warning` | `#a05e07` | `#8f5406` | 4.58:1 on `--bg`, 5.07:1 on `--surface`, 5.48:1 on `--warning-bg` |

Declared decorative instead of adjusted: `--border` container hairline (1.07:1 on `--bg`, 1.18:1 on `--surface`) — never the sole boundary of an interactive control; `--border-strong` carries control boundaries at 3.09:1 on `--surface` (2.79:1 on `--bg`, so controls must not sit boundary-only on `--bg`); `--lime-700` title accent rule (1.52:1 on `--bg`); semantic status badge borders (2.61:1 / 1.79:1 / 1.29:1 on their tints).

## Token Architecture

Declare the locked canonical roles once in `tokens.css :root`: chrome 950/900/active; bg/header-bg/surface/border; lime 500/600/700; teal 500/400; text/text-muted/text-on-dark/text-on-dark-2. Keep Inter as UI direction. `--corp-*` remains compatibility indirection (`--corp-bg`→`--bg`, surface/border/text/muted aliases to corresponding roles); keep `--corp-primary` targeting legacy `--primary-800`, never chrome. Preserve exact legacy `--primary-50..900` values until an independently approved migration covers the extensive CSS/dashboard/story consumers.

Set `--table-head-bg` to a non-white derived/semantic surface (prefer `var(--surface)` unless visual inspection requires a subtle differentiated sage), and set `--border-strong` only to a measured boundary role, not an assumed passing value. Semantic tints (`--danger-bg`, `--success-bg`, `--warning-bg`, `--*-tint`, `--info-tint`) remain semantically named, non-white surface fills; test every resolved tint and foreground. `--shadow-1..3` remain declared, but cards use none; overlay/drawer/dialog may use shadow-3. The old `--brand-bg-elevated` mix must resolve away from white and be included in surface resolution. Existing spacing and z-index are unchanged; existing radius keys are retained but values tuned. `tokens.ts` remains only spacing/radius/z-index mirror, with tests adjusted for changed radius values, no color mirror.

## Component and Shell Architecture

`AppShell` continues selecting the page and owns History API route transitions; `PanelShell` receives current view, `onNavigate`, user and notifications, then derives all presentation from `NAVIGATION` and route authority (`panelRoutes.ts`, `pathForRoute()`). Sidebar, header, mobile/tab/rail variants are extended composition, not new route primitives. Search is a new small sidebar control/filter over the existing role-filtered entries; grouped sections are presentation grouping of existing entries, not new destinations. Bottom tab set is explicitly Panel/dashboard, Conversaciones, Asistente/chat, Agenda, Clientes. Other authorized entries remain in drawer. Tablet rail is compact sidebar navigation with accessible names. Existing logo assets are consumed from `web/public/brand/`; expanded/mobile lockup uses `lumat-logo.png` with alt `Lumat`; compact mark uses `lumat-mark.png` alt empty/aria-hidden because the containing brand region carries accessible name `Lumat, panel operativo`.

Responsive tiers (existing token references 640/1024/1280): `<640`: dark mobile header, five-tab bottom bar, modal drawer; `640–1023`: tablet icon rail and modal drawer; `1024–1279`: desktop sidebar/header, collapse supported; `≥1280`: expanded sidebar by default, collapse supported. Keep exact breakpoints adjustable only with evidence from supplied geometry. Sidebar collapsed/expanded state is local `PanelShell` state and hidden labels remain accessible. Drawer state is local boolean, opened by menu, dismissed by close/outside/Escape or resize to desktop. Opening captures trigger, locks body scroll preserving prior overflow, makes content inert via native modal semantics, and moves focus into dialog; close restores focus to trigger if it remains connected. Resize crossing to desktop closes drawer and restores page state. Reduced-motion disables/shortens transform/opacity transitions without removing state feedback. Native dialog is chosen as described above; verify keyboard cycling, screen-reader naming, browser support, and viewport resize behavior.

Dashboard composition remains in existing `Dashboard.tsx`: quick access excludes Casos; today/quick-access and KPI metric group; assistant banner/card; activity trend/chart with explicit empty state; Motivos. Preserve current data and urgent-case operational data (the override removes only unified dashboard destination/shortcut; urgent cases remain in “Hoy” under existing contract). Apply reference hierarchy: title/green title rule and date, today actions, assistant banner, quick-access row, period KPIs, chart + Motivos; stack/reflow at mobile, KPI 2x2 and chart then Motivos; no fabricated data.

## Responsive Drawer State Sequence

`closed → open(trigger)` captures active trigger, calls native modal open, sets drawer state, locks scroll; `open → close(reason)` closes modal, releases lock, clears inert/scroll effects, restores focus. `reason ∈ {close button, Escape, backdrop, navigation, desktop resize}`. Only one drawer instance exists. Resize reconciliation runs while open and dismisses at `>=1024px`; cleanup restores prior body overflow even on unmount. Reduced motion affects animation only, never focus or state transition.

## File Changes

| File | Action | Description |
|---|---|---|
| `web/src/tokens/tokens.css` | Modify | Locked role families, aliases, no-white surfaces, semantic and radius/depth adjustments. |
| `web/src/tokens/tokens.test.ts` | Modify | Exact role asserts, resolved surfaces, measured contrast block, radius/depth, alias/non-palette integrity and JS mirror. |
| `web/src/tokens/tokens.ts` | Verify/no change expected | Keep spacing/radius/z-index subset; update values only if CSS radius mirror requires it. |
| `web/src/components/primitives/primitives.css` | Modify | Shared primitive colors, focus, no-white surfaces, flat cards, dialog geometry, shell style changes. |
| `web/src/components/domain/PanelShell.tsx` | Modify | Responsive shell composition, search/group sections, five tabs, modal drawer; preserve existing authority. |
| `web/src/components/domain/AppShell.tsx` | Modify only if props/route bridge needed | Keep route/page ownership; no route inventory changes. |
| `web/src/components/domain/panelRoutes.ts` | No route change expected | Existing route authority; tests ensure no invented route. |
| `web/src/components/pages/Dashboard.tsx` | Modify | Remove Casos quick-access card, update composition/accent use without dropping urgent data. |
| `web/src/components/style-boundary.test.ts` | Modify | Extend source checks to shell/dashboard sources as appropriate; no inline style/SVG. |
| `web/src/components/dependency-boundary.test.ts` | No change expected | Existing rule already protects production components from story imports; only extend if shell primitive boundary is altered. |
| `web/src/components/domain/AppShell.test.tsx`, `PanelShell.test.tsx` | Modify | Replace dashboard-to-Casos shortcut expectations; verify all shell states and role filtering. |
| `web/src/components/pages/Dashboard.test.tsx` and stories | Modify | No Casos shortcut; retain urgent cases and responsive representative states. |
| `web/src/stories/domain/AppShell.stories.tsx`, `web/src/stories/pages/PanelEntry.stories.tsx` | Modify | Updated geometry/state docs and viewport states. |
| `web/DESIGN_SYSTEM.md` | Modify | Final roles, surface/depth, shell, logo and honest contrast guidance. |

## Guard Test Changes

- **`tokens.test.ts`**: replace substring spot checks and legacy palette values with exact equality for each locked role; verify single `:root`, non-palette token stability where baseline fixture exists, aliases. Add recursive alias/derived surface resolver and reject pure white RGB, including surface-subtle/table-head/elevated/tints and corp aliases. Replace old contrast block with the table's actual role pairs; mark expected failures as explicit known-failure evidence until token/design correction lands (do not turn failures into passing threshold assertions). Keep no-hex walk. Update primary action chosen pair, radius expectations (~10/~14), flat-card/no-shadow expectation, and shadow-3 overlay expectation. Keep tokens.ts parity for space/radius/z-index.
- **`style-boundary.test.ts`**: include new shell-owned TSX sources in inline `<style>` rejection automatically (already source-wide); extend static inline-style allowlist checks to `PanelShell.tsx`/Dashboard if implementation eliminates their current CSS custom-property `style={{...}}` use. These two currently have dynamic style props, so do not blanket-ban without migrating them. Existing inline SVG source checks already include both.
- **`dependency-boundary.test.ts`**: retain unchanged unless a production shell control is introduced; ensure no production shell/component imports Storybook modules. No need to invent a primitive/test exception.

## Data Flow

```text
window History API → AppShell route/page + current view
                       │ user, notifications, navigate
                       ▼
                   PanelShell ── NAVIGATION + role filter
                  /     |      \
          desktop     tablet    mobile
          sidebar     rail      header + tabs
                  \     |      /
              modal drawer for overflow destinations
                       ▼
                    page content
```

## Slice and Work-Unit Plan

Target no more than 400 changed lines per review unit; split any measured diff exceeding budget, keeping dependencies ordered. Four proposal slices map to:

1. **Tokens, guards, direction**: WU1 canonical role values/aliases/radius/shadow in `tokens.css`; WU2 contrast and surface resolver/token guards in `tokens.test.ts`; WU3 final direction in `DESIGN_SYSTEM.md`. Keep token edits and guard evidence together, split documentation only if >400 lines.
2. **Primitive restyle**: WU4 controls/actions and semantic feedback (`primitives.css` sections + focused primitive tests); WU5 cards/tables/dialogs and their tests. Each <400 changed lines, no API changes.
3. **Responsive shell**: WU6 sidebar/header and desktop collapse/search/grouping; WU7 tablet/mobile surfaces, tab bar, dialog state/focus/accessibility; WU8 shell tests/stories and boundary guards. Keep each under 400 lines; if PanelShell implementation alone exceeds budget, split desktop and responsive transitions without splitting its tests from behavior.
4. **Dashboard consumer**: WU9 Dashboard visual hierarchy and Casos shortcut removal; WU10 Dashboard tests/stories at representative widths. Keep API/data state unchanged and preserve urgent-case content.

Work dependencies: WU1→WU2→WU4/5→WU6/7→WU9; WU3 can accompany WU1; tests/stories travel with each behavior-bearing unit. Global DS-GRAMMAR-1/T3 ownership must remain coordinated with `panel-grammar-global`; this plan does not take over its ClientesList/ClientFicha T3.

## Testing Strategy

| Layer | What to test | Approach |
|---|---|---|
| Unit | Exact tokens, alias resolution, surface resolution, contrast ratios, no Casos quick access | Vitest with computed WCAG formula and explicit failing-pair ledger; focused component tests. |
| Integration | `PanelShell` route callbacks, admin filtering, drawer lifecycle, keyboard/focus/resize/reduced motion; Dashboard data states | React Testing Library/jsdom for state and behavior; verify focus restore, no parallel route source. |
| Visual | Geometry and reflow | Storybook at 390/640/768/1024/1280 widths; compare only the six named supplied images for proportions/layout, not palette derivation. |
| Build | TypeScript and bundled assets | `npm run build`; confirm public logo URL handling under `BASE_URL`. |

Rendered browser verification remains required before claiming visual/accessibility conformance. Contrast table is static token evidence, not proof of all rendered combinations.

## Threat Matrix

Applicable: routing and shell interaction boundaries. N/A: shell commands, subprocesses, VCS/PR automation, executable-file classification, process integration.

| Boundary case | Status | Expected safe/failure behavior | Planned RED test |
|---|---|---|---|
| Unknown/malformed route | Applicable (existing `panelRoutes.ts`) | Existing parser falls back to dashboard; no new destination introduced. | Retain route parser invalid-path fallback tests; assert mobile tabs map only to existing route views. |
| Unauthorized admin destination | Applicable (`NAVIGATION`) | Role filter omits admin-only entries from sidebar, tabs, drawer/search. | Operator tests assert admin-only nav absent in every responsive representation. |
| Drawer keyboard escape/focus | Applicable (`PanelShell`) | Escape closes; focus returns to invoking menu button; Tab remains in modal. | RED keyboard open/traverse/escape/restore case. |
| Drawer background interaction and scroll | Applicable | Modal makes background inert; preserve and restore preexisting overflow; no stale lock after unmount. | RED test for inert/modal + prior overflow restoration, including cleanup. |
| Resize while drawer open | Applicable | Crossing desktop tier closes, unlocks and restores focus; resize within supported overlay tier leaves open. | RED dispatch resize across threshold and assert state/focus/scroll. |
| Navigation while drawer open | Applicable | Existing navigation callback executes once and closes drawer. | RED test verifies callback and close/restore. |
| Notifications/account surface | Applicable shell UI, existing behavior | Keep existing notification/route behavior; do not make decorative header control inert. | Existing notification tests plus header accessible-name/action test. |
| Shell command/subprocess/VCS/process | N/A | No such boundary is introduced. | None. |

## Migration / Rollout

No data migration. Source-only rollout; apply in token → primitive → shell → dashboard order. Roll back in reverse work-unit dependency order. Do not claim AA until open failures are either corrected and recomputed or explicitly limited to non-text/decorative contexts.

## Open Questions

- Contrast failures are not owner-gated questions, but implementation must select measured replacement roles for normal muted copy, warning foreground on general surfaces, required hairline boundaries, and the title rule before asserting conformance.
- Confirm supported browser baseline for native `<dialog>.showModal()` through project/browser test configuration; if inadequate, surface the evidence before replacing the design choice.
- `panel-grammar-global` DS-GRAMMAR-1/T3 ownership coordination remains a sequencing dependency from proposal; retain its amendment relationship and do not duplicate its dense-page work.

## Graph Check

Read `graphify-out/GRAPH_REPORT.md`; it reports AppShell, Dashboard, tokens.test and primitives.css among relevant hubs/communities. Consulted graph nodes/edges: `AppShell.tsx --imports_from--> PanelShell.tsx`; `PanelShell.tsx` contains `NAVIGATION`; `panelRoutes.ts <--references-- PanelShell.tsx` and undirected path `panelRoutes.ts — PanelShell.tsx — NAVIGATION`; queried `tokens.css`↔`primitives.css` and found no path (not evidence of a direct dependency); query surfaced `Dashboard()`, `Dashboard.tsx`, `PanelShell.tsx`, `AppShell.tsx`, `NAVIGATION`, `panelRoutes`, token and test nodes. The report's recorded build commit is `96a6f69b` and source metadata has previously been inconsistent; graph is structural guidance, while exact source was read directly. No graph refresh performed.

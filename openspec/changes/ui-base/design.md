# Design: UI Base

## Technical Approach

Keep production components authoritative and make Storybook a harness around them. Add one outer `withPanelShell` decorator, retain `withPanelSurface` as its inner content wrapper, and load both token and primitive CSS globally. Enforce the one-way `components → primitives/shared` boundary with a Vitest source scan. Implement only the specified first-slice mechanics, using the platform before dependencies. (Graph: `preview.ts → tokens.ts`; `app.tsx → AppShell.tsx → PanelShell.tsx`; `PanelShell.tsx → primitives`.)

## Architecture Decisions

| Option | Tradeoff | Decision |
|---|---|---|
| Shell decorator wraps `Story` in `PanelShell` with a deterministic fixture user; `withPanelSurface` remains inner | Adds one harness layer, but stories exercise the production shell | Choose; outer `withPanelShell`, inner existing surface, `fullscreen` behavior preserved. (Graph: `preview`, `PanelShell.tsx`.) |
| Native mechanics vs broad UI library | Native reduces dependencies; Radix is useful only for composite keyboard semantics | Native popover/CSS anchors/`<dialog>`; add only `@radix-ui/react-dropdown-menu` for menu. Radix has no combobox primitive: use native input + listbox semantics, so no combobox package is justified. CSS anchors are progressive enhancement under `@supports`; fallback is positioned popover content anchored by the trigger's containing block, with Popover API dismissal/focus retained. (Graph: `primitives.css`, `devDependencies`.) |
| Keep InboxThread vs remove it | It duplicates contracts already covered by `ConversationsList` and production-backed `ConversationThread` | Quarantine `InboxThread.stories.tsx` and its test under `web/.storybook/quarantine/pages/` as a reference. Do not promote its unique composite controls or create a second story owner. (Graph: `InboxThread.stories.tsx`, `ConversationThread.tsx`, `ConversationThread.stories.tsx`.) |

## Data Flow

`preview.ts` → `PanelShell` fixture → `withPanelSurface` → canonical production-backed story → production component → token/primitives CSS. Quarantined references are outside discovery and data flow.

Story imports may reference components. Component imports MUST NOT reference stories, except the exact compatibility imports in the two existing tests.

## File Changes

| File | Action | Description |
|---|---|---|
| `web/.storybook/preview.ts` | Modify | Add shell decorator, import `primitives.css`, preserve surface, define 640/1024/1280 presets plus permitted 390/768. |
| `web/src/components/primitives/` | Create/modify | Native popover, tooltip, dropdown presentation/positioning/dismissal/focus, `<dialog>` modal; CSS-only sidebar rail and skeleton; Radix menu; native combobox-class control. All use existing/`--corp-*` tokens, keyboard behavior, complete states, and 40px/44px sizing. |
| `web/src/components/shared/` | Modify | Complete the helper closure without adding story ownership to production. |
| `web/src/components/dependency-boundary.test.ts` | Create | Narrow source-import boundary test. |
| `web/src/stories/concept/AiAgentGrammar.{stories.tsx,stories.test.tsx}` | Delete | Stale concept copy. |
| `web/.storybook/quarantine/pages/ChatWithAgent.{stories.tsx,stories.test.tsx}` | Move | Quarantine with `web/.storybook/quarantine/README.md` marker `QUARANTINED — excluded from Storybook and Vitest`; do not discover/import it. |
| `web/.storybook/quarantine/pages/InboxThread.{stories.tsx,stories.test.tsx}` | Move | Quarantine composite reference with the existing marker; exclude it from Storybook discovery and Vitest. |
| `web/DESIGN_SYSTEM.md`, `web/package.json` | Modify | Record policy and add `@radix-ui/react-dropdown-menu`. |

## Interfaces / Contracts

The boundary test recursively scans `web/src/components/**` `.ts/.tsx` files for static and dynamic imports resolving under `web/src/stories/**`. Its allowlist is an exact `Set` of two repository-relative paths: `src/components/shared/closure.test.tsx` and `src/components/shared/helpers.test.tsx`; no glob, directory, suffix, or test-wide exception is permitted. Any other importer fails.

`withPanelShell` supplies a stable `User`, renders `<PanelShell user={fixture}>`, and passes Storybook `ctx` to the nested story. Viewport keys map to `--bp-sm/md/lg`; 390px and 768px remain named optional presets.

The panel target is Safari 26+, Chrome 125+, and Firefox 147+ on current operating systems, including iPhone 12+ hardware running current iOS. Capability follows the OS: an iPhone 12 on iOS 18 is below target and lacks anchors. The Popover API alone remains usable on Safari 17+; anchor positioning is guarded by `@supports` and falls back explicitly to containing-block positioning, never a silent polyfill. Formalize this browser-version target in `DESIGN_SYSTEM.md` (or a small `browserslist`) so it is not re-litigated.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | Primitive contracts | Vitest + Testing Library: roles, labels, states, keyboard events, dismissal, focus return, dialog `showModal/close`, and token-class contracts. |
| Integration | Boundary and viewport drift | Source-scan test rejects every non-allowlisted component→story import. Drift test parses `tokens.css` and `preview.ts`, asserting 640/1024/1280 equality and 390/768 presence. |
| Build | Harness and stories | `npm test`; `npm run build-storybook`. jsdom has no layout engine: tests MUST NOT claim real anchor geometry, responsive layout, or viewport rendering; those remain Storybook/manual checks. |

## Threat Matrix

N/A — no routing, shell commands, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary.

## Migration / Rollout

No data migration or feature flag. Revert the UI commit(s) to restore the prior story set, harness, dependencies, and docs.

## Open Questions

None.

Ponytail review cuts: no Radix combobox package, no icon dependency, no resizable panels, no broad component-library adoption, no Playwright/visual-regression suite, and no extra shell abstraction.

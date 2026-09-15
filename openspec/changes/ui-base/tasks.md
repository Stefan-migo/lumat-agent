# Tasks: UI Base

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | ~700–950 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 foundation/guards → PR 2 primitives → PR 3 harness/triage/docs |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|---|---|---|---|---|---|
| 1 | Boundary, Vitest exclusion, primitive RED tests | PR 1 | `cd web && npm test -- dependency-boundary` | N/A: source/config guards | Revert guard/config/test files |
| 2 | Token-mapped first-slice primitives | PR 2 | `cd web && npm test -- primitives` | `cd web && npm run storybook` interaction smoke | Revert `src/components/primitives/` and package lock |
| 3 | Harness, triage, policy docs | PR 3 | `cd web && npm test && npm run build-storybook` | Storybook smoke at 640/1024/1280 | Revert preview, quarantine, story, docs |

## Phase 1: Foundation and RED Guards

- [x] 1.1 **RED:** create `web/src/components/dependency-boundary.test.ts`; scan component `.ts/.tsx` imports and allow only exact `src/components/shared/closure.test.tsx` and `src/components/shared/helpers.test.tsx`.
- [x] 1.2 Extend the existing viewport-drift guard for `web/.storybook/preview.ts` against `web/src/tokens/tokens.css`; require 640/1024/1280 and permit 390/768 (guard-extension convention).
- [x] 1.3 Configure `test.exclude` in `web/vite.config.ts` for `**/.storybook/quarantine/**/*.test.tsx`; keep Storybook discovery limited to `src/stories/**`.

## Phase 2: First-Slice Primitives

- [x] 2.1 Make `web/src/components/primitives/` native popover/tooltip/dropdown presentation, dismissal, focus, and containing-block fallback; add Testing Library keyboard/focus/state tests first. — PR #187. The dropdown lands as the Radix menu in 2.3.
- [x] 2.2 Implement `<dialog>` modal and native combobox-class input/listbox in `web/src/components/primitives/`; test showModal/close, focus return, roles, keyboard navigation, and states first. — PR #188 and #189.
- [x] 2.3 Implement CSS-only sidebar rail and skeleton, plus Radix menu via `@radix-ui/react-dropdown-menu`; update `web/package.json`/lockfile and test 40px/44px sizing, tokens, labels, and keyboard states. — PR #190 and #191.
- [x] 2.4 **Added post-slice (gatekeeper finding):** make the 44px touch rule executable — the D7 test asserts exactly one `@media (hover: none)` block plus its required selector set, and `.combobox__option` rejoins the block. — PR #192.

## Phase 3: Harness and Story Ownership

- [x] 3.1 Modify `web/.storybook/preview.ts`: global `primitives.css`, outer `withPanelShell` with stable user/`PanelShell`, inner `withPanelSurface`, and token-aligned viewport presets. — PR #193. Shell-owning stories opt out with `parameters.panelShell = false` (PanelEntry, AppShell) so the harness never nests two shells.
- [x] 3.2 Delete `web/src/stories/concept/AiAgentGrammar.{stories.tsx,stories.test.tsx}`; move `ChatWithAgent.*` and `InboxThread.*` pairs to `web/.storybook/quarantine/pages/` with the README marker. — PR #194. Moves tracked as renames; `main.ts` and `preview.ts` untouched.
- [x] 3.3 Complete `web/src/components/shared/` helper closure without story imports; verify Dashboard, Clientes list/ficha, Conversations list/thread, Cases, KB, Settings, and Login stories remain under `web/src/stories/pages/`, with `main.ts` glob unchanged. — PR #193.

## Phase 4: Documentation and Verification

- [x] 4.1 Update `web/DESIGN_SYSTEM.md` with platform-first defaults, narrow Radix package scope, line-480 justification, Safari 26+/Chrome 125+/Firefox 147+ targets, anchor `@supports`, and containing-block fallback policy. — PR #195. Every documented claim verified against `primitives.css` and `package.json` before commit.
- [ ] 4.2 Run `cd web && npm test`, typecheck, and `npm run build-storybook`; manually smoke shell, viewport presets, dismissal, focus return, and quarantine exclusion. Do not claim jsdom geometry. — **Automated half done** (526 tests, `tsc -b` clean, Storybook built with 156 stories and zero quarantined entries). **Manual smoke still pending** — it needs a human in a browser and has not been claimed.

## Graph Check

Consulted `preview.ts`, `withPanelSurface()`, `PanelShell.tsx`, `primitives.css`, `web/package.json`, `dependency-boundary.test.ts`, `shared/toneMaps.ts`, `closure.test.tsx`, `InboxThread.stories.tsx`, and page components. Edges: preview→surface/shell, PanelShell→Avatar/primitives, stories→components, package→Vitest/Storybook, design→tokens/preview.

## Ponytail Task Review

`shrink`: combine viewport drift with the boundary slice; `native`: platform-owned modal/popover/combobox; `yagni`: no Radix combobox, icons, resizable panel, Playwright, visual regression, or extra shell abstraction. net: -6 tasks.

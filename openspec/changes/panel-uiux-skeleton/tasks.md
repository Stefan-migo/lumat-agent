# Tasks: Panel UI/UX Skeleton

## Review Workload Forecast

| Slice | Estimated lines | Focused proof | Rollback boundary |
|---|---:|---|---|
| 1. Routing and IA | 300 | `cd web && npx vitest run src/components/domain/panelRoutes.test.ts src/components/domain/AppShell.test.tsx` | route table, nav, segment wiring |
| 2. Header and settings | 320 | `cd web && npx vitest run src/components/pages/NotificationCenter.test.tsx src/components/pages/Settings.stories.test.tsx` | header actions, notification composition, push section |
| 3. Responsive shell | 360 | `cd web && npx vitest run src/stories/pages/PanelEntry.stories.test.tsx src/stories/domain/AppShell.stories.test.tsx` | shell CSS, drawer lifecycle, icons |
| 4. Login and shared chrome | 240 | `cd web && npx vitest run src/components/pages/LoginAuth.test.tsx src/components/shared/PageHeader.test.tsx` | login/PageHeader/token CSS |
| 5. Review and acceptance | 180 | `cd web && npx vitest run` plus `uv run pytest tests/` | stories, PWA assertions, test-only changes |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

Delivery: auto-chain; PRs merge in order. Slice 5 runs both full suites; backend files remain untouched.

## Phase 1: Slice 1 — Routing and Information Architecture

- [x] 1.1 **RED (PNL-APP-1, PNL-APP-21):** Add failing Vitest coverage for exactly eight role-filtered destinations, pathname-only parsing, `/cases` and `/advanced-dashboard` aliases, history safety, and Conversations/Cases selection without URL mutation.
- [x] 1.2 **GREEN:** Modify `web/src/components/domain/panelRoutes.ts`, `PanelShell.tsx`, and `AppShell.tsx` to implement the eight-item IA, role gates, internal `ConversationTab`, aliases, and accessible active state; preserve existing page/API ownership.

## Phase 2: Slice 2 — Header Notifications and Settings Composition

- [x] 2.1 **RED (PNL-APP-10, PNL-APP-22, NC-4):** Test bell/avatar names and focus, fetch-on-mount unread loading/zero/error states, mark-read reachability, logout, and Settings push permission/unsupported/fallback states.
- [x] 2.2 **GREEN:** Modify `PanelShell.tsx`, `AppShell.tsx`, `Settings.tsx`, `PushSettings.tsx`, `NotificationCenter.tsx`, and existing API/types only as needed; link the bell to the center and add no polling/realtime behavior.

## Phase 3: Slice 3 — Responsive Shell and Icon Coherence

- [x] 3.1 **RED (DS-RESP-1, DS-SHELL-6):** Add failing tests/stories for 390/640/768/1024/1280 tiers, 44px targets, Escape/outside/resize drawer behavior, inert background, scroll lock, focus return, reduced motion, overflow, and distinct inline icons.
- [x] 3.2 **GREEN:** Modify `PanelShell.tsx`, `web/src/components/primitives/primitives.css`, and `web/src/tokens/tokens.css` for tiered rail/drawer behavior, accessibility lifecycle, touch targets, overflow, motion, and semantic native SVGs.

## Phase 4: Slice 4 — Login and Tokenized Shared Chrome

- [ ] 4.1 **RED (DS-UI-LOGIN, DS-SHELL-6):** Test desktop two-region/mobile stacked LoginAuth, preserved username-safe errors and Spanish labels, absent `card--auth`, token usage, and responsive PageHeader action wrapping.
- [ ] 4.2 **GREEN:** Modify `web/src/components/pages/LoginAuth.tsx`, `web/src/components/shared/PageHeader.tsx`, and shared CSS to use `PageFrame`/existing tokens; remove inline auth chrome and the phantom class without broad page sweeps.

## Phase 5: Slice 5 — Stories, PWA Boundary, and Acceptance

- [ ] 5.1 Add Storybook states in `web/src/stories/{pages/PanelEntry.stories.tsx,pages/Login.stories.tsx,pages/Settings.stories.tsx,domain/AppShell.stories.tsx}` for shell tiers, roles, drawer, header states, segments, push, and login states.
- [ ] 5.2 **RED/GREEN (PNL-APP-22, PNL-APP-23):** Assert `web/src/pwa.ts` scope/cache exclusions and unchanged page contracts; run `cd web && npx vitest run` and `uv run pytest tests/`; record failures before fixes and final green evidence.

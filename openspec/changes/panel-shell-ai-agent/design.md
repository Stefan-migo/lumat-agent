# Design: Panel Shell AI-Agent Infrastructure

## Technical Approach

Keep the existing `AppShell` → `PanelShell` seam and add a finite native History API route module, with no router dependency or React routing hook. Promote the complete production helper closure into `web/src/components/shared/`, retain story re-export wrappers, and update every production import. Move the existing shell CSS into the already-loaded tokenized `primitives.css` boundary, preserving computed values and responsive markup. This implements PNL-APP-1, R-PRD-PG-2, and DS-SHELL-3 without visual redesign.

Graph Check consulted: `AppShell()`, `PanelShell()`, `app.tsx`, `AppShell.tsx`, `PanelShell.tsx`, `api.ts`, `types.ts`, `ClientFicha.tsx`, `ConversationsList.tsx`, `KbList.tsx`, `PageFrame.tsx`, `StateMessage.tsx`, and `toneMaps.ts`; extracted edge `AppShell.tsx --imports_from--> PanelShell.tsx` (shortest path: one hop).

## Architecture Decisions

| Option | Tradeoff | Decision |
|---|---|---|
| Native route table | Small parsing/normalization surface to test | Choose; finite routes need no library |
| Router package | More machinery and dependency; solves future scale not required now | Reject |
| `components/shared/` closure | One layer usable by pages and primitives without upward imports | Choose; wrappers re-export unchanged contracts |
| Dedicated shell CSS file | Clear ownership but another global stylesheet boundary | Reject; `primitives.css` is already imported by `main.tsx` and guarded by token tests |
| Role-based redirect | Hides the requested deep link and can turn 403 into navigation ambiguity | Reject; render the page’s existing permission state |

## Data Flow

`window.location.pathname` → `parsePanelPath()` → `PanelRoute` → `AppShell` page branch

Navigation link/callback → `history.pushState()` → state update; browser back/forward → `popstate` → same parser. Initial canonicalization and unknown routes use `replaceState()` to `/panel/app/`.

## File Changes

| File | Action | Description |
|---|---|---|
| `web/src/components/domain/panelRoutes.ts` | Create | Typed `PanelRoute`, route table, parser, normalizer, and path builders for nine views plus numeric client/conversation IDs. |
| `web/src/components/domain/AppShell.tsx` | Modify | Initialize from URL, subscribe/cleanup `popstate`, push/replace history, and compose drill-down state. |
| `web/src/components/domain/PanelShell.tsx` | Modify | Consume route paths, render anchors with `aria-current`, remove injected style block; retain drawer/focus/collapse behavior. |
| `web/src/components/primitives/primitives.css` | Modify | Append the unchanged shell rules, replacing only representable dimensions with equivalent existing-token expressions. |
| `web/src/components/shared/{EmptyState,DataTable,PageHeader,StatCard,PageFrame,StateMessage,toneMaps}.{tsx,ts}` | Create | Production helper closure. |
| `web/src/stories/pages/_shared/{...}` | Modify | Thin re-export wrappers and tests remain story-compatible. |
| `web/src/components/pages/*.tsx`, `ClientMemories.tsx`, `StatusBadge.tsx` | Modify | Remove all production imports from `stories/`; convert client hashes and drill-down callbacks to route navigation. |
| `web/src/components/domain/AppShell.test.tsx`, relevant page/story tests | Modify/Create | History, boundary, role, CSS, and compatibility coverage. |

## Interfaces / Contracts

```ts
type PanelRoute = { view: PanelView; clientId?: number; conversationId?: number };
function parsePanelPath(pathname: string): PanelRoute;
function pathForRoute(route: PanelRoute): string;
function pathForView(view: PanelView): string;
```

Normalize repeated/trailing slashes, use pathname only (ignore query/hash), require positive decimal IDs, and decode safely. Valid paths are `/panel/app/`, `/clients`, `/conversations`, and the explicit `/:id` drill-downs. Invalid or outside-base paths resolve to the dashboard and are canonicalized with `replaceState`. Admin deep links remain routable for operators; KB/Settings retain their existing 403 state.

## Testing Strategy

| Layer | What to Test | Approach / slice boundary |
|---|---|---|
| Unit | Parser, builders, normalization, unknown fallback | Pure Vitest tests; Slice 1 RED first |
| Integration | URL navigation, refresh/deep-link, push/replace, popstate, drill-down back/forward, `aria-current`, operator 403 | jsdom `AppShell.test.tsx` and page tests; Slice 1 |
| Boundary | No production import from `stories/`; wrapper exports and CSS token guard | Vitest source scans; Slices 2–4 |
| Regression | No PanelShell injected `<style>`; drawer, collapse, focus, roles, reduced motion | Existing shell tests plus source/DOM assertions; Slices 5–7 |

## Threat Matrix

The UI routing boundary is applicable: malformed/out-of-base paths safely resolve to dashboard; unauthorized deep links render permission denial without crash or bypass; history listeners are cleaned up. In the supplied matrix, Documentation-like paths, Git repository selection, Commit state, Push state, and PR commands are all `N/A` because this change executes no documentation-like files, VCS commands, subprocesses, or PR automation; therefore no tests are required for those rows.

## Migration / Rollout

No data migration or flag. Auto-chain stacked-to-main slices, each below 400 authored changed lines: (1) route module/AppShell/navigation, (2) four core helper promotions, (3) PageFrame/StateMessage/toneMaps promotion, (4) production import and hash-link closure, (5–7) shell CSS moved in three cohesive chunks and injection removed with guards. Each slice has focused RED tests, verification, and reversible file ownership.

## Open Questions

None.

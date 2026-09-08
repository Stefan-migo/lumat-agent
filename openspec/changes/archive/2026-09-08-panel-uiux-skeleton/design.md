# Design: Panel UI/UX Skeleton

## Technical Approach

Evolve the existing `PanelShell`/`AppShell` seam and typed History API; add no router, icon package, CSS framework, or backend behavior. Keep page components and serializers authoritative. The shell exposes eight destinations; compatibility routes remain internal dispatch cases. Conversations owns a `Conversaciones|Casos` segment; Cases keeps its API. The header owns notification and identity actions; Settings composes push UI.

## Architecture Decisions

| Option | Tradeoff | Decision |
|---|---|---|
| New router/shell | Larger churn and deep-link/PWA risk | Extend `panelRoutes.ts`, preserving native History |
| Header unread polling/realtime | Misleading contract and new backend coupling | Fetch once on mount via existing notifications API; no polling/realtime |
| Reuse one generic icon | Cheap but semantically ambiguous | Add distinct inline SVGs per destination/action |
| Rewrite page bodies | Better consistency later, high scope | Change chrome/composition only; defer redesigns |

`Asistente Lumat`, KB, and Configuración retain current role gates. Legacy `cases` and `advanced-dashboard` stay parseable and render existing pages, but are omitted from navigation.

## Data Flow

```text
URL → parsePanelPath → AppShell route → existing page/API
                              ↑
PanelShell navigation/header ─┘
                              └→ listNotifications → badge; center → markNotificationRead
```

The Conversations/Cases segment is internal state; changing it does not change the browser URL. The badge derives only from mounted `listNotifications`; loading is labelled, zero shows no number, and failure is unknown/error. Existing read actions remain authoritative.

## File Changes

| File | Action | Description |
|---|---|---|
| `web/src/components/domain/PanelShell.tsx` | Modify | Eight-item IA, segment active state, bell/badge, avatar menu/logout, inline SVGs, drawer accessibility lifecycle. |
| `web/src/components/domain/AppShell.tsx` | Modify | Path dispatch, internal segment state, compatibility rendering, notification wiring, Settings composition. |
| `web/src/components/domain/panelRoutes.ts` | Modify | Pathname-only typed route parsing and canonical paths; accept `/cases` and `/advanced-dashboard` safely. |
| `web/src/components/pages/{Settings,PushSettings,NotificationCenter}.tsx` | Modify | Push composition and notification summary without removing states. |
| `web/src/components/pages/LoginAuth.tsx` | Modify | Two-region tokenized frame and mobile stack; remove `Card`, `card--auth`, and inline styles. |
| `web/src/components/shared/PageHeader.tsx` | Modify | Tokenized classes; responsive action wrapping. |
| `web/src/components/primitives/primitives.css`, `web/src/tokens/tokens.css` | Modify | Tokenized shell/login/header classes and responsive tiers with touch, overflow, and motion rules. |
| `web/src/stories/**`, focused `*.test.tsx` | Modify | Width/state stories plus route, accessibility, badge, segment, push, and login tests. |
| `web/src/pwa.ts` | Verify only | Confirm scope and cache exclusions remain unchanged. |

## Interfaces / Contracts

```ts
type PanelRoute = { view: PanelView; clientId?: number; conversationId?: number; automationRuleId?: number };
type ConversationTab = "conversations" | "cases"; // internal UI state, not URL state
```

`panelRoutes.ts` parses pathname only. `/panel/app/conversations` renders the Conversations surface with an internal `ConversationTab`; `/panel/app/cases` remains a pathname compatibility route rendering `CasesList`. `/panel/app/advanced-dashboard` remains a non-menu legacy route. Invalid/encoded paths fall back to Panel; existing API/page authorization remains enforced.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | Pathname-only route parsing/canonicalization; internal tab state; badge state mapping; permission preservation | Vitest pure tests and component tests; assert no query parameter is required |
| Integration | Eight nav items, role filtering, segment switch without URL mutation, `/cases` and `/advanced-dashboard` aliases, history, avatar/logout, drawer Escape/outside/resize, inert body and scroll lock; notification fetch/read/error; Settings push states | Testing Library with mocked existing API and browser globals |
| Storybook | 390/640/768/1024/1280 shell tiers, admin/operator, drawer/rail, header zero/unread/error/menu, Conversations/Cases, Settings push, login desktop/mobile/error/loading | Extend `PanelEntry`, `AppShell`, `Login`, `Settings`; add notification-header states |
| Acceptance | PWA exclusions and unchanged page/API contracts | `uv run pytest tests/` and `cd web && npx vitest run` |

## Threat Matrix

All threat-matrix rows are **N/A**: there is no documentation execution, Git selection, commit, push, PR command, subprocess, or VCS automation boundary. Route tests cover malformed paths, aliases, and authorization safety.

| Boundary | Applicability | Safe/failure behavior and RED test |
|---|---|---|
| Documentation-like paths | N/A — no execution classification | No task/test. |
| Git repository selection | N/A — no Git command | No task/test. |
| Commit state | N/A — no commit automation | No task/test. |
| Push state | N/A — no push automation | No task/test. |
| PR commands | N/A — no PR automation | No task/test. |

## Migration / Rollout

No migration required. Ship shell/login slices; preserve service-worker scope `/panel/app/` and API/HTML exclusions. Revert UI commits if acceptance fails.

## Open Questions

- None blocking. Dashboard metric unification, page redesigns, realtime unread behavior, dark mode, and dependency changes remain deferred.

## Graphify Consultation

Consulted `PanelShell.tsx`/`NAVIGATION` → `AppShell.tsx` → `panelRoutes.ts`; `LoginAuth.tsx` → `PageFrame`; notification/push → `api.ts`; `Settings.tsx`; `pwa.ts`; and token/primitives CSS. Graph report: `graphify-out/GRAPH_REPORT.md` (built from `eb990dcf`; stale, not rebuilt).

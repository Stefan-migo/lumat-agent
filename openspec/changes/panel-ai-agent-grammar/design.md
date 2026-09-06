# Design: Panel AI-Agent Grammar

## Technical Approach

Choose Approach 1: evolve the existing `AppShell` → `PanelShell` seam and restyle conversation surfaces. It is smallest, preserves History/data contracts, and leaves C a clean boundary. A universal three-column shell wastes dense-page width; a separate shell duplicates navigation and accessibility. The tradeoff is explicit slots for inspector, activity, and active-thread content.

Graph nodes: `AppShell.tsx`, `PanelShell.tsx`, `AppShell()`, `PanelShell()`, `panelRoutes.ts`, `ConversationThread.tsx`, `ConversationsList.tsx`, `AgentChat.tsx`, `ClientFicha()`, `AiAgentGrammar.stories.tsx`, `api.ts`, `StatusBadge.tsx`, `primitives.css`, `tokens.css`, `DESIGN_SYSTEM.md`. Edges: `AppShell.tsx` → shell/thread; pages → `api.ts`; `activeThreads` is story-local. The story is reference.

## Architecture Decisions

| Decision | Choice | Alternatives / rationale |
|---|---|---|
| Shell contract | Add optional `activeThreads` and `inspector` render slot; shell never fetches. | Reject shell-owned `listConversations()`: network coupling and no customer names. Graph: `PanelShell.tsx` → `AppShell.tsx` → `api.ts`. |
| Route context | Keep `PANEL_ROUTES`, parsing, pushState, popstate, and fallback unchanged; add only a narrow conversation-detail predicate if needed. | No router or route fork. Graph: `panelRoutes.ts` → `AppShell()`. |
| Layout | Expanded rail is about 15rem, compact about 4rem; inspector is conditional and approximately 18rem only when supplied. | No permanent three-column frame; preserves dense working width. Graph: `PanelShell()` → page components. |
| Styling | Move stable AiAgentGrammar rules into `primitives.css`; use existing tokens first and no shell `<style>`. | Do not duplicate story-local CSS or add dependencies. |

## Data Flow

`AppShell` parses route → selects page and optional inspector/context → `PanelShell` renders rail/state → page owns existing `useAsyncData`/API calls → primitives render states. `activeThreads` is presentational:

```ts
type ActiveThreadsState =
  | { status: "loading" | "empty" | "error" | "placeholder"; message?: string }
  | { status: "ready"; threads: Array<{ id: number; label: string; status: ConversationState; active?: boolean }> };
```

`ConversationState` aliases the exported production union from `types.ts` (`"bot" | "human" | "closed"`), used by `ConversationsList`/`ConversationThread` and their API calls. Because `PanelShell` never fetches, `ready` is reachable only through tests/stories or an explicit parent-supplied prop (for example, a future C-owned provider); production defaults to the truthful placeholder/empty state.

No enrichment, shell retry, fabricated rows, polling, or realtime transport is introduced.

## File Changes

| File | Action | Description |
|---|---|---|
| `PanelShell.tsx` | Modify | Add semantic rail/active-thread regions, compact behavior, optional contract/slot; preserve role filtering, focus, drawer, labels, logout. |
| `AppShell.tsx`, `panelRoutes.ts` | Modify | Pass conversation context/inspector only where route context exists; preserve all History outcomes and page ownership. |
| `primitives.css` | Modify | Add token-only rail, bubble, activity, handoff, composer, inspector, responsive, and reduced-motion classes. |
| `ConversationThread.tsx`, `ConversationsList.tsx`, `AgentChat.tsx`, `ClientFicha.tsx` | Modify | Apply agent grammar to chat/list chrome; retain API, mutations, authorization, tables, cards, badges, and state primitives. |
| `ChatWithAgent.stories.tsx`, `InboxThread.stories.tsx`, concept/test files | Modify | Promote/test stable visual contracts without wiring mocks into production. |

Message rows become directional bubbles with `Avatar`, author labels, `StatusBadge`, retry controls, handoff text, and `Textarea`/`Button`. `ConversationsList` remains a `DataTable`; `ClientFicha` retains cards and history tables.

## State Model

- Rail: expanded, compact (active-thread region may be hidden), and no supplied data (truthful placeholder); supplied loading/empty/error use visible `status`/`alert` semantics.
- Thread: loading, loaded, empty, error/denied; failed delivery retains retry and submitted content behavior.
- Composer: enabled only when current persisted conversation is human-owned and `reply_window_open`; disabled for closed window or not-taken/bot ownership; mutation busy may show a non-realtime processing label. No fake streaming state or “writing” animation.
- Internal chat: loading, persisted empty, processing during existing `sendChatMessage`, failed/retry, and forbidden. Processing is not streaming truth.
- Authorized privileged-action refusal: render the existing persisted refusal message/state in the current thread, without new privileged tools or changed escalation copy. Preserve the concrete behavior where `"Delete all clients"` persists a refusal containing `"approved operational workflow"` and makes no model call (`tests/integration/test_h4_chat.py:84-94`).

## Accessibility, Tokens, and Responsive Behavior

Use landmarks/headings, `aria-current`, labels, `role=status`/`alert`, visible disabled reasons, existing focus rings, and keyboard drawer behavior. `<640px`: one column and navigation drawer; `640–1023px`: compact navigation; `1024px+`: persistent rail; inspector only when it fits. Preserve reduced motion and critical actions.

Map rail to `--primary-800/700`, `--brand-lime`, `--surface`; bubbles to `--surface`, `--primary-800`, `--border`; activity to `--info`, `--brand-aqua`, `--info-tint`; handoff to warning roles; composer/inspector to surface/border/corp roles. Add a semantic token only after a repeated consumer rule cannot be expressed by these roles; initial design adds none.

## Testing Strategy

Extend `AppShell.test.tsx` for compact/role-safe rail, active-thread states, no fetch, inspector conditionality, and unchanged History/deep links. Extend `AppShell.stories.test.tsx`/concept tests for token/no-hex/no-style and viewport contracts. Extend page tests for direction, identity, loading/empty/error, retry, disabled reasons, processing, authorization, and retained list/ficha primitives. Keep `InboxThread`/`ChatWithAgent` story tests as visual contracts.

## Slice Feasibility

Natural slices: shell contract/CSS; thread/list presentation; internal `AgentChat`; inspector/client-ficha alignment; stories/regressions. Each must compile and keep tests green; do not land a prop without its render path or a class without a consumer. Risks are route breakage and behavior changes replacing the message table.

## Threat Matrix

Applicable: routing (History/deep links/unknown paths); executable/process, subprocess/VCS/PR: N/A. Safe behavior is unchanged route normalization and no new shell process/network boundary. RED tests: `AppShell.test.tsx` History cases plus no-shell-fetch assertions. No shell retry or fabricated data.

## Migration / Rollout

No migration required. C later supplies live active-thread data and realtime semantics.

## Open Questions

- None blocking. C must decide whether live rail data comes from a dedicated summary endpoint or composed existing endpoints.

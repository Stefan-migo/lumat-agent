# Design: Panel H2/H4 UI Advance (Inbox + Chat)

## Technical Approach

Page-first, additive, Storybook-only (R-PRD-PG-13). Reuse the shipped `_shared/` helpers (DataTable, PageHeader, FlashMessage, EmptyState, toneMaps) + the tokenized inline-style bubble pattern from `ConversationThreadBubbles`; composers/chips from `Textarea`+`Button` + tokens — **zero new primitives, zero CSS** (guard R-PRD-PG-1). Two chained batches: B1 inbox (H2), B2 chat (H4). H1 `ConversationThread` untouched (R4).

## Architecture Decisions (D#)

| # | Decision | Options | Chosen |
|---|---|---|---|
| D1 | InboxThread scope | New story vs mutate `ConversationThread` | **New `InboxThread.stories.tsx`** — H1 shows read-only auto-channel (HH-5) + DataTable; inbox needs bubbles + composer + state controls; mutating violates R4. |
| D2 | Chat data shape | Reuse `Conversation`/`Message` vs dedicated | **Dedicated `AgentChatMessage {id, role:'admin'\|'agent', text, created_at}`** (R3, R-PRD-PG-12) — WhatsApp `Message` is inbound/outbound media model; chat is a separate H4 system view. |
| D3 | Assignee source | Inline in story vs shared `users.ts` | **Dedicated `users.ts`** exporting `UserRef[]` (R2); `cases.ts` re-imports it to kill duplication (existing `users` export preserved). |
| D4 | Composer disabled semantics | Disable only on closed vs closed+bot/stale | **Disabled when closed (S3)**; bot/paused/outside-window variants also show `ComposerDisabled` (stale/bot/paused support it per R-PRD-PG-10). Closed label "outside 24h window"; bot label "bot paused". |
| D5 | State domain | Enum/union type vs string+test | **Keep `Conversation.state` a plain `string`** (R-PRD-PG-14); domain `bot|human|closed` enforced by mock values + test; renders `<StatusBadge status={c.state as Status}>`. |
| D6 | `"open"` fix | Leave vs correct | **Correct conv 101 `"open"`→`bot`** (R1); add bot + stale (>24h) conversations + outbound human-reply `Message` row. |
| D7 | AgentStatus indicator | New component vs `.spinner` | **Reuse existing `.spinner` class** in a story-local inline block (no new component), `status: 'idle'|'processing'`. |

## Data Flow

```
conversations.ts ──▶ ConversationsList.stories ──▶ DataTable(StatusBadge, users.ts) ──▶ filter Select
conversations.ts ──▶ InboxThread.stories ──▶ bubbles + FlashMessage(window) + Textarea/Button + state Select
chat.ts ──▶ ChatWithAgent.stories ──▶ PageHeader + bubbles + Avatar + AgentStatus(.spinner) + chips + composer
```

- Assignee display: `const userName = (id) => users.find(u => u.id === id)?.username ?? "—"` (mirrors `responsibleLabel` pattern).
- `AgentStatus`: `idle` → text "Agent idle"; `processing` → `.spinner` + "Agent is thinking…" (Ag-agentThinking variant drives composer `disabled`).
- 24h window: `const open = now - last_message_at < 24h` → `FlashMessage tone=success/warning` open or `tone=danger` closed; closed disables send Button.

## Component/Story Structure (excludeStories + variants)

- **ConversationsList**: `ConversationsListView` (added state `<StatusBadge status={c.state as Status}>`, assignee column, row highlight `background: var(--warning-bg)` for `human`, filter-by-state `Select` + filtered rows) + `ConversationsListEmpty`; variants `Default`, `FilterByState`.
- **InboxThread** (new): exports `InboxThreadView`, `InboxThreadStateControls`, `InboxComposer`; variants `ComposerEnabled`, `ComposerDisabled(closed)`, `ComposerDisabled(bot)`, `OutsideWindow`. Bubbles copy `ConversationThreadBubbles` inline grid (data-bubble, direction aria-label).
- **ChatWithAgent** (new): exports `ChatWithAgentView`, `SuggestionChips`, `AgentStatusBar`; variants `Default(idle+chips+enabled)`, `AgentThinking(processing+disabled composer)`.

## File Changes

| File | Action | Responsibility |
|---|---|---|
| `web/src/stories/pages/_shared/mockData/users.ts` | Create | Canonical `UserRef[]` (D3) |
| `web/src/stories/pages/_shared/mockData/users.test.ts` | Create | Fidelity + unique ids |
| `web/src/stories/pages/_shared/mockData/conversations.ts` | Modify | `"open"`→`bot` (D6), +bot, +stale, +human outbound row |
| `web/src/stories/pages/_shared/mockData/conversations.test.ts` | Modify | Assert no `"open"`, all in `{bot,human,closed}`, stale/window present |
| `web/src/stories/pages/_shared/mockData/cases.ts` | Modify | Re-export `users` from `users.ts` (D3) |
| `web/src/stories/pages/_shared/mockData/chat.ts` | Create | `AgentChatMessage[]` + `AgentStatus` (R3) |
| `web/src/stories/pages/_shared/mockData/chat.test.ts` | Create | Shape fidelity, idle/processing coverage |
| `web/src/stories/pages/ConversationsList.stories.tsx` | Modify | State+assignee columns, highlight, filter variant |
| `web/src/stories/pages/ConversationsList.stories.test.tsx` | Modify | State badge, assignee, filter scenarios |
| `web/src/stories/pages/InboxThread.stories.tsx` | Create | H2 inbox (D1) |
| `web/src/stories/pages/InboxThread.stories.test.tsx` | Create | Composer + window + controls |
| `web/src/stories/pages/ChatWithAgent.stories.tsx` | Create | H4 chat (D2) |
| `web/src/stories/pages/ChatWithAgent.stories.test.tsx` | Create | idle/thinking + composer |

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| `<ConversationsList>.test` | R8: state badge (`data-tone`), assignee cell, human-row highlight, `FilterByState` narrows rows | RTL |
| `<InboxThread>.test` | R9/R10: composer enabled vs disabled(closed/bot/outside-window), FlashMessage open/closed, state controls exchange (Tomar→human, Cerrar→closed, Volver a bot) | RTL |
| `<ChatWithAgent>.test` | R11: idles + chips + enabled composer; AgentThinking shows `.spinner` + disabled composer | RTL |
| `chat.test.ts` / `users.test.ts` | R12: `AgentChatMessage` shape + `AgentStatus` idle/processing; `UserRef` fidelity | unit |
| `conversations.test.ts` | R14: every state ∈ {bot,human,closed}, no `"open"` | unit |
| Gates | R13: `npm test`, `npx tsc -b`, `npm run build-storybook` green; zero `components/**`/`.storybook/main.ts`/CSS edits | CI |

## Threat Matrix

`N/A` — additive Storybook-only (stories, `_shared/` mocks, tests). No routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary.

## Batch/PR Plan

**B1 Inbox (~330 lines)**: users.ts(+test), conversations.ts edits(+test), cases.ts re-export, ConversationsList story(+test) edits, InboxThread story(+test). Verify: `npm test` + build-storybook green.
**B2 Chat (~280 lines)**: chat.ts(+test), ChatWithAgent story(+test). Verify: green. Auto-chain, stacked-to-main, work-unit commits (`feat(web):` per slice).

## Migration / Rollout

No migration. No flags. Rollback = delete new files + revert the 2 edits (ConversationsList story, conversations/cases mocks).

## Graph Notes

Consulted (graph stale 2026-08-19; structural nodes valid): `ConversationsList.stories.tsx`, `ConversationThread.stories.tsx`, `ConversationsList.stories.test.tsx`, `mockData/conversations.ts`, `mockData/cases.ts`, `mockData/clients.ts`, `DataTable.tsx`, `PageHeader.tsx`, `FlashMessage.tsx`, `toneMaps.ts`, `EmptyState.tsx`, communities 51/66/36/22/92/57/67.

## Open Questions

- None blocking. (R4/H1 preserve confirmed.)

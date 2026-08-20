# Tasks: Panel H2/H4 UI Advance (Inbox + Chat)

> Change: `2026-08-20-panel-h2-advance` · Project: LumatAgent · Date: 2026-08-20
> Storybook-only additive delta: H2 inbox + H4 chat. Zero new primitives/CSS, zero `web/src/components/**`/.`storybook/main.ts` edits (R-PRD-PG-13). H1 `ConversationThread` untouched (R4/D1). Strict TDD. Numbering: `T1.x`=B1 Inbox, `T2.x`=B2 Chat.

## Review Workload Forecast

Estimated changed lines: ~610 (B1 ~330 · B2 ~280)

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Medium

Two stacked PRs (PR1=B1, PR2=B2), auto-chain — each batch <400 lines, total >400.

### Suggested Work Units

| Unit | PR | Focused test | Runtime harness | Rollback boundary |
|------|----|--------------|-----------------|-------------------|
| B1 Inbox | PR1 | `cd web && npm test && npx tsc -b` | `storybook` → ConversationsList, InboxThread | Delete users.ts(+test)/InboxThread.stories.*; revert conversations/cases/ConversationsList edits |
| B2 Chat | PR2 | `cd web && npm test && npx tsc -b` | `storybook` → ChatWithAgent | Delete chat.ts(+test)/ChatWithAgent.stories.* |
| Reqs | R-PRD-PG-8:T1.1,T1.2,T1.5,T1.6 · PG-9/10:T1.7,T1.8 · PG-11:T2.2,T2.3 · PG-12:T1.3,T1.4,T2.1 · PG-13:all gates · PG-14:T1.1,T1.2 | D# | D1→T1.8·D2/R3→T2.1·D3→T1.3,T1.4·D4→T1.8·D5→T1.6·D6/R1→T1.2·D7→T2.3 | |

## Phase 1 — B1 Inbox (T1.x, PR 1)

Gate: `cd web && npm test && npx tsc -b && npm run build-storybook` green; diff web/-only.

- [x] **T1.1** RED: `conversations.test.ts` — every `state`∈{bot,human,closed}, no `"open"`, bot/stale(>24h)/human-outbound rows present. [R-PRD-PG-14]
- [x] **T1.2** GREEN: `conversations.ts` — conv 101 `"open"`→`bot` (R1/D6), add bot/stale convs, add outbound human-reply `Message` 9007. [R-PRD-PG-8,14 · Deps: T1.1]
- [x] **T1.3** Test-first: `users.ts` (canonical `UserRef[]`, ≥3 rows) + `users.test.ts` (`{id,username}`, unique ids). [R-PRD-PG-12]
- [x] **T1.4** `cases.ts` — re-export `users` from `users.ts` (D3), keep export green; adjust `cases.test.ts` import. [R-PRD-PG-12 · Deps: T1.3]
- [x] **T1.5** RED: `ConversationsList.stories.test.tsx` — `data-tone` status badge, assignee cell, human-row highlight, `FilterByState` narrows rows. [R-PRD-PG-8 · Deps: T1.2,T1.3]
- [x] **T1.6** GREEN: `ConversationsList.stories.tsx` — `StatusBadge` state column, assignee from `users`, human-row `--warning-bg` highlight, filter-by-state `Select` + `FilterByState` variant (D5). [R-PRD-PG-8 · Deps: T1.5]
- [x] **T1.7** RED: `InboxThread.stories.test.tsx` — composer enabled vs disabled(closed/bot/outside-window), FlashMessage open/closed, state controls (Tomar→human, Cerrar→closed, Volver a bot). [R-PRD-PG-9,10 · Deps: T1.2]
- [x] **T1.8** GREEN: `InboxThread.stories.tsx` — bubbles grid + composer (Textarea/Button) + state controls + 24h FlashMessage (open success/warning, closed danger); variants ComposerEnabled/ComposerDisabled(closed|bot)/OutsideWindow (D1,D4). [R-PRD-PG-9,10 · Deps: T1.7]

## Phase 2 — B2 Chat (T2.x, PR 2)

Gate: same as PR1; index includes ChatWithAgent.

- [ ] **T2.1** Test-first: `chat.test.ts` (shape `{id,role,text,created_at}`, `AgentStatus` idle/processing) + `chat.ts` (D2/R3 — dedicated, not `Conversation`). [R-PRD-PG-12]
- [ ] **T2.2** RED: `ChatWithAgent.stories.test.tsx` — Default: header+bubbles+Avatar+idle+chips+enabled; AgentThinking: `.spinner`+disabled. [R-PRD-PG-11 · Deps: T2.1]
- [ ] **T2.3** GREEN: `ChatWithAgent.stories.tsx` — PageHeader + bubbles + Avatar + `AgentStatusBar` (idle / `.spinner`+thinking, D7) + `SuggestionChips` + Textarea/Button composer; variants Default / AgentThinking (disabled). [R-PRD-PG-11 · Deps: T2.2]

## Lifecycle Gates

- [ ] Bounded review on PR1 (B1) before chaining PR2. <!-- sdd-owner: parent -->
- [ ] Archive gate: run `graphify . --update` after apply. <!-- sdd-owner: parent -->

## Notes

- StatusBadge/.spinner imported read-only from `src/components/primitives` — guard blocks edits only.
- 24h computed from `last_message_at`; stale >24h past renders closed (T1.2).
- `GET /conversations` list-endpoint gap: existing, out of scope, flag at apply.

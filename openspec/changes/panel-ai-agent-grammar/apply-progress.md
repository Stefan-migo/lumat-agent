# Apply Progress: Panel AI-Agent Grammar

## Slice

Phase 3: Internal AgentChat (tasks 3.1–3.2), applied after the merged Phase 2
thread/list presentation. Delivery is `auto-chain`, `stacked-to-main`; this
slice is under the 400-line budget. Phases 4–5 remain intentionally
unimplemented.

## Completed Tasks

- [x] 1.1 RED — Added shell role, History/no-fetch, active-thread state, compact,
  and inspector assertions in `web/src/components/domain/AppShell.test.tsx`
  and `web/src/stories/domain/AppShell.stories.test.tsx`.
- [x] 1.2 GREEN — Added typed optional `activeThreads` and `inspector` slots,
  semantic rail/active-thread/inspector regions, truthful default state, and
  conversation-route predicate while preserving navigation and drawer behavior.
- [x] 1.3 RED — Added concept-story assertions for shared tokens, no injected
  style, accessible regions, inspector conditionality, and reduced motion in
  `web/src/stories/concept/AiAgentGrammar.stories.test.tsx`.
- [x] 1.4 GREEN — Promoted concept grammar and shell rail/inspector/responsive/
  motion rules into `web/src/components/primitives/primitives.css`; no tokens
  or dependencies were added.
- [x] 2.1 RED — Added failing-first assertions for directional bubbles, approved
  owner labels, handoff, reply-window reasons, delivery failure/retry, list
  selection, filters, and retained DataTable semantics in
  `ConversationThread.test.tsx` and `ConversationsList.test.tsx`. Updated the
  existing thread story contract to assert bubbles instead of the retired
  message table.
- [x] 2.2 GREEN — Replaced thread message rows with Avatar-labelled directional
  bubbles, StatusBadge owner state, truthful handoff, primitive controls,
  delivery errors/retry, and human-owner/reply-window composer gating. Kept
  API calls, mutation refresh, submitted-content recovery, permissions, and
  list filters/DataTable behavior unchanged; added selected-row semantics.
- [x] 3.1 RED — Extended `AgentChat.test.tsx` with failing-first coverage for
  agent/administrator directional bubbles and avatars, persisted empty state,
  processing and disabled composer, failed delivery/retry recovery, operator
  denial, and preserved authorized refusal text.
- [x] 3.2 GREEN — Restyled `AgentChat.tsx` with the existing Avatar, Button,
  Textarea, StateMessage, and `ai-agent-grammar__*` primitives/classes. Kept
  `createChatThread`, `sendChatMessage`, `getChatThread`, authorization
  handling, refusal content, and failed submitted content behavior unchanged;
  added no realtime transport, fake activity, endpoints, or backend changes.

## TDD Cycle Evidence

| Task | Test file | RED | GREEN | Triangulate | Refactor |
|---|---|---|---|---|---|
| 1.1 | `AppShell.test.tsx`, `AppShell.stories.test.tsx` | ✅ Written; focused run failed 7 tests | ✅ 38/38 focused tests | ✅ default, ready, loading/error | ✅ Clean |
| 1.2 | `AppShell.test.tsx` | ✅ Existing new assertions drove missing slots | ✅ 38/38 focused tests | ✅ operator/admin and History paths | ✅ Clean |
| 1.3 | `AiAgentGrammar.stories.test.tsx` | ✅ Written; missing shared CSS/style contract failed | ✅ 4/4 concept tests | ✅ expanded/compact and inspector states | ✅ Clean |
| 1.4 | `AppShell.stories.test.tsx`, `AiAgentGrammar.stories.test.tsx` | ✅ CSS assertions failed before implementation | ✅ 38/38 focused tests | ✅ shell and concept grammar consumers | ✅ Clean |
| 2.1 | `ConversationThread.test.tsx`, `ConversationsList.test.tsx` | ✅ Focused run failed 5 new assertions before presentation changes | ✅ 15/15 focused page tests | ✅ Existing story contract updated for bubbles | ✅ Clean |
| 2.2 | `ConversationThread.tsx`, `ConversationsList.tsx` | ✅ Same RED tests drove missing bubbles, labels, handoff, retry, selection, and filter region | ✅ Focused page run 15/15 | ✅ Full suite and build gates | ✅ Clean |
| 3.1 | `AgentChat.test.tsx` | ✅ 2/2 baseline | ✅ New assertions failed 4/6 before implementation | ✅ 6/6 focused after GREEN | ✅ Clean |
| 3.2 | `AgentChat.tsx`, `AgentChat.test.tsx` | ✅ RED assertions drove missing surface states and recoverable rendering | ✅ Focused run 6/6 | ✅ Full suite 428/428; refusal/403 fixtures | ✅ Clean |

## Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command | `cd web && npx vitest run src/components/domain/AppShell.test.tsx src/stories/domain/AppShell.stories.test.tsx src/stories/concept/AiAgentGrammar.stories.test.tsx` — PASS, 3 files, 38 tests |
| Runtime harness | `cd web && npm test` — PASS, 62 files, 419 tests |
| Typecheck | `cd web && npx tsc -b` — PASS |
| Build | `cd web && npm run build` — PASS (`vite v6.4.3`, 70 modules transformed) |
| Rollback boundary | Revert the four shell/story test files plus `PanelShell.tsx`, `AppShell.tsx`, `panelRoutes.ts`, and `primitives.css`; no unrelated pages, APIs, or tokens are involved. |

### Phase 2 evidence

| Evidence | Result |
|---|---|
| Focused test command | `cd web && npx vitest run src/components/pages/ConversationThread.test.tsx src/components/pages/ConversationsList.test.tsx` — PASS, 2 files, 15 tests |
| Runtime harness | `cd web && npm test` — PASS, 62 files, 424 tests |
| Typecheck | `cd web && npx tsc -b` — PASS |
| Build | `cd web && npm run build` — PASS (`vite v6.4.3`, 70 modules transformed) |
| Rollback boundary | Revert `ConversationThread.tsx`, `ConversationsList.tsx`, their page tests, and `ConversationThread.stories.test.tsx`; no API, route, backend, shell, or token changes are involved. |

### Phase 3 evidence

| Evidence | Result |
|---|---|
| Focused test command | `cd web && npx vitest run src/components/pages/AgentChat.test.tsx` — PASS, 1 file, 6 tests |
| Runtime harness | `cd web && npm test` — PASS, 62 files, 428 tests; authorized refusal, 403 denial, and failed-message recovery fixtures included |
| Typecheck | `cd web && npx tsc -b` — PASS |
| Build | `cd web && npm run build` — PASS (`vite v6.4.3`, 70 modules transformed) |
| Realtime boundary | No WebSocket, SSE, polling, streaming truth, fake writing/activity state, new API calls, or backend files added; existing post-send `getChatThread` refresh remains unchanged. |
| Rollback boundary | Revert `web/src/components/pages/AgentChat.tsx` and `web/src/components/pages/AgentChat.test.tsx`; no API, backend, route, CSS, token, or Phase 4–5 files are involved. |

## Graph Check

Consulted `graphify-out/GRAPH_REPORT.md` (AppShell hub, `types.ts`,
`AiAgentGrammar.stories.tsx`, `ConversationThread.tsx`, `ConversationsList.tsx`,
`primitives.css`, `tokens.css`, and `api.ts`). Query:
`PanelShell AppShell rail shell grammar`. Path check:
`PanelShell` → `AppShell` returned no directed path because the match was
ambiguous; the report and query exposed the `PanelShell.tsx`/`AppShell.tsx`
community and `AppShell` route edges used here.

## Remaining Slices

- Phase 4: Inspector/Ficha Alignment (tasks 4.1–4.2)
- Phase 5: Stories and Regression Gates (tasks 5.1–5.3)

## Graph Check — Phase 2

Consulted `graphify-out/GRAPH_REPORT.md` and ran
`graphify query "ConversationThread ConversationsList bubbles thread"`.
Relevant nodes: `ConversationThread.tsx`, `ConversationThread.test.tsx`,
`ConversationsList.tsx`, `ConversationsList.test.tsx`, `ConversationThread()`
and `ConversationsList()`, `api.ts`, `getConversation()`, `sendMessage()`,
`retryMessage()`, `changeConversationState()`, `StatusBadge.tsx`,
`shared/DataTable.tsx`, `shared/PageFrame.tsx`, `shared/StateMessage.tsx`,
`shared/EmptyState.tsx`, `types.ts`, and `primitives.css`.
The directed path check between `ConversationThread` and
`ConversationsList` was ambiguous/no directed path; the query exposed both
pages in the `api.ts` community and their shared API/primitive edges.

## Graph Check — Phase 3

Consulted `graphify-out/GRAPH_REPORT.md` and ran
`graphify query "AgentChat internal chat"` plus
`graphify query "AgentChat role bubbles composer processing retry authorization refusal"`.
Relevant nodes: `AgentChat.tsx`, `AgentChat.test.tsx`, `AgentChat()`,
`createChatThread()`, `getChatThread()`, `sendChatMessage()`, `api.ts`,
`types.ts`, `Avatar.tsx`, `Button.tsx`, `Textarea.tsx`, `StateMessage.tsx`,
`AiAgentGrammar.stories.tsx`, `IAC-4 Conversation Surface Presentation`, and
`IAC-5 Authorization and Context Non-Regression`. Path check:
`AgentChat.tsx` → `api.ts` via `imports_from` (1 hop); no directed path was
found to the spec node, so the query/report supplied the spec and primitive
community edges used here.

## Phase 2 deviations

None — implementation follows the binding design. The stale thread story test
was updated because the approved presentation replaces the message table with
directional bubbles; `ConversationsList` remains a DataTable.

## Phase 3 deviations

None — implementation follows the binding design. The existing empty copy was
reframed as a labelled `StateMessage`; persisted APIs, refusal text, and
error/recovery content remain unchanged.

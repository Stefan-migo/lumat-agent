# Apply Progress: Panel AI-Agent Grammar

## Slice

Phase 5: Stories and Regression Gates (tasks 5.1–5.3), applied after the
merged Phase 4 inspector/ficha alignment. Delivery is `auto-chain`,
`stacked-to-main`; this slice is under the 400-line budget.

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

- [x] 4.1 RED — Created `web/src/components/pages/ClientFicha.test.tsx` with
  page rhythm, customer context, conditional inspector, retained cards,
  memories, notes, badges, and four DataTable assertions. The initial focused
  run failed only because the note matcher ignored the rendered
  `author · note` contract.
- [x] 4.2 GREEN — Aligned `ClientFicha.tsx` chrome with the existing
  `PageFrame` meta line and a labelled customer-summary region while retaining
  memo, `ClientMemories`, notes, badges, visits, appointments, visit history,
  and the three history DataTables. No inspector column or chat surface was
  added.

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

## Phase 4 TDD Cycle Evidence

| Task | Test file | RED | GREEN | Triangulate | Refactor |
|---|---|---|---|---|---|
| 4.1 | `ClientFicha.test.tsx` | ✅ Focused RED failed 1 stale note matcher | ✅ Focused run 2/2 after matching `author · note` | ✅ Populated dense sections plus empty appointments path | ✅ Clean |
| 4.2 | `ClientFicha.tsx`, `ClientFicha.test.tsx` | ✅ Existing RED contract exposed the required hierarchy | ✅ Focused run 2/2 | ✅ Cards, memories, notes, badges, and four tables remain rendered | ✅ Clean |

## Phase 4 Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command | `cd web && npx vitest run src/components/pages/ClientFicha.test.tsx` — PASS, 1 file, 2 tests |
| Runtime harness | `cd web && npm test` — PASS, 63 files, 430 tests; dense ficha fixture included |
| Typecheck | `cd web && npx tsc -b` — PASS |
| Rollback boundary | Revert `web/src/components/pages/ClientFicha.tsx`, `web/src/components/pages/ClientFicha.test.tsx`, and the Phase 4 task/progress rows; no API, backend, route, shell, CSS, or Phase 5 files are involved. |

## Remaining Slices

- None — Phase 5 is complete.

## Phase 5 TDD Cycle Evidence

| Task | Test file | RED | GREEN | Triangulate | Refactor |
|---|---|---|---|---|---|
| 5.1 | `ChatWithAgent.stories.test.tsx`, `InboxThread.stories.test.tsx`, `AiAgentGrammar.stories.test.tsx` | ✅ New viewport/state/identity/inspector assertions failed before story updates | ✅ Focused run 24/24 | ✅ Processing, compact/inspector-hidden, inbound/outbound, handoff | ✅ Clean |
| 5.2 | Same story files and shared chat fixture | ✅ Contract expectations written first | ✅ Focused run 3 files, 24 tests | ✅ Deterministic reply window and dense inspector context | ✅ Removed streaming language and aligned production labels |
| 5.3 | Full web gates | ✅ Baseline focused suite 20/20 before additions | ✅ Full suite and build gates pass | ✅ Storybook production build pass | ✅ Clean |

## Phase 5 Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command | `cd web && npx vitest run src/stories/pages/ChatWithAgent.stories.test.tsx src/stories/pages/InboxThread.stories.test.tsx src/stories/concept/AiAgentGrammar.stories.test.tsx` — PASS, 3 files, 24 tests |
| Runtime harness | `cd web && npm run build-storybook` — PASS, Storybook 8.6.18 preview built; responsive story viewport metadata and all three stories compiled |
| Full test command | `cd web && npm test` — PASS, 63 files, 434 tests |
| Typecheck | `cd web && npx tsc -b` — PASS |
| Build | `cd web && npm run build` — PASS (`vite v6.4.3`, 70 modules transformed) |
| Rollback boundary | Revert the seven changed story/test/fixture files; no production components, APIs, backend files, tokens, or dependencies are involved. |
| Negative gates | PASS: no backend files, new endpoints, `fetch` in `PanelShell`, fabricated threads, streaming/realtime behavior, or new dependencies. Existing story fixtures remain the source of rendered rows/messages. |

## Graph Check — Phase 5

Consulted `graphify-out/GRAPH_REPORT.md` and ran
`graphify query "ChatWithAgent InboxThread AiAgentGrammar stories"`.
Relevant nodes: `ChatWithAgent.stories.tsx`, `ChatWithAgent.stories.test.tsx`,
`InboxThread.stories.tsx`, `InboxThread.stories.test.tsx`,
`AiAgentGrammar.stories.tsx`, `AiAgentGrammar.stories.test.tsx`,
`Stories _shared Helpers Origin (pre-promotion)`, `ConversationThread.tsx`,
`ConversationsList.tsx`, `AgentChat.tsx`, `Avatar.tsx`, `StatusBadge.tsx`,
`Textarea.tsx`, `Button.tsx`, `primitives.css`, and `types.ts`.
Edges consulted: story files → shared mock fixtures/primitives; production
conversation and agent pages → `api.ts` and shared grammar primitives. Directed
paths requested from `ChatWithAgent` → `ConversationThread`, `InboxThread` →
`ConversationsList`, and `AiAgentGrammar` → `AgentChat` were absent/ambiguous;
the graph query and communities supplied the story-to-contract boundaries.

## Phase 5 Deviations

None — implementation matches the design. Story-only processing copy now uses
the persisted production terminology and removes the pre-existing realtime/
streaming wording; no production behavior was changed.

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

## Graph Check — Phase 4

Consulted `graphify-out/GRAPH_REPORT.md` and ran
`graphify query "ClientFicha client ficha"`.
Relevant nodes: `ClientFicha()`, `pages/ClientFicha.tsx`, `ClientFicha.test.tsx`,
`ClientMemories.tsx`, `PageFrame()`, `shared/PageFrame.tsx`, `DataTable()`,
`shared/DataTable.tsx`, `Badge.tsx`, `api.ts`, `types.ts`, and
`AiAgentGrammar.stories.tsx`. Path check:
`ClientFicha()` → `PageFrame()` resolved through `pages/ClientFicha.tsx` →
`PageFrame()` in two hops; the direct ClientFicha → ClientMemories lookup was
ambiguous/no directed path, so the query/report supplied the imported domain
component and shared primitive edges.

## Phase 4 deviations

None — implementation matches the design. The interrupted working-tree GREEN
was completed by correcting the test to assert the actual `author · note` DOM
contract; dense operational sections remain unchanged.

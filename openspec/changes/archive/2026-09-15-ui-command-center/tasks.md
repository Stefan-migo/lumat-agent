# Tasks: UI Command Center

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | ~950–1,250; ~220–320 per slice |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 API seam → PR 2 focus/streaming → PR 3 zones/migration → PR 4 browser harness |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | PR | Test command | Runtime harness | Rollback boundary |
|---|---|---|---|---|---|
| 1 | Authorized bounded thread-list seam | PR 1 | `uv run pytest tests/integration/test_assistant_chat.py -k thread_list`; `cd web && npm test -- api` | N/A: API/client contract | Revert `chat.py`, serializers/types, `api.ts`, seam tests |
| 2 | Focus mode and durable stream state | PR 2 | `cd web && npm test -- PanelShell AgentChat` | N/A: Vitest covers component behavior | Revert `PanelShell*`, `AgentChat*`, related tests |
| 3 | Zones, responsive switching, scenario ownership | PR 3 | `cd web && npm test -- AgentChat ConversationThread` | `cd web && npm run dev`; inspect at 390/768/1024 | Revert page/CSS/story files |
| 4 | Narrow browser contract | PR 4 | `cd web && npx playwright test web/playwright/command-center.spec.ts` | Local Vite/API fixture route at 390/768/1024 | Revert Playwright spec/config only |

## Phase 1: Thread Seam (PR 1)

- [x] 1.1 **RED [M]:** Add backend tests in `tests/integration/test_assistant_chat.py` for owner/admin authorization, bound/order, rejected operador/unbounded requests, and no planning-session fabrication; add `api.ts`/`types.ts` client tests.
- [x] 1.2 **GREEN [M]:** Add the bounded `GET /panel/api/chat/threads?limit=N` serializer/route in `app/panel/api/routes/chat.py` and `app/panel/api/serializers.py`; implement typed client access in `web/src/api.ts` and `web/src/types.ts` without changing write permissions.

## Phase 2: Focus / Conversation (PR 2)

- [x] 2.1 **RED [S]:** Extend `web/src/components/domain/PanelShell.test.tsx` and `AgentChat.test.tsx` for keyboard entry, focus trap/restoration, Escape, stream failure, persisted-history authority, read-only context, and approval/retry/send actions.
- [x] 2.2 **GREEN [M]:** Implement focus/region control in `PanelShell.tsx`; update `AgentChat.tsx` to separate transient SSE/WebSocket state from authoritative data and expose truthful recovery/error semantics.

## Phase 3: Production Composition and Migration (PR 3)

- [x] 3.1 **RED [M]:** Add Vitest scenarios for desktop order and mobile single-zone selection at `<640` and `640–1023`, preserving selection/actions; add `ConversationThread.test.tsx` coverage for migrated InboxThread scenarios.
- [x] 3.2 **GREEN [M]:** Compose navigator, conversation, and read-only context in `AgentChat.tsx`; keep `AppShell.tsx` route-stable and add token-backed tiers/visibility in `web/src/components/primitives/primitives.css`.
- [x] 3.3 **GREEN [S]:** Move required story scenarios to `web/src/components/pages/ConversationThread.{tsx,test.tsx}` and delete `web/.storybook/quarantine/pages/InboxThread.{stories.tsx,stories.test.tsx}`; verify no prototype or fabricated catalog ownership remains.

## Phase 4: Browser Verification (PR 4)

- [x] 4.1 **RED/GREEN [M]:** Create `web/playwright/command-center.spec.ts` and local configuration/script; verify geometry/order, breakpoint visibility, keyboard switching, focus/Escape/restoration, and critical actions at 390/768/1024. No screenshots, CI, PWA, or visual regression.

## Graph / Ponytail Review

Graph consulted `AgentChat.tsx`, `PanelShell.tsx`, `AppShell.tsx`, `api.ts`, `types.ts`, `chat.py`, `InternalChatThread`, `ConversationThread.test.tsx`, and `serializers.py`; paths: `PanelShell → AppShell → ConversationThread` and `AgentChat → AppShell → chat.py`. Threat rows are N/A. Ponytail found no dependency, fabricated data, screenshot, CI, or feature-flag scope.

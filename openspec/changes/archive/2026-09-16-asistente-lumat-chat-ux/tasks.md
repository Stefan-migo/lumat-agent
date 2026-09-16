# Tasks: Asistente Lumat Chat UX

## Phase 1: Persistence and API Foundation

- [x] 1.1 **RED:** add migration/model tests in `tests/integration/test_migrations.py` for nullable `InternalChatThread.title`; **GREEN:** create `db/migrations/025_internal_chat_thread_title.sql` and update `app/models.py`.
- [x] 1.2 **RED:** extend `tests/integration/test_assistant_chat.py` for explicit creation, non-empty filtering, ordering, timestamps, ownership, rename, delete, and Spanish failures; **GREEN:** update `app/panel/api/serializers.py`, `app/panel/api/routes/chat.py`, `web/src/api.ts`, and `web/src/types.ts`.

## Phase 2: Title Lifecycle and Backend Contracts

- [x] 2.1 **RED:** add tests for one-time title generation, normal cost gate, `record_llm_cost`, timeout/error/non-normal fallback, and bounded UTF-8 opening-message fallback; **GREEN:** update `app/services/agent_chat.py` without changing SSE, approval, recovery, attachments, or planning APIs.
- [x] 2.2 **RED:** extend `tests/integration/test_agent_chat_realtime.py` and `tests/integration/test_assistant_chat.py` for `?thread_id=` ownership, tier metadata, persisted recovery, and localized failure responses; **GREEN:** close contract gaps and verify `uv run pytest tests/`.

## Phase 3: Conversation Surface

- [x] 3.1 **RED:** rewrite the three zone/tab suites—`web/src/components/pages/AgentChat.test.tsx`, `web/src/components/pages/ConversationThread.test.tsx`, and `web/playwright/command-center.spec.ts`—for centered composition, Spanish states, no auto-create, deep links, streaming cursor, copy/retry, attachments, approval/evidence anchoring, planning dialog, and composer keyboard behavior; **GREEN:** recompose `AgentChat.tsx` using existing primitives, inline `PlanCard`/`EvidenceList`, auto-grow composer, popover history, closed context drawer, and responsive token CSS.
- [x] 3.2 **RED:** add Settings capability-host assertions; **GREEN:** move `AssistantCapabilitiesView` to `web/src/components/pages/Settings.tsx` and remove the chat-page capability dump.
- [x] 3.3 **RED:** add browser assertions to the rewritten `web/playwright/command-center.spec.ts` for desktop/narrow layout, history/context disclosure, navigator grouping/actions, focus/zoom/reduced-motion semantics, and preserved send/approval/retry/planning paths; **GREEN:** wire final responsive behavior and verify with `cd web && npm run test:e2e`.

## Phase 4: Verification and Cleanup

- [x] 4.1 Run `uv run pytest tests/`, `cd web && npm test`, `cd web && npx tsc -b`, and browser verification; fix only scoped regressions and inspect the diff for forbidden token changes, dependencies, dark-mode work, D5/D6 work, raw status, or `Thread #N`.

## Review Workload Forecast

| Area | Estimate |
|------|----------|
| Frontend | 450–650 lines |
| Backend | 220–320 lines |
| Migration | 10–20 lines |
| Tests | 500–700 lines (zone/tab files rewritten) |
| Docs | 0 lines |
| Total authored change | 1,180–1,690 lines |

Chained PRs recommended: Yes
400-line budget risk: High
Decision needed before apply: No
Chain strategy: stacked-to-main

PR #1 (base feature branch): migration/model + RED/GREEN tests; `uv run pytest tests/`; runtime N/A (schema/model unit boundary); rollback migration/model files. PR #2 (base PR #1): serializer/routes/types + tests; `uv run pytest tests/`; runtime N/A (API contract tests); rollback API contract files. PR #3 (base PR #2): title lifecycle/service + tests; `uv run pytest tests/`; runtime N/A (cost/fallback integration tests); rollback title path. PR #4 (base PR #3): `AgentChat`/CSS/Settings + rewritten Vitest tests; `cd web && npm test && npx tsc -b`; runtime N/A until browser slice; rollback page/UI files. PR #5 (base PR #4): rewritten Playwright command-center coverage and final verification; `cd web && npm run test:e2e`; runtime browser scenarios; rollback e2e file only.

## Corrective Slice: Verification Findings

- [x] C1 Anchor plan and evidence to the producing message's existing `assistant_metadata.run_id` and event `run_id`; add multi-run regression coverage.
- [x] C2 Make `Reintentar mensaje` resubmit the failed content and preserve any unsent composer draft; strengthen Shift+Enter and retry assertions.
- [x] C3 Trace titleless-thread reachability and guarantee a bounded non-empty fallback when no admin opening exists.

### Corrective Work Unit Evidence

| Evidence | Exact result |
|---|---|
| Focused tests | `cd web && npm test -- --run src/components/pages/AgentChat.test.tsx`; 27 passed. `TEST_ADMIN_DB_URL=... uv run pytest tests/integration/test_assistant_chat.py tests/integration/test_agent_chat_realtime.py -q`; 33 passed. |
| Runtime harness | `cd web && npm run test:e2e -- playwright/command-center.spec.ts`; 8 passed. |
| Rollback boundary | Revert `AgentChat.tsx`, `AgentChat.test.tsx`, `agent_chat.py`, `command-center.spec.ts`, and this corrective task section. |

### Corrective TDD Evidence

| Fix | RED counter-check | GREEN |
|---|---|---|
| C1 run anchoring | Reverted to `last`; multi-run test failed because old evidence was absent from its producing message. | 27 frontend tests passed. |
| C2 retry | Reverted retry handler; test failed with only 2 fetch calls instead of the retry POST. | 27 frontend tests passed. |
| Shift+Enter | Reverted newline branch; test failed: expected `Hola\n`, received `Hola`. | 27 frontend tests passed. |
| C3 fallback | Reverted default; backend test failed: expected `Conversación con el asistente`, received empty string. | 33 focused backend tests passed. |

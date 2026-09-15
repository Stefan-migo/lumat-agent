# Apply Progress: UI Command Center — PR 2 Focus / Conversation

**Status**: Phase 1 tasks 1.1–1.2 and Phase 2 tasks 2.1–2.2 complete; Phase 3–4 untouched.
**Mode**: Strict TDD (Vitest component tests).
**Delivery**: auto-chain, stacked-to-main; PR 2 targets the PR 1 branch.

## Completed Tasks

- [x] 1.1 RED — Backend authorization/bound/order and client seam coverage.
- [x] 1.2 GREEN — Bounded authorized thread-list API and typed client seam.
- [x] 2.1 RED — Added keyboard focus entry, focus trap/restoration, Escape, stream failure/recovery, and persisted-history authority tests.
- [x] 2.2 GREEN — Added PanelShell focus mode and separated transient stream state from persisted history with truthful recovery semantics.

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 1.1 | `tests/integration/test_assistant_chat.py`, `web/src/api.test.ts` | Integration + unit/client | ✅ 20/20 backend; 13/13 frontend | ✅ Written | ✅ Passed | ✅ Multiple scenarios | ✅ Clean |
| 1.2 | same | Integration + unit/client | ✅ Existing seam suite | ✅ Written | ✅ Passed | ✅ Bound/auth/order cases | ✅ Clean |
| 2.1 | `web/src/components/domain/PanelShell.test.tsx`, `web/src/components/pages/AgentChat.test.tsx` | Component/unit | ✅ 17/17 | ✅ Written; 3 tests failed before implementation | ✅ 20/20 | ✅ Focus, disconnect, persistence paths | ✅ Clean; `git diff --check` passed |
| 2.2 | same | Component/unit | ✅ 17/17 | ✅ Tests preceded production changes | ✅ 20/20 | ✅ Normal close, stream failure, reload authority | ✅ Clean; build passed |

## Work Unit Evidence

- Focused test: `cd web && npm test -- --run src/components/domain/PanelShell.test.tsx src/components/pages/AgentChat.test.tsx` — PASS, 20/20 tests.
- Build/typecheck: `cd web && npm run build` — PASS (`tsc -b` and Vite build).
- Runtime harness: N/A — frontend-only component slice; Vitest/jsdom is the available runtime boundary and covers keyboard/stream behavior.
- Rollback boundary: revert `web/src/components/domain/PanelShell.tsx`, `PanelShell.test.tsx`, `web/src/components/pages/AgentChat.tsx`, and `AgentChat.test.tsx`; no backend or unrelated route behavior is affected.

## Graph Check

- Consulted `GRAPH_REPORT.md`: `domain/PanelShell.tsx`, `PanelShell.test.tsx`, `AgentChat.tsx`, `AgentChat.test.tsx`, `types.ts`, `api.ts`, `InternalChatThread`, and `InternalChatMessage`.
- Queries: `PanelShell keyboard focus trap restoration Escape`; `AgentChat stream failure persisted history authoritative read-only context approval retry send`.
- Edges: `PanelShell.test.tsx --imports_from--> domain/PanelShell.tsx`; `AgentChat.test.tsx --imports_from--> AgentChat.tsx`; `AgentChat.tsx` references `api.ts` and realtime state.

## Deviations / Issues

- None from the design. The existing Spanish UI copy was preserved while adding explicit recovery semantics.

## Remaining Tasks

- [ ] 3.1–3.3 Production composition, responsive zones, and story migration.
- [ ] 4.1 Narrow browser contract.

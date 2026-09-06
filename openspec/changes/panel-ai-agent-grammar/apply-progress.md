# Apply Progress: Panel AI-Agent Grammar

## Slice

Phase 1: Shell and Shared Grammar (tasks 1.1–1.4). Delivery is `auto-chain`,
`stacked-to-main`; this slice remains the first review unit and is under the
400-line budget. Phases 2–5 are intentionally not implemented.

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

## TDD Cycle Evidence

| Task | Test file | RED | GREEN | Triangulate | Refactor |
|---|---|---|---|---|---|
| 1.1 | `AppShell.test.tsx`, `AppShell.stories.test.tsx` | ✅ Written; focused run failed 7 tests | ✅ 38/38 focused tests | ✅ default, ready, loading/error | ✅ Clean |
| 1.2 | `AppShell.test.tsx` | ✅ Existing new assertions drove missing slots | ✅ 38/38 focused tests | ✅ operator/admin and History paths | ✅ Clean |
| 1.3 | `AiAgentGrammar.stories.test.tsx` | ✅ Written; missing shared CSS/style contract failed | ✅ 4/4 concept tests | ✅ expanded/compact and inspector states | ✅ Clean |
| 1.4 | `AppShell.stories.test.tsx`, `AiAgentGrammar.stories.test.tsx` | ✅ CSS assertions failed before implementation | ✅ 38/38 focused tests | ✅ shell and concept grammar consumers | ✅ Clean |

## Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command | `cd web && npx vitest run src/components/domain/AppShell.test.tsx src/stories/domain/AppShell.stories.test.tsx src/stories/concept/AiAgentGrammar.stories.test.tsx` — PASS, 3 files, 38 tests |
| Runtime harness | `cd web && npm test` — PASS, 62 files, 419 tests |
| Typecheck | `cd web && npx tsc -b` — PASS |
| Build | `cd web && npm run build` — PASS (`vite v6.4.3`, 70 modules transformed) |
| Rollback boundary | Revert the four shell/story test files plus `PanelShell.tsx`, `AppShell.tsx`, `panelRoutes.ts`, and `primitives.css`; no unrelated pages, APIs, or tokens are involved. |

## Graph Check

Consulted `graphify-out/GRAPH_REPORT.md` (AppShell hub, `types.ts`,
`AiAgentGrammar.stories.tsx`, `ConversationThread.tsx`, `ConversationsList.tsx`,
`primitives.css`, `tokens.css`, and `api.ts`). Query:
`PanelShell AppShell rail shell grammar`. Path check:
`PanelShell` → `AppShell` returned no directed path because the match was
ambiguous; the report and query exposed the `PanelShell.tsx`/`AppShell.tsx`
community and `AppShell` route edges used here.

## Remaining Slices

- Phase 2: Thread and List Presentation (tasks 2.1–2.2)
- Phase 3: Internal AgentChat (tasks 3.1–3.2)
- Phase 4: Inspector/Ficha Alignment (tasks 4.1–4.2)
- Phase 5: Stories and Regression Gates (tasks 5.1–5.3)

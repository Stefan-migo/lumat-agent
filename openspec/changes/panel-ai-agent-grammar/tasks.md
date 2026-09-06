# Tasks: Panel AI-Agent Grammar

Web-only. Every GREEN task follows RED; each slice compiles and passes focused tests before stacking.

## Phase 1: Shell and Shared Grammar (PNL-APP-10/11, DS-GRAMMAR-1/2/3)

- [ ] 1.1 RED: Extend `AppShell.test.tsx`/`AppShell.stories.test.tsx` for compact roles, History paths, no fetch, rail states, and inspector.
- [ ] 1.2 GREEN: Modify `PanelShell.tsx`, `AppShell.tsx`, `panelRoutes.ts` with semantic slots; preserve drawer, focus, `aria-current`, filtering, and routes.
- [ ] 1.3 RED: Extend `AiAgentGrammar.stories.test.tsx` for token colors, no injected style, reduced motion, and accessible regions.
- [ ] 1.4 GREEN: Modify `primitives.css` with minimal tokenized rail, active-thread, inspector, responsive, and motion rules; no new tokens/dependencies.

## Phase 2: Thread and List Presentation (PNL-APP-12, DS-GRAMMAR-1/3)

- [ ] 2.1 RED: Extend `ConversationThread.test.tsx`/`ConversationsList.test.tsx` for bubbles, labels, handoff, reply-window reasons, retry/error, selection, and tables.
- [ ] 2.2 GREEN: Modify `ConversationThread.tsx`/`ConversationsList.tsx` with existing primitives; preserve APIs/mutations and no fake activity.

## Phase 3: Internal AgentChat (IAC-4/5, DS-GRAMMAR-1/3)

- [ ] 3.1 RED: Extend `AgentChat.test.tsx` for role bubbles, empty/processing/failure-retry, disabled composer, denial, and refusal context.
- [ ] 3.2 GREEN: Modify `AgentChat.tsx` with existing APIs/primitives; preserve persistence, authorization, refusal text, and recoverable content.

## Phase 4: Inspector/Ficha Alignment (PNL-APP-12, DS-GRAMMAR-1/3)

- [ ] 4.1 RED: Create `ClientFicha.test.tsx` for page rhythm, conditional inspector, and retained cards, memories, notes, badges, and history tables.
- [ ] 4.2 GREEN: Modify `ClientFicha.tsx` for aligned chrome/inspector hierarchy; retain dense operational sections.

## Phase 5: Stories and Regression Gates (all requirements)

- [ ] 5.1 RED: Extend `web/src/stories/pages/ChatWithAgent.stories.test.tsx`, `InboxThread.stories.test.tsx`, and `web/src/stories/concept/AiAgentGrammar.stories.test.tsx` for viewports, states, inspector, motion, and dense pages.
- [ ] 5.2 GREEN: Modify those stories to trace production contracts without production mocks or realtime behavior.
- [ ] 5.3 Verify: `cd web && npm test`; `cd web && npx tsc -b`; `cd web && npm run build`; confirm no backend files, new endpoints, fetch in `PanelShell`, fabricated threads, streaming, or dependencies.

## Review Workload Forecast

| Slice | Lines | Focused test / harness | Rollback boundary |
|---|---:|---|---|
| 1 | 280 | `npx vitest run src/components/domain`; Storybook shell states | Revert shell/CSS/tests |
| 2 | 300 | `npx vitest run src/components/pages/{ConversationThread,ConversationsList}.test.tsx`; conversation route | Revert two pages/tests |
| 3 | 220 | `npx vitest run src/components/pages/AgentChat.test.tsx`; authorized/denied fixture | Revert AgentChat/tests |
| 4 | 170 | `npx vitest run src/components/pages/ClientFicha.test.tsx`; dense ficha fixture | Revert Ficha/tests |
| 5 | 230 | `npm test && npx tsc -b && npm run build`; Storybook matrix | Revert stories/tests |
| **Total** | **1200** | **High overall** | **Five independent PRs, stacked to main in order** |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

One work-unit commit per PR; tests stay beside behavior. PR N targets `main` after PR N-1. Load `/home/stefan/.config/opencode/skills/chained-pr/SKILL.md` and `/home/stefan/.config/opencode/skills/work-unit-commits/SKILL.md` during apply.

## Graph Check

Nodes: `AppShell`, `PanelShell`, `ConversationThread`, `AgentChat`, `ConversationsList`, `ClientFicha`, `AiAgentGrammar`, `api`, `StatusBadge`, `primitives.css`. Edge: `PanelShell → AppShell → ConversationThread`; absent AgentChat/ClientFicha paths are test boundaries.

## Ponytail Review

Cut token generation, backend/API work, shell fetch/retry, fabricated fixtures, and universal three-column layout; merged route/context into shell.

# Proposal: Panel AI-Agent Grammar

## Intent

Make the panel visibly read as an agent application: users should finally see the promised frontend while operational data remains precise. `AiAgentGrammar` is authoritative.

## Scope

### In Scope
- Evolve `AppShell` → `PanelShell` into a forest rail, role-safe navigation, compact/expanded behavior, and structural `Conversaciones activas` chrome.
- Restyle conversation detail, `AgentChat`, and list chrome; retain dense control-room tables/KPIs/badges.
- Add optional active-thread/inspector slots with truthful states and CSS.

### Out of Scope
- WebSocket/SSE/streaming, realtime truth, activity-event data/persistence, unread/freshness semantics, customer-name enrichment, or new endpoints.
- Shell-owned fetching or current-conversations endpoint consumption for the rail; C owns its source.
- Backend API changes, dark mode, icon/font dependencies, router dependencies, or CSS-framework dependencies.

## Capabilities

### New Capabilities
- None. Existing capability ownership is sufficient.

### Modified Capabilities
- `panel-app`: global chrome, conditional regions, conversation presentation, and rail states; native History/API behavior MUST remain unchanged.
- `internal-agent-chat`: bubble/role/processing/error/retry/composer presentation; persistence and authorization MUST remain unchanged.
- `panel-design-system`: “appearance of agent app, physiology of control room,” token use, primitive reuse, and DOM contracts.

Acceptance: `PanelShell` MUST render role-safe rail/truthful states without fetch; conversation DOM MUST expose direction, status, handoff, reply-window, retry, and permission semantics; `AgentChat` MUST expose persisted, processing, empty, and failure states; dense pages MUST retain table/KPI/badge primitives. Tests SHOULD cover approved viewports and reduced motion.

## Approach

Use Approach 1: shared chrome plus adaptive conversation surfaces, not a universal three-column or duplicated shell. Keep `PanelShell` data-free with an optional active-thread contract. Preserve reply-window, permission, delivery, retry, and mutation behavior. Use existing tokens first.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `web/src/components/domain`, `pages` | Modified | Shell and conversation surfaces; dense primitives retained. |
| `web/src/components/primitives`, stories/tests | Modified | Styles and acceptance matrix. |

## Graph Validation

Graph consulted: `AppShell.tsx`, `PanelShell.tsx`, `ConversationThread.tsx`, `AgentChat()`, `activeThreads`, `AiAgentGrammar.stories.tsx`, `StatusBadge.tsx`, `primitives.css`; confirmed `PanelShell → AppShell → ConversationThread` and no AppShell → concept-story path.

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Width cost harms dense pages | Med | Conditional inspector/thread regions. |
| Visual restyle regresses delivery behavior | Med | Preserve and test existing contracts. |
| Fake threads or duplicated CSS | Med | No shell fetch; shared patterns only. |

## Rollback Plan

Revert the web-only shell, page, CSS, and tests. Existing routes, APIs, messages, and pages remain available.

## Dependencies

- Existing History shell, token boundary, page contracts, and approved story.

## Success Criteria

- [ ] Shell and conversation surfaces satisfy DOM/story contracts at approved states.
- [ ] Active rail is truthful structural chrome with no shell-owned network request or fabricated thread data.
- [ ] Existing routing, permissions, reply-window, delivery/retry, accessibility, and dense control-room contracts remain green.

# Proposal: UI Command Center

## Intent

Turn production `AgentChat` into a three-zone Lumat assistant command center while preserving SSE, WebSocket, approval, attachment, and Cortex semantics.

## Scope

### In Scope
- Compose the `chat` route into production-owned left, center, and right zones.
- Add responsive mobile web at `<640px`, `640–1023px`, and `>=1024px`; mobile selects one.
- Add a narrow reusable `PanelShell` focus/region-visibility contract with escape, keyboard, and restoration.
- Add the owned internal-thread list contract; never fabricate it.
- Preserve useful `InboxThread` scenarios through production-backed `ConversationThread` coverage and remove the duplicate.
- Add narrow Playwright checks for geometry, breakpoints, focus, and keyboard behavior.

### Out of Scope
- Installable/offline PWA, offline execution or writes, service-worker/cache changes.
- Global shell redesign, unrelated route redesign, or broad catalog completion.
- Screenshot baselines, visual regression, and CI integration.
- Phantom Corporate entries, speculative primitives, agent-configuration APIs, or standalone prototype pages.

## Capabilities

### New Capabilities
- `ui-command-center`: Responsive three-zone assistant workspace, focus mode, and browser-verifiable interaction contract.

### Modified Capabilities
- `internal-agent-chat`: Expose bounded thread-list/read data and retain durable streaming and approval semantics.
- `panel-design-system`: Define Command Center responsive zones, focus visibility, accessibility, and production-story ownership.

## Approach

Refactor `AgentChat` in place; keep `AppShell` as route boundary. Extend `PanelShell` only with focus mode. Prefer existing primitives/CSS. Keep streaming transient, context read-only, and history independent of planning sessions.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `web/src/components/pages/AgentChat.tsx` | Modified | Three-zone composition. |
| `web/src/components/domain/PanelShell.tsx` | Modified | Focus/visibility contract. |
| `web/src/api.ts`, `web/src/types.ts`, `app/panel/api/routes/chat.py` | Modified | Thread-list seam. |
| `web/src/components/pages/ConversationThread.tsx`, stories/quarantine | Modified/Removed | Preserve scenarios; remove duplicate. |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Thread-list API is absent | High | Treat it as a prerequisite; no fabricated list. |
| Responsive/focus mode hides critical actions | Med | Zone, keyboard, escape, and Playwright checks. |
| Stream implies false completion | Med | Persisted history remains authoritative. |

## Rollback Plan

Revert UI/API commits and story disposition; existing behavior remains available. Remove an unused additive list contract.

## Dependencies

- Internal assistant-thread list endpoint in `app/panel/api/routes/chat.py` is required for the left navigator.
- Existing chat, thread, SSE/WebSocket, and breakpoint contracts.

## Success Criteria

- [ ] Authorized users navigate the three-zone workspace with durable, recoverable states.
- [ ] Mobile tiers remain usable and focus mode preserves escape, keyboard access, and critical actions.
- [ ] Playwright checks prove geometry/visibility/breakpoint invariants; no screenshot/CI claim is made.
- [ ] `InboxThread` is no longer an owner and no phantom catalog scope is added.

## Graph Check Consulted

Graph: `AppShell → PanelShell`; `AgentChat ↔ chat.py`; `ConversationThread ↔ InboxThread`.

# Design: UI Command Center

## Technical Approach

Refactor `AgentChat` in place into a production-owned Command Center while keeping `AppShell` as the route boundary and preserving the existing SSE, WebSocket, approval, attachment, and Cortex seams. At `>=1024px`, CSS grid presents navigator, conversation, and read-only inspector; below 1024px, a keyboard-operable zone selector presents exactly one primary region. Reuse `PageFrame`, `Card`, `Button`, `Badge`, `Avatar`, `Textarea`, `StateMessage`, and existing token CSS. Do not add a split-pane library or speculative primitives. (Graph nodes: `AgentChat.tsx`, `domain/PanelShell.tsx`, `domain/AppShell.tsx`, `api.ts`, `types.ts`, `chat.py`, `InternalChatThread`, `InternalChatMessage`.)

## Architecture Decisions

| Option | Tradeoff | Decision |
|---|---|---|
| Compose in `AgentChat` vs new page | In-place preserves route and state; new page duplicates behavior | Choose in-place composition. |
| CSS grid/media queries vs split-pane dependency | CSS has no drag resizing, but satisfies fixed responsive contract with no dependency | Choose existing CSS/tokens; no resizable pane. |
| New bounded thread list vs planning-session inference | Requires a small API seam; inference is incorrect data ownership | Add an owner/admin-only recent list; never treat planning sessions as threads. |
| Generic `PanelShell` extension vs Command Center-only focus state | Reusable contract touches shell; local state would duplicate accessibility logic | Add narrow `focusMode` plus region-visibility contract to `PanelShell`; no shell redesign. |

## Data Flow

`AppShell` → `PanelShell` → `AgentChat`

`GET /panel/api/chat/threads?limit=N` → navigator → selected `thread_id` → `GET /chat/threads/{id}` → center/context

`sendChatMessage` → persisted admin message/run → SSE + WebSocket transient events → visible run state → reload/reconnect reads persisted thread; incomplete runs remain recoverable. The inspector derives plan, evidence, capabilities, attachment metadata, and connection state but contains no execution controls. Approval remains a center action.

The list response is bounded server-side (fixed maximum, stable `updated_at` ordering, no arbitrary unbounded page), scoped to the authenticated owner/admin, and contains `{id, title_or_preview, updated_at, status, unread, run_status, approval_status}` where available. The exact serializer must use existing model data only; unavailable fields are nullable/omitted, not invented.

## File Changes

| File | Action | Description |
|---|---|---|
| `web/src/components/pages/AgentChat.tsx` | Modify | Three zones, list selection, mobile zone switching, transient stream/history separation, read-only inspector, critical-action placement. |
| `web/src/components/domain/PanelShell.tsx` | Modify | Add focus entry/exit, Escape, focus trap, restoration, and explicit region visibility API. |
| `web/src/components/domain/AppShell.tsx` | Modify | Keep `chat` route stable; pass only explicit Command Center context if required. |
| `web/src/api.ts`, `web/src/types.ts` | Modify | Add bounded list client and shared response/types; retain existing thread contracts. |
| `app/panel/api/routes/chat.py` | Modify | Add bounded authorized list endpoint and serializer path; no write-permission expansion. |
| `web/src/components/primitives/primitives.css` | Modify | Token-backed grid, tier rules, overflow, focus/visibility states; no new primitive. |
| `web/src/components/pages/ConversationThread.{tsx,test.tsx}`, stories | Modify | Preserve inbox scenarios against production data/controls. |
| `web/.storybook/quarantine/pages/InboxThread.{stories.tsx,stories.test.tsx}` | Delete | Remove duplicate owner after scenario extraction. |
| `web/playwright/command-center.spec.ts` (and minimal config/script) | Create/modify | Narrow browser geometry, breakpoint, focus, keyboard, and critical-action checks; no screenshots/CI. |

## Interfaces / Contracts

`PanelShell` exposes a narrow controlled contract: `focusMode?: boolean`, `onFocusModeChange`, and named region visibility/restore state. Entry is a labelled, keyboard-operable control; focus moves into the active region, Tab is trapped while focused, Escape exits, and the initiating control regains focus. Resize does not discard selected thread or prior visibility; closing restores the captured shell/zone state. Escape, send, approval, retry, and emergency actions remain reachable in every tier.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Vitest | List client/types, zone state, focus restoration, stream failure, read-only inspector, ConversationThread scenario parity | Mock `apiFetch`/realtime; assert roles, labels, disabled/busy/error states. Backend tests cover auth, bound, ordering, and no fabricated sessions. |
| Playwright | `<640`, `640–1023`, `>=1024`; order, widths/overflow, zone switching, focus trap/Escape/restoration, critical actions | Minimal route harness with controlled API fixtures; inspect DOM geometry and active element. Manual/local execution only. |

## Threat Matrix

| Boundary | Applicability | Safe/failure behavior | Planned RED test |
|---|---|---|---|
| Documentation-like paths | N/A — no executable-file classification | None | None |
| Git repository selection | N/A — no VCS automation | None | None |
| Commit state | N/A — no commit automation | None | None |
| Push state | N/A — no push automation | None | None |
| PR commands | N/A — no PR automation | None | None |

## Migration / Rollout

No data migration or feature flag. Ship the additive list seam with authorization and a fixed bound before enabling the navigator. Roll back by reverting the UI/API/story commits; existing create/read/send/stream behavior remains usable. If the list endpoint is unavailable, render a truthful unavailable navigator state rather than fabricate entries.

## Risks

- Missing or incomplete list data can block the left zone; fail closed with an explicit state.
- Focus/resize interactions can hide approval, retry, send, or emergency controls; Playwright must cover each tier.
- SSE and WebSocket events can imply completion; persisted reload remains authoritative.
- Capability metadata may include writable tools; inspector must remain informational.
- No CI Playwright gate means local evidence must be reported separately from Vitest/build evidence.

## Open Questions

- [ ] Confirm the bounded list maximum and title/preview derivation from the existing model/serializer.
- [ ] Confirm the local Playwright startup command without adding CI infrastructure.

## Graph Check Consulted

`domain/AppShell.tsx --imports_from--> domain/PanelShell.tsx`; `api.ts --imports_from--> types.ts`; `AgentChat()` connected to `chat.py` through the recorded six-hop graph path; `ConversationThread.test.tsx → pages/ConversationThread.tsx → Avatar.tsx ← stories/pages/InboxThread.stories.tsx`. Query communities included `AgentChat.tsx`, `domain/PanelShell.tsx`, `chat.py`, `types.ts`, `InternalChatThread`, `InternalChatMessage`, and `ConversationThread`.

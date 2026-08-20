# Proposal: Panel H2/H4 UI Advance (Inbox + Chat)

## Intent

Advance Storybook UI for reply-from-panel (inbox) and chat-with-agent while client Meta/OpenAI credentials are pending. Human inbox is a MUST: the Cloud API number cannot also live in the WhatsApp app. H1's `ConversationThread` stays untouched. Additive, Storybook-only; consumed by H2 (inbox) and H4 (§4.9).

## Scope

### In Scope
- **B1 inbox**: extend `ConversationsList.stories.tsx` (StatusBadge state column, assignee column from users mock, filter by state) + new `InboxThread.stories.tsx` (bubbles, Textarea+Button composer, 24h-window FlashMessage, state controls Tomar→human / Cerrar→closed / Volver a bot; variants ComposerEnabled/Disabled/OutsideWindow).
- **B2 chat**: new `ChatWithAgent.stories.tsx` — PageHeader, bubbles, Avatar, AgentStatus (idle/processing), suggestion chips, composer; new `AgentChatMessage` + `AgentStatus` mocks.
- **Mock fixes**: `"open"`→`bot` (conv 101), add bot + stale (>24h) conversations, outbound human-reply row, assignee users mock.
- **Tests**: 3 new `.test.tsx` (InboxThread, ChatWithAgent, mock) + ConversationsList tests.

### Out of Scope
- Backend endpoints (incl. GET /conversations gap — tracked separately); production wiring (H2 inbox, H4 chat, real credentials).
- Edits to `web/src/components/**`, `.storybook/main.ts`, `app/`/`db/`/`infra/`.

## Capabilities

- **New — `panel-h2-advance`**: Storybook UI for H2 human-inbox and H4 chat-with-agent, page-first per R-PRD-PG-1..7.
- **Modified — `panel-design-system`**: corrects the shipped mock's invalid `"open"` state to the serializable `bot|human|closed` domain; no component change.

## Approach

Page-first, additive, zero new primitives: reuse `_shared/` helpers (DataTable, PageHeader, FlashMessage, toneMaps); composer/chips from Textarea+Button + tokens (ConversationThreadBubbles pattern). Mocks serializer-faithful (snake_case, ISO dates, valid domains). Tests: excludeStories render + RTL; mock `.test.ts` pins shape fidelity. Auto-chain, ≤400 lines/PR.

## Product Assumptions & Constraints

- **S1** Bandeja: all conversations by state; human-state highlighted for replying.
- **S2** Pausa de bot: →human pauses bot in that thread (UI-level; real state H2).
- **S3** Ventana 24h: open/closed notice; closed disables send (template-only).
- **S4** Chat alcance: operational + automations (services today, clients, KPIs, create automation).
- **S5** Chat datos: agent sees real system data.
- **R1** Fix invalid `"open"` mock → bot/human/closed.
- **R2** Assignee is design mock (no backend field).
- **R3** Dedicated `AgentChatMessage`, not WhatsApp Conversation.
- **R4** H1 `ConversationThread` untouched; new `InboxThread`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `ConversationsList.stories.tsx` | Modified | State/assignee columns, filter variant |
| `InboxThread.stories.tsx` | New | Inbox + composer + 24h window |
| `ChatWithAgent.stories.tsx` | New | Chat-with-agent page story |
| `_shared/mockData/conversations.ts` | Modified | `"open"`→`bot`, bot/stale rows, human reply |
| `_shared/mockData/chat.ts` | New | `AgentChatMessage` + `AgentStatus` mocks (+test) |
| `_shared/mockData/users.ts` | New | Assignee user refs (+test) |
| `.test.tsx` companions | New/Mod | InboxThread, ChatWithAgent, mock, ConversationsList |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Invalid `"open"` mock shipped H1 | Confirmed | Correct to `bot`; test pins domain |
| Assignee derived, no field | Med | R2 records; H2 adds real field |
| 24h window UI-only today | Med | S3 UI-level; H2 enforces |
| `AgentChatMessage` new shape | Med | Dedicated mock (R3); confirm H4 in spec |
| Zero new primitives | Low | Textarea+Button+tokens |

## Rollback Plan

All additive: delete new `.stories.tsx`/`.test.tsx`/`chat.ts`/`users.ts` and revert the two edits (ConversationsList story, conversations mock). No component/layout change → trivially safe backout.

## Dependencies

- None external. Consumes `panel-design-system` R-PRD-PG-1..7 + shipped `_shared/` helpers.

## Success Criteria

- [ ] 2 new page stories render; build-storybook index green.
- [ ] `npm test` green incl. 3 new files + mock corrections.
- [ ] No `web/src/components/**` nor `.storybook/main.ts` edits.
- [ ] No `"open"` state remains in any mock.

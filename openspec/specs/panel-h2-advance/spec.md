# Delta for panel-h2-advance

New Storybook-only capability: H2 human inbox + H4 chat-with-agent, page-first (R-PRD-PG-1..7). No component, `.storybook/main.ts`, or CSS changes.

## ADDED Requirements

### Requirement: R-PRD-PG-8 — Inbox List: State, Assignee & Filter

`ConversationsList.stories.tsx` SHALL render a state column via `StatusBadge` (bot/human/closed tones), an assignee column from the `users` mock (design-only, R2 — no `Conversation` field), and SHALL expose a filter-by-state control. Every mock conversation SHALL carry a valid `bot|human|closed` state; human rows SHALL be highlighted (S1).

#### Scenario: Columns and highlight render

- GIVEN the ConversationsList story
- WHEN it renders with mocked conversations
- THEN each row shows a `StatusBadge` state and assignee, and human rows are highlighted

#### Scenario: Filter narrows rows

- GIVEN conversations spanning all three states
- WHEN a user filters by `human`
- THEN only human-state conversations remain listed

### Requirement: R-PRD-PG-9 — Inbox Thread Composer & State Controls

`InboxThread.stories.tsx` SHALL render message bubbles (ConversationThreadBubbles pattern), a composer from `Textarea`+`Button`, and state controls: take (→ human, pauses bot S2), close (→ closed), return to bot (→ bot). H1 `ConversationThread` MUST stay untouched (R4).

#### Scenario: Composer enabled

- GIVEN an open in-window thread
- WHEN it renders
- THEN the composer shows an enabled Textarea and send Button

#### Scenario: State controls switch state

- GIVEN a thread currently in bot state
- WHEN "Tomar" (→ human) is selected
- THEN state updates to human, and "Volver a bot" and "Cerrar" (→ closed) appear

### Requirement: R-PRD-PG-10 — 24-Hour Reply Window

The inbox thread SHALL show an open/closed window notice (FlashMessage) from the 24h window on `last_message_at`. When closed (stale > 24h), the send Button MUST be disabled (template-only, S3); stale/bot/paused threads SHALL support `ComposerDisabled`.

#### Scenario: Open window

- GIVEN `last_message_at` within 24 hours
- WHEN the thread renders
- THEN an open-window notice shows and send Button is enabled

#### Scenario: Outside window disables send

- GIVEN `last_message_at` older than 24 hours
- WHEN the thread renders
- THEN the send Button is disabled and a closed-window notice is shown

### Requirement: R-PRD-PG-11 — Chat With Agent Page

`ChatWithAgent.stories.tsx` SHALL render a PageHeader, bubble list, per-message `Avatar`, `AgentStatus` (idle/processing), suggestion chips, and a composer from `Textarea`+`Button`. `AgentThinking` SHALL show processing and a disabled composer.

#### Scenario: Default idle + chips

- GIVEN the ChatWithAgent Default variant
- WHEN it renders
- THEN header, message list with avatars, idle status, chips, and an enabled composer appear

#### Scenario: Agent thinking disables input

- GIVEN the AgentThinking variant
- WHEN it renders
- THEN status shows processing and the composer is disabled

### Requirement: R-PRD-PG-12 — Dedicated Chat & Assignee Mock Shapes

`_shared/mockData/chat.ts` SHALL define a dedicated `AgentChatMessage` (`{ id, role: 'admin'|'agent', text, created_at }`) and an `AgentStatus` mock (S4/S5), SHALL NOT reuse WhatsApp `Conversation`/`Message` (R3). `_shared/mockData/users.ts` SHALL provide assignee `UserRef` rows (R2). Each mock SHALL ship an `.test.ts` pinning fidelity and valid domains.

#### Scenario: Chat mock shape fidelity

- GIVEN the `chat.ts` mock
- WHEN its test runs
- THEN every `AgentChatMessage` matches the shape and `AgentStatus` covers idle/processing

#### Scenario: No "open" state remains

- GIVEN all conversation mocks
- WHEN the test iterates every state
- THEN every value is within `bot|human|closed`, no `"open"`

### Requirement: R-PRD-PG-13 — Verification Gates & Boundary Guards

The change MUST keep `npm test` green, `npx tsc -b` clean, and `npm run build-storybook` green, incl. new `.test.tsx` suites. The diff MUST NOT modify `web/src/components/**`, `.storybook/main.ts`, or add CSS; it MUST NOT add backend endpoints or production wiring.

#### Scenario: Tests, typecheck, and build green

- GIVEN the applied change
- WHEN `npm test`, `npx tsc -b`, and `npm run build-storybook` run in `web/`
- THEN all three succeed and the index includes InboxThread and ChatWithAgent

#### Scenario: Boundary respected

- GIVEN the diff
- WHEN it is reviewed
- THEN no file under `web/src/components/**`, `.storybook/main.ts`, app/db/infra, or CSS is modified

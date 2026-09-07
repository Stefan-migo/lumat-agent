# Delta for human-handoff

## MODIFIED Requirements

### Requirement: HH-1 — Per-Conversation State Model

The system MUST track each conversation's state as `bot`, `human`, or `closed` in the database. Transitions MUST be recorded with timestamp and cause (escalation trigger, human takeover, closure), and an escalation transition MUST persist the approved `escalation` activity in the existing `ConversationEvent` model.
(Previously: state transitions were recorded but had no required realtime activity record.)

#### Scenario: Bot to human
- GIVEN an escalation trigger fires
- WHEN the handoff is initiated
- THEN the conversation state changes to `human` and the transition is recorded
- AND one `escalation` activity is persisted

#### Scenario: Close conversation
- GIVEN a case is resolved
- WHEN the owner/operador closes it
- THEN the state becomes `closed` and the closure is recorded

## ADDED Requirements

### Requirement: HH-6 — State Change Publication

After a state transition commits, the system MUST publish a typed `conversation` event to connected authorized panel clients. Publication MUST be best-effort and MUST NOT make the state transition fail.

#### Scenario: Connected panel receives handoff
- GIVEN an authorized panel client is connected
- WHEN a bot conversation transitions to human
- THEN a `conversation` event identifies the conversation and human state

#### Scenario: No connected client
- GIVEN no panel client is connected
- WHEN a transition commits
- THEN the transition remains persisted and the command succeeds
